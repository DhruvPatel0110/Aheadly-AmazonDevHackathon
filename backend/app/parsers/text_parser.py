"""
Text parser for raw text inputs, pasted snippets, and SMS messages.
Handles text cleaning, character offset tracking, and checksum hashing.
"""
import hashlib
import re
from typing import Dict, Any, Optional


def hash_content(text: str) -> str:
    """Compute SHA-256 hash of content."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse_text_input(
    raw_text: str,
    default_title: Optional[str] = None,
    source_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Parse and normalize raw text snippet or SMS.
    If an explicit title is provided, it is preserved. Otherwise, infers title from first line.
    Preserves explicitly supplied source_type or safely defaults to 'manual'.
    """
    if not raw_text or not raw_text.strip():
        raise ValueError("Provided text is empty or whitespace only.")

    cleaned = raw_text.strip()
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]

    # If explicit title is provided by caller, use it
    if default_title and default_title.strip() and default_title.strip() != "Pasted Text":
        inferred_title = default_title.strip()
    else:
        inferred_title = default_title.strip() if (default_title and default_title.strip()) else "Pasted Text"
        if lines and len(lines[0]) < 80:
            first_line = lines[0]
            # Remove common prefixes like 'Subject:', 'Fwd:', etc.
            first_line = re.sub(r'^(subject|fwd|re|notice):\s*', '', first_line, flags=re.IGNORECASE)
            if first_line:
                inferred_title = first_line

    # Source type resolution:
    # 1. Use explicit source_type if valid
    valid_source_types = {"manual", "sms", "email", "receipt", "pdf"}
    if source_type and source_type.lower() in valid_source_types:
        final_source_type = source_type.lower()
    else:
        # Default safely to 'manual' for pasted text snippets
        final_source_type = "manual"

    return {
        "title": inferred_title,
        "clean_text": cleaned,
        "raw_text": raw_text,
        "file_hash": hash_content(cleaned),
        "source_type": final_source_type
    }
