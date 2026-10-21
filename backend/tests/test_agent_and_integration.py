"""
Integration tests for Phase 5: Backend Application Layer, Agent Host & MCP Client Integration.
Tests multipart uploads, conversational agent interactions, real MCP tool-call logging,
and calendar export.
"""
import pytest
import io
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import init_db
from app.services.mcp_client import MCPClientBridge


@pytest.fixture(autouse=True)
async def setup_env():
    await init_db()
    MCPClientBridge.clear_logs()


@pytest.mark.asyncio
async def test_source_upload_raw_text():
    """Verify POST /api/sources/upload with form data triggers ingest_source and find_deadline_candidates."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "raw_text": "Airtel Wi-Fi bill due on 2026-11-20 for INR 999.",
            "title": "Airtel Fiber Bill"
        }
        res = await ac.post("/api/sources/upload", data=payload)
        assert res.status_code == 200
        data = res.json()
        assert "source" in data
        assert data["source"]["title"] == "Airtel Fiber Bill"
        assert len(data["candidates"]) >= 1
        assert data["candidates"][0]["candidate_date"] == "2026-11-20"
        assert data["candidates"][0]["provider_name"] == "Airtel"

        # Verify MCP tool log recorded both calls
        log_res = await ac.get("/api/mcp/log")
        assert log_res.status_code == 200
        logs = log_res.json()
        assert len(logs) >= 2
        tool_names = [l["tool_name"] for l in logs]
        assert "ingest_source" in tool_names
        assert "find_deadline_candidates" in tool_names


@pytest.mark.asyncio
async def test_source_upload_file():
    """Verify POST /api/sources/upload with multipart file attachment (.txt / .eml)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        file_content = (
            b"From: support@tatapower.com\r\n"
            b"Subject: Electricity Bill Notice\r\n\r\n"
            b"Your power bill amount is Rs. 1450. Payment due on 2026-11-05."
        )
        files = {
            "file": ("notice.eml", io.BytesIO(file_content), "message/rfc822")
        }
        res = await ac.post("/api/sources/upload", files=files)
        assert res.status_code == 200
        data = res.json()
        assert data["source"]["source_type"] == "email"
        assert len(data["candidates"]) >= 1
        assert data["candidates"][0]["candidate_date"] == "2026-11-05"


@pytest.mark.asyncio
async def test_conversational_agent_e2e_flow():
    """
    Test the conversational agent:
    1. Send user utterance with trial notice.
    2. Agent extracts date, quotes evidence, and asks for confirmation.
    3. User confirms date.
    4. User asks for reminders.
    5. User asks how to cancel.
    6. User marks as cancelled.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Step 1: Send message with trial notice
        msg1 = "I started a free trial. Here is the email: Your 14-day Netflix trial ends on 2026-10-20. Card charged INR 649 unless cancelled."
        res1 = await ac.post("/api/agent/chat", json={"message": msg1})
        assert res1.status_code == 200
        data1 = res1.json()
        assert "2026-10-20" in data1["reply"]
        assert "Netflix" in data1["reply"]
        deadline_id = data1["active_deadline_id"]
        assert deadline_id is not None
        assert "ingest_source" in data1["tools_invoked"]
        assert "find_deadline_candidates" in data1["tools_invoked"]

        # Step 2: Inquire about evidence
        res_ev = await ac.post("/api/agent/chat", json={"message": "Show evidence for Netflix", "active_deadline_id": deadline_id})
        assert res_ev.status_code == 200
        assert "Source Evidence for Netflix" in res_ev.json()["reply"]
        assert "get_deadline_evidence" in res_ev.json()["tools_invoked"]

        # Step 3: Confirm date
        res2 = await ac.post("/api/agent/chat", json={"message": "Confirm this date", "active_deadline_id": deadline_id})
        assert res2.status_code == 200
        assert "Confirmed" in res2.json()["reply"]
        assert "confirm_or_correct_deadline" in res2.json()["tools_invoked"]

        # Step 4: Schedule reminders
        res3 = await ac.post("/api/agent/chat", json={"message": "Remind me 3 days before and export calendar", "active_deadline_id": deadline_id})
        assert res3.status_code == 200
        assert "Scheduled" in res3.json()["reply"]
        assert "create_follow_up" in res3.json()["tools_invoked"]

        # Step 5: Ask how to cancel
        res4 = await ac.post("/api/agent/chat", json={"message": "How do I cancel?", "active_deadline_id": deadline_id})
        assert res4.status_code == 200
        assert "Next Steps for Netflix" in res4.json()["reply"]
        assert "prepare_next_step" in res4.json()["tools_invoked"]

        # Step 6: Mark as cancelled
        res5 = await ac.post("/api/agent/chat", json={"message": "I cancelled my subscription", "active_deadline_id": deadline_id})
        assert res5.status_code == 200
        assert "Cancelled" in res5.json()["reply"]
        assert "update_deadline_status" in res5.json()["tools_invoked"]


@pytest.mark.asyncio
async def test_conversational_agent_vague_date_scenario_d():
    """Verify agent refuses to invent a date when text contains vague expression."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        msg = "Hi, my annual maintenance charge is due sometime near the end of the month."
        res = await ac.post("/api/agent/chat", json={"message": msg})
        assert res.status_code == 200
        reply = res.json()["reply"]
        assert "will not guess or invent a deadline" in reply
        assert "near the end of the month" in reply


@pytest.mark.asyncio
async def test_mcp_tool_log_clearing():
    """Verify MCP log clearing endpoint."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Trigger an action
        await ac.post("/api/agent/chat", json={"message": "What is due this week?"})
        log_res = await ac.get("/api/mcp/log")
        assert len(log_res.json()) >= 1

        # Clear
        del_res = await ac.delete("/api/mcp/log")
        assert del_res.status_code == 200
        assert del_res.json()["status"] == "cleared"

        empty_logs = await ac.get("/api/mcp/log")
        assert len(empty_logs.json()) == 0
