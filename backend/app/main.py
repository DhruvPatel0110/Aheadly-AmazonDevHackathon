import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Query, Response, UploadFile, File, Form, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db
from app.schemas import Deadline, DeadlineCreate, DeadlineUpdate, Source, SourceCreate, ChatRequest, Reminder
from app.services.deadline_service import DeadlineService
from app.services.calendar_service import generate_ics_content
from app.services.mcp_client import MCPClientBridge
from app.services.agent_service import DeadlineAgentService
from app.mcp_server.server import mcp_server
from app.mcp_server.transport import mcp_router
from app.parsers.text_parser import parse_text_input
from app.parsers.email_parser import parse_email_input
from app.parsers.pdf_parser import parse_pdf_input, ScannedPdfError

logger = logging.getLogger(__name__)

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MiB ceiling (SEC-002)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database on startup
    await init_db()

    # Lightweight local background reminder delivery worker (60s tick)
    async def reminder_worker():
        while True:
            try:
                await asyncio.sleep(60)
                await DeadlineService.process_due_reminders()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in background reminder worker: {e}")

    worker_task = asyncio.create_task(reminder_worker())
    yield
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Aheadly: Evidence-backed personal deadline rescue agent for the Alexa+ hackathon track.",
    lifespan=lifespan
)

# CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount MCP Streamable HTTP / SSE router
app.include_router(mcp_router)


# ---------------------------------------------------------------------------
# System & Meta Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
        "mcp_protocol": settings.mcp_protocol_version,
        "budget_mode": "Strict ₹0 out-of-pocket"
    }


@app.get("/api/info")
async def app_info():
    return {
        "track": "Alexa+",
        "mcp_server": settings.mcp_server_name,
        "protocol_version": settings.mcp_protocol_version,
        "storage": "Local SQLite",
        "llm_dependency": "None required (Deterministic parser + optional local Ollama)"
    }


@app.get("/api/mcp/tools")
async def list_mcp_tools():
    """List all registered MCP tools and their parameter schemas for UI inspection."""
    tools = await mcp_server.list_tools()
    return [
        {
            "name": t.name,
            "description": t.description,
            "inputSchema": getattr(t, "input_schema", None) or getattr(t, "inputSchema", None)
        }
        for t in tools
    ]


@app.get("/api/mcp/log")
async def get_mcp_log(limit: int = Query(50, ge=1, le=200)):
    """Retrieve chronological tool call log for the judge inspection panel."""
    return MCPClientBridge.get_logs(limit=limit)


@app.delete("/api/mcp/log")
async def clear_mcp_log():
    """Clear recorded MCP tool call history."""
    MCPClientBridge.clear_logs()
    return {"status": "cleared"}


class ToolCallRequest(BaseModel):
    tool: str
    arguments: Dict[str, Any] = {}


@app.post("/api/mcp/call")
async def call_mcp_tool_route(req: ToolCallRequest):
    """Directly execute an MCP tool via the official in-process MCPClientBridge."""
    try:
        res = await MCPClientBridge.call_tool(req.tool, req.arguments)
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))



@app.post("/api/demo/reset")
async def reset_demo_database(
    request: Request,
    confirm: Optional[bool] = Query(None),
    x_confirm_reset: Optional[str] = Header(None)
):
    """
    Reset the database and MCP logs for a clean demonstration state (SEC-001).
    Restricted to local clients and requires confirmation query, header, or body.
    """
    client_host = request.client.host if request.client else "unknown"
    is_local = client_host in ("127.0.0.1", "localhost", "::1", "testclient")
    if not is_local:
        raise HTTPException(status_code=403, detail="Demo reset is restricted to local demonstration clients.")

    confirmed = (confirm is True) or (x_confirm_reset == "confirm-reset")
    if not confirmed:
        try:
            body = await request.json()
            if isinstance(body, dict) and body.get("confirm") is True:
                confirmed = True
        except Exception:
            pass

    if not confirmed:
        raise HTTPException(
            status_code=400,
            detail="Confirmation required: pass ?confirm=true, X-Confirm-Reset: confirm-reset header, or {'confirm': true} in JSON body."
        )

    await DeadlineService.clear_all_data()
    MCPClientBridge.clear_logs()
    return {"status": "reset", "message": "Demo database and MCP tool call logs successfully cleared."}



@app.get("/api/stats")
async def get_stats():
    """Aggregate summary statistics for active dashboard."""
    return await DeadlineService.get_stats()


# ---------------------------------------------------------------------------
# Ingestion & Upload Endpoint
# ---------------------------------------------------------------------------

@app.post("/api/sources/upload")
async def upload_source(
    file: Optional[UploadFile] = File(None),
    raw_text: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    source_type: Optional[str] = Form(None)
):
    """
    Ingest a document (PDF, EML, TXT) or raw pasted text snippet.
    Dispatches through the MCP tool pipeline: ingest_source -> find_deadline_candidates.
    Enforces a strict 10 MiB limit (SEC-002) and validates permitted file formats.
    """
    if file:
        chunks = []
        total_size = 0
        while True:
            chunk = await file.read(64 * 1024)
            if not chunk:
                break
            total_size += len(chunk)
            if total_size > MAX_UPLOAD_SIZE:
                raise HTTPException(
                    status_code=413,
                    detail=f"Uploaded file exceeds maximum allowed size of {MAX_UPLOAD_SIZE // (1024 * 1024)} MiB."
                )
            chunks.append(chunk)

        if total_size == 0:
            raise HTTPException(status_code=400, detail="Uploaded file cannot be empty.")

        content_bytes = b"".join(chunks)
        filename = file.filename or "uploaded_file"
        lower_fn = filename.lower()
        valid_exts = (".pdf", ".eml", ".txt", ".text")
        if not any(lower_fn.endswith(ext) for ext in valid_exts):
            raise HTTPException(
                status_code=415,
                detail=f"Unsupported file format for '{filename}'. Allowed types: .pdf, .eml, .txt"
            )

        if lower_fn.endswith(".pdf"):
            try:
                parsed = parse_pdf_input(content_bytes, default_title=title or filename)
            except ScannedPdfError as spe:
                raise HTTPException(status_code=422, detail=str(spe))
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"PDF parsing error: {str(e)}")
            stype = "pdf"
        elif lower_fn.endswith(".eml") or (file.content_type and "email" in file.content_type.lower()):
            parsed = parse_email_input(content_bytes, default_title=title or filename)
            stype = "email"
        else:
            text_str = content_bytes.decode("utf-8", errors="replace")
            parsed = parse_text_input(text_str, default_title=title or filename, source_type=source_type)
            stype = parsed["source_type"]

        target_text = parsed["clean_text"]
        target_title = title.strip() if (title and title.strip()) else parsed["title"]
    elif raw_text and raw_text.strip():
        if len(raw_text.encode("utf-8")) > MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"Pasted text exceeds maximum allowed size of {MAX_UPLOAD_SIZE // (1024 * 1024)} MiB."
            )
        parsed = parse_text_input(raw_text, default_title=title or "Pasted Text", source_type=source_type)
        target_text = parsed["clean_text"]
        target_title = title.strip() if (title and title.strip()) else parsed["title"]
        stype = parsed["source_type"]
    else:
        raise HTTPException(status_code=400, detail="Either a file or raw_text must be provided.")

    # Execute MCP tool pipeline
    ingest_res = await MCPClientBridge.call_tool("ingest_source", {
        "raw_text": target_text,
        "title": target_title,
        "source_type": stype
    })

    candidates = await MCPClientBridge.call_tool("find_deadline_candidates", {
        "source_id": ingest_res["source_id"]
    })

    return {
        "source": ingest_res,
        "candidates": candidates,
        "candidates_count": len(candidates)
    }


@app.get("/api/sources/{source_id}", response_model=Source)
async def get_source_endpoint(source_id: str):
    """Retrieve full source record for verbatim evidence inspection (FE-002)."""
    source = await DeadlineService.get_source(source_id)
    if not source:
        raise HTTPException(status_code=404, detail=f"Source with ID '{source_id}' not found.")
    return source


@app.get("/api/reminders/due", response_model=List[Reminder])
async def list_due_reminders():
    """List scheduled reminders that are due or past due (Section 6.3)."""
    return await DeadlineService.get_due_reminders()


@app.post("/api/reminders/process")
async def process_due_reminders_endpoint():
    """Trigger processing of due reminders to fired status."""
    fired = await DeadlineService.process_due_reminders()
    return {"processed_count": len(fired), "fired": [r.model_dump() for r in fired]}


# ---------------------------------------------------------------------------
# Conversational Agent Endpoint (Simulated Alexa+)
# ---------------------------------------------------------------------------


@app.post("/api/agent/chat")
async def chat_with_agent(req: ChatRequest):
    """
    Conversational agent endpoint that dispatches natural language queries to MCP tools.
    """
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    return await DeadlineAgentService.process_chat(
        message=req.message,
        active_deadline_id=req.active_deadline_id
    )


# ---------------------------------------------------------------------------
# Deadlines REST Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/deadlines", response_model=List[Deadline])
async def list_deadlines(
    status: Optional[str] = Query(None, description="Filter by status"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(50, ge=1, le=200)
):
    return await DeadlineService.list_deadlines(status_filter=status, category_filter=category, limit=limit)


@app.get("/api/deadlines/{deadline_id}", response_model=Deadline)
async def get_deadline(deadline_id: str):
    deadline = await DeadlineService.get_deadline(deadline_id)
    if not deadline:
        raise HTTPException(status_code=404, detail="Deadline not found")
    return deadline


@app.get("/api/deadlines/{deadline_id}/ics")
async def download_deadline_ics(deadline_id: str):
    deadline = await DeadlineService.get_deadline(deadline_id)
    if not deadline:
        raise HTTPException(status_code=404, detail="Deadline not found")
    if not deadline.candidate_date or deadline.candidate_date == "UNVERIFIED":
        raise HTTPException(status_code=400, detail="Cannot export calendar for unverified deadline")
    try:
        reminders = await DeadlineService.get_reminders(deadline_id)
        ics_text = generate_ics_content(deadline, reminders)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return Response(
        content=ics_text,
        media_type="text/calendar",
        headers={"Content-Disposition": f"attachment; filename=deadline-{deadline.id}.ics"}
    )


@app.patch("/api/deadlines/{deadline_id}", response_model=Deadline)
async def update_deadline(deadline_id: str, update_in: DeadlineUpdate):
    updated = await DeadlineService.update_deadline(deadline_id, update_in)
    if not updated:
        raise HTTPException(status_code=404, detail="Deadline not found")
    return updated


@app.delete("/api/deadlines/{deadline_id}")
async def delete_deadline(deadline_id: str):
    success = await DeadlineService.delete_deadline(deadline_id)
    if not success:
        raise HTTPException(status_code=404, detail="Deadline not found")
    return {"status": "deleted", "id": deadline_id}


@app.get("/api/deadlines/{deadline_id}/audit")
async def get_deadline_audit(deadline_id: str):
    return await DeadlineService.get_audit_logs(deadline_id)
