"""
Unit and integration tests for Phase 4: Self-Hosted MCP Server.
Tests Streamable HTTP, SSE streaming, JSON-RPC 2.0 protocol compliance,
and all 8 core MCP tools reading & writing SQLite state.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import init_db
from app.config import settings


@pytest.fixture(autouse=True)
async def ensure_db():
    await init_db()


@pytest.mark.asyncio
async def test_mcp_initialize_jsonrpc():
    """Verify JSON-RPC 2.0 initialize request returns MCP spec 2025-11-25+ info."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        req = {
            "jsonrpc": "2.0",
            "id": "req-init-1",
            "method": "initialize",
            "params": {}
        }
        res = await ac.post("/mcp", json=req)
        assert res.status_code == 200
        data = res.json()
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == "req-init-1"
        result = data["result"]
        assert result["protocolVersion"] == "2025-11-25"
        assert result["serverInfo"]["name"] == "deadline-rescue-mcp"
        assert "tools" in result["capabilities"]


@pytest.mark.asyncio
async def test_mcp_tools_list():
    """Verify tools/list returns all 8 required tools with schema definitions."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        req = {
            "jsonrpc": "2.0",
            "id": "req-list-2",
            "method": "tools/list",
            "params": {}
        }
        res = await ac.post("/mcp", json=req)
        assert res.status_code == 200
        data = res.json()
        tools = data["result"]["tools"]
        tool_names = [t["name"] for t in tools]

        expected_tools = [
            "ingest_source",
            "find_deadline_candidates",
            "get_deadline_evidence",
            "confirm_or_correct_deadline",
            "create_follow_up",
            "prepare_next_step",
            "update_deadline_status",
            "list_deadlines"
        ]
        for exp in expected_tools:
            assert exp in tool_names, f"Expected tool '{exp}' not found in registered MCP tools."


@pytest.mark.asyncio
async def test_mcp_tool_execution_lifecycle():
    """
    End-to-end test executing all tools sequentially via JSON-RPC over Streamable HTTP:
    1. ingest_source
    2. find_deadline_candidates
    3. get_deadline_evidence
    4. confirm_or_correct_deadline
    5. create_follow_up (with calendar export)
    6. prepare_next_step
    7. update_deadline_status
    8. list_deadlines
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Ingest source
        sample_email = (
            "From: notifications@netflix.com\n"
            "Subject: Your 14-day Netflix trial is ending\n\n"
            "Your trial ends and your subscription renews on 2026-10-20. "
            "Monthly charge of INR 649 will apply unless cancelled before cut-off."
        )
        ingest_req = {
            "jsonrpc": "2.0",
            "id": "req-tool-1",
            "method": "tools/call",
            "params": {
                "name": "ingest_source",
                "arguments": {
                    "raw_text": sample_email,
                    "title": "Netflix Trial Email",
                    "source_type": "email"
                }
            }
        }
        res_ingest = await ac.post("/mcp", json=ingest_req)
        assert res_ingest.status_code == 200
        ingest_data = res_ingest.json()["result"]["structuredContent"]
        assert "source_id" in ingest_data
        source_id = ingest_data["source_id"]

        # 2. Find deadline candidates
        find_req = {
            "jsonrpc": "2.0",
            "id": "req-tool-2",
            "method": "tools/call",
            "params": {
                "name": "find_deadline_candidates",
                "arguments": {"source_id": source_id}
            }
        }
        res_find = await ac.post("/mcp", json=find_req)
        assert res_find.status_code == 200
        candidates = res_find.json()["result"]["structuredContent"]
        assert len(candidates) >= 1
        cand = candidates[0]
        assert cand["provider_name"] == "Netflix"
        assert cand["candidate_date"] == "2026-10-20"
        deadline_id = cand["id"]

        # 3. Get deadline evidence
        evidence_req = {
            "jsonrpc": "2.0",
            "id": "req-tool-3",
            "method": "tools/call",
            "params": {
                "name": "get_deadline_evidence",
                "arguments": {"deadline_id": deadline_id}
            }
        }
        res_ev = await ac.post("/mcp", json=evidence_req)
        assert res_ev.status_code == 200
        ev_data = res_ev.json()["result"]["structuredContent"]
        assert "Your trial ends and your subscription renews on 2026-10-20" in ev_data["evidence_snippet"]

        # 4. Confirm or correct deadline
        confirm_req = {
            "jsonrpc": "2.0",
            "id": "req-tool-4",
            "method": "tools/call",
            "params": {
                "name": "confirm_or_correct_deadline",
                "arguments": {
                    "deadline_id": deadline_id,
                    "confirmed_date": "2026-10-20",
                    "provider_name": "Netflix Streaming",
                    "notes": "Verified by user via email receipt"
                }
            }
        }
        res_conf = await ac.post("/mcp", json=confirm_req)
        assert res_conf.status_code == 200
        conf_data = res_conf.json()["result"]["structuredContent"]
        assert conf_data["status"] == "confirmed"
        assert conf_data["provider_name"] == "Netflix Streaming"

        # 5. Create follow-up with calendar export
        follow_req = {
            "jsonrpc": "2.0",
            "id": "req-tool-5",
            "method": "tools/call",
            "params": {
                "name": "create_follow_up",
                "arguments": {
                    "deadline_id": deadline_id,
                    "lead_days": [3, 1],
                    "export_calendar": True
                }
            }
        }
        res_follow = await ac.post("/mcp", json=follow_req)
        assert res_follow.status_code == 200
        follow_data = res_follow.json()["result"]["structuredContent"]
        assert follow_data["reminders_count"] == 2
        assert follow_data["calendar_ics"] is not None
        assert "BEGIN:VCALENDAR" in follow_data["calendar_ics"]
        assert "Netflix Streaming" in follow_data["calendar_ics"]

        # 6. Prepare next step
        prep_req = {
            "jsonrpc": "2.0",
            "id": "req-tool-6",
            "method": "tools/call",
            "params": {
                "name": "prepare_next_step",
                "arguments": {"deadline_id": deadline_id}
            }
        }
        res_prep = await ac.post("/mcp", json=prep_req)
        assert res_prep.status_code == 200
        prep_data = res_prep.json()["result"]["structuredContent"]
        assert prep_data["has_verified_url"] is True
        assert len(prep_data["checklist"]) >= 3

        # 7. Update deadline status
        status_req = {
            "jsonrpc": "2.0",
            "id": "req-tool-7",
            "method": "tools/call",
            "params": {
                "name": "update_deadline_status",
                "arguments": {
                    "deadline_id": deadline_id,
                    "new_status": "cancelled",
                    "resolution_notes": "Cancelled through Netflix portal."
                }
            }
        }
        res_stat = await ac.post("/mcp", json=status_req)
        assert res_stat.status_code == 200
        stat_data = res_stat.json()["result"]["structuredContent"]
        assert stat_data["status"] == "cancelled"

        # 8. List deadlines with filter
        list_req = {
            "jsonrpc": "2.0",
            "id": "req-tool-8",
            "method": "tools/call",
            "params": {
                "name": "list_deadlines",
                "arguments": {"status_filter": "cancelled"}
            }
        }
        res_list = await ac.post("/mcp", json=list_req)
        assert res_list.status_code == 200
        list_data = res_list.json()["result"]["structuredContent"]
        assert any(d["id"] == deadline_id for d in list_data)


@pytest.mark.asyncio
async def test_mcp_error_handling_jsonrpc():
    """Verify JSON-RPC error codes for invalid methods and tool errors."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Unknown method
        res = await ac.post("/mcp", json={"jsonrpc": "2.0", "id": 99, "method": "unknown_rpc_method"})
        assert res.status_code == 200
        data = res.json()
        assert "error" in data
        assert data["error"]["code"] == -32601

        # Unknown tool name in tools/call
        res_tool = await ac.post("/mcp", json={
            "jsonrpc": "2.0",
            "id": 100,
            "method": "tools/call",
            "params": {"name": "non_existent_tool", "arguments": {}}
        })
        assert res_tool.status_code == 200
        assert res_tool.json()["error"]["code"] == -32601

        # Missing tool name
        res_missing = await ac.post("/mcp", json={
            "jsonrpc": "2.0",
            "id": 101,
            "method": "tools/call",
            "params": {"arguments": {}}
        })
        assert res_missing.status_code == 200
        assert res_missing.json()["error"]["code"] == -32602


@pytest.mark.asyncio
async def test_mcp_sse_endpoint_headers():
    """Verify GET /mcp responds with SSE text/event-stream headers per Streamable HTTP spec."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/mcp?once=true")
        assert res.status_code == 200
        assert "text/event-stream" in res.headers["content-type"]
        assert "no-cache" in res.headers["cache-control"]
        assert res.headers.get("x-accel-buffering") == "no"
        assert "endpoint" in res.text
        assert "deadline-rescue-mcp" in res.text


@pytest.mark.asyncio
async def test_mcp_tools_api_inspection_endpoint():
    """Verify GET /api/mcp/tools returns schemas for the frontend inspector."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/api/mcp/tools")
        assert res.status_code == 200
        tools = res.json()
        assert len(tools) == 8
        names = [t["name"] for t in tools]
        assert "ingest_source" in names
        assert "find_deadline_candidates" in names
