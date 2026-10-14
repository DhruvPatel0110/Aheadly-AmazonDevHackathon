"""
Application Configuration - Deadline Rescue
Enforces strict ₹0 budget and local-first execution.
"""
from pathlib import Path
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

SAMPLE_DATA_DIR = BASE_DIR / "sample_data"
SAMPLE_DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "deadline_rescue.db"

class Settings(BaseModel):
    app_name: str = "Deadline Rescue"
    app_version: str = "1.0.0"
    mcp_server_name: str = "deadline-rescue-mcp"
    mcp_protocol_version: str = "2025-11-25"
    db_url: str = f"sqlite+aiosqlite:///{DB_PATH}"
    db_path: str = str(DB_PATH)
    host: str = "127.0.0.1"
    port: int = 8000
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ]

settings = Settings()
