"""
Text parser for raw text inputs, pasted snippets, and SMS messages.
Handles text cleaning, character offset tracking, and checksum hashing.
"""
import hashlib
import re
from typing import Dict, Any


def hash_content(text: str) -> str:
    """Compute SHA-256 hash of content."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse_text_input(raw_text: str, default_title: str = "Pasted Text") -> Dict[str, Any]:
    """
    Parse and normalize raw text snippet or SMS.
    Returns cleaned text, inferred title, and checksum.
    """
    if not raw_text or not raw_text.strip():
        raise ValueError("Provided text is empty or whitespace only.")

    # Preserve original text for verbatim character matching, but strip outer whitespace
    cleaned = raw_text.strip()

    # If first line looks like a subject or header, use it as title
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    inferred_title = default_title
    if lines and len(lines[0]) < 80:
        first_line = lines[0]
        # Remove common prefixes like 'Subject:', 'Fwd:', etc.
        first_line = re.sub(r'^(subject|fwd|re|notice):\s*', '', first_line, flags=re.IGNORECASE)
        if first_line:
            inferred_title = first_line

    return {
        "title": inferred_title,
        "clean_text": cleaned,
        "raw_text": raw_text,
        "file_hash": hash_content(cleaned),
        "source_type": "manual" if len(cleaned) < 300 and "sms" not in cleaned.lower() else "email"
    }
