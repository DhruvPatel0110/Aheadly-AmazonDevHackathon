"""
Unit tests for SQLite database schema, CRUD operations, and audit logs.
"""
import pytest
import os
import tempfile
from app.database import init_db
from app.models import (
    SourceCreate, SourceType,
    DeadlineCreate, DeadlineUpdate,
    DeadlineCategory, ObligationType, DeadlineStatus, VerificationStatus, RecurrenceType
)
from app.services.deadline_service import DeadlineService


@pytest.fixture
async def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    await init_db(path)
    yield path
    if os.path.exists(path):
        os.remove(path)


@pytest.mark.asyncio
async def test_source_creation_and_retrieval(temp_db):
    source_in = SourceCreate(
        title="Netflix Trial Notice",
        raw_text="Your 14-day free trial ends on October 20.",
        source_type=SourceType.EMAIL,
        file_hash="abc123hash"
    )
    source = await DeadlineService.create_source(source_in, db_path=temp_db)
    assert source.id is not None
    assert source.title == "Netflix Trial Notice"

    fetched = await DeadlineService.get_source(source.id, db_path=temp_db)
    assert fetched is not None
    assert fetched.title == source.title
    assert fetched.raw_text == source.raw_text
    assert fetched.source_type == SourceType.EMAIL


@pytest.mark.asyncio
async def test_deadline_creation_and_audit(temp_db):
    source = await DeadlineService.create_source(
        SourceCreate(title="Test Bill", raw_text="Broadband bill due on 2026-11-15 for INR 999"),
        db_path=temp_db
    )

    deadline_in = DeadlineCreate(
        source_id=source.id,
        provider_name="Airtel Broadband",
        category=DeadlineCategory.BROADBAND,
        obligation_type=ObligationType.PAYMENT_DUE,
        candidate_date="2026-11-15",
        original_date_str="15th Nov 2026",
        amount=999.0,
        currency="INR",
        evidence_snippet="Broadband bill due on 2026-11-15 for INR 999",
        extraction_confidence=0.95,
        verification_status=VerificationStatus.SOURCE_STATED,
        recurrence=RecurrenceType.MONTHLY,
        status=DeadlineStatus.NEEDS_REVIEW
    )

    deadline = await DeadlineService.create_deadline(deadline_in, db_path=temp_db)
    assert deadline.id is not None
    assert deadline.provider_name == "Airtel Broadband"
    assert deadline.amount == 999.0

    # Verify audit log was recorded
    audit_logs = await DeadlineService.get_audit_logs(deadline.id, db_path=temp_db)
    assert len(audit_logs) == 1
    assert audit_logs[0].action == "extracted"


@pytest.mark.asyncio
async def test_deadline_update_and_status_audit(temp_db):
    source = await DeadlineService.create_source(
        SourceCreate(title="Policy", raw_text="Insurance due 2026-12-01"),
        db_path=temp_db
    )
    deadline = await DeadlineService.create_deadline(
        DeadlineCreate(
            source_id=source.id,
            provider_name="HDFC ERGO",
            category=DeadlineCategory.INSURANCE,
            obligation_type=ObligationType.RENEWAL,
            candidate_date="2026-12-01",
            evidence_snippet="Insurance due 2026-12-01",
            status=DeadlineStatus.NEEDS_REVIEW
        ),
        db_path=temp_db
    )

    # Confirm the deadline and update provider name
    updated = await DeadlineService.update_deadline(
        deadline.id,
        DeadlineUpdate(
            provider_name="HDFC ERGO General Insurance",
            status=DeadlineStatus.CONFIRMED,
            verification_status=VerificationStatus.USER_CONFIRMED
        ),
        db_path=temp_db
    )
    assert updated.provider_name == "HDFC ERGO General Insurance"
    assert updated.status == DeadlineStatus.CONFIRMED
    assert updated.verification_status == VerificationStatus.USER_CONFIRMED

    # Check audit log diffs
    audit_logs = await DeadlineService.get_audit_logs(deadline.id, db_path=temp_db)
    assert len(audit_logs) == 2
    latest_audit = audit_logs[0]
    assert latest_audit.action == "status_changed"


@pytest.mark.asyncio
async def test_reminders_and_calendar(temp_db):
    source = await DeadlineService.create_source(
        SourceCreate(title="Trial", raw_text="Ends 2026-10-25"),
        db_path=temp_db
    )
    deadline = await DeadlineService.create_deadline(
        DeadlineCreate(
            source_id=source.id,
            provider_name="Amazon Prime",
            candidate_date="2026-10-25",
            evidence_snippet="Ends 2026-10-25"
        ),
        db_path=temp_db
    )

    reminders = await DeadlineService.create_reminders(deadline.id, lead_days=[7, 1], db_path=temp_db)
    assert len(reminders) == 2
    assert reminders[0].lead_days == 7
    assert reminders[1].lead_days == 1

    fetched_reminders = await DeadlineService.get_reminders(deadline.id, db_path=temp_db)
    assert len(fetched_reminders) == 2


@pytest.mark.asyncio
async def test_filtering_and_stats(temp_db):
    source = await DeadlineService.create_source(
        SourceCreate(title="Multi-bills", raw_text="Various"),
        db_path=temp_db
    )
    await DeadlineService.create_deadline(
        DeadlineCreate(
            source_id=source.id,
            provider_name="Bill 1",
            category=DeadlineCategory.UTILITY,
            candidate_date="2026-10-20",
            evidence_snippet="Electricity",
            status=DeadlineStatus.NEEDS_REVIEW
        ),
        db_path=temp_db
    )
    await DeadlineService.create_deadline(
        DeadlineCreate(
            source_id=source.id,
            provider_name="Bill 2",
            category=DeadlineCategory.BROADBAND,
            candidate_date="2026-10-22",
            evidence_snippet="Internet",
            status=DeadlineStatus.UPCOMING
        ),
        db_path=temp_db
    )

    all_items = await DeadlineService.list_deadlines(db_path=temp_db)
    assert len(all_items) == 2

    filtered_utility = await DeadlineService.list_deadlines(category_filter="utility", db_path=temp_db)
    assert len(filtered_utility) == 1
    assert filtered_utility[0].provider_name == "Bill 1"

    stats = await DeadlineService.get_stats(db_path=temp_db)
    assert stats["total"] == 2
    assert stats["needs_review"] == 1
    assert stats["upcoming"] == 1
