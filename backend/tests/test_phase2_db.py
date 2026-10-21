"""
Phase 2: Database Schema & Core Data Model Implementation (SQLite)
Tests idempotency, schema tables, columns, indexes, foreign keys, cascade, CRUD,
audit logging, transaction rollback, duplicate detection, and enum enforcement.
"""
import pytest
import os
import tempfile
import sqlite3
import aiosqlite
from pydantic import ValidationError

from app.database import init_db, get_db
from app.config import settings
from app.models import (
    SourceCreate, SourceType,
    DeadlineCreate, DeadlineUpdate,
    DeadlineCategory, ObligationType, DeadlineStatus, VerificationStatus, RecurrenceType
)
from app.services.deadline_service import DeadlineService


@pytest.fixture
async def temp_db_path():
    fd, path = tempfile.mkstemp(suffix="_phase2.db")
    os.close(fd)
    old_db_path = settings.db_path
    settings.db_path = path
    await init_db(path)
    yield path
    settings.db_path = old_db_path
    if os.path.exists(path):
        os.remove(path)


@pytest.mark.asyncio
async def test_db_initialization_idempotency(temp_db_path):
    """Confirm DB initializes and running initialization twice is idempotent."""
    # Run second time
    await init_db(temp_db_path)
    
    # Check tables count
    async with get_db(temp_db_path) as db:
        async with db.execute("SELECT count(*) as count FROM sqlite_master WHERE type='table'") as cur:
            row = await cur.fetchone()
            # Expect 4 domain tables + sqlite internal tables
            assert row["count"] >= 4


@pytest.mark.asyncio
async def test_schema_tables_and_columns(temp_db_path):
    """Confirm the four tables (sources, deadlines, reminders, audit_logs) exist with expected columns."""
    expected_tables = {
        "sources": {"id", "title", "raw_text", "source_type", "file_hash", "created_at"},
        "deadlines": {
            "id", "source_id", "provider_name", "category", "obligation_type",
            "candidate_date", "original_date_str", "amount", "currency",
            "evidence_snippet", "evidence_char_start", "evidence_char_end",
            "extraction_confidence", "verification_status", "recurrence",
            "official_url", "next_step_instructions", "status", "owner",
            "created_at", "updated_at"
        },
        "reminders": {"id", "deadline_id", "remind_at", "lead_days", "status", "created_at"},
        "audit_logs": {"id", "deadline_id", "action", "previous_value", "new_value", "timestamp"}
    }

    async with get_db(temp_db_path) as db:
        for tbl_name, expected_cols in expected_tables.items():
            async with db.execute(f"PRAGMA table_info({tbl_name})") as cur:
                rows = await cur.fetchall()
                col_names = {r["name"] for r in rows}
                assert col_names == expected_cols, f"Mismatch in {tbl_name} columns: {col_names ^ expected_cols}"


@pytest.mark.asyncio
async def test_schema_indexes_exist(temp_db_path):
    """Confirm indexes exist on deadlines.status, deadlines.candidate_date, deadlines.source_id, etc."""
    expected_indexes = {
        "idx_deadlines_status",
        "idx_deadlines_date",
        "idx_deadlines_source",
        "idx_reminders_deadline",
        "idx_audit_deadline"
    }
    async with get_db(temp_db_path) as db:
        async with db.execute("SELECT name FROM sqlite_master WHERE type='index'") as cur:
            rows = await cur.fetchall()
            found_indexes = {r["name"] for r in rows}
            for idx in expected_indexes:
                assert idx in found_indexes, f"Expected index {idx} not found in {found_indexes}"


@pytest.mark.asyncio
async def test_foreign_keys_enforced(temp_db_path):
    """Confirm foreign keys are enforced (insert a deadline with a non-existent source_id; it must fail)."""
    async with get_db(temp_db_path) as db:
        with pytest.raises(Exception) as exc_info:
            await db.execute(
                """
                INSERT INTO deadlines (
                    id, source_id, provider_name, category, obligation_type,
                    candidate_date, evidence_snippet, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ("d-fake", "non-existent-source", "Netflix", "subscription", "trial_ending", "2026-10-20", "evidence", "needs_review")
            )
            await db.commit()
        assert "FOREIGN KEY constraint failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_crud_and_audit_trail(temp_db_path):
    """CRUD: insert source, create candidate, update status, verify audit_logs row with previous_value and new_value."""
    # 1. Insert source
    source = await DeadlineService.create_source(
        SourceCreate(title="Test Source", raw_text="Trial ends 2026-10-20", source_type=SourceType.EMAIL, file_hash="hash123"),
        db_path=temp_db_path
    )
    assert source.id is not None

    # 2. Create candidate deadline
    deadline = await DeadlineService.create_deadline(
        DeadlineCreate(
            source_id=source.id,
            provider_name="Netflix",
            category=DeadlineCategory.SUBSCRIPTION,
            obligation_type=ObligationType.TRIAL_ENDING,
            candidate_date="2026-10-20",
            evidence_snippet="Trial ends 2026-10-20",
            status=DeadlineStatus.NEEDS_REVIEW
        ),
        db_path=temp_db_path
    )
    assert deadline.id is not None

    # 3. Update status to confirmed
    updated = await DeadlineService.update_deadline(
        deadline.id,
        DeadlineUpdate(status=DeadlineStatus.CONFIRMED),
        db_path=temp_db_path
    )
    assert updated.status == DeadlineStatus.CONFIRMED

    # 4. Check audit log
    audit_logs = await DeadlineService.get_audit_logs(deadline.id, db_path=temp_db_path)
    assert len(audit_logs) >= 2  # 1 extraction + 1 status_changed
    status_change_log = next((l for l in audit_logs if l.action == "status_changed"), None)
    assert status_change_log is not None
    assert "needs_review" in status_change_log.previous_value
    assert "confirmed" in status_change_log.new_value


@pytest.mark.asyncio
async def test_transaction_rollback_on_error(temp_db_path):
    """Rollback: force an error mid-transaction and verify no partial writes persist."""
    async with get_db(temp_db_path) as db:
        await db.execute("BEGIN TRANSACTION")
        await db.execute(
            "INSERT INTO sources (id, title, raw_text, source_type, created_at) VALUES (?, ?, ?, ?, ?)",
            ("rollback-src-1", "Rollback Test", "Text content", "manual", "2026-10-15T00:00:00Z")
        )
        # Force mid-transaction error by syntax error or constraint violation
        try:
            await db.execute("INSERT INTO non_existent_table VALUES (1, 2, 3)")
            await db.commit()
        except Exception:
            await db.rollback()

    # Verify no partial write persisted
    async with get_db(temp_db_path) as db:
        async with db.execute("SELECT * FROM sources WHERE id = ?", ("rollback-src-1",)) as cur:
            row = await cur.fetchone()
            assert row is None, "Partial write persisted despite transaction rollback!"


@pytest.mark.asyncio
async def test_duplicate_source_detection_via_file_hash(temp_db_path):
    """
    Duplicate protection: ingesting identical raw_text twice must be detected via file_hash (SHA-256).
    Checks whether duplicate source ingestion is prevented or if multiple rows are created.
    """
    raw_text = "Your 14-day free trial ends on October 20."
    source_in = SourceCreate(
        title="Duplicate Test 1",
        raw_text=raw_text,
        source_type=SourceType.EMAIL,
        file_hash="sha256_identical_hash_1"
    )
    src1 = await DeadlineService.create_source(source_in, db_path=temp_db_path)

    # Ingest identical raw_text with identical hash
    source_in_2 = SourceCreate(
        title="Duplicate Test 2",
        raw_text=raw_text,
        source_type=SourceType.EMAIL,
        file_hash="sha256_identical_hash_1"
    )
    src2 = await DeadlineService.create_source(source_in_2, db_path=temp_db_path)

    async with get_db(temp_db_path) as db:
        async with db.execute("SELECT count(*) as count FROM sources WHERE file_hash = ?", ("sha256_identical_hash_1",)) as cur:
            row = await cur.fetchone()
            # If the database enforces duplicate protection, count should be 1.
            # If count == 2, duplicate protection is NOT enforced in SQLite or service layer.
            assert row["count"] == 1, (
                f"Duplicate protection failed: found {row['count']} rows for identical file_hash! "
                "The database allowed inserting duplicate source without deduplication."
            )


@pytest.mark.asyncio
async def test_enum_constraints_rejected_in_pydantic():
    """Confirm Pydantic models and Enums reject invalid values for status, verification_status, obligation_type, category, source_type."""
    with pytest.raises((ValueError, ValidationError)):
        DeadlineCategory("invalid_category")

    with pytest.raises((ValueError, ValidationError)):
        ObligationType("invalid_obligation")

    with pytest.raises((ValueError, ValidationError)):
        VerificationStatus("invalid_verification")

    with pytest.raises((ValueError, ValidationError)):
        DeadlineStatus("invalid_status")

    with pytest.raises((ValueError, ValidationError)):
        SourceType("invalid_source_type")


@pytest.mark.asyncio
async def test_enum_constraints_enforced_in_sqlite_ddl(temp_db_path):
    """
    Confirm whether SQLite schema enforces CHECK constraints for invalid enum values on raw SQL insert.
    """
    source = await DeadlineService.create_source(
        SourceCreate(title="Enum Check Source", raw_text="Some text", source_type=SourceType.MANUAL),
        db_path=temp_db_path
    )

    async with get_db(temp_db_path) as db:
        with pytest.raises(Exception) as exc_info:
            await db.execute(
                """
                INSERT INTO deadlines (
                    id, source_id, provider_name, category, obligation_type,
                    candidate_date, evidence_snippet, status, verification_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "d-invalid-enum", source.id, "Test", "INVALID_CAT", "INVALID_OBLIG",
                    "2026-10-20", "evidence", "INVALID_STATUS", "INVALID_VERIF"
                )
            )
            await db.commit()
        assert "CHECK constraint failed" in str(exc_info.value), (
            "SQLite schema does NOT define CHECK constraints on enum columns! "
            "Raw SQL was able to insert invalid enum values."
        )
