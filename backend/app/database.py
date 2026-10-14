"""
Database connection and schema management using aiosqlite.
Strictly ₹0 local storage with ACID compliance and foreign key enforcement.
"""
import aiosqlite
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from app.config import settings

logger = logging.getLogger(__name__)

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    raw_text TEXT NOT NULL,
    source_type TEXT NOT NULL,
    file_hash TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS deadlines (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    provider_name TEXT NOT NULL,
    category TEXT NOT NULL,
    obligation_type TEXT NOT NULL,
    candidate_date TEXT NOT NULL,
    original_date_str TEXT,
    amount REAL,
    currency TEXT NOT NULL DEFAULT 'INR',
    evidence_snippet TEXT NOT NULL,
    evidence_char_start INTEGER,
    evidence_char_end INTEGER,
    extraction_confidence REAL NOT NULL DEFAULT 0.8,
    verification_status TEXT NOT NULL DEFAULT 'source_stated',
    recurrence TEXT NOT NULL DEFAULT 'unconfirmed',
    official_url TEXT,
    next_step_instructions TEXT,
    status TEXT NOT NULL DEFAULT 'needs_review',
    owner TEXT DEFAULT 'Self',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS reminders (
    id TEXT PRIMARY KEY,
    deadline_id TEXT NOT NULL,
    remind_at TEXT NOT NULL,
    lead_days INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'scheduled',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (deadline_id) REFERENCES deadlines(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id TEXT PRIMARY KEY,
    deadline_id TEXT NOT NULL,
    action TEXT NOT NULL,
    previous_value TEXT,
    new_value TEXT,
    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (deadline_id) REFERENCES deadlines(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_deadlines_status ON deadlines(status);
CREATE INDEX IF NOT EXISTS idx_deadlines_date ON deadlines(candidate_date);
CREATE INDEX IF NOT EXISTS idx_deadlines_source ON deadlines(source_id);
CREATE INDEX IF NOT EXISTS idx_reminders_deadline ON reminders(deadline_id);
CREATE INDEX IF NOT EXISTS idx_audit_deadline ON audit_logs(deadline_id);
"""

@asynccontextmanager
async def get_db(db_path: str = None) -> AsyncGenerator[aiosqlite.Connection, None]:
    """Provide an asynchronous connection to the SQLite database with row dicts."""
    target_path = db_path or settings.db_path
    db = await aiosqlite.connect(target_path)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON;")
    try:
        yield db
    finally:
        await db.close()


async def init_db(db_path: str = None) -> None:
    """Initialize database tables and indexes idempotently."""
    target_path = db_path or settings.db_path
    logger.info(f"Initializing SQLite database at: {target_path}")
    async with get_db(target_path) as db:
        await db.executescript(SCHEMA_SQL)
        await db.commit()
    logger.info("Database schema initialized successfully.")
