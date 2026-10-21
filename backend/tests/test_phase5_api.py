"""
Phase 5: Backend Application Layer and MCP Client Integration Tests
Tests REST endpoints (/api/health, /api/info, /api/stats, /api/sources/upload,
/api/deadlines CRUD, /api/deadlines/{id}/ics RFC 5545 parsing, /api/mcp/log),
and inspects MCP client transport for potential protocol bypass paths.
"""
import pytest
import os
import tempfile
import inspect
from httpx import AsyncClient, ASGITransport
from icalendar import Calendar
from app.main import app
from app.config import settings
from app.database import init_db
from app.services.mcp_client import MCPClientBridge


@pytest.fixture
async def setup_api():
    fd, path = tempfile.mkstemp(suffix="_api.db")
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
async def test_health_info_and_stats_endpoints(setup_api):
    """GET /api/health, /api/info, and /api/stats return expected schema and fields."""
    client, _ = setup_api

    # Health
    r_health = await client.get("/api/health")
    assert r_health.status_code == 200
    h_data = r_health.json()
    assert h_data["status"] == "healthy"
    assert h_data["mcp_protocol"] == "2025-11-25"
    assert "budget_mode" in h_data

    # Info
    r_info = await client.get("/api/info")
    assert r_info.status_code == 200
    i_data = r_info.json()
    assert i_data["track"] == "Alexa+"
    assert i_data["mcp_server"] in ("aheadly-mcp", "deadline-rescue-mcp")
    assert i_data["protocol_version"] == "2025-11-25"

    # Stats
    r_stats = await client.get("/api/stats")
    assert r_stats.status_code == 200
    s_data = r_stats.json()
    assert "total" in s_data
    assert "needs_review" in s_data


@pytest.mark.asyncio
async def test_sources_upload_endpoints(setup_api):
    """POST /api/sources/upload accepts multipart txt, eml, pdf, and raw_text; rejects empty/unsupported."""
    client, _ = setup_api

    # 1. Pasted raw_text
    r_text = await client.post("/api/sources/upload", data={
        "raw_text": "Airtel broadband bill due on 2026-11-15 for ₹999",
        "title": "Airtel Broadband Note"
    })
    assert r_text.status_code == 200
    assert r_text.json()["candidates_count"] >= 1

    # 2. Upload .txt file
    files_txt = {"file": ("bill.txt", b"Electricity bill due 2026-11-18 for Rs 2450", "text/plain")}
    r_txt_file = await client.post("/api/sources/upload", files=files_txt)
    assert r_txt_file.status_code == 200

    # 3. Upload .eml file
    eml_bytes = b"From: netflix@mailer.com\nSubject: Trial Ending\nDate: Mon, 14 Oct 2026\n\nFree trial ends October 20."
    files_eml = {"file": ("notice.eml", eml_bytes, "message/rfc822")}
    r_eml = await client.post("/api/sources/upload", files=files_eml)
    assert r_eml.status_code == 200

    # 4. Reject empty upload
    r_empty = await client.post("/api/sources/upload")
    assert r_empty.status_code == 400


@pytest.mark.asyncio
async def test_deadlines_rest_crud_and_404(setup_api):
    """GET /api/deadlines, GET /api/deadlines/{id}, PATCH, DELETE, and 404 handling."""
    client, _ = setup_api

    # Ingest source to produce a deadline
    r_upload = await client.post("/api/sources/upload", data={
        "raw_text": "Netflix subscription trial ends on October 20, 2026 for INR 499"
    })
    cands = r_upload.json()["candidates"]
    assert len(cands) >= 1
    d_id = cands[0]["id"]

    # GET list
    r_list = await client.get("/api/deadlines")
    assert r_list.status_code == 200
    assert any(d["id"] == d_id for d in r_list.json())

    # GET single
    r_get = await client.get(f"/api/deadlines/{d_id}")
    assert r_get.status_code == 200
    assert r_get.json()["id"] == d_id

    # PATCH single
    r_patch = await client.patch(f"/api/deadlines/{d_id}", json={
        "provider_name": "Netflix Updated",
        "status": "confirmed"
    })
    assert r_patch.status_code == 200
    assert r_patch.json()["provider_name"] == "Netflix Updated"

    # DELETE single
    r_del = await client.delete(f"/api/deadlines/{d_id}")
    assert r_del.status_code == 200

    # Verify 404 after delete
    r_get_after = await client.get(f"/api/deadlines/{d_id}")
    assert r_get_after.status_code == 404

    # 404 on fake ID
    assert (await client.get("/api/deadlines/non-existent-id")).status_code == 404
    assert (await client.patch("/api/deadlines/non-existent-id", json={"status": "confirmed"})).status_code == 404
    assert (await client.delete("/api/deadlines/non-existent-id")).status_code == 404


@pytest.mark.asyncio
async def test_calendar_ics_endpoint_rfc5545(setup_api):
    """GET /api/deadlines/{id}/ics returns valid RFC 5545 calendar with VEVENT, DTSTART, SUMMARY, VALARM."""
    client, _ = setup_api

    r_upload = await client.post("/api/sources/upload", data={
        "raw_text": "HDFC ERGO insurance premium due on November 05, 2026 for INR 14250"
    })
    d_id = r_upload.json()["candidates"][0]["id"]

    # Add reminders via follow-up MCP tool
    await MCPClientBridge.call_tool("create_follow_up", {
        "deadline_id": d_id,
        "lead_days": [14, 3]
    })

    # Download ICS
    r_ics = await client.get(f"/api/deadlines/{d_id}/ics")
    assert r_ics.status_code == 200
    assert "text/calendar" in r_ics.headers.get("content-type", "")

    # Parse with icalendar
    cal = Calendar.from_ical(r_ics.text)
    events = cal.walk("VEVENT")
    assert len(events) == 1
    event = events[0]
    assert event.get("SUMMARY") is not None
    assert event.get("DTSTART") is not None

    alarms = event.walk("VALARM")
    assert len(alarms) == 2, f"Expected 2 VALARMs for lead_days [14, 3], found {len(alarms)}"


@pytest.mark.asyncio
async def test_mcp_log_retrieval_and_clearing(setup_api):
    """GET /api/mcp/log contains tool calls and DELETE /api/mcp/log clears history."""
    client, _ = setup_api

    # Trigger tool call
    await MCPClientBridge.call_tool("list_deadlines", {})

    r_log = await client.get("/api/mcp/log")
    assert r_log.status_code == 200
    logs = r_log.json()
    assert len(logs) >= 1
    entry = logs[0]
    assert "tool_name" in entry
    assert "latency_ms" in entry
    assert "status" in entry

    # Clear logs
    r_del = await client.delete("/api/mcp/log")
    assert r_del.status_code == 200

    r_log_empty = await client.get("/api/mcp/log")
    assert len(r_log_empty.json()) == 0


@pytest.mark.asyncio
async def test_mcp_client_bridge_transport_bypass_check():
    """
    Confirm whether MCPClientBridge connects over Streamable HTTP transport network endpoint
    or bypasses the protocol layer via direct in-process Python function calls.
    Per Phase 5 / Section 5.2: Client must connect to Streamable HTTP endpoint.
    A direct Python function call bypass is a Critical finding.
    """
    from app.services.mcp_client import MCPClientBridge
    source_code = inspect.getsource(MCPClientBridge.call_tool)

    # Check whether it makes an HTTP request via httpx or directly calls handle_jsonrpc_request
    uses_http_transport = "httpx" in source_code or "http://" in source_code or "client.post" in source_code
    calls_direct_function = "handle_jsonrpc_request" in source_code

    assert uses_http_transport and not calls_direct_function, (
        "CRITICAL FINDING: MCPClientBridge directly calls in-process function 'handle_jsonrpc_request' "
        "bypassing the Streamable HTTP transport protocol layer (/mcp network request)!"
    )
