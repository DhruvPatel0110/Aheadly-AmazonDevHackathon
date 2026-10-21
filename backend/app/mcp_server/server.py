"""
Official MCP Server for Deadline Rescue (Spec 2025-11-25+ over Streamable HTTP).
Registers the 8 core tools and exposes ASGI Streamable HTTP and JSON-RPC 2.0 transports.
"""
import logging
from typing import List, Dict, Any, Optional
from mcp.server.mcpserver import MCPServer
from app.mcp_server.tools import DeadlineRescueTools
from app.config import settings

logger = logging.getLogger(__name__)

# Initialize official MCPServer
mcp_server = MCPServer(
    name=settings.mcp_server_name,
    version=settings.app_version,
    instructions="Evidence-backed deadline tracking, verification, and follow-through tools for Alexa+."
)

# ---------------------------------------------------------------------------
# Tool 1: ingest_source
# ---------------------------------------------------------------------------
@mcp_server.tool(
    name="ingest_source",
    description="Ingest raw text, email notices, or bill messages into the local source repository."
)
async def ingest_source(raw_text: str, title: str = "", source_type: str = "manual") -> Dict[str, Any]:
    """Ingest a new text or document into the local database and return the assigned source ID."""
    return await DeadlineRescueTools.ingest_source(raw_text=raw_text, title=title, source_type=source_type)


# ---------------------------------------------------------------------------
# Tool 2: find_deadline_candidates
# ---------------------------------------------------------------------------
@mcp_server.tool(
    name="find_deadline_candidates",
    description="Search source records and identify potential bills, renewals, validity dates, or cancellation windows with evidence spans."
)
async def find_deadline_candidates(source_id: str) -> List[Dict[str, Any]]:
    """Scan the given source record for candidate obligations and persist them to SQLite."""
    return await DeadlineRescueTools.find_deadline_candidates(source_id=source_id)


# ---------------------------------------------------------------------------
# Tool 3: get_deadline_evidence
# ---------------------------------------------------------------------------
@mcp_server.tool(
    name="get_deadline_evidence",
    description="Retrieve verbatim evidence quote, source context, and attribution coordinates for a candidate deadline."
)
async def get_deadline_evidence(deadline_id: str) -> Dict[str, Any]:
    """Retrieve the verbatim evidence snippet and source metadata for a specific deadline."""
    return await DeadlineRescueTools.get_deadline_evidence(deadline_id=deadline_id)


# ---------------------------------------------------------------------------
# Tool 4: confirm_or_correct_deadline
# ---------------------------------------------------------------------------
@mcp_server.tool(
    name="confirm_or_correct_deadline",
    description="Confirm, amend, or correct a candidate deadline date and provider name. Updates status and logs audit diff."
)
async def confirm_or_correct_deadline(
    deadline_id: str,
    confirmed_date: str = "",
    provider_name: str = "",
    notes: str = ""
) -> Dict[str, Any]:
    """Confirm or update candidate date and provider information with audit trail recording."""
    return await DeadlineRescueTools.confirm_or_correct_deadline(
        deadline_id=deadline_id,
        confirmed_date=confirmed_date,
        provider_name=provider_name,
        notes=notes
    )


# ---------------------------------------------------------------------------
# Tool 5: create_follow_up
# ---------------------------------------------------------------------------
@mcp_server.tool(
    name="create_follow_up",
    description="Create in-app reminder schedules (e.g. 7 days and 1 day prior) and optionally generate a downloadable .ics calendar."
)
async def create_follow_up(
    deadline_id: str,
    lead_days: Optional[List[int]] = None,
    export_calendar: bool = False
) -> Dict[str, Any]:
    """Schedule advance reminders and optionally generate RFC 5545 .ics calendar data."""
    return await DeadlineRescueTools.create_follow_up(
        deadline_id=deadline_id,
        lead_days=lead_days,
        export_calendar=export_calendar
    )


# ---------------------------------------------------------------------------
# Tool 6: prepare_next_step
# ---------------------------------------------------------------------------
@mcp_server.tool(
    name="prepare_next_step",
    description="Build an actionable checklist and surface verified official provider links for payment, renewal, or cancellation."
)
async def prepare_next_step(deadline_id: str) -> Dict[str, Any]:
    """Prepare provider-specific action checklist and verified account URLs."""
    return await DeadlineRescueTools.prepare_next_step(deadline_id=deadline_id)


# ---------------------------------------------------------------------------
# Tool 7: update_deadline_status
# ---------------------------------------------------------------------------
@mcp_server.tool(
    name="update_deadline_status",
    description="Transition deadline status (completed, cancelled, action_needed). Maintains distinction between user report and external verification."
)
async def update_deadline_status(
    deadline_id: str,
    new_status: str,
    resolution_notes: str = ""
) -> Dict[str, Any]:
    """Update task lifecycle state (completed, cancelled, action_needed)."""
    return await DeadlineRescueTools.update_deadline_status(
        deadline_id=deadline_id,
        new_status=new_status,
        resolution_notes=resolution_notes
    )


# ---------------------------------------------------------------------------
# Tool 8: list_deadlines
# ---------------------------------------------------------------------------
@mcp_server.tool(
    name="list_deadlines",
    description="Query tracked obligations with optional filtering by status and category."
)
async def list_deadlines(
    status_filter: str = "",
    category_filter: str = ""
) -> List[Dict[str, Any]]:
    """List tracked deadlines matching optional status and category filters."""
    return await DeadlineRescueTools.list_deadlines(
        status_filter=status_filter,
        category_filter=category_filter
    )


def validate_tool_arguments(tool_name: str, arguments: dict, schema: dict) -> Optional[str]:
    """
    Validate tool call arguments against its inputSchema.
    Returns error message string on failure, or None on success.
    """
    if not isinstance(arguments, dict):
        return f"Arguments for tool '{tool_name}' must be an object, got {type(arguments).__name__}"

    # Check required fields
    required = schema.get("required", [])
    for field in required:
        if field not in arguments:
            return f"Missing required argument: '{field}' for tool '{tool_name}'"
        if arguments[field] is None:
            return f"Required argument '{field}' cannot be null for tool '{tool_name}'"

    # Check types of provided arguments
    properties = schema.get("properties", {})
    for arg_name, arg_val in arguments.items():
        if arg_name in properties:
            prop_def = properties[arg_name]
            expected_type = prop_def.get("type")
            if expected_type == "string" and not isinstance(arg_val, str):
                return f"Invalid type for argument '{arg_name}': expected string, got {type(arg_val).__name__}"
            elif expected_type == "integer" and (isinstance(arg_val, bool) or not isinstance(arg_val, int)):
                return f"Invalid type for argument '{arg_name}': expected integer, got {type(arg_val).__name__}"
            elif expected_type == "number" and (isinstance(arg_val, bool) or not isinstance(arg_val, (int, float))):
                return f"Invalid type for argument '{arg_name}': expected number, got {type(arg_val).__name__}"
            elif expected_type == "boolean" and not isinstance(arg_val, bool):
                return f"Invalid type for argument '{arg_name}': expected boolean, got {type(arg_val).__name__}"
            elif expected_type == "array" and not isinstance(arg_val, list):
                return f"Invalid type for argument '{arg_name}': expected array, got {type(arg_val).__name__}"
            elif expected_type == "object" and not isinstance(arg_val, dict):
                return f"Invalid type for argument '{arg_name}': expected object, got {type(arg_val).__name__}"
    return None


# ---------------------------------------------------------------------------
# JSON-RPC 2.0 Direct Handler for HTTP POST & Test Compatibility
# ---------------------------------------------------------------------------

async def handle_jsonrpc_request(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Standard JSON-RPC 2.0 processor conforming to MCP protocol specification.
    Handles initialize, tools/list, and tools/call methods.
    """
    req_id = payload.get("id")
    method = payload.get("method")
    params = payload.get("params", {})

    if not method:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32600, "message": "Invalid Request: method is required"}
        }

    try:
        # 1. Initialize
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": settings.mcp_protocol_version,
                    "serverInfo": {
                        "name": settings.mcp_server_name,
                        "version": settings.app_version
                    },
                    "capabilities": {
                        "tools": {"listChanged": False}
                    }
                }
            }
        # 1.5. Initialized Notification
        elif method == "notifications/initialized":
            return {}

        # 2. Tools List
        elif method == "tools/list":
            tools_data = []
            registered_tools = await mcp_server.list_tools()
            for t in registered_tools:
                schema = getattr(t, "input_schema", None) or getattr(t, "inputSchema", None)
                if hasattr(schema, "model_dump"):
                    schema = schema.model_dump()
                tools_data.append({
                    "name": t.name,
                    "description": t.description,
                    "inputSchema": schema
                })
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": tools_data}
            }

        # 3. Tools Call
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            if not tool_name:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32602, "message": "Missing 'name' parameter for tools/call"}
                }

            tools = await mcp_server.list_tools()
            target_tool = next((t for t in tools if t.name == tool_name), None)
            if not target_tool:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Method/Tool '{tool_name}' not found"}
                }

            schema = getattr(target_tool, "input_schema", None) or getattr(target_tool, "inputSchema", None)
            if hasattr(schema, "model_dump"):
                schema = schema.model_dump()

            if schema:
                val_err = validate_tool_arguments(tool_name, arguments, schema)
                if val_err:
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {"code": -32602, "message": val_err}
                    }

            # Dispatch tool call
            if tool_name == "ingest_source":
                res = await ingest_source(**arguments)
            elif tool_name == "find_deadline_candidates":
                res = await find_deadline_candidates(**arguments)
            elif tool_name == "get_deadline_evidence":
                res = await get_deadline_evidence(**arguments)
            elif tool_name == "confirm_or_correct_deadline":
                res = await confirm_or_correct_deadline(**arguments)
            elif tool_name == "create_follow_up":
                res = await create_follow_up(**arguments)
            elif tool_name == "prepare_next_step":
                res = await prepare_next_step(**arguments)
            elif tool_name == "update_deadline_status":
                res = await update_deadline_status(**arguments)
            elif tool_name == "list_deadlines":
                res = await list_deadlines(**arguments)
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Method/Tool '{tool_name}' not found"}
                }

            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": str(res)}],
                    "structuredContent": res,
                    "isError": False
                }
            }

        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Method '{method}' not recognized"}
            }

    except Exception as e:
        logger.exception(f"Error handling JSON-RPC method {method}")
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32603,
                "message": f"Internal error during execution: {str(e)}"
            }
        }
