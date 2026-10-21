"""
Phase 4: MCP Protocol & Streamable HTTP Transport Tests (Spec 2025-11-25+)
Tests GET /mcp SSE stream, POST /mcp initialize, notifications/initialized, tools/list,
JSON-RPC 2.0 framing, error codes (-32601, -32602, -32700, -32603), server health recovery,
and concurrent transport calls.
"""
import pytest
import asyncio
import json
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings


@pytest.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_mcp_get_sse_stream_and_endpoint_event(async_client):
    """GET /mcp returns text/event-stream and emits initial endpoint event with server, version, protocol."""
    response = await async_client.get("/mcp?once=true")
    assert response.status_code == 200
    content_type = response.headers.get("content-type", "")
    assert "text/event-stream" in content_type

    body = response.text
    assert "event: endpoint" in body
    assert "deadline-rescue-mcp" in body
    assert "1.0.0" in body
    assert "2025-11-25" in body


@pytest.mark.asyncio
async def test_mcp_post_initialize(async_client):
    """POST /mcp with 'initialize' returns protocolVersion, serverInfo, and capabilities."""
    req_payload = {
        "jsonrpc": "2.0",
        "id": "init-req-1",
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-11-25",
            "clientInfo": {"name": "test-client", "version": "1.0.0"}
        }
    }
    response = await async_client.post("/mcp", json=req_payload)
    assert response.status_code == 200
    data = response.json()
    assert data.get("jsonrpc") == "2.0"
    assert data.get("id") == "init-req-1"

    result = data.get("result", {})
    assert result.get("protocolVersion") == "2025-11-25"
    assert result.get("serverInfo", {}).get("name") == "deadline-rescue-mcp"
    assert result.get("serverInfo", {}).get("version") == "1.0.0"
    assert "tools" in result.get("capabilities", {})


@pytest.mark.asyncio
async def test_mcp_post_notifications_initialized(async_client):
    """
    POST /mcp 'notifications/initialized' is accepted with correct response code (202 or 200, per spec).
    Notifications do not expect a JSON-RPC error response.
    """
    notif_payload = {
        "jsonrpc": "2.0",
        "method": "notifications/initialized",
        "params": {}
    }
    response = await async_client.post("/mcp", json=notif_payload)
    assert response.status_code in (200, 202)
    data = response.json()
    # Per MCP / JSON-RPC spec, notification should not return an error code like -32601
    assert "error" not in data, (
        f"Server failed to recognize 'notifications/initialized' notification! Error: {data.get('error')}"
    )


@pytest.mark.asyncio
async def test_mcp_tools_list_count_and_schema_comparison(async_client):
    """
    POST /mcp 'tools/list' returns exactly 8 tools.
    Verify names match Section 4.2.
    Compare tools/list output against GET /api/mcp/tools: they must match exactly.
    """
    req_payload = {
        "jsonrpc": "2.0",
        "id": "tools-list-req",
        "method": "tools/list",
        "params": {}
    }
    response = await async_client.post("/mcp", json=req_payload)
    assert response.status_code == 200
    data = response.json()
    assert data.get("jsonrpc") == "2.0"
    assert data.get("id") == "tools-list-req"

    tools = data.get("result", {}).get("tools", [])
    assert len(tools) == 8, f"Expected exactly 8 tools, found {len(tools)}"

    tool_names = [t["name"] for t in tools]
    expected_names = [
        "ingest_source", "find_deadline_candidates", "get_deadline_evidence",
        "confirm_or_correct_deadline", "create_follow_up", "prepare_next_step",
        "update_deadline_status", "list_deadlines"
    ]
    for name in expected_names:
        assert name in tool_names, f"Tool {name} missing from tools/list"

    # Compare against GET /api/mcp/tools
    api_resp = await async_client.get("/api/mcp/tools")
    assert api_resp.status_code == 200
    api_tools = api_resp.json()
    assert tools == api_tools, "Mismatch between POST /mcp tools/list and GET /api/mcp/tools!"


@pytest.mark.asyncio
async def test_mcp_error_unknown_method(async_client):
    """Unknown method returns JSON-RPC error -32601."""
    req_payload = {
        "jsonrpc": "2.0",
        "id": "unk-meth-1",
        "method": "non_existent_method",
        "params": {}
    }
    response = await async_client.post("/mcp", json=req_payload)
    assert response.status_code == 200
    data = response.json()
    assert data.get("jsonrpc") == "2.0"
    assert data.get("id") == "unk-meth-1"
    assert "error" in data
    assert data["error"]["code"] == -32601


@pytest.mark.asyncio
async def test_mcp_error_missing_required_argument(async_client):
    """
    tools/call with missing required argument (e.g., ingest_source without raw_text):
    expect JSON-RPC code -32602 (Invalid params).
    """
    req_payload = {
        "jsonrpc": "2.0",
        "id": "missing-arg-1",
        "method": "tools/call",
        "params": {
            "name": "ingest_source",
            "arguments": {}  # Missing required raw_text
        }
    }
    response = await async_client.post("/mcp", json=req_payload)
    assert response.status_code == 200
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == -32602, (
        f"Expected JSON-RPC error code -32602 for missing params, got {data['error']['code']}: {data['error']['message']}"
    )


@pytest.mark.asyncio
async def test_mcp_error_wrong_argument_type(async_client):
    """
    tools/call with wrong type (e.g., source_id as integer):
    expect JSON-RPC code -32602 (Invalid params).
    """
    req_payload = {
        "jsonrpc": "2.0",
        "id": "wrong-type-1",
        "method": "tools/call",
        "params": {
            "name": "find_deadline_candidates",
            "arguments": {
                "source_id": 99999  # Integer instead of string
            }
        }
    }
    response = await async_client.post("/mcp", json=req_payload)
    assert response.status_code == 200
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == -32602, (
        f"Expected JSON-RPC error code -32602 for wrong param type, got {data['error']['code']}: {data['error']['message']}"
    )


@pytest.mark.asyncio
async def test_mcp_error_unknown_tool_name(async_client):
    """tools/call for an unknown tool name: record actual code and behavior."""
    req_payload = {
        "jsonrpc": "2.0",
        "id": "unk-tool-1",
        "method": "tools/call",
        "params": {
            "name": "unknown_tool_xyz",
            "arguments": {}
        }
    }
    response = await async_client.post("/mcp", json=req_payload)
    assert response.status_code == 200
    data = response.json()
    assert "error" in data
    # Check whether code is -32601 (Method not found) or -32602
    assert data["error"]["code"] in (-32601, -32602)


@pytest.mark.asyncio
async def test_mcp_error_malformed_json_and_health_recovery(async_client):
    """Malformed JSON body returns parse error -32700, and server stays healthy afterward."""
    response = await async_client.post(
        "/mcp",
        content="{\"jsonrpc\": \"2.0\", \"method\": unclosed...",
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data.get("error", {}).get("code") == -32700

    # Server must stay up and healthy
    health_resp = await async_client.get("/api/health")
    assert health_resp.status_code == 200
    assert health_resp.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_mcp_concurrent_tool_calls(async_client):
    """Send 3 concurrent tools/call requests and confirm no response mix-ups or DB locking errors."""
    payloads = [
        {
            "jsonrpc": "2.0",
            "id": f"conc-{i}",
            "method": "tools/call",
            "params": {
                "name": "ingest_source",
                "arguments": {
                    "raw_text": f"Concurrent test text {i} trial ends October 20.",
                    "title": f"Concurrent {i}",
                    "source_type": "manual"
                }
            }
        }
        for i in range(3)
    ]

    tasks = [async_client.post("/mcp", json=p) for p in payloads]
    responses = await asyncio.gather(*tasks)

    for i, resp in enumerate(responses):
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("id") == f"conc-{i}"
        assert data.get("result", {}).get("isError") is False
        assert "source_id" in data.get("result", {}).get("structuredContent", {})
