import asyncio
import json
import logging
import time
import uuid
from typing import Dict, Any, Set, Optional
from fastapi import APIRouter, Request, Response
from sse_starlette.sse import EventSourceResponse
from app.mcp_server.server import mcp_server, handle_jsonrpc_request
from app.config import settings

logger = logging.getLogger(__name__)

mcp_router = APIRouter(tags=["MCP Server"])

# Active sessions and SSE event subscribers
_ACTIVE_SESSIONS: Dict[str, Dict[str, Any]] = {}
_EVENT_SUBSCRIBERS: Set[asyncio.Queue] = set()


def broadcast_tool_event(event_dict: Dict[str, Any]) -> None:
    """Broadcast real tool execution event to all connected SSE observers."""
    for q in list(_EVENT_SUBSCRIBERS):
        try:
            q.put_nowait(event_dict)
        except Exception:
            pass


@mcp_router.post("/mcp")
async def mcp_post_endpoint(request: Request) -> Response:
    """
    HTTP POST endpoint for JSON-RPC 2.0 messages over MCP Streamable HTTP transport.
    Supports session lifecycle via 'Mcp-Session-Id' header (Spec 2025-11-25+).
    Handles 'initialize', 'notifications/initialized', 'tools/list', and 'tools/call'.
    """
    session_id = request.headers.get("mcp-session-id")

    try:
        body = await request.json()
    except Exception:
        err_res = {
            "jsonrpc": "2.0",
            "id": None,
            "error": {"code": -32700, "message": "Parse error: invalid JSON payload"}
        }
        return Response(content=json.dumps(err_res), status_code=200, media_type="application/json")

    method = body.get("method")

    # Notification handling
    if method == "notifications/initialized":
        headers = {}
        if session_id:
            headers["Mcp-Session-Id"] = session_id
        return Response(content="{}", status_code=202, media_type="application/json", headers=headers)

    # Initialize handling: issue new Mcp-Session-Id
    if method == "initialize":
        new_session_id = str(uuid.uuid4())
        _ACTIVE_SESSIONS[new_session_id] = {
            "created_at": time.time(),
            "client_info": body.get("params", {}).get("clientInfo", {})
        }
        res_data = await handle_jsonrpc_request(body)
        headers = {
            "Mcp-Session-Id": new_session_id
        }
        return Response(content=json.dumps(res_data), status_code=200, media_type="application/json", headers=headers)

    # Subsequent requests: pass session header if present
    res_data = await handle_jsonrpc_request(body)
    headers = {}
    if session_id:
        headers["Mcp-Session-Id"] = session_id

    # If tools/call was executed, broadcast to live SSE subscribers
    if method == "tools/call" and "result" in res_data:
        tool_name = body.get("params", {}).get("name")
        broadcast_tool_event({
            "event": "tool_execution",
            "tool_name": tool_name,
            "status": "success",
            "timestamp": time.time()
        })

    return Response(content=json.dumps(res_data), status_code=200, media_type="application/json", headers=headers)


@mcp_router.get("/mcp")
async def mcp_sse_endpoint(request: Request):
    """
    HTTP GET endpoint for Server-Sent Events (SSE) streamable transport.
    Emits an initial connection event announcing server details and readiness,
    and broadcasts live tool executions to connected observers.
    """
    queue: asyncio.Queue = asyncio.Queue()
    _EVENT_SUBSCRIBERS.add(queue)

    async def event_generator():
        try:
            # Emit initial endpoint connection event per MCP SSE transport spec
            init_event = {
                "type": "endpoint",
                "server": settings.mcp_server_name,
                "version": settings.app_version,
                "protocol": settings.mcp_protocol_version,
                "endpoint": "/mcp"
            }
            yield {
                "event": "endpoint",
                "data": json.dumps(init_event)
            }

            # If client only requested connection verification, finish generator
            if request.query_params.get("once") == "true":
                return

            while not await request.is_disconnected():
                try:
                    # Wait for live event or timeout after 5s for ping
                    event_data = await asyncio.wait_for(queue.get(), timeout=5.0)
                    yield {
                        "event": "tool_event",
                        "data": json.dumps(event_data)
                    }
                except asyncio.TimeoutError:
                    yield {
                        "event": "ping",
                        "data": json.dumps({"status": "active"})
                    }
        finally:
            _EVENT_SUBSCRIBERS.discard(queue)

    response = EventSourceResponse(event_generator(), ping=15)
    response.headers["Cache-Control"] = "no-cache, no-transform"
    response.headers["X-Accel-Buffering"] = "no"
    return response
