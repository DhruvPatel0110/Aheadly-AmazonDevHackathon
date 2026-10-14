"""
Obligation Classifier and Analysis Pipeline.
Integrates text parsing, date extraction, provider cataloging, and certainty checks.
Strictly conforms to ₹0 budget rule with deterministic certainty and zero hallucination.
"""
import logging
from typing import List, Dict, Any, Optional
from app.engine.date_extractor import find_candidate_dates
from app.engine.category_rules import (
    detect_provider,
    classify_obligation,
    extract_amount_and_currency
)
from app.models import DeadlineStatus, VerificationStatus

logger = logging.getLogger(__name__)


class AnalysisEngine:
    @staticmethod
    def extract_obligations(
        raw_text: str,
        source_id: str = "",
        source_title: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Main extraction pipeline.
        Transforms raw document/message text into structured, evidence-backed candidate deadlines.
        """
        if not raw_text or not raw_text.strip():
            return []

        # 1. Extract dates, anchored deadlines, and vague statements
        date_candidates = find_candidate_dates(raw_text)
        if not date_candidates:
            logger.info("No deadline candidates or dates identified in source.")
            return []

        # 2. Extract provider details from entire document
        provider_info = detect_provider(raw_text)

        results = []
        for cand in date_candidates:
            # Contextual analysis for each candidate's evidence window
            evidence_text = cand["evidence_snippet"]
            
            # Re-check provider within the specific evidence window if different
            local_provider = detect_provider(evidence_text)
            final_provider = local_provider if local_provider["name"] != "Service Provider" else provider_info

            # Classify category and obligation type
            category, obligation_type, recurrence = classify_obligation(
                raw_text + " " + evidence_text,
                default_cat=final_provider["category"]
            )

            # Extract amount and currency from evidence or source
            amount, currency = extract_amount_and_currency(evidence_text)
            if amount is None:
                amount, currency = extract_amount_and_currency(raw_text)

            is_vague = cand.get("is_vague", False)

            if is_vague:
                status = DeadlineStatus.DATE_UNVERIFIED
                verification_status = VerificationStatus.UNVERIFIED
                next_steps = (
                    f"A deadline was mentioned in the source ('{cand['original_date_str']}'), "
                    "but no exact calendar date was stated. "
                    "Please check your account or input the exact date to confirm."
                )
                candidate_date = "UNVERIFIED"
                confidence = 0.40
            else:
                status = DeadlineStatus.NEEDS_REVIEW
                verification_status = VerificationStatus.SOURCE_STATED
                next_steps = final_provider.get("action_guide")
                candidate_date = cand["candidate_date"]
                confidence = cand["confidence"]

            results.append({
                "source_id": source_id,
                "provider_name": final_provider["name"],
                "category": category,
                "obligation_type": obligation_type,
                "candidate_date": candidate_date,
                "original_date_str": cand.get("original_date_str"),
                "amount": amount,
                "currency": currency,
                "evidence_snippet": evidence_text,
                "evidence_char_start": cand.get("evidence_char_start"),
                "evidence_char_end": cand.get("evidence_char_end"),
                "extraction_confidence": confidence,
                "verification_status": verification_status,
                "recurrence": recurrence,
                "official_url": final_provider.get("official_url"),
                "next_step_instructions": next_steps,
                "status": status,
                "requires_user_input": is_vague or (status == DeadlineStatus.NEEDS_REVIEW)
            })

        return results
