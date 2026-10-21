"""
Service layer for managing Sources, Deadlines, Reminders, and Audit Trails.
Coordinates business logic and database persistence using aiosqlite.
"""
import uuid
import json
import logging
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from app.database import get_db
from app.models import (
    Source, SourceCreate,
    Deadline, DeadlineCreate, DeadlineUpdate, DeadlineStatus,
    Reminder, ReminderCreate, ReminderStatus,
    AuditLog
)

logger = logging.getLogger(__name__)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class DeadlineService:
    @staticmethod
    async def create_source(source_in: SourceCreate, db_path: Optional[str] = None) -> Source:
        """
        Create a new source record or return an existing source if file_hash already exists.

        Computes SHA-256 of raw_text if file_hash is not explicitly provided.
        If a source with the file_hash already exists in the database, returns the existing
        source with a 'duplicate': True flag and does not insert a new row.
        """
        file_hash = source_in.file_hash or hashlib.sha256(source_in.raw_text.encode("utf-8")).hexdigest()

        async with get_db(db_path) as db:
            if file_hash:
                async with db.execute(
                    "SELECT id, title, raw_text, source_type, file_hash, created_at FROM sources WHERE file_hash = ?",
                    (file_hash,)
                ) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        return Source(
                            id=row["id"],
                            title=row["title"],
                            raw_text=row["raw_text"],
                            source_type=row["source_type"],
                            file_hash=row["file_hash"],
                            created_at=str(row["created_at"]),
                            duplicate=True
                        )

            source_id = str(uuid.uuid4())
            created_at = _utc_now_iso()
            query = """
            INSERT INTO sources (id, title, raw_text, source_type, file_hash, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """
            await db.execute(
                query,
                (source_id, source_in.title, source_in.raw_text, source_in.source_type.value,
                 file_hash, created_at)
            )
            await db.commit()

        return Source(
            id=source_id,
            title=source_in.title,
            raw_text=source_in.raw_text,
            source_type=source_in.source_type,
            file_hash=file_hash,
            created_at=created_at,
            duplicate=False
        )

    @staticmethod
    async def get_source(source_id: str, db_path: Optional[str] = None) -> Optional[Source]:
        query = "SELECT * FROM sources WHERE id = ?"
        async with get_db(db_path) as db:
            async with db.execute(query, (source_id,)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return None
                return Source(
                    id=row["id"],
                    title=row["title"],
                    raw_text=row["raw_text"],
                    source_type=row["source_type"],
                    file_hash=row["file_hash"],
                    created_at=str(row["created_at"])
                )

    @staticmethod
    async def create_deadline(deadline_in: DeadlineCreate, db_path: Optional[str] = None) -> Deadline:
        deadline_id = str(uuid.uuid4())
        now = _utc_now_iso()

        insert_sql = """
        INSERT INTO deadlines (
            id, source_id, provider_name, category, obligation_type,
            candidate_date, original_date_str, amount, currency,
            evidence_snippet, evidence_char_start, evidence_char_end,
            extraction_confidence, verification_status, recurrence,
            official_url, next_step_instructions, status, owner,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        async with get_db(db_path) as db:
            await db.execute(
                insert_sql,
                (
                    deadline_id, deadline_in.source_id, deadline_in.provider_name,
                    deadline_in.category.value, deadline_in.obligation_type.value,
                    deadline_in.candidate_date, deadline_in.original_date_str,
                    deadline_in.amount, deadline_in.currency,
                    deadline_in.evidence_snippet, deadline_in.evidence_char_start,
                    deadline_in.evidence_char_end, deadline_in.extraction_confidence,
                    deadline_in.verification_status.value, deadline_in.recurrence.value,
                    deadline_in.official_url, deadline_in.next_step_instructions,
                    deadline_in.status.value, deadline_in.owner,
                    now, now
                )
            )

            # Record initial audit entry
            audit_id = str(uuid.uuid4())
            audit_sql = """
            INSERT INTO audit_logs (id, deadline_id, action, previous_value, new_value, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """
            await db.execute(
                audit_sql,
                (audit_id, deadline_id, "extracted", None, json.dumps({
                    "provider": deadline_in.provider_name,
                    "date": deadline_in.candidate_date,
                    "status": deadline_in.status.value
                }), now)
            )
            await db.commit()

        return Deadline(
            id=deadline_id,
            source_id=deadline_in.source_id,
            provider_name=deadline_in.provider_name,
            category=deadline_in.category,
            obligation_type=deadline_in.obligation_type,
            candidate_date=deadline_in.candidate_date,
            original_date_str=deadline_in.original_date_str,
            amount=deadline_in.amount,
            currency=deadline_in.currency,
            evidence_snippet=deadline_in.evidence_snippet,
            evidence_char_start=deadline_in.evidence_char_start,
            evidence_char_end=deadline_in.evidence_char_end,
            extraction_confidence=deadline_in.extraction_confidence,
            verification_status=deadline_in.verification_status,
            recurrence=deadline_in.recurrence,
            official_url=deadline_in.official_url,
            next_step_instructions=deadline_in.next_step_instructions,
            status=deadline_in.status,
            owner=deadline_in.owner,
            created_at=now,
            updated_at=now
        )

    @staticmethod
    async def get_deadline(deadline_id: str, db_path: Optional[str] = None) -> Optional[Deadline]:
        query = "SELECT * FROM deadlines WHERE id = ?"
        async with get_db(db_path) as db:
            async with db.execute(query, (deadline_id,)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return None
                return Deadline(
                    id=row["id"],
                    source_id=row["source_id"],
                    provider_name=row["provider_name"],
                    category=row["category"],
                    obligation_type=row["obligation_type"],
                    candidate_date=row["candidate_date"],
                    original_date_str=row["original_date_str"],
                    amount=row["amount"],
                    currency=row["currency"],
                    evidence_snippet=row["evidence_snippet"],
                    evidence_char_start=row["evidence_char_start"],
                    evidence_char_end=row["evidence_char_end"],
                    extraction_confidence=row["extraction_confidence"],
                    verification_status=row["verification_status"],
                    recurrence=row["recurrence"],
                    official_url=row["official_url"],
                    next_step_instructions=row["next_step_instructions"],
                    status=row["status"],
                    owner=row["owner"],
                    created_at=str(row["created_at"]),
                    updated_at=str(row["updated_at"])
                )

    @staticmethod
    async def list_deadlines(
        status_filter: Optional[str] = None,
        category_filter: Optional[str] = None,
        limit: int = 50,
        db_path: Optional[str] = None
    ) -> List[Deadline]:
        clauses = []
        params = []

        if status_filter:
            clauses.append("status = ?")
            params.append(status_filter)
        if category_filter:
            clauses.append("category = ?")
            params.append(category_filter)

        where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        query = f"SELECT * FROM deadlines {where_clause} ORDER BY candidate_date ASC LIMIT ?"
        params.append(limit)

        results = []
        async with get_db(db_path) as db:
            async with db.execute(query, tuple(params)) as cursor:
                rows = await cursor.fetchall()
                for row in rows:
                    results.append(
                        Deadline(
                            id=row["id"],
                            source_id=row["source_id"],
                            provider_name=row["provider_name"],
                            category=row["category"],
                            obligation_type=row["obligation_type"],
                            candidate_date=row["candidate_date"],
                            original_date_str=row["original_date_str"],
                            amount=row["amount"],
                            currency=row["currency"],
                            evidence_snippet=row["evidence_snippet"],
                            evidence_char_start=row["evidence_char_start"],
                            evidence_char_end=row["evidence_char_end"],
                            extraction_confidence=row["extraction_confidence"],
                            verification_status=row["verification_status"],
                            recurrence=row["recurrence"],
                            official_url=row["official_url"],
                            next_step_instructions=row["next_step_instructions"],
                            status=row["status"],
                            owner=row["owner"],
                            created_at=str(row["created_at"]),
                            updated_at=str(row["updated_at"])
                        )
                    )
        return results

    @staticmethod
    async def update_deadline(
        deadline_id: str,
        update_in: DeadlineUpdate,
        db_path: Optional[str] = None
    ) -> Optional[Deadline]:
        current = await DeadlineService.get_deadline(deadline_id, db_path)
        if not current:
            return None

        fields_to_update = {}
        diff_previous = {}
        diff_new = {}

        data = update_in.model_dump(exclude_unset=True)
        for key, val in data.items():
            if key == "resolution_notes":
                continue
            if val is not None:
                val_to_store = val.value if hasattr(val, "value") else val
                current_val = getattr(current, key)
                current_val_clean = current_val.value if hasattr(current_val, "value") else current_val
                if val_to_store != current_val_clean:
                    fields_to_update[key] = val_to_store
                    diff_previous[key] = current_val_clean
                    diff_new[key] = val_to_store

        if not fields_to_update:
            return current

        now = _utc_now_iso()
        fields_to_update["updated_at"] = now

        set_clause = ", ".join([f"{k} = ?" for k in fields_to_update.keys()])
        query = f"UPDATE deadlines SET {set_clause} WHERE id = ?"
        params = list(fields_to_update.values()) + [deadline_id]

        async with get_db(db_path) as db:
            await db.execute(query, tuple(params))

            # Record audit trail
            action = "status_changed" if "status" in fields_to_update else "user_edited"
            audit_id = str(uuid.uuid4())
            audit_sql = """
            INSERT INTO audit_logs (id, deadline_id, action, previous_value, new_value, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """
            await db.execute(
                audit_sql,
                (audit_id, deadline_id, action, json.dumps(diff_previous), json.dumps(diff_new), now)
            )
            await db.commit()

        return await DeadlineService.get_deadline(deadline_id, db_path)

    @staticmethod
    async def get_deadlines_by_source(source_id: str, db_path: Optional[str] = None) -> List[Deadline]:
        """Retrieve all tracked deadlines associated with a specific ingested source."""
        query = "SELECT * FROM deadlines WHERE source_id = ? ORDER BY candidate_date ASC"
        results = []
        async with get_db(db_path) as db:
            async with db.execute(query, (source_id,)) as cursor:
                rows = await cursor.fetchall()
                for row in rows:
                    results.append(
                        Deadline(
                            id=row["id"],
                            source_id=row["source_id"],
                            provider_name=row["provider_name"],
                            category=row["category"],
                            obligation_type=row["obligation_type"],
                            candidate_date=row["candidate_date"],
                            original_date_str=row["original_date_str"],
                            amount=row["amount"],
                            currency=row["currency"],
                            evidence_snippet=row["evidence_snippet"],
                            evidence_char_start=row["evidence_char_start"],
                            evidence_char_end=row["evidence_char_end"],
                            extraction_confidence=row["extraction_confidence"],
                            verification_status=row["verification_status"],
                            recurrence=row["recurrence"],
                            official_url=row["official_url"],
                            next_step_instructions=row["next_step_instructions"],
                            status=row["status"],
                            owner=row["owner"],
                            created_at=str(row["created_at"]),
                            updated_at=str(row["updated_at"])
                        )
                    )
        return results

    @staticmethod
    async def create_reminders(
        deadline_id: str,
        lead_days: List[int],
        db_path: Optional[str] = None
    ) -> List[Reminder]:
        deadline = await DeadlineService.get_deadline(deadline_id, db_path)
        if not deadline:
            raise ValueError(f"Deadline with ID {deadline_id} not found.")

        # Validate candidate date
        if not deadline.candidate_date or deadline.candidate_date == "UNVERIFIED":
            raise ValueError(f"Cannot schedule reminders for deadline with unverified date: '{deadline.candidate_date}'")

        # Parse target date
        try:
            target_date = datetime.fromisoformat(deadline.candidate_date.replace("Z", "+00:00"))
        except ValueError:
            try:
                target_date = datetime.strptime(deadline.candidate_date[:10], "%Y-%m-%d")
            except ValueError:
                raise ValueError(f"Invalid deadline date format '{deadline.candidate_date}' for reminder scheduling.")

        if target_date.tzinfo is None:
            target_date = target_date.replace(tzinfo=timezone.utc)

        # Validate lead days
        if not lead_days:
            raise ValueError("lead_days list cannot be empty.")
        dedup_lead_days = list(dict.fromkeys(lead_days))
        for d in dedup_lead_days:
            if d < 0:
                raise ValueError(f"lead_days cannot contain negative values: {d}")

        created_reminders = []
        now = _utc_now_iso()

        async with get_db(db_path) as db:
            for days in dedup_lead_days:
                remind_at = (target_date - timedelta(days=days)).isoformat()
                rem_id = str(uuid.uuid4())
                query = """
                INSERT INTO reminders (id, deadline_id, remind_at, lead_days, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """
                await db.execute(query, (rem_id, deadline_id, remind_at, days, ReminderStatus.SCHEDULED.value, now))
                created_reminders.append(
                    Reminder(
                        id=rem_id,
                        deadline_id=deadline_id,
                        remind_at=remind_at,
                        lead_days=days,
                        status=ReminderStatus.SCHEDULED,
                        created_at=now
                    )
                )

            # Record audit
            audit_id = str(uuid.uuid4())
            audit_sql = """
            INSERT INTO audit_logs (id, deadline_id, action, previous_value, new_value, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """
            await db.execute(
                audit_sql,
                (audit_id, deadline_id, "reminder_created", None, json.dumps({"lead_days": dedup_lead_days}), now)
            )
            await db.commit()

        return created_reminders

    @staticmethod
    async def get_due_reminders(now_iso: Optional[str] = None, db_path: Optional[str] = None) -> List[Reminder]:
        """Query scheduled reminders that have reached or passed their remind_at timestamp."""
        check_time = now_iso or _utc_now_iso()
        query = "SELECT * FROM reminders WHERE status = 'scheduled' AND remind_at <= ? ORDER BY remind_at ASC"
        results = []
        async with get_db(db_path) as db:
            async with db.execute(query, (check_time,)) as cursor:
                rows = await cursor.fetchall()
                for row in rows:
                    results.append(
                        Reminder(
                            id=row["id"],
                            deadline_id=row["deadline_id"],
                            remind_at=str(row["remind_at"]),
                            lead_days=row["lead_days"],
                            status=row["status"],
                            created_at=str(row["created_at"])
                        )
                    )
        return results

    @staticmethod
    async def process_due_reminders(now_iso: Optional[str] = None, db_path: Optional[str] = None) -> List[Reminder]:
        """
        Process due scheduled reminders: transitions status to 'fired' and records an audit log.
        Prevents duplicate firing and operates local-first at zero cost.
        """
        check_time = now_iso or _utc_now_iso()
        due = await DeadlineService.get_due_reminders(now_iso=check_time, db_path=db_path)
        if not due:
            return []

        fired = []
        now = _utc_now_iso()
        async with get_db(db_path) as db:
            for rem in due:
                await db.execute(
                    "UPDATE reminders SET status = ? WHERE id = ? AND status = 'scheduled'",
                    (ReminderStatus.FIRED.value, rem.id)
                )
                audit_id = str(uuid.uuid4())
                await db.execute(
                    """
                    INSERT INTO audit_logs (id, deadline_id, action, previous_value, new_value, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        audit_id,
                        rem.deadline_id,
                        "reminder_fired",
                        json.dumps({"status": "scheduled", "reminder_id": rem.id}),
                        json.dumps({"status": "fired", "lead_days": rem.lead_days, "remind_at": rem.remind_at}),
                        now
                    )
                )
                fired.append(
                    Reminder(
                        id=rem.id,
                        deadline_id=rem.deadline_id,
                        remind_at=rem.remind_at,
                        lead_days=rem.lead_days,
                        status=ReminderStatus.FIRED,
                        created_at=rem.created_at
                    )
                )
            await db.commit()
        return fired

    @staticmethod
    async def get_reminders(deadline_id: str, db_path: Optional[str] = None) -> List[Reminder]:
        query = "SELECT * FROM reminders WHERE deadline_id = ? ORDER BY remind_at ASC"
        results = []
        async with get_db(db_path) as db:
            async with db.execute(query, (deadline_id,)) as cursor:
                rows = await cursor.fetchall()
                for row in rows:
                    results.append(
                        Reminder(
                            id=row["id"],
                            deadline_id=row["deadline_id"],
                            remind_at=str(row["remind_at"]),
                            lead_days=row["lead_days"],
                            status=row["status"],
                            created_at=str(row["created_at"])
                        )
                    )
        return results

    @staticmethod
    async def get_audit_logs(deadline_id: str, db_path: Optional[str] = None) -> List[AuditLog]:
        query = "SELECT * FROM audit_logs WHERE deadline_id = ? ORDER BY timestamp DESC"
        results = []
        async with get_db(db_path) as db:
            async with db.execute(query, (deadline_id,)) as cursor:
                rows = await cursor.fetchall()
                for row in rows:
                    results.append(
                        AuditLog(
                            id=row["id"],
                            deadline_id=row["deadline_id"],
                            action=row["action"],
                            previous_value=row["previous_value"],
                            new_value=row["new_value"],
                            timestamp=str(row["timestamp"])
                        )
                    )
        return results

    @staticmethod
    async def delete_deadline(deadline_id: str, db_path: Optional[str] = None) -> bool:
        async with get_db(db_path) as db:
            cursor = await db.execute("DELETE FROM deadlines WHERE id = ?", (deadline_id,))
            await db.commit()
            return cursor.rowcount > 0

    @staticmethod
    async def get_stats(db_path: Optional[str] = None) -> Dict[str, Any]:
        """Aggregate summary counts for dashboard."""
        query = """
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN status = 'needs_review' THEN 1 ELSE 0 END) as needs_review,
            SUM(CASE WHEN status = 'upcoming' THEN 1 ELSE 0 END) as upcoming,
            SUM(CASE WHEN status = 'confirmed' THEN 1 ELSE 0 END) as confirmed,
            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
            SUM(CASE WHEN status = 'date_unverified' THEN 1 ELSE 0 END) as date_unverified
        FROM deadlines
        """
        async with get_db(db_path) as db:
            async with db.execute(query) as cursor:
                row = await cursor.fetchone()
                return {
                    "total": row["total"] or 0,
                    "needs_review": row["needs_review"] or 0,
                    "upcoming": row["upcoming"] or 0,
                    "confirmed": row["confirmed"] or 0,
                    "completed": row["completed"] or 0,
                    "date_unverified": row["date_unverified"] or 0,
                }

    @staticmethod
    async def clear_all_data(db_path: Optional[str] = None) -> bool:
        """Clear all sources, deadlines, reminders, and audit logs for demo reset."""
        async with get_db(db_path) as db:
            await db.execute("DELETE FROM reminders")
            await db.execute("DELETE FROM audit_logs")
            await db.execute("DELETE FROM deadlines")
            await db.execute("DELETE FROM sources")
            await db.commit()
            return True

