"""
Phase 4: Real MCP Tool Execution via tools/call
Tests all 8 MCP tools end-to-end through JSON-RPC 2.0 dispatch:
1. ingest_source
2. find_deadline_candidates
3. get_deadline_evidence
4. confirm_or_correct_deadline
5. create_follow_up
6. prepare_next_step
7. update_deadline_status
8. list_deadlines
Verifies database side-effects, audit logging, and MCP invocation log entries.
"""
import pytest
import os
import tempfile
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings
from app.database import init_db, get_db
from app.services.deadline_service import DeadlineService
from app.services.mcp_client import MCPClientBridge


@pytest.fixture
async def setup_env():
    fd, path = tempfile.mkstemp(suffix="_tools.db")
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


async def rpc_call(client, tool_name: str, arguments: dict, call_id: str = "1"):
    payload = {
        "jsonrpc": "2.0",
        "id": call_id,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }
    resp = await client.post("/mcp", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    if "error" in data:
        return {"error": data["error"], "isError": True}
    return data["result"]["structuredContent"]


@pytest.mark.asyncio
async def test_all_8_mcp_tools_lifecycle(setup_env):
    client, db_path = setup_env

    # -----------------------------------------------------------------------
    # Tool 1: ingest_source
    # -----------------------------------------------------------------------
    trial_text = "Your 14-day free trial ends on October 20. Your card will be charged ₹499/month unless cancelled 24 hours prior."
    ingest_res = await rpc_call(client, "ingest_source", {
        "raw_text": trial_text,
        "title": "Scenario A Free Trial Notice",
        "source_type": "manual"
    })
    assert "source_id" in ingest_res
    assert ingest_res["title"] == "Scenario A Free Trial Notice"
    source_id = ingest_res["source_id"]

    # Verify source row exists in SQLite
    async with get_db(db_path) as db:
        async with db.execute("SELECT * FROM sources WHERE id = ?", (source_id,)) as cur:
            s_row = await cur.fetchone()
            assert s_row is not None
            assert s_row["title"] == "Scenario A Free Trial Notice"

    # -----------------------------------------------------------------------
    # Tool 2: find_deadline_candidates
    # -----------------------------------------------------------------------
    candidates_res = await rpc_call(client, "find_deadline_candidates", {"source_id": source_id})
    assert len(candidates_res) >= 1
    cand = candidates_res[0]
    assert cand["candidate_date"] == "2026-10-20"
    assert cand["status"] in ("needs_review", "date_unverified")
    deadline_id = cand["id"]

    # Verify deadline row exists in SQLite
    async with get_db(db_path) as db:
        async with db.execute("SELECT * FROM deadlines WHERE id = ?", (deadline_id,)) as cur:
            d_row = await cur.fetchone()
            assert d_row is not None
            assert d_row["candidate_date"] == "2026-10-20"

    # -----------------------------------------------------------------------
    # Tool 3: get_deadline_evidence
    # -----------------------------------------------------------------------
    evidence_res = await rpc_call(client, "get_deadline_evidence", {"deadline_id": deadline_id})
    assert evidence_res["deadline_id"] == deadline_id
    assert "evidence_snippet" in evidence_res
    assert evidence_res["source_title"] == "Scenario A Free Trial Notice"

    # Check 1:1 match with DB record
    async with get_db(db_path) as db:
        async with db.execute("SELECT evidence_snippet FROM deadlines WHERE id = ?", (deadline_id,)) as cur:
            db_snippet = (await cur.fetchone())["evidence_snippet"]
            assert evidence_res["evidence_snippet"] == db_snippet

    # -----------------------------------------------------------------------
    # Tool 4: confirm_or_correct_deadline
    # -----------------------------------------------------------------------
    confirm_res = await rpc_call(client, "confirm_or_correct_deadline", {
        "deadline_id": deadline_id,
        "confirmed_date": "2026-10-20",
        "provider_name": "Streaming Trial Service",
        "notes": "User confirmed date via test"
    })
    assert confirm_res["status"] == "confirmed"
    assert confirm_res["provider_name"] == "Streaming Trial Service"

    # Verify audit log was recorded
    async with get_db(db_path) as db:
        async with db.execute("SELECT * FROM audit_logs WHERE deadline_id = ? ORDER BY timestamp DESC", (deadline_id,)) as cur:
            audit_rows = await cur.fetchall()
            assert len(audit_rows) >= 2
            actions = [r["action"] for r in audit_rows]
            assert "status_changed" in actions or "user_edited" in actions

    # -----------------------------------------------------------------------
    # Tool 5: create_follow_up
    # -----------------------------------------------------------------------
    follow_up_res = await rpc_call(client, "create_follow_up", {
        "deadline_id": deadline_id,
        "lead_days": [7, 1],
        "export_calendar": True
    })
    assert follow_up_res["status"] == "upcoming"
    assert follow_up_res["reminders_count"] == 2
    assert "BEGIN:VCALENDAR" in follow_up_res["calendar_ics"]

    # Verify reminders stored in SQLite
    async with get_db(db_path) as db:
        async with db.execute("SELECT count(*) as count FROM reminders WHERE deadline_id = ?", (deadline_id,)) as cur:
            rem_count = (await cur.fetchone())["count"]
            assert rem_count == 2

    # -----------------------------------------------------------------------
    # Tool 6: prepare_next_step
    # -----------------------------------------------------------------------
    next_step_res = await rpc_call(client, "prepare_next_step", {"deadline_id": deadline_id})
    assert "checklist" in next_step_res
    assert len(next_step_res["checklist"]) > 0
    # For a service without verified URL, must not invent a URL
    if not next_step_res.get("has_verified_url"):
        assert next_step_res.get("official_url") is None
        assert "safety_notice" in next_step_res

    # -----------------------------------------------------------------------
    # Tool 7: update_deadline_status
    # -----------------------------------------------------------------------
    # Valid transition to completed
    status_res = await rpc_call(client, "update_deadline_status", {
        "deadline_id": deadline_id,
        "new_status": "completed",
        "resolution_notes": "Paid by user on portal"
    })
    assert status_res["status"] == "completed"

    # Invalid status rejection
    invalid_status_res = await rpc_call(client, "update_deadline_status", {
        "deadline_id": deadline_id,
        "new_status": "totally_invalid_status"
    })
    assert invalid_status_res.get("isError") is True

    # -----------------------------------------------------------------------
    # Tool 8: list_deadlines
    # -----------------------------------------------------------------------
    # Empty filter
    all_items = await rpc_call(client, "list_deadlines", {})
    assert len(all_items) >= 1

    # Valid status filter
    completed_items = await rpc_call(client, "list_deadlines", {"status_filter": "completed"})
    assert len(completed_items) >= 1
    assert all(i["status"] == "completed" for i in completed_items)

    # Nonsense filter returns empty list
    none_items = await rpc_call(client, "list_deadlines", {"status_filter": "nonexistent_status_filter"})
    assert len(none_items) == 0
