"""
Conversational Agent Service simulating Alexa+ Personal Deadline Assistant.
Converts natural language utterances and text inputs into verified MCP tool invocations
via MCPClientBridge, strictly highlighting evidence and refusing to invent dates.
"""
import re
import logging
from typing import Dict, Any, List, Optional
from app.services.mcp_client import MCPClientBridge
from app.services.deadline_service import DeadlineService

logger = logging.getLogger(__name__)


def format_enum_val(val: Any) -> str:
    """Safely format an enum or string into human-readable label or value."""
    if hasattr(val, "value"):
        val = val.value
    s = str(val)
    if "." in s:
        s = s.split(".")[-1]
    return s.replace("_", " ").lower()


def format_status(val: Any) -> str:
    """Format a status enum or string into capitalized label."""
    if hasattr(val, "value"):
        val = val.value
    s = str(val)
    if "." in s:
        s = s.split(".")[-1]
    return s.replace("_", " ").title()


class DeadlineAgentService:
    @staticmethod
    async def process_chat(message: str, active_deadline_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process user conversational query and dispatch to real MCP tools.
        Returns agent response text, invoked tool logs, and updated candidate/deadline state.
        """
        clean_msg = message.strip()
        lower = clean_msg.lower()
        tools_invoked = []

        # -------------------------------------------------------------------
        # Intent 1: Evidence Inquiry
        # -------------------------------------------------------------------
        if any(k in lower for k in ["show evidence", "prove it", "where did you find", "why this date", "view snippet"]):
            # Find target deadline
            target_id = active_deadline_id
            if not target_id:
                deadlines = await DeadlineService.list_deadlines(limit=1)
                if deadlines:
                    target_id = deadlines[0].id

            if target_id:
                res = await MCPClientBridge.call_tool("get_deadline_evidence", {"deadline_id": target_id})
                tools_invoked.append("get_deadline_evidence")
                reply = (
                    f"**Source Evidence for {res['provider_name']}**:\n\n"
                    f"> \"{res['evidence_snippet']}\"\n\n"
                    f"Source: *{res['source_title']}* (Verification: `{format_enum_val(res['verification_status'])}`). "
                    f"Extracted Date: **{res['candidate_date']}**."
                )
                return {
                    "reply": reply,
                    "tools_invoked": tools_invoked,
                    "active_deadline_id": target_id,
                    "data": res
                }

        # -------------------------------------------------------------------
        # Intent 2: Confirmation / Date Correction
        # -------------------------------------------------------------------
        if any(k in lower for k in ["confirm", "looks good", "correct date", "verify this"]):
            target_id = active_deadline_id
            if not target_id:
                needs_review = await DeadlineService.list_deadlines(status_filter="needs_review", limit=1)
                if needs_review:
                    target_id = needs_review[0].id

            if target_id:
                # Check if user specified a date (e.g. "confirm for 2026-10-25")
                date_match = re.search(r'\b(20\d{2}[-/]\d{2}[-/]\d{2})\b', clean_msg)
                confirmed_date = date_match.group(1) if date_match else ""

                res = await MCPClientBridge.call_tool("confirm_or_correct_deadline", {
                    "deadline_id": target_id,
                    "confirmed_date": confirmed_date,
                    "notes": f"Confirmed via conversational agent: '{clean_msg}'"
                })
                tools_invoked.append("confirm_or_correct_deadline")
                reply = (
                    f"Confirmed **{res['provider_name']}** obligation for **{res['candidate_date']}**. "
                    "Would you like me to set advance reminders (e.g., 7 days and 1 day before) "
                    "or export a calendar event?"
                )
                return {
                    "reply": reply,
                    "tools_invoked": tools_invoked,
                    "active_deadline_id": target_id,
                    "data": res
                }

        # -------------------------------------------------------------------
        # Intent 3: Schedule Reminders / Follow-up
        # -------------------------------------------------------------------
        if any(k in lower for k in ["remind me", "set reminder", "create reminder", "export calendar", "add reminder"]):
            target_id = active_deadline_id
            if not target_id:
                deadlines = await DeadlineService.list_deadlines(limit=1)
                if deadlines:
                    target_id = deadlines[0].id

            if target_id:
                lead_days = [7, 1]
                # Check for explicit numbers (e.g. "remind me 3 days before")
                day_match = re.search(r'(\d+)\s+days?', lower)
                if day_match:
                    lead_days = [int(day_match.group(1)), 1]

                res = await MCPClientBridge.call_tool("create_follow_up", {
                    "deadline_id": target_id,
                    "lead_days": lead_days,
                    "export_calendar": "calendar" in lower or "ics" in lower
                })
                tools_invoked.append("create_follow_up")
                reply = (
                    f"Scheduled {res['reminders_count']} advance reminders for this deadline. "
                    f"Reminders will fire {lead_days} days in advance. Task status is now **Upcoming**."
                )
                if res.get("calendar_ics"):
                    reply += " Calendar file (.ics) has been prepared for download."

                return {
                    "reply": reply,
                    "tools_invoked": tools_invoked,
                    "active_deadline_id": target_id,
                    "data": res
                }

        # -------------------------------------------------------------------
        # Intent 4: Action Guide / How to Pay / How to Cancel
        # -------------------------------------------------------------------
        if any(k in lower for k in ["how do i cancel", "how to cancel", "how to pay", "next step", "what to do"]):
            target_id = active_deadline_id
            if not target_id:
                deadlines = await DeadlineService.list_deadlines(limit=1)
                if deadlines:
                    target_id = deadlines[0].id

            if target_id:
                res = await MCPClientBridge.call_tool("prepare_next_step", {"deadline_id": target_id})
                tools_invoked.append("prepare_next_step")
                reply = (
                    f"**Next Steps for {res['provider_name']}**:\n\n"
                    + "\n".join(res["checklist"])
                )
                if res.get("official_url"):
                    reply += f"\n\nOfficial Verified Portal: {res['official_url']}"
                reply += f"\n\n> *Note: {res['safety_notice']}*"

                return {
                    "reply": reply,
                    "tools_invoked": tools_invoked,
                    "active_deadline_id": target_id,
                    "data": res
                }

        # -------------------------------------------------------------------
        # Intent 5: Status Resolution (Paid / Cancelled)
        # -------------------------------------------------------------------
        if any(k in lower for k in ["i paid", "marked paid", "i cancelled", "mark cancelled", "done", "complete"]):
            target_id = active_deadline_id
            if not target_id:
                upcoming = await DeadlineService.list_deadlines(status_filter="upcoming", limit=1)
                if upcoming:
                    target_id = upcoming[0].id
                else:
                    all_d = await DeadlineService.list_deadlines(limit=1)
                    if all_d:
                        target_id = all_d[0].id

            if target_id:
                new_status = "cancelled" if any(w in lower for w in ["cancel", "cancelled"]) else "completed"
                res = await MCPClientBridge.call_tool("update_deadline_status", {
                    "deadline_id": target_id,
                    "new_status": new_status,
                    "resolution_notes": f"User marked as {new_status} via chat."
                })
                tools_invoked.append("update_deadline_status")
                reply = (
                    f"Updated {res['provider_name']} status to **{format_status(new_status)}** "
                    "(recorded as user confirmation)."
                )
                return {
                    "reply": reply,
                    "tools_invoked": tools_invoked,
                    "active_deadline_id": target_id,
                    "data": res
                }

        # -------------------------------------------------------------------
        # Intent 6: Querying List of Deadlines
        # -------------------------------------------------------------------
        if any(k in lower for k in ["what is due", "show deadlines", "list deadlines", "what bills", "upcoming"]):
            res = await MCPClientBridge.call_tool("list_deadlines", {})
            tools_invoked.append("list_deadlines")
            if not res:
                reply = "You currently have no tracked deadlines. Ingest an email or bill to get started!"
            else:
                summary = [f"• **{d['provider_name']}**: due **{d['candidate_date']}** (Status: `{format_enum_val(d['status'])}`)" for d in res[:5]]
                reply = f"Here are your currently tracked obligations ({len(res)} total):\n\n" + "\n".join(summary)

            return {
                "reply": reply,
                "tools_invoked": tools_invoked,
                "active_deadline_id": active_deadline_id,
                "data": res
            }

        # -------------------------------------------------------------------
        # Intent 7: Default Pipeline (Ingest & Extract Source)
        # -------------------------------------------------------------------
        ingest_res = await MCPClientBridge.call_tool("ingest_source", {
            "raw_text": clean_msg,
            "title": "Conversational Note / Input",
            "source_type": "manual"
        })
        tools_invoked.append("ingest_source")

        candidates = await MCPClientBridge.call_tool("find_deadline_candidates", {
            "source_id": ingest_res["source_id"]
        })
        tools_invoked.append("find_deadline_candidates")

        if not candidates:
            reply = (
                "I ingested your message, but didn't detect an explicit money-related deadline or due date. "
                "You can paste a bill notification, subscription email, or specify the exact date directly."
            )
            return {
                "reply": reply,
                "tools_invoked": tools_invoked,
                "active_deadline_id": None,
                "data": None
            }

        first_cand = candidates[0]
        # Scenario D: Unverified Date
        if first_cand["candidate_date"] == "UNVERIFIED":
            reply = (
                f"I found an obligation from **{first_cand['provider_name']}**, but the text states: "
                f"*\"{first_cand['evidence_snippet']}\"* without an exact calendar date.\n\n"
                "I will not guess or invent a deadline. Please check your provider account "
                "or tell me the exact date (e.g. *\"Confirm date as 2026-10-31\"*)."
            )
        else:
            amount_str = f" for **{first_cand['currency']} {first_cand['amount']}**" if first_cand.get("amount") else ""
            ob_type_label = format_enum_val(first_cand['obligation_type'])
            reply = (
                f"The source states that your **{first_cand['provider_name']}** {ob_type_label} is due on "
                f"**{first_cand['candidate_date']}**{amount_str}.\n\n"
                f"Evidence: *\"{first_cand['evidence_snippet']}\"*\n\n"
                "Would you like me to confirm this date and prepare advance reminders?"
            )

        return {
            "reply": reply,
            "tools_invoked": tools_invoked,
            "active_deadline_id": first_cand["id"],
            "candidates": candidates
        }
