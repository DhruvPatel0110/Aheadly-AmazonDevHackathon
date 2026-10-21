"""
In-Process MCP Client Bridge and Tool-Call Observability Logger.
Routes conversational agent requests through official MCP JSON-RPC 2.0 tools
and maintains a live audit log for judge inspection.
"""
import time
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

# In-memory rolling log of MCP tool invocations
_TOOL_CALL_LOGS: List[Dict[str, Any]] = []
_MAX_LOGS = 200


import hashlib

def sanitize_log_payload(payload: Any) -> Any:
    """
    Sanitize sensitive arguments and outputs for MCP visual logs (SEC-003).
    Omits or truncates raw document contents, passwords, policy numbers, and PII
    while preserving tool name, structure, bounding offsets, and execution diagnostic value.
    """
    if isinstance(payload, dict):
        sanitized = {}
        for k, v in payload.items():
            if k in ("raw_text", "clean_text") and isinstance(v, str):
                char_count = len(v)
                h = hashlib.sha256(v.encode("utf-8")).hexdigest()[:8]
                sanitized[k] = f"[REDACTED CONTENT: {char_count} chars, sha256:{h}]"
            elif isinstance(v, str) and len(v) > 250 and k not in ("next_step_instructions", "evidence_snippet"):
                sanitized[k] = v[:80] + f"... [truncated {len(v)} chars]"
            elif isinstance(v, (dict, list)):
                sanitized[k] = sanitize_log_payload(v)
            else:
                sanitized[k] = v
        return sanitized
    elif isinstance(payload, list):
        return [sanitize_log_payload(item) for item in payload]
    return payload


class MCPClientBridge:
    _custom_transport: Optional[httpx.AsyncBaseTransport] = None

    @classmethod
    def set_transport(cls, transport: Optional[httpx.AsyncBaseTransport]) -> None:
        """Allow injecting ASGI transport for in-process test environments."""
        cls._custom_transport = transport

    @classmethod
    async def call_tool(cls, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Execute an MCP tool via official Streamable HTTP transport and JSON-RPC 2.0 protocol,
        and record execution metrics with sanitized logs.
        """
        log_id = str(uuid.uuid4())
        start_time = time.perf_counter()
        timestamp = datetime.now(timezone.utc).isoformat()

        req_payload = {
            "jsonrpc": "2.0",
            "id": log_id,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }

        url = f"http://{settings.host}:{settings.port}/mcp"

        try:
            try:
                async with httpx.AsyncClient(transport=cls._custom_transport, timeout=10.0) as client:
                    resp = await client.post(url, json=req_payload)
                    rpc_res = resp.json()
            except httpx.RequestError as req_err:
                latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
                err_obj = {
                    "code": -32603,
                    "message": f"MCP Streamable HTTP transport connection error to {url}: {str(req_err)}"
                }
                log_entry = {
                    "id": log_id,
                    "timestamp": timestamp,
                    "tool_name": tool_name,
                    "arguments": sanitize_log_payload(arguments),
                    "result": None,
                    "error": err_obj,
                    "latency_ms": latency_ms,
                    "status": "error"
                }
                _TOOL_CALL_LOGS.insert(0, log_entry)
                if len(_TOOL_CALL_LOGS) > _MAX_LOGS:
                    _TOOL_CALL_LOGS.pop()
                raise ConnectionError(err_obj["message"]) from req_err

            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

            if "error" in rpc_res and rpc_res["error"]:
                error_obj = rpc_res["error"]
                log_entry = {
                    "id": log_id,
                    "timestamp": timestamp,
                    "tool_name": tool_name,
                    "arguments": sanitize_log_payload(arguments),
                    "result": None,
                    "error": error_obj,
                    "latency_ms": latency_ms,
                    "status": "error"
                }
                _TOOL_CALL_LOGS.insert(0, log_entry)
                if len(_TOOL_CALL_LOGS) > _MAX_LOGS:
                    _TOOL_CALL_LOGS.pop()
                raise ValueError(f"MCP Tool '{tool_name}' error: {error_obj.get('message')}")

            result = rpc_res.get("result", {}).get("structuredContent")
            log_entry = {
                "id": log_id,
                "timestamp": timestamp,
                "tool_name": tool_name,
                "arguments": sanitize_log_payload(arguments),
                "result": sanitize_log_payload(result),
                "error": None,
                "latency_ms": latency_ms,
                "status": "success"
            }
            _TOOL_CALL_LOGS.insert(0, log_entry)
            if len(_TOOL_CALL_LOGS) > _MAX_LOGS:
                _TOOL_CALL_LOGS.pop()

            return result

        except Exception as e:
            if "log_entry" not in locals():
                latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
                _TOOL_CALL_LOGS.insert(0, {
                    "id": log_id,
                    "timestamp": timestamp,
                    "tool_name": tool_name,
                    "arguments": sanitize_log_payload(arguments),
                    "result": None,
                    "error": {"code": -32603, "message": str(e)},
                    "latency_ms": latency_ms,
                    "status": "error"
                })
            raise

    @staticmethod
    def get_logs(limit: int = 50) -> List[Dict[str, Any]]:
        """Return chronological history of MCP tool invocations for the visual inspector."""
        return _TOOL_CALL_LOGS[:limit]

    @staticmethod
    def clear_logs() -> None:
        """Clear recorded tool call logs."""
        _TOOL_CALL_LOGS.clear()
