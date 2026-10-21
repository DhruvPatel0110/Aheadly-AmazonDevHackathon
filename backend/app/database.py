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
    source_type TEXT NOT NULL CHECK (source_type IN ('email', 'pdf', 'sms', 'receipt', 'manual')),
    file_hash TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS deadlines (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    provider_name TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('subscription', 'insurance', 'broadband', 'mobile', 'utility', 'dth', 'return_window', 'other')),
    obligation_type TEXT NOT NULL CHECK (obligation_type IN ('payment_due', 'renewal', 'trial_ending', 'validity_expiry', 'cancellation_deadline', 'return_deadline')),
    candidate_date TEXT NOT NULL,
    original_date_str TEXT,
    amount REAL,
    currency TEXT NOT NULL DEFAULT 'INR',
    evidence_snippet TEXT NOT NULL,
    evidence_char_start INTEGER,
    evidence_char_end INTEGER,
    extraction_confidence REAL NOT NULL DEFAULT 0.8,
    verification_status TEXT NOT NULL DEFAULT 'source_stated' CHECK (verification_status IN ('source_stated', 'user_confirmed', 'estimated', 'unverified')),
    recurrence TEXT NOT NULL DEFAULT 'unconfirmed' CHECK (recurrence IN ('one_time', 'monthly', 'annual', 'unconfirmed')),
    official_url TEXT,
    next_step_instructions TEXT,
    status TEXT NOT NULL DEFAULT 'needs_review' CHECK (status IN ('needs_review', 'confirmed', 'upcoming', 'action_needed', 'completed', 'cancelled', 'date_unverified', 'dismissed')),
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
    status TEXT NOT NULL DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'fired', 'dismissed')),
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
CREATE UNIQUE INDEX IF NOT EXISTS idx_sources_file_hash ON sources(file_hash);
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
    """Initialize database tables and indexes idempotently with safe migration."""
    target_path = db_path or settings.db_path
    logger.info(f"Initializing SQLite database at: {target_path}")
    async with get_db(target_path) as db:
        # Pre-migration 1: deduplicate existing sources if needed so UNIQUE index succeeds
        try:
            async with db.execute(
                "SELECT file_hash, count(*) FROM sources WHERE file_hash IS NOT NULL GROUP BY file_hash HAVING count(*) > 1"
            ) as cur:
                dup_hashes = await cur.fetchall()
            for dup in dup_hashes:
                f_hash = dup[0]
                async with db.execute(
                    "SELECT id FROM sources WHERE file_hash = ? ORDER BY rowid ASC",
                    (f_hash,)
                ) as cur:
                    src_rows = await cur.fetchall()
                if src_rows:
                    keeper_id = src_rows[0][0]
                    duplicate_ids = [r[0] for r in src_rows[1:]]
                    for dup_id in duplicate_ids:
                        await db.execute(
                            "UPDATE deadlines SET source_id = ? WHERE source_id = ?",
                            (keeper_id, dup_id)
                        )
                        await db.execute("DELETE FROM sources WHERE id = ?", (dup_id,))
            await db.commit()
        except Exception as e:
            logger.debug(f"Pre-migration deduplication skipped: {e}")

        # Pre-migration 2: Add CHECK constraints to existing database tables if missing
        try:
            async with db.execute("SELECT name, sql FROM sqlite_master WHERE type='table'") as cur:
                raw_tables = await cur.fetchall()
                existing_tables = {r[0]: r[1] for r in raw_tables if r[1]}

            needs_enum_migration = any(
                t in existing_tables and ("CHECK" not in existing_tables[t] or "dismissed" not in existing_tables[t])
                for t in ["deadlines"]
            )
            if needs_enum_migration:
                logger.info("Migrating existing tables to enforce updated SQLite CHECK constraints...")
                await db.commit()
                await db.execute("PRAGMA foreign_keys = OFF;")
                for t in ["audit_logs", "reminders", "deadlines", "sources"]:
                    if t in existing_tables:
                        await db.execute(f"ALTER TABLE {t} RENAME TO {t}_old;")
                await db.executescript(SCHEMA_SQL)
                for t in ["sources", "deadlines", "reminders", "audit_logs"]:
                    if t in existing_tables:
                        # Inspect columns in new and old tables
                        async with db.execute(f"PRAGMA table_info({t})") as c1:
                            new_cols = [row[1] for row in await c1.fetchall()]
                        async with db.execute(f"PRAGMA table_info({t}_old)") as c2:
                            old_cols = [row[1] for row in await c2.fetchall()]
                        common_cols = [c for c in new_cols if c in old_cols]
                        cols_str = ", ".join(common_cols)
                        await db.execute(f"INSERT INTO {t} ({cols_str}) SELECT {cols_str} FROM {t}_old;")
                        await db.execute(f"DROP TABLE {t}_old;")
                
                # Verify foreign key integrity
                async with db.execute("PRAGMA foreign_key_check;") as cur:
                    fk_violations = await cur.fetchall()
                    if fk_violations:
                        logger.warning(f"Detected foreign key inconsistencies after migration: {fk_violations}")

                await db.commit()
                await db.execute("PRAGMA foreign_keys = ON;")
        except Exception as e:
            logger.error(f"CHECK constraint migration error: {e}", exc_info=True)
            await db.execute("PRAGMA foreign_keys = ON;")
            await db.commit()

        await db.executescript(SCHEMA_SQL)
        await db.commit()
    logger.info("Database schema initialized successfully.")
