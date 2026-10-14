"""
Streamable HTTP and JSON-RPC 2.0 transport handler for MCP server.
Supports SSE (GET /mcp) and JSON-RPC 2.0 requests (POST /mcp).
"""
import json
import logging
from typing import Dict, Any
from fastapi import APIRouter, Request, Response
from sse_starlette.sse import EventSourceResponse
from app.mcp_server.server import mcp_server, handle_jsonrpc_request
from app.config import settings

logger = logging.getLogger(__name__)

mcp_router = APIRouter(tags=["MCP Server"])


@mcp_router.post("/mcp")
async def mcp_post_endpoint(request: Request) -> Dict[str, Any]:
    """
    HTTP POST endpoint for JSON-RPC 2.0 messages over MCP Streamable HTTP transport.
    Handles 'initialize', 'tools/list', and 'tools/call'.
    """
    try:
        body = await request.json()
    except Exception:
        return {
            "jsonrpc": "2.0",
            "id": None,
            "error": {"code": -32700, "message": "Parse error: invalid JSON payload"}
        }

    return await handle_jsonrpc_request(body)


@mcp_router.get("/mcp")
async def mcp_sse_endpoint(request: Request):
    """
    HTTP GET endpoint for Server-Sent Events (SSE) streamable transport.
    Emits an initial connection event announcing server details and readiness.
    """
    async def event_generator():
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

        import asyncio
        while not await request.is_disconnected():
            await asyncio.sleep(5)
            yield {
                "event": "ping",
                "data": json.dumps({"status": "active"})
            }

    response = EventSourceResponse(event_generator(), ping=15)
    response.headers["Cache-Control"] = "no-cache, no-transform"
    response.headers["X-Accel-Buffering"] = "no"
    return response
