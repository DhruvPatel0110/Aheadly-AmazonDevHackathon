"""
Comprehensive Stress & Edge-Case Audit for Phases 1 to 3.
Tests edge cases, boundary conditions, data integrity, and potential failure modes.
"""
import pytest
import os
import io
import tempfile
from datetime import datetime, timezone
from pypdf import PdfWriter

from app.database import init_db, get_db
from app.models import (
    SourceCreate, SourceType,
    DeadlineCreate, DeadlineUpdate, DeadlineCategory, ObligationType,
    DeadlineStatus, VerificationStatus, RecurrenceType
)
from app.services.deadline_service import DeadlineService
from app.parsers.text_parser import parse_text_input, hash_content
from app.parsers.email_parser import parse_email_input, strip_html
from app.parsers.pdf_parser import parse_pdf_input, ScannedPdfError
from app.engine.date_extractor import (
    find_candidate_dates,
    normalize_parsed_date,
    extract_evidence_sentence
)
from app.engine.category_rules import (
    detect_provider,
    classify_obligation,
    extract_amount_and_currency
)
from app.engine.obligation_classifier import AnalysisEngine


@pytest.fixture
async def audit_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    await init_db(path)
    yield path
    if os.path.exists(path):
        os.remove(path)


# ---------------------------------------------------------------------------
# 1. DATABASE & PERSISTENCE INTEGRITY TESTS
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_foreign_key_cascade_deletion(audit_db):
    """Verify CASCADE deletion: deleting a source or deadline must delete associated rows."""
    source = await DeadlineService.create_source(
        SourceCreate(title="Cascade Test", raw_text="Trial ends 2026-10-25"),
        db_path=audit_db
    )
    deadline = await DeadlineService.create_deadline(
        DeadlineCreate(
            source_id=source.id,
            provider_name="Test Provider",
            candidate_date="2026-10-25",
            evidence_snippet="Trial ends 2026-10-25"
        ),
        db_path=audit_db
    )
    await DeadlineService.create_reminders(deadline.id, lead_days=[7, 1], db_path=audit_db)

    # Verify rows exist
    reminders = await DeadlineService.get_reminders(deadline.id, db_path=audit_db)
    assert len(reminders) == 2
    audits = await DeadlineService.get_audit_logs(deadline.id, db_path=audit_db)
    assert len(audits) >= 2

    # Delete the deadline
    deleted = await DeadlineService.delete_deadline(deadline.id, db_path=audit_db)
    assert deleted is True

    # Check cascading deletion on reminders and audit logs
    reminders_after = await DeadlineService.get_reminders(deadline.id, db_path=audit_db)
    assert len(reminders_after) == 0
    audits_after = await DeadlineService.get_audit_logs(deadline.id, db_path=audit_db)
    assert len(audits_after) == 0


@pytest.mark.asyncio
async def test_invalid_uuid_and_nonexistent_lookups(audit_db):
    """Verify system handles non-existent lookups gracefully without throwing unhandled exceptions."""
    non_existent = "non-existent-uuid-12345"
    src = await DeadlineService.get_source(non_existent, db_path=audit_db)
    assert src is None

    dl = await DeadlineService.get_deadline(non_existent, db_path=audit_db)
    assert dl is None

    # Update non-existent returns None
    res = await DeadlineService.update_deadline(non_existent, DeadlineUpdate(status=DeadlineStatus.CONFIRMED), db_path=audit_db)
    assert res is None

    # Delete non-existent returns False
    res_del = await DeadlineService.delete_deadline(non_existent, db_path=audit_db)
    assert res_del is False

    # Creating reminders for non-existent deadline raises ValueError
    with pytest.raises(ValueError):
        await DeadlineService.create_reminders(non_existent, lead_days=[1], db_path=audit_db)


@pytest.mark.asyncio
async def test_update_with_empty_or_unchanged_fields(audit_db):
    """Verify updating with empty payload does not corrupt data or produce false audit logs."""
    source = await DeadlineService.create_source(
        SourceCreate(title="Unchanged Test", raw_text="Bill due 2026-10-30"),
        db_path=audit_db
    )
    deadline = await DeadlineService.create_deadline(
        DeadlineCreate(
            source_id=source.id,
            provider_name="Original Name",
            candidate_date="2026-10-30",
            evidence_snippet="Bill due 2026-10-30"
        ),
        db_path=audit_db
    )

    initial_audits = await DeadlineService.get_audit_logs(deadline.id, db_path=audit_db)
    assert len(initial_audits) == 1

    # Empty update
    updated = await DeadlineService.update_deadline(deadline.id, DeadlineUpdate(), db_path=audit_db)
    assert updated.provider_name == "Original Name"

    # Audits count should remain unchanged
    audits_after = await DeadlineService.get_audit_logs(deadline.id, db_path=audit_db)
    assert len(audits_after) == 1


# ---------------------------------------------------------------------------
# 2. PARSER ROBUSTNESS & EDGE CASES
# ---------------------------------------------------------------------------

def test_text_parser_edge_cases():
    """Verify text parser handles unicode, emojis, multiline titles, and whitespace variations."""
    # Unicode and emojis
    raw = "Subject: Electricity Bill ⚡💡\n\nAmount due is ₹ 500 on 2026-10-25."
    parsed = parse_text_input(raw)
    assert "⚡💡" in parsed["title"]
    assert parsed["clean_text"].startswith("Subject:")

    # Long text with multiple newlines
    long_raw = "\n\n   \n   Subject: Broadband Payment   \n\nBody line 1\nBody line 2\n\n"
    long_parsed = parse_text_input(long_raw)
    assert long_parsed["title"] == "Broadband Payment"


def test_email_parser_edge_cases():
    """Verify email parser handles multipart with attachments, missing subject, encoded characters."""
    # Email with no subject
    no_subj = "From: alerts@jio.com\r\n\r\nYour validity expires on 2026-10-22."
    parsed = parse_email_input(no_subj, default_title="Fallback Title")
    assert parsed["title"] == "Fallback Title"
    assert "From: alerts@jio.com" in parsed["clean_text"]

    # Complex HTML with nested tags and entities
    html_email = (
        "Subject: Amazon Prime Renewal\r\n"
        "Content-Type: text/html\r\n\r\n"
        "<div><p>Your membership will renew on &nbsp;<b>2026-11-01</b>.</p>"
        "<script>console.log('ignore');</script>"
        "<a href='https://amazon.in'>Click here</a></div>"
    )
    parsed_html = parse_email_input(html_email)
    assert "2026-11-01" in parsed_html["clean_text"]
    assert "<script>" not in parsed_html["clean_text"]


def test_pdf_parser_with_valid_and_corrupt_files():
    """Verify PDF parser with generated in-memory PDF and corrupted input."""
    # 1. Create a genuine PDF in memory with PyPDF
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    # Empty page should trigger ScannedPdfError because full_text < 25 chars
    buf = io.BytesIO()
    writer.write(buf)
    with pytest.raises(ScannedPdfError):
        parse_pdf_input(buf.getvalue())

    # 2. Zero-byte or truncated PDF raises ValueError
    with pytest.raises(ValueError):
        parse_pdf_input(b"%PDF-1.4 truncate")


# ---------------------------------------------------------------------------
# 3. DATE EXTRACTOR BOUNDARY & FORMAT TESTS
# ---------------------------------------------------------------------------

def test_date_extractor_boundary_conditions():
    """Test date at exact start and end of strings, punctuation immediately touching date."""
    # Date at very beginning of string (index 0)
    text_start = "2026-10-25 is your last day of free trial."
    cands_start = find_candidate_dates(text_start)
    assert len(cands_start) >= 1
    assert cands_start[0]["candidate_date"] == "2026-10-25"
    assert cands_start[0]["evidence_char_start"] == 0

    # Date at very end of string with trailing period
    text_end = "Your plan validity will expire on 2026-11-30."
    cands_end = find_candidate_dates(text_end)
    assert len(cands_end) >= 1
    assert cands_end[0]["candidate_date"] == "2026-11-30"

    # Date with commas and parentheses: "(due: 15/12/2026)"
    text_paren = "Broadband invoice (due: 15/12/2026) ready for review."
    cands_paren = find_candidate_dates(text_paren)
    assert len(cands_paren) >= 1
    assert cands_paren[0]["candidate_date"] == "2026-12-15"


def test_date_normalization_variations():
    """Verify various human date formats normalize to identical ISO YYYY-MM-DD."""
    assert normalize_parsed_date("2026-10-20") == "2026-10-20"
    assert normalize_parsed_date("20/10/2026") == "2026-10-20"
    assert normalize_parsed_date("20-10-2026") == "2026-10-20"
    assert normalize_parsed_date("20th October 2026") == "2026-10-20"
    assert normalize_parsed_date("October 20, 2026") == "2026-10-20"
    assert normalize_parsed_date("20-Oct-2026") == "2026-10-20"


def test_multiple_dates_in_single_document():
    """Verify handling when document contains bill generation date AND bill due date."""
    text = (
        "Bill Date: 2026-10-01. "
        "Due Date: 2026-10-20. "
        "Late payment charges of INR 100 apply if paid after due date."
    )
    candidates = AnalysisEngine.extract_obligations(text)
    assert len(candidates) >= 1
    # The anchored "Due Date" should be prioritized or present
    due_cand = next((c for c in candidates if c["candidate_date"] == "2026-10-20"), None)
    assert due_cand is not None
    assert due_cand["extraction_confidence"] >= 0.90


# ---------------------------------------------------------------------------
# 4. OBLIGATION CLASSIFICATION & AMOUNT PARSING
# ---------------------------------------------------------------------------

def test_indian_lakh_and_comma_amounts():
    """Verify Indian numbering format (e.g. 1,50,000 or 14,250) and currency signs."""
    amt1, curr1 = extract_amount_and_currency("Total vehicle insurance premium is ₹ 1,50,000 for fleet.")
    assert amt1 == 150000.0
    assert curr1 == "INR"

    amt2, curr2 = extract_amount_and_currency("Monthly Wi-Fi charges: INR 1,299.00.")
    assert amt2 == 1299.0
    assert curr2 == "INR"

    amt3, curr3 = extract_amount_and_currency("SaaS plan billed at $29.99 / mo.")
    assert amt3 == 29.99
    assert curr3 == "USD"


def test_vague_expression_does_not_override_real_date():
    """If document contains BOTH a real due date AND a vague phrase like 'sometime this month', the real date must be prioritized."""
    text = (
        "We noticed you were asking about your bill sometime this month. "
        "Your official electricity bill due date is 2026-10-28 for INR 1800."
    )
    results = AnalysisEngine.extract_obligations(text)
    assert len(results) >= 1
    # Must capture the concrete due date
    assert any(c["candidate_date"] == "2026-10-28" for c in results)
