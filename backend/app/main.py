"""
Deadline Rescue - Main Application Entrypoint
FastAPI Backend + Streamable HTTP MCP Server Mount
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Evidence-backed deadline rescue agent for the Alexa+ hackathon track."
)

# CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
