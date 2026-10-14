"""
Deterministic Date and Evidence Extraction Engine.
Extracts candidate dates, relative expressions, and verbatim evidence spans.
Strictly handles uncertainty (Scenario D) without inventing calendar dates.
"""
import re
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dateutil import parser as date_parser

# Common anchored context keywords
ANCHOR_REGEX = re.compile(
    r'(?i)\b(?:due\s+date|due\s+on|pay\s+before|pay\s+by|payment\s+by|bill\s+due|'
    r'renews\s+on|renewal\s+date|trial\s+ends|free\s+trial\s+ends|expires\s+on|'
    r'expiry\s+date|valid\s+till|validity\s+ends|return\s+before|return\s+window|'
    r'cancel\s+before|cut-?off|last\s+date)\b[:\s]*([^\n\r,\.;]+)',
    re.IGNORECASE
)

# Ambiguous phrases that deliberately lack a calendar day (Scenario D)
VAGUE_DATE_PATTERNS = [
    re.compile(r'(?i)\b(?:near|around|towards)\s+the\s+end\s+of\s+the\s+month\b'),
    re.compile(r'(?i)\bsometime\s+(?:this|next)\s+month\b'),
    re.compile(r'(?i)\bearly\s+next\s+week\b'),
    re.compile(r'(?i)\bsometime\s+next\s+week\b'),
    re.compile(r'(?i)\bin\s+a\s+few\s+days\b'),
    re.compile(r'(?i)\bend\s+of\s+the\s+month\b'),
]

# Explicit date regexes
DATE_PATTERNS = [
    # YYYY-MM-DD
    re.compile(r'\b(20\d{2}[-/](?:0[1-9]|1[0-2])[-/](?:0[1-9]|[12]\d|3[01]))\b'),
    # DD-MM-YYYY or DD/MM/YYYY
    re.compile(r'\b((?:0[1-9]|[12]\d|3[01])[-/](?:0[1-9]|1[0-2])[-/](?:20\d{2}))\b'),
    # DD Month YYYY (e.g. 20 October 2026, 20th Oct 2026, 05 November, 2026)
    re.compile(
        r'\b((?:0?[1-9]|[12]\d|3[01])(?:st|nd|rd|th)?\s+(?:Jan(?:uary)?|Feb(?:ruary)?|'
        r'Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|'
        r'Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)(?:,?\s+20\d{2})?)\b',
        re.IGNORECASE
    ),
    # Month DD, YYYY (e.g. October 20, 2026 or Oct 20)
    re.compile(
        r'\b((?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|'
        r'Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|'
        r'Dec(?:ember)?)\s+(?:0?[1-9]|[12]\d|3[01])(?:st|nd|rd|th)?(?:,?\s+20\d{2})?)\b',
        re.IGNORECASE
    )
]

# Relative expressions: e.g. "in 14 days", "in 48 hours"
RELATIVE_DAY_PATTERN = re.compile(r'(?i)\bin\s+(\d+)\s+days?\b')
RELATIVE_HOUR_PATTERN = re.compile(r'(?i)\bin\s+(\d+)\s+hours?\b')


def extract_evidence_sentence(text: str, start: int, end: int, window: int = 120) -> Tuple[str, int, int]:
    """
    Extract the surrounding sentence or context window for verbatim evidence attribution.
    Returns (snippet, char_start, char_end).
    """
    # Look back for sentence start (. or \n or start of text)
    left_bound = max(0, start - window)
    prev_period = max(text.rfind('.', 0, start), text.rfind('\n', 0, start))
    if prev_period != -1 and prev_period >= left_bound:
        actual_start = prev_period + 1
    else:
        actual_start = left_bound

    # Look ahead for sentence end
    right_bound = min(len(text), end + window)
    next_period = min(
        [p for p in [text.find('.', end), text.find('\n', end)] if p != -1] or [right_bound]
    )
    if next_period <= right_bound:
        actual_end = next_period
    else:
        actual_end = right_bound

    snippet = text[actual_start:actual_end].strip()
    return snippet, actual_start, actual_end


def normalize_parsed_date(raw_date_str: str) -> Optional[str]:
    """
    Parse a raw date string into an ISO YYYY-MM-DD string.
    Correctly distinguishes ISO (YYYY-MM-DD) from Indian formats (DD/MM/YYYY).
    """
    clean_str = re.sub(r'(?<=\d)(st|nd|rd|th)', '', raw_date_str).strip()

    # 1. Exact ISO format match: YYYY-MM-DD
    iso_match = re.match(r'^(\d{4})[-/](\d{1,2})[-/](\d{1,2})$', clean_str)
    if iso_match:
        y, m, d = int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3))
        try:
            return datetime(y, m, d, tzinfo=timezone.utc).strftime("%Y-%m-%d")
        except ValueError:
            pass

    # 2. Exact DD-MM-YYYY or DD/MM/YYYY match
    dmy_match = re.match(r'^(\d{1,2})[-/](\d{1,2})[-/](\d{4})$', clean_str)
    if dmy_match:
        d, m, y = int(dmy_match.group(1)), int(dmy_match.group(2)), int(dmy_match.group(3))
        try:
            return datetime(y, m, d, tzinfo=timezone.utc).strftime("%Y-%m-%d")
        except ValueError:
            pass

    # 3. Textual dates: "20 October 2026", "November 05, 2026"
    try:
        dt = date_parser.parse(clean_str, dayfirst=True)
        current_year = datetime.now(timezone.utc).year
        # If no year was explicitly in string and parsed date is in the past, adjust
        if str(current_year) not in clean_str and str(current_year + 1) not in clean_str:
            if dt.month < datetime.now(timezone.utc).month:
                dt = dt.replace(year=current_year + 1)
            else:
                dt = dt.replace(year=current_year)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return None


def find_candidate_dates(text: str) -> List[Dict[str, Any]]:
    """
    Scans text for explicit dates, anchored dates, relative terms, and vague terms.
    Returns list of candidate extraction records.
    """
    candidates = []
    seen_evidence_starts = set()

    # 1. First, check for anchored context (highest confidence)
    for match in ANCHOR_REGEX.finditer(text):
        target_clause = match.group(1)
        clause_start = match.start(1)

        # Check for explicit dates inside this target clause
        found_in_anchor = False
        for pattern in DATE_PATTERNS:
            for d_match in pattern.finditer(target_clause):
                date_str = d_match.group(1)
                iso_date = normalize_parsed_date(date_str)
                if iso_date:
                    abs_start = clause_start + d_match.start(1)
                    abs_end = clause_start + d_match.end(1)
                    evidence, ev_start, ev_end = extract_evidence_sentence(text, abs_start, abs_end)
                    if ev_start not in seen_evidence_starts:
                        seen_evidence_starts.add(ev_start)
                        candidates.append({
                            "candidate_date": iso_date,
                            "original_date_str": date_str,
                            "evidence_snippet": evidence,
                            "evidence_char_start": ev_start,
                            "evidence_char_end": ev_end,
                            "confidence": 0.95,
                            "verification_status": "source_stated",
                            "is_vague": False
                        })
                    found_in_anchor = True
                    break
            if found_in_anchor:
                break

    # 2. Check for general explicit dates across text if not already captured
    for pattern in DATE_PATTERNS:
        for match in pattern.finditer(text):
            date_str = match.group(1)
            iso_date = normalize_parsed_date(date_str)
            if not iso_date:
                continue

            start, end = match.start(1), match.end(1)
            evidence, ev_start, ev_end = extract_evidence_sentence(text, start, end)
            if ev_start not in seen_evidence_starts:
                seen_evidence_starts.add(ev_start)
                candidates.append({
                    "candidate_date": iso_date,
                    "original_date_str": date_str,
                    "evidence_snippet": evidence,
                    "evidence_char_start": ev_start,
                    "evidence_char_end": ev_end,
                    "confidence": 0.85,
                    "verification_status": "source_stated",
                    "is_vague": False
                })

    # 3. Check for relative dates (e.g., "in 14 days")
    rel_match = RELATIVE_DAY_PATTERN.search(text)
    if rel_match and not candidates:
        days_offset = int(rel_match.group(1))
        target_dt = datetime.now(timezone.utc) + timedelta(days=days_offset)
        iso_date = target_dt.strftime("%Y-%m-%d")
        start, end = rel_match.start(), rel_match.end()
        evidence, ev_start, ev_end = extract_evidence_sentence(text, start, end)
        candidates.append({
            "candidate_date": iso_date,
            "original_date_str": rel_match.group(0),
            "evidence_snippet": evidence,
            "evidence_char_start": ev_start,
            "evidence_char_end": ev_end,
            "confidence": 0.80,
            "verification_status": "estimated",
            "is_vague": False
        })

    # 4. Scenario D: Ambiguity / Uncertainty Detection
    # If text contains vague deadline phrases and NO exact candidate dates were found
    if not candidates:
        for vague_pat in VAGUE_DATE_PATTERNS:
            vague_match = vague_pat.search(text)
            if vague_match:
                start, end = vague_match.start(), vague_match.end()
                evidence, ev_start, ev_end = extract_evidence_sentence(text, start, end)
                # DO NOT invent a date! Set placeholder flag and unverified status
                candidates.append({
                    "candidate_date": "UNVERIFIED",
                    "original_date_str": vague_match.group(0),
                    "evidence_snippet": evidence,
                    "evidence_char_start": ev_start,
                    "evidence_char_end": ev_end,
                    "confidence": 0.40,
                    "verification_status": "unverified",
                    "is_vague": True
                })
                break

    return candidates
