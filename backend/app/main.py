"""
Deadline Rescue - Main Application Entrypoint
FastAPI Backend + Streamable HTTP MCP Server Mount
"""
from contextlib import asynccontextmanager
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db
from app.models import Deadline, DeadlineCreate, DeadlineUpdate, Source, SourceCreate
from app.services.deadline_service import DeadlineService
from app.services.calendar_service import generate_ics_content
from app.mcp_server.server import mcp_server
from app.mcp_server.transport import mcp_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database on startup
    await init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Evidence-backed deadline rescue agent for the Alexa+ hackathon track.",
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


@app.get("/api/stats")
async def get_stats():
    return await DeadlineService.get_stats()


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
    reminders = await DeadlineService.get_reminders(deadline_id)
    ics_text = generate_ics_content(deadline, reminders)
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


@app.get("/api/deadlines/{deadline_id}/audit")
async def get_deadline_audit(deadline_id: str):
    return await DeadlineService.get_audit_logs(deadline_id)
