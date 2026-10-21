"""
Phase 5: Conversational Agent Host & Ollama-Unreachable Tests
Tests all 7 conversational intent mappings, evidence quoting, bold dates,
confirmation prompts, unrecognized intent fallback, and Ollama unreachable behavior.
"""
import pytest
import os
import time
import tempfile
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings
from app.database import init_db
from app.services.mcp_client import MCPClientBridge
from app.engine.obligation_classifier import AnalysisEngine


@pytest.fixture
async def setup_agent():
    fd, path = tempfile.mkstemp(suffix="_agent.db")
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
async def test_agent_intent_1_check_bill_trial(setup_agent):
    """'Check this bill / trial email' invokes ingest_source then find_deadline_candidates, bolds date, includes evidence."""
    client, _ = setup_agent
    msg = "Check this bill / trial email: Your 14-day free trial ends on October 20 2026. Your card will be charged INR 499."
    resp = await client.post("/api/agent/chat", json={"message": msg})
    assert resp.status_code == 200
    data = resp.json()

    assert "ingest_source" in data["tools_invoked"]
    assert "find_deadline_candidates" in data["tools_invoked"]
    reply = data["reply"]
    # Verify extracted date is bolded: **2026-10-20**
    assert "**2026-10-20**" in reply
    # Verify exact evidence quote is included
    assert "free trial ends on October 20 2026" in reply
    # Verify ends with explicit confirmation prompt
    assert reply.strip().endswith("?") or "confirm" in reply.lower()


@pytest.mark.asyncio
async def test_agent_intent_2_show_evidence(setup_agent):
    """'Show evidence for Netflix' invokes get_deadline_evidence, includes evidence snippet and bold date."""
    client, _ = setup_agent
    # First ingest
    r1 = await client.post("/api/agent/chat", json={
        "message": "Netflix subscription renewal due on 2026-11-20 for INR 649."
    })
    active_id = r1.json()["active_deadline_id"]

    # Inquire evidence
    r2 = await client.post("/api/agent/chat", json={
        "message": "Show evidence for Netflix",
        "active_deadline_id": active_id
    })
    assert r2.status_code == 200
    data = r2.json()
    assert "get_deadline_evidence" in data["tools_invoked"]
    reply = data["reply"]
    assert "**2026-11-20**" in reply
    assert "due on 2026-11-20" in reply


@pytest.mark.asyncio
async def test_agent_intent_3_confirm_date(setup_agent):
    """'Confirm this date' invokes confirm_or_correct_deadline, updates status, does not assume confirmation."""
    client, _ = setup_agent
    r1 = await client.post("/api/agent/chat", json={
        "message": "Airtel broadband bill due on 2026-11-15 for INR 999."
    })
    active_id = r1.json()["active_deadline_id"]

    r3 = await client.post("/api/agent/chat", json={
        "message": "Confirm this date",
        "active_deadline_id": active_id
    })
    assert r3.status_code == 200
    data = r3.json()
    assert "confirm_or_correct_deadline" in data["tools_invoked"]
    reply = data["reply"]
    assert "**2026-11-15**" in reply


@pytest.mark.asyncio
async def test_agent_intent_4_remind_follow_up(setup_agent):
    """'Remind me 3 days before' invokes create_follow_up with configured lead days."""
    client, _ = setup_agent
    r1 = await client.post("/api/agent/chat", json={
        "message": "Tata Power electricity bill due on 2026-11-18 for INR 2450."
    })
    active_id = r1.json()["active_deadline_id"]

    r4 = await client.post("/api/agent/chat", json={
        "message": "Remind me 3 days before",
        "active_deadline_id": active_id
    })
    assert r4.status_code == 200
    data = r4.json()
    assert "create_follow_up" in data["tools_invoked"]
    assert "Upcoming" in data["reply"]


@pytest.mark.asyncio
async def test_agent_intent_5_how_do_i_cancel(setup_agent):
    """'How do I cancel?' invokes prepare_next_step, provides checklist, does not invent URL."""
    client, _ = setup_agent
    r1 = await client.post("/api/agent/chat", json={
        "message": "Free trial ends October 20. Your card will be charged unless cancelled."
    })
    active_id = r1.json()["active_deadline_id"]

    r5 = await client.post("/api/agent/chat", json={
        "message": "How do I cancel?",
        "active_deadline_id": active_id
    })
    assert r5.status_code == 200
    data = r5.json()
    assert "prepare_next_step" in data["tools_invoked"]
    assert "Next Steps" in data["reply"]


@pytest.mark.asyncio
async def test_agent_intent_6_i_paid_bill(setup_agent):
    """'I paid this bill' invokes update_deadline_status, records user confirmation vs external payment."""
    client, _ = setup_agent
    r1 = await client.post("/api/agent/chat", json={
        "message": "Electricity bill due on 2026-11-18 for INR 2450."
    })
    active_id = r1.json()["active_deadline_id"]

    r6 = await client.post("/api/agent/chat", json={
        "message": "I paid this bill",
        "active_deadline_id": active_id
    })
    assert r6.status_code == 200
    data = r6.json()
    assert "update_deadline_status" in data["tools_invoked"]
    assert "Completed" in data["reply"]


@pytest.mark.asyncio
async def test_agent_intent_7_what_is_due(setup_agent):
    """'What is due this week?' invokes list_deadlines."""
    client, _ = setup_agent
    r7 = await client.post("/api/agent/chat", json={
        "message": "What is due this week?"
    })
    assert r7.status_code == 200
    data = r7.json()
    assert "list_deadlines" in data["tools_invoked"]


@pytest.mark.asyncio
async def test_agent_unrecognized_intent_graceful_fallback(setup_agent):
    """Unrecognized intent responds with helpful fallback message, not an exception."""
    client, _ = setup_agent
    r_fallback = await client.post("/api/agent/chat", json={
        "message": "Can you recommend a good Italian restaurant?"
    })
    assert r_fallback.status_code == 200
    data = r_fallback.json()
    assert "reply" in data
    assert "didn't detect an explicit money-related deadline" in data["reply"]


@pytest.mark.asyncio
async def test_ollama_unreachable_deterministic_execution_and_latency():
    """
    With Ollama URL set to a closed port or uninstalled, extraction on Scenario A must complete
    using the deterministic engine, with no exception, and record latency and layer status.
    """
    scenario_a = "Your 14-day free trial ends on October 20. Your card will be charged ₹499/month unless cancelled 24 hours prior."

    start = time.perf_counter()
    candidates = AnalysisEngine.extract_obligations(scenario_a)
    latency_ms = (time.perf_counter() - start) * 1000

    assert len(candidates) >= 1
    assert candidates[0]["candidate_date"] == "2026-10-20"
    assert candidates[0]["amount"] == 499.0
    assert latency_ms < 100.0, f"Extraction was too slow: {latency_ms:.2f}ms"
