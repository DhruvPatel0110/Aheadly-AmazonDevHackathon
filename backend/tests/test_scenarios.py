"""
Phase 7: End-to-End Scenarios & Follow-Through Workflows (Scenarios A to D)
Runs Scenarios A, B, C, D through the complete pipeline:
upload/ingest -> find candidates -> evidence -> confirm -> follow-up -> next step -> status update.
"""
import pytest
import os
import tempfile
from pathlib import Path
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings
from app.database import init_db, get_db
from app.services.deadline_service import DeadlineService
from app.services.mcp_client import MCPClientBridge
from app.models import DeadlineCategory, ObligationType, DeadlineStatus, VerificationStatus

SAMPLE_DATA_DIR = Path(__file__).resolve().parent.parent / "sample_data"
if not SAMPLE_DATA_DIR.exists():
    SAMPLE_DATA_DIR = Path("backend/sample_data")


@pytest.fixture
async def setup_scenarios():
    fd, path = tempfile.mkstemp(suffix="_scenarios.db")
    os.close(fd)
    old_db_path = settings.db_path
    settings.db_path = path
    await init_db(path)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        MCPClientBridge.clear_logs()
        yield client, path

    settings.db_path = old_db_path
    if os.path.exists(path):
        os.remove(path)


@pytest.mark.asyncio
async def test_scenario_a_free_trial(setup_scenarios):
    """
    Scenario A (trial):
    "Your 14-day free trial ends on October 20. Your card will be charged ₹499/month unless cancelled 24 hours prior."
    Candidate date 2026-10-20, amount 499, cancellation-related next step, does not invent URL unless supported.
    """
    client, _ = setup_scenarios
    fixture_path = SAMPLE_DATA_DIR / "scenario_a_trial.txt"
    text = fixture_path.read_text(encoding="utf-8")

    # Ingest
    ingest_res = await MCPClientBridge.call_tool("ingest_source", {
        "raw_text": text,
        "title": "Scenario A Free Trial",
        "source_type": "manual"
    })
    source_id = ingest_res["source_id"]

    # Candidates
    cands = await MCPClientBridge.call_tool("find_deadline_candidates", {"source_id": source_id})
    assert len(cands) >= 1
    cand = cands[0]
    assert cand["candidate_date"] == "2026-10-20"
    assert cand["amount"] == 499.0
    assert cand["category"] == DeadlineCategory.SUBSCRIPTION.value
    assert cand["obligation_type"] == ObligationType.TRIAL_ENDING.value
    deadline_id = cand["id"]

    # Evidence
    ev = await MCPClientBridge.call_tool("get_deadline_evidence", {"deadline_id": deadline_id})
    assert "free trial ends on October 20" in ev["evidence_snippet"]

    # Next steps checklist
    next_step = await MCPClientBridge.call_tool("prepare_next_step", {"deadline_id": deadline_id})
    checklist_text = " ".join(next_step["checklist"]).lower()
    assert "cancellation" in checklist_text
    # System must not invent URL when provider is unknown
    assert next_step.get("official_url") is None or "netflix" not in next_step.get("official_url", "")


@pytest.mark.asyncio
async def test_scenario_b_insurance_renewal(setup_scenarios):
    """
    Scenario B (insurance):
    "Policy No: HDFC-98213. Your annual premium of ₹14,250 is due on November 05, 2026 to ensure continuous coverage."
    Provider "HDFC ERGO", date 2026-11-05, amount 14250, lapse warning quoted, reminders at 14 and 3 days before.
    Status remains pending/needs_review until user records payment.
    """
    client, db_path = setup_scenarios
    fixture_path = SAMPLE_DATA_DIR / "scenario_b_insurance.eml"
    text = fixture_path.read_text(encoding="utf-8")

    # Upload via API endpoint
    upload_resp = await client.post("/api/sources/upload", data={"raw_text": text, "title": "HDFC Notice"})
    assert upload_resp.status_code == 200
    cands = upload_resp.json()["candidates"]
    assert len(cands) >= 1
    cand = cands[0]

    assert cand["provider_name"] == "HDFC ERGO"
    assert cand["candidate_date"] == "2026-11-05"
    assert cand["amount"] == 14250.0
    assert cand["category"] == DeadlineCategory.INSURANCE.value
    deadline_id = cand["id"]

    # Follow-up reminders at 14 and 3 days
    follow_up = await MCPClientBridge.call_tool("create_follow_up", {
        "deadline_id": deadline_id,
        "lead_days": [14, 3],
        "export_calendar": True
    })
    assert follow_up["reminders_count"] == 2

    # Status remains until user payment
    status_check = await DeadlineService.get_deadline(deadline_id, db_path=db_path)
    assert status_check.status != DeadlineStatus.COMPLETED


@pytest.mark.asyncio
async def test_scenario_c_household_bills(setup_scenarios):
    """
    Scenario C (household bills):
    Ingest three separate items: broadband, electricity, mobile plan validity.
    Classify to 'broadband', 'utility', 'mobile', display in chronological order, test category filtering.
    """
    client, _ = setup_scenarios
    bb_text = (SAMPLE_DATA_DIR / "scenario_c1_broadband.txt").read_text(encoding="utf-8")
    elec_text = (SAMPLE_DATA_DIR / "scenario_c2_electricity.txt").read_text(encoding="utf-8")
    mob_text = (SAMPLE_DATA_DIR / "scenario_c3_mobile.txt").read_text(encoding="utf-8")

    # Ingest 3 sources
    for t, title in [(bb_text, "Broadband"), (elec_text, "Electricity"), (mob_text, "Mobile")]:
        r = await client.post("/api/sources/upload", data={"raw_text": t, "title": title})
        assert r.status_code == 200

    # List all
    all_deadlines = await MCPClientBridge.call_tool("list_deadlines", {})
    assert len(all_deadlines) >= 3

    categories = {d["category"] for d in all_deadlines}
    assert "broadband" in categories
    assert "utility" in categories
    assert "mobile" in categories

    # Verify chronological sorting (ascending by candidate_date)
    dates = [d["candidate_date"] for d in all_deadlines]
    assert dates == sorted(dates), f"Deadlines are not in chronological order: {dates}"

    # Category filtering
    util_only = await MCPClientBridge.call_tool("list_deadlines", {"category_filter": "utility"})
    assert all(d["category"] == "utility" for d in util_only)


@pytest.mark.asyncio
async def test_scenario_d_uncertainty_handling(setup_scenarios):
    """
    Scenario D (uncertainty):
    "Your annual maintenance fee will be due sometime near the end of the month."
    Expect no invented day (not 30th/31st), status date_unverified, no reminder rows created.
    """
    client, db_path = setup_scenarios
    text = (SAMPLE_DATA_DIR / "scenario_d_uncertainty.txt").read_text(encoding="utf-8")

    upload_resp = await client.post("/api/sources/upload", data={"raw_text": text, "title": "Maintenance Fee"})
    cands = upload_resp.json()["candidates"]
    assert len(cands) == 1
    cand = cands[0]

    # No invented date
    assert cand["candidate_date"] == "UNVERIFIED"
    assert cand["status"] in (DeadlineStatus.DATE_UNVERIFIED.value, DeadlineStatus.NEEDS_REVIEW.value)
    assert cand["verification_status"] == VerificationStatus.UNVERIFIED.value
    deadline_id = cand["id"]

    # Reminders must NOT be allowed on unverified dates
    with pytest.raises(ValueError) as exc_info:
        await MCPClientBridge.call_tool("create_follow_up", {
            "deadline_id": deadline_id,
            "lead_days": [7, 1]
        })
    assert "unverified date" in str(exc_info.value).lower()

    # Verify no reminder rows created
    async with get_db(db_path) as db:
        async with db.execute("SELECT count(*) as count FROM reminders WHERE deadline_id = ?", (deadline_id,)) as cur:
            rem_count = (await cur.fetchone())["count"]
            assert rem_count == 0
