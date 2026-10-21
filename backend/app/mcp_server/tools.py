"""
Real MCP Tool Handlers for Deadline Rescue.
Implements the 8 core tools defined in idea.md and phases.txt.
All tools execute genuine database reads, writes, and deterministic logic (no static mocks).
"""
import logging
from typing import List, Dict, Any, Optional
from app.models import (
    SourceType,
    DeadlineCategory, ObligationType,
    DeadlineStatus, VerificationStatus, RecurrenceType
)
from app.schemas import SourceCreate, DeadlineCreate, DeadlineUpdate
from app.services.deadline_service import DeadlineService
from app.services.calendar_service import generate_ics_content
from app.parsers.text_parser import parse_text_input
from app.parsers.email_parser import parse_email_input
from app.engine.obligation_classifier import AnalysisEngine
from app.engine.category_rules import PROVIDER_CATALOG

logger = logging.getLogger(__name__)


class DeadlineRescueTools:
    @staticmethod
    async def ingest_source(raw_text: str, title: str = "", source_type: str = "manual") -> Dict[str, Any]:
        """
        Tool 1: Ingest user text or message content into the local source repository.
        """
        if not raw_text or not raw_text.strip():
            raise ValueError("Input text cannot be empty.")

        # If it looks like an email with headers, parse as email
        if "from:" in raw_text.lower() and "subject:" in raw_text.lower():
            parsed = parse_email_input(raw_text, default_title=title or "Email Notice")
            stype = SourceType.EMAIL
        else:
            parsed = parse_text_input(raw_text, default_title=title or "Pasted Document")
            stype = SourceType.MANUAL if source_type == "manual" else SourceType.EMAIL

        final_title = title.strip() if (title and title.strip()) else parsed["title"]
        source_in = SourceCreate(
            title=final_title,
            raw_text=parsed["raw_text"],
            source_type=stype,
            file_hash=parsed["file_hash"]
        )
        source = await DeadlineService.create_source(source_in)
        return {
            "source_id": source.id,
            "title": source.title,
            "source_type": source.source_type.value,
            "char_count": len(source.raw_text),
            "file_hash": source.file_hash,
            "created_at": source.created_at,
            "status": "ingested"
        }

    @staticmethod
    async def find_deadline_candidates(source_id: str) -> List[Dict[str, Any]]:
        """
        Tool 2: Scan source records and extract candidate obligations with verbatim evidence spans.
        Persists extracted candidates to SQLite with status 'needs_review' or 'date_unverified'.
        """
        source = await DeadlineService.get_source(source_id)
        if not source:
            raise ValueError(f"Source with ID '{source_id}' not found.")

        raw_candidates = AnalysisEngine.extract_obligations(
            raw_text=source.raw_text,
            source_id=source.id,
            source_title=source.title
        )

        existing_deadlines = await DeadlineService.get_deadlines_by_source(source.id)
        persisted_candidates = []
        for cand in raw_candidates:
            # Check if this candidate obligation was already extracted for this source
            matching = None
            for ed in existing_deadlines:
                same_provider = ed.provider_name.strip().lower() == cand["provider_name"].strip().lower()
                same_obligation = (
                    ed.obligation_type == cand["obligation_type"] or 
                    getattr(ed.obligation_type, "value", str(ed.obligation_type)) == getattr(cand["obligation_type"], "value", str(cand["obligation_type"]))
                )
                same_span = (
                    (ed.evidence_char_start is not None and ed.evidence_char_start == cand.get("evidence_char_start")) or
                    (ed.evidence_snippet.strip() == cand["evidence_snippet"].strip())
                )
                if same_provider and same_obligation and same_span:
                    matching = ed
                    break

            if matching:
                # Preserve existing deadline, preserving user corrections, status changes, and confirmed dates
                persisted_candidates.append(matching.model_dump())
            else:
                deadline_in = DeadlineCreate(
                    source_id=source.id,
                    provider_name=cand["provider_name"],
                    category=cand["category"],
                    obligation_type=cand["obligation_type"],
                    candidate_date=cand["candidate_date"],
                    original_date_str=cand.get("original_date_str"),
                    amount=cand.get("amount"),
                    currency=cand.get("currency", "INR"),
                    evidence_snippet=cand["evidence_snippet"],
                    evidence_char_start=cand.get("evidence_char_start"),
                    evidence_char_end=cand.get("evidence_char_end"),
                    extraction_confidence=cand["extraction_confidence"],
                    verification_status=cand["verification_status"],
                    recurrence=cand["recurrence"],
                    official_url=cand.get("official_url"),
                    next_step_instructions=cand.get("next_step_instructions"),
                    status=cand["status"]
                )
                saved = await DeadlineService.create_deadline(deadline_in)
                persisted_candidates.append(saved.model_dump())

        return persisted_candidates

    @staticmethod
    async def get_deadline_evidence(deadline_id: str) -> Dict[str, Any]:
        """
        Tool 3: Retrieve verbatim evidence quote, source context, and attribution coordinates for a candidate.
        """
        deadline = await DeadlineService.get_deadline(deadline_id)
        if not deadline:
            raise ValueError(f"Deadline with ID '{deadline_id}' not found.")

        source = await DeadlineService.get_source(deadline.source_id)
        return {
            "deadline_id": deadline.id,
            "provider_name": deadline.provider_name,
            "candidate_date": deadline.candidate_date,
            "original_date_str": deadline.original_date_str,
            "amount": deadline.amount,
            "currency": deadline.currency,
            "evidence_snippet": deadline.evidence_snippet,
            "evidence_char_start": deadline.evidence_char_start,
            "evidence_char_end": deadline.evidence_char_end,
            "source_id": deadline.source_id,
            "source_title": source.title if source else "Unknown Source",
            "verification_status": deadline.verification_status.value,
            "status": deadline.status.value,
            "extraction_confidence": deadline.extraction_confidence
        }

    @staticmethod
    async def confirm_or_correct_deadline(
        deadline_id: str,
        confirmed_date: str = "",
        provider_name: str = "",
        notes: str = ""
    ) -> Dict[str, Any]:
        """
        Tool 4: Confirm, correct, or amend a candidate obligation.
        Preserves original extraction and writes diff to audit trail.
        """
        deadline = await DeadlineService.get_deadline(deadline_id)
        if not deadline:
            raise ValueError(f"Deadline with ID '{deadline_id}' not found.")

        update_fields = DeadlineUpdate(
            resolution_notes=notes or None
        )
        if confirmed_date:
            update_fields.candidate_date = confirmed_date
            update_fields.verification_status = VerificationStatus.USER_CONFIRMED
            update_fields.status = DeadlineStatus.CONFIRMED

        if provider_name:
            update_fields.provider_name = provider_name

        updated = await DeadlineService.update_deadline(deadline_id, update_fields)
        return updated.model_dump()

    @staticmethod
    async def create_follow_up(
        deadline_id: str,
        lead_days: Optional[List[int]] = None,
        export_calendar: bool = False
    ) -> Dict[str, Any]:
        """
        Tool 5: Create configured advance reminders for a confirmed deadline and optionally export an .ics calendar.
        """
        days = lead_days if (lead_days and len(lead_days) > 0) else [7, 1]
        deadline = await DeadlineService.get_deadline(deadline_id)
        if not deadline:
            raise ValueError(f"Deadline with ID '{deadline_id}' not found.")

        if deadline.candidate_date == "UNVERIFIED":
            raise ValueError("Cannot schedule reminders for an unverified date. Please confirm the date first.")

        reminders = await DeadlineService.create_reminders(deadline_id, lead_days=days)
        # Update status to 'upcoming' if it was confirmed or needs_review
        if deadline.status in [DeadlineStatus.CONFIRMED, DeadlineStatus.NEEDS_REVIEW]:
            await DeadlineService.update_deadline(deadline_id, DeadlineUpdate(status=DeadlineStatus.UPCOMING))

        ics_payload = None
        if export_calendar:
            ics_payload = generate_ics_content(deadline, reminders)

        return {
            "deadline_id": deadline_id,
            "status": DeadlineStatus.UPCOMING.value,
            "reminders_count": len(reminders),
            "scheduled_reminders": [r.model_dump() for r in reminders],
            "calendar_ics": ics_payload
        }

    @staticmethod
    async def prepare_next_step(deadline_id: str) -> Dict[str, Any]:
        """
        Tool 6: Prepare an actionable checklist and surface verified provider action URLs.
        Strict safety: Does not claim external actions were completed.
        """
        deadline = await DeadlineService.get_deadline(deadline_id)
        if not deadline:
            raise ValueError(f"Deadline with ID '{deadline_id}' not found.")

        # Determine checklist steps according to obligation type
        if deadline.obligation_type == ObligationType.TRIAL_ENDING:
            checklist = [
                "1. Verify the exact cancellation cut-off hour in account settings.",
                "2. Open official cancellation page using the verified link below.",
                "3. Follow prompts to confirm cancellation and avoid the next billing cycle.",
                "4. Save cancellation confirmation number or receipt."
            ]
        elif deadline.obligation_type == ObligationType.RENEWAL:
            checklist = [
                "1. Review renewal terms, premium amount, and payment options.",
                "2. Visit the verified insurer/provider payment portal.",
                "3. Complete renewal transaction before policy/service expires.",
                "4. Retain updated policy document or payment receipt."
            ]
        elif deadline.obligation_type == ObligationType.RETURN_DEADLINE:
            checklist = [
                "1. Ensure product is intact with original packaging and tags.",
                "2. Initiate return request on the provider order portal.",
                "3. Schedule courier pick-up or drop package at designated depot.",
                "4. Track refund status to your original payment method."
            ]
        else:
            checklist = [
                "1. Check bill summary and consumer/account ID.",
                "2. Navigate to official bill payment portal.",
                "3. Complete payment to prevent late fees or service interruption.",
                "4. Mark task as completed once payment receipt is received."
            ]

        return {
            "deadline_id": deadline_id,
            "provider_name": deadline.provider_name,
            "obligation_type": deadline.obligation_type.value,
            "official_url": deadline.official_url,
            "has_verified_url": bool(deadline.official_url),
            "action_instructions": deadline.next_step_instructions,
            "checklist": checklist,
            "safety_notice": "Deadline Rescue prepares the verified path; external actions must be completed by the user."
        }

    @staticmethod
    async def update_deadline_status(
        deadline_id: str,
        new_status: str,
        resolution_notes: str = ""
    ) -> Dict[str, Any]:
        """
        Tool 7: Transition deadline lifecycle state (completed, cancelled, action_needed).
        Maintains clear boundary: user self-report != third-party provider verification.
        """
        valid_statuses = [s.value for s in DeadlineStatus]
        if new_status not in valid_statuses:
            raise ValueError(f"Invalid status '{new_status}'. Must be one of: {valid_statuses}")

        updated = await DeadlineService.update_deadline(
            deadline_id,
            DeadlineUpdate(
                status=DeadlineStatus(new_status),
                resolution_notes=resolution_notes or None
            )
        )
        if not updated:
            raise ValueError(f"Deadline with ID '{deadline_id}' not found.")

        return updated.model_dump()

    @staticmethod
    async def list_deadlines(
        status_filter: str = "",
        category_filter: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Tool 8: Query tracked deadlines with optional status and category filtering.
        """
        s_filter = status_filter if status_filter.strip() else None
        c_filter = category_filter if category_filter.strip() else None
        items = await DeadlineService.list_deadlines(status_filter=s_filter, category_filter=c_filter)
        return [item.model_dump() for item in items]
