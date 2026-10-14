"""
Category classification rules, provider knowledge base, and official action links.
Provides deterministic categorization, next steps, and verified provider URLs.
"""
import re
from typing import Dict, Any, Optional
from app.models import DeadlineCategory, ObligationType, RecurrenceType

PROVIDER_CATALOG = {
    "netflix": {
        "name": "Netflix",
        "category": DeadlineCategory.SUBSCRIPTION,
        "official_url": "https://www.netflix.com/youraccount",
        "action_guide": "Log in to Netflix > Account > Cancel Membership to avoid recurring charge."
    },
    "amazon prime": {
        "name": "Amazon Prime",
        "category": DeadlineCategory.SUBSCRIPTION,
        "official_url": "https://www.amazon.in/mc/manage",
        "action_guide": "Go to Amazon Account > Prime Membership > Manage Membership > End Membership."
    },
    "spotify": {
        "name": "Spotify",
        "category": DeadlineCategory.SUBSCRIPTION,
        "official_url": "https://www.spotify.com/account/subscription/",
        "action_guide": "Go to Spotify Account overview > Your plan > Change plan > Cancel Premium."
    },
    "airtel": {
        "name": "Airtel",
        "category": DeadlineCategory.BROADBAND,
        "official_url": "https://www.airtel.in/pay-bills",
        "action_guide": "Use Airtel Thanks App or web portal to verify bill and complete payment before cut-off."
    },
    "jio": {
        "name": "Jio",
        "category": DeadlineCategory.MOBILE,
        "official_url": "https://www.jio.com/selfcare/recharge/",
        "action_guide": "Open MyJio app or web recharge portal to renew plan validity."
    },
    "tata power": {
        "name": "Tata Power",
        "category": DeadlineCategory.UTILITY,
        "official_url": "https://www.tatapower.com/bill-pay",
        "action_guide": "Check electricity consumer number and pay via Tata Power customer portal to avoid late fee."
    },
    "bescom": {
        "name": "BESCOM",
        "category": DeadlineCategory.UTILITY,
        "official_url": "https://bescom.karnataka.gov.in/",
        "action_guide": "Enter BESCOM Account ID online or via electricity board counter before due date."
    },
    "hdfc ergo": {
        "name": "HDFC ERGO",
        "category": DeadlineCategory.INSURANCE,
        "official_url": "https://www.hdfcergo.com/renew-insurance",
        "action_guide": "Review policy renewal notice, verify IDV and NCB, then pay renewal premium to maintain coverage."
    },
    "hdfc": {
        "name": "HDFC ERGO",
        "category": DeadlineCategory.INSURANCE,
        "official_url": "https://www.hdfcergo.com/renew-insurance",
        "action_guide": "Review policy renewal notice, verify IDV and NCB, then pay renewal premium to maintain coverage."
    },
    "icici lombard": {
        "name": "ICICI Lombard",
        "category": DeadlineCategory.INSURANCE,
        "official_url": "https://www.icicilombard.com/renew-online",
        "action_guide": "Enter policy number and vehicle/member details to complete renewal before policy expiry."
    },
    "tata play": {
        "name": "Tata Play",
        "category": DeadlineCategory.DTH,
        "official_url": "https://www.tataplay.com/quick-recharge",
        "action_guide": "Recharge subscriber ID online to ensure uninterrupted TV broadcast service."
    }
}

# Regex for currency and amounts (e.g. ₹499, Rs. 14,250, INR 999, $14.99)
AMOUNT_REGEX = re.compile(
    r'(?:(?:₹|rs\.?|inr|\$)\s*([\d,]+(?:\.\d{1,2})?)|([\d,]+(?:\.\d{1,2})?)\s*(?:₹|rs\.?|inr|\$))',
    re.IGNORECASE
)


def extract_amount_and_currency(text: str) -> tuple[Optional[float], str]:
    """Extract financial amount and currency from text snippet."""
    match = AMOUNT_REGEX.search(text)
    if not match:
        return None, "INR"

    raw_val = match.group(1) or match.group(2)
    clean_val = raw_val.replace(',', '')
    try:
        amount = float(clean_val)
        currency = "USD" if "$" in match.group(0) else "INR"
        return amount, currency
    except ValueError:
        return None, "INR"


def detect_provider(text: str) -> Dict[str, Any]:
    """Detect known brand provider or infer from headers / text."""
    lower_text = text.lower()
    for key, info in PROVIDER_CATALOG.items():
        if key in lower_text:
            return info

    # Fallback: check 'From:' header or capitalized words
    from_match = re.search(r'(?i)from:\s*([^<\n\r]+)', text)
    if from_match:
        inferred = from_match.group(1).strip()
        inferred = re.sub(r'["\']', '', inferred)
        if inferred:
            return {
                "name": inferred,
                "category": DeadlineCategory.OTHER,
                "official_url": None,
                "action_guide": "Check official provider website or support channel for next steps."
            }

    return {
        "name": "Service Provider",
        "category": DeadlineCategory.OTHER,
        "official_url": None,
        "action_guide": "Check official provider website or account page."
    }


def classify_obligation(text: str, default_cat: DeadlineCategory) -> tuple[DeadlineCategory, ObligationType, RecurrenceType]:
    """
    Classify the obligation type, category, and recurrence pattern based on text triggers.
    """
    lower = text.lower()

    # Recurrence
    if any(k in lower for k in ["monthly", "per month", "/mo", "every month", "each month"]):
        recurrence = RecurrenceType.MONTHLY
    elif any(k in lower for k in ["annual", "yearly", "per year", "/yr", "annually", "every year"]):
        recurrence = RecurrenceType.ANNUAL
    elif any(k in lower for k in ["one-time", "recharge pack", "validity pack"]):
        recurrence = RecurrenceType.ONE_TIME
    else:
        recurrence = RecurrenceType.UNCONFIRMED

    # 1. High-priority explicit categories
    if any(k in lower for k in ["trial", "free trial", "trial ends", "trial renews"]):
        return DeadlineCategory.SUBSCRIPTION, ObligationType.TRIAL_ENDING, recurrence

    if any(k in lower for k in ["return deadline", "return window", "return before", "return policy"]):
        return DeadlineCategory.RETURN_WINDOW, ObligationType.RETURN_DEADLINE, RecurrenceType.ONE_TIME

    if any(k in lower for k in ["dth", "dish", "cable tv", "tata play", "set-top"]):
        return DeadlineCategory.DTH, ObligationType.RENEWAL, recurrence

    if any(k in lower for k in ["policy", "premium", "insurance", "ncb", "idv"]):
        return DeadlineCategory.INSURANCE, ObligationType.RENEWAL, recurrence

    if any(k in lower for k in ["broadband", "wi-fi", "fiber", "internet bill"]):
        return DeadlineCategory.BROADBAND, ObligationType.PAYMENT_DUE, recurrence

    if any(k in lower for k in ["electricity", "power", "water bill", "gas bill", "bescom", "tata power"]):
        return DeadlineCategory.UTILITY, ObligationType.PAYMENT_DUE, recurrence

    if any(k in lower for k in ["validity", "valid till", "pack expires", "recharge", "prepaid"]):
        return DeadlineCategory.MOBILE, ObligationType.VALIDITY_EXPIRY, recurrence

    if any(k in lower for k in ["subscription", "autopay", "membership renews"]):
        return DeadlineCategory.SUBSCRIPTION, ObligationType.RENEWAL, recurrence

    if any(k in lower for k in ["due date", "bill due", "invoice due", "payment by"]):
        return default_cat, ObligationType.PAYMENT_DUE, recurrence

    return default_cat, ObligationType.PAYMENT_DUE, recurrence
