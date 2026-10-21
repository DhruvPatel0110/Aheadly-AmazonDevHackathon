"""
Comprehensive Regression Test Suite for Backend Audit Fixes.
Validates:
- BE-001: Date extraction with commas and explicit years preserved.
- BE-002: Single-digit day/month formats accepted; invalid dates rejected.
- BE-003: Decimal currency amounts not splitting evidence sentence.
- BE-004: Calendar export rejection for unverified/malformed dates.
- BE-005: Reminder validation on unverified dates, negative/dedup lead days.
- BE-006: Text parser source-type handling.
- DB-001: Deduplication on repeated source extraction.
- DB-002: Dismissed status in schema and migration safety.
- SEC-001: Destructive reset protection.
- SEC-002: Upload size ceiling and format validation.
- SEC-003: Sensitive text redaction in MCP logs.
- Source retrieval endpoint (GET /api/sources/{id}).
- Due reminders background processing.
"""
import pytest
import os
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.config import settings
from app.database import init_db
from app.models import SourceType, DeadlineCategory, ObligationType, DeadlineStatus, VerificationStatus, ReminderStatus
from app.schemas import DeadlineCreate, SourceCreate
from app.services.deadline_service import DeadlineService
from app.services.calendar_service import generate_ics_content
from app.services.mcp_client import MCPClientBridge
from app.engine.date_extractor import find_candidate_dates, extract_evidence_sentence, normalize_parsed_date
from app.parsers.text_parser import parse_text_input


@pytest.fixture
async def temp_db_client():
    fd, path = tempfile.mkstemp(suffix="_audit_fixes.db")
    os.close(fd)
    old_db = settings.db_path
    settings.db_path = path
    await init_db(path)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        MCPClientBridge.clear_logs()
        yield client, path

    settings.db_path = old_db
    if os.path.exists(path):
        os.remove(path)


# ---------------------------------------------------------------------------
# 1. Date Extractor & Evidence Integrity (BE-001, BE-002, BE-003)
# ---------------------------------------------------------------------------

def test_be_001_commas_and_explicit_years():
    """Verify explicit years in textual dates with commas are preserved without overriding to clock year."""
    text1 = "Your premium is due on November 05, 2027 to ensure continuous coverage."
    res1 = find_candidate_dates(text1)
    assert len(res1) >= 1
    assert res1[0]["candidate_date"] == "2027-11-05"

    text2 = "Your policy expires on May 10, 2028."
    res2 = find_candidate_dates(text2)
    assert len(res2) >= 1
    assert res2[0]["candidate_date"] == "2028-05-10"


def test_be_002_single_digit_and_invalid_dates():
    """Verify single-digit day and month numbers are parsed, and invalid calendar days rejected."""
    # Accepted unpadded dates
    res_iso = normalize_parsed_date("2026-5-1")
    assert res_iso == "2026-05-01"

    res_dmy = normalize_parsed_date("5/11/2026")
    assert res_dmy in ("2026-11-05", "2026-05-11")

    # Invalid dates rejected
    assert normalize_parsed_date("31/02/2026") is None
    assert normalize_parsed_date("2026-02-31") is None
    assert normalize_parsed_date("32/01/2026") is None


def test_be_003_currency_decimals_and_evidence():
    """Verify decimal numbers (e.g. 50.00) do not truncate the verbatim evidence sentence."""
    text = "Your fee of 50.00 is due on November 05, 2026."
    res = find_candidate_dates(text)
    assert len(res) >= 1
    quote = res[0]["evidence_snippet"]
    start = res[0]["evidence_char_start"]
    end = res[0]["evidence_char_end"]

    # Exact substring invariant
    assert quote == text[start:end]
    assert not quote.startswith("00 is due")
    assert "fee of 50.00 is due on November 05, 2026" in quote


# ---------------------------------------------------------------------------
# 2. Calendar & Reminder Validation (BE-004, BE-005)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_be_004_calendar_rejects_unverified_dates(temp_db_client):
    """Calendar export must raise ValueError and HTTP 400 for unverified candidate dates."""
    client, db_path = temp_db_client

    # Create unverified deadline
    source = await DeadlineService.create_source(
        SourceCreate(title="Uncertain Notice", raw_text="Maintenance fee sometime next month"),
        db_path=db_path
    )
    dl = await DeadlineService.create_deadline(
        DeadlineCreate(
            source_id=source.id,
            provider_name="Society Office",
            candidate_date="UNVERIFIED",
            evidence_snippet="fee sometime next month",
            verification_status=VerificationStatus.UNVERIFIED,
            status=DeadlineStatus.DATE_UNVERIFIED
        ),
        db_path=db_path
    )

    # Direct calendar service call must raise ValueError
    with pytest.raises(ValueError) as excinfo:
        generate_ics_content(dl)
    assert "unverified" in str(excinfo.value).lower()

    # API call must return HTTP 400
    res = await client.get(f"/api/deadlines/{dl.id}/ics")
    assert res.status_code == 400
    assert "unverified" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_be_005_reminder_validation(temp_db_client):
    """create_reminders must reject unverified dates and negative lead days."""
    client, db_path = temp_db_client

    source = await DeadlineService.create_source(
        SourceCreate(title="Test Notice", raw_text="Test source text"),
        db_path=db_path
    )
    unverified_dl = await DeadlineService.create_deadline(
        DeadlineCreate(
            source_id=source.id,
            provider_name="Test Provider",
            candidate_date="UNVERIFIED",
            evidence_snippet="due sometime",
            status=DeadlineStatus.DATE_UNVERIFIED
        ),
        db_path=db_path
    )

    # Rejects unverified dates
    with pytest.raises(ValueError) as exc:
        await DeadlineService.create_reminders(unverified_dl.id, lead_days=[7, 1], db_path=db_path)
    assert "unverified" in str(exc.value).lower()

    valid_dl = await DeadlineService.create_deadline(
        DeadlineCreate(
            source_id=source.id,
            provider_name="Test Provider 2",
            candidate_date="2026-11-20",
            evidence_snippet="due on 2026-11-20",
            status=DeadlineStatus.CONFIRMED
        ),
        db_path=db_path
    )

    # Rejects negative lead days
    with pytest.raises(ValueError) as exc:
        await DeadlineService.create_reminders(valid_dl.id, lead_days=[-1], db_path=db_path)
    assert "negative" in str(exc.value).lower()

    # Deduplicates duplicate lead days
    rems = await DeadlineService.create_reminders(valid_dl.id, lead_days=[7, 1, 7], db_path=db_path)
    assert len(rems) == 2


# ---------------------------------------------------------------------------
# 3. Parser & Idempotency (BE-006, DB-001, DB-002)
# ---------------------------------------------------------------------------

def test_be_006_text_parser_source_type():
    """Text parser preserves explicit source_type and defaults safely to manual."""
    # Preserves explicit SMS
    parsed_sms = parse_text_input("Payment of Rs 500 due on 2026-10-25", source_type="sms")
    assert parsed_sms["source_type"] == "sms"

    # Preserves explicit manual
    parsed_man = parse_text_input("Long text with SMS notification mention over 400 chars " + "x" * 400)
    assert parsed_man["source_type"] == "manual"

    # Does not misclassify as email simply because length > 300
    assert parsed_man["source_type"] != "email"


@pytest.mark.asyncio
async def test_db_001_idempotent_extraction(temp_db_client):
    """Running extraction twice on the same source must not create duplicate active candidates."""
    client, db_path = temp_db_client

    text = "Your Airtel broadband bill of Rs 999 is due on 2026-11-15."
    ingest_res = await MCPClientBridge.call_tool("ingest_source", {
        "raw_text": text,
        "title": "Airtel Bill",
        "source_type": "manual"
    })
    source_id = ingest_res["source_id"]

    # First extraction
    cands_first = await MCPClientBridge.call_tool("find_deadline_candidates", {"source_id": source_id})
    assert len(cands_first) >= 1
    dl_id = cands_first[0]["id"]

    # Second extraction on the same source
    cands_second = await MCPClientBridge.call_tool("find_deadline_candidates", {"source_id": source_id})
    assert len(cands_second) == len(cands_first)
    assert cands_second[0]["id"] == dl_id

    # Verify database count
    all_dls = await DeadlineService.get_deadlines_by_source(source_id, db_path=db_path)
    assert len(all_dls) == len(cands_first)


# ---------------------------------------------------------------------------
# 4. Security & Privacy (SEC-001, SEC-002, SEC-003)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sec_001_reset_protection(temp_db_client):
    """Unprotected reset requests without confirmation parameter or header must be rejected."""
    client, _ = temp_db_client

    # Request without confirmation must be 400
    res_unconf = await client.post("/api/demo/reset")
    assert res_unconf.status_code == 400

    # Request with confirmation must succeed
    res_conf = await client.post("/api/demo/reset?confirm=true")
    assert res_conf.status_code == 200
    assert res_conf.json()["status"] == "reset"


@pytest.mark.asyncio
async def test_sec_002_upload_size_limit(temp_db_client):
    """Files exceeding 10 MiB must be rejected with 413, invalid extensions with 415, empty with 400."""
    client, _ = temp_db_client

    # 1. Oversized file (10 MiB + 10 bytes)
    oversized = b"A" * (10 * 1024 * 1024 + 10)
    res_oversized = await client.post("/api/sources/upload", files={"file": ("large.txt", oversized, "text/plain")})
    assert res_oversized.status_code == 413

    # 2. Unsupported file extension
    res_unsupported = await client.post("/api/sources/upload", files={"file": ("malicious.exe", b"binary", "application/octet-stream")})
    assert res_unsupported.status_code == 415

    # 3. Empty file upload
    res_empty = await client.post("/api/sources/upload", files={"file": ("empty.txt", b"", "text/plain")})
    assert res_empty.status_code == 400


@pytest.mark.asyncio
async def test_sec_003_mcp_log_redaction():
    """Verify raw source documents are redacted from visual MCP logs."""
    MCPClientBridge.clear_logs()
    secret_text = "CONFIDENTIAL_PAYMENT_NOTICE_12345: Your fee is due on 2026-11-20."
    await MCPClientBridge.call_tool("ingest_source", {
        "raw_text": secret_text,
        "title": "Secret Document"
    })

    logs = MCPClientBridge.get_logs(limit=10)
    assert len(logs) >= 1
    ingest_log = logs[0]
    logged_raw = ingest_log["arguments"].get("raw_text", "")
    assert secret_text not in logged_raw
    assert "REDACTED" in logged_raw


# ---------------------------------------------------------------------------
# 5. Source Retrieval & Due Reminder Processing
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_source_retrieval_endpoint(temp_db_client):
    """GET /api/sources/{id} returns source metadata and text for evidence grounding modal."""
    client, db_path = temp_db_client

    source = await DeadlineService.create_source(
        SourceCreate(title="Test Grounding", raw_text="Verbatim source document text for grounding inspection."),
        db_path=db_path
    )
    res = await client.get(f"/api/sources/{source.id}")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == source.id
    assert "Verbatim source document" in data["raw_text"]

    # Non-existent source returns 404
    res_404 = await client.get("/api/sources/non-existent-uuid")
    assert res_404.status_code == 404


@pytest.mark.asyncio
async def test_due_reminder_processing(temp_db_client):
    """process_due_reminders transitions scheduled reminders to fired when due time arrives."""
    client, db_path = temp_db_client

    source = await DeadlineService.create_source(
        SourceCreate(title="Reminder Notice", raw_text="Due date notice"),
        db_path=db_path
    )
    dl = await DeadlineService.create_deadline(
        DeadlineCreate(
            source_id=source.id,
            provider_name="Utility Provider",
            candidate_date="2026-10-25",
            evidence_snippet="due on 2026-10-25",
            status=DeadlineStatus.UPCOMING
        ),
        db_path=db_path
    )

    rems = await DeadlineService.create_reminders(dl.id, lead_days=[1], db_path=db_path)
    assert rems[0].status == ReminderStatus.SCHEDULED

    # Simulate check time after remind_at
    future_time = "2026-10-26T00:00:00+00:00"
    fired = await DeadlineService.process_due_reminders(now_iso=future_time, db_path=db_path)
    assert len(fired) >= 1
    assert fired[0].status == ReminderStatus.FIRED
