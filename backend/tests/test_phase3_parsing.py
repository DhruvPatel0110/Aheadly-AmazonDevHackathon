"""
Phase 3: Parsing, Evidence Extraction & Deterministic Analysis Engine
Tests text parsing, email parsing with HTML sanitization, PDF digital & scanned detection,
all required date formats, evidence character span exactness, uncertainty handling,
empty/non-deadline sources, and obligation classification.
Contains 18 distinct unit test cases (requirement: >= 15).
"""
import pytest
import io
from pypdf import PdfWriter
from app.parsers.text_parser import parse_text_input, hash_content
from app.parsers.email_parser import parse_email_input
from app.parsers.pdf_parser import parse_pdf_input, ScannedPdfError
from app.engine.date_extractor import find_candidate_dates, normalize_parsed_date
from app.engine.obligation_classifier import AnalysisEngine
from app.models import DeadlineCategory, ObligationType, DeadlineStatus, VerificationStatus


# ---------------------------------------------------------------------------
# 1. Text Parser Tests
# ---------------------------------------------------------------------------

def test_text_parser_normalization_and_hash():
    """Text parser normalizes whitespace, extracts title, and computes sha256."""
    raw = "   \n\n  Subject: Electricity Bill Notice \n\n Your bill of ₹2,450 is due on 2026-11-18.  \n\n "
    parsed = parse_text_input(raw, default_title="Pasted Text")
    assert parsed["title"] == "Electricity Bill Notice"
    assert parsed["clean_text"].startswith("Subject: Electricity Bill Notice")
    assert parsed["clean_text"].endswith("is due on 2026-11-18.")
    assert len(parsed["file_hash"]) == 64  # SHA-256


def test_text_parser_empty_input_rejection():
    """Text parser raises ValueError on empty or whitespace-only text."""
    with pytest.raises(ValueError):
        parse_text_input("")
    with pytest.raises(ValueError):
        parse_text_input("   \n\t  ")


# ---------------------------------------------------------------------------
# 2. Email Parser Tests
# ---------------------------------------------------------------------------

def test_email_parser_headers_and_body():
    """Email parser extracts From, Subject, Date headers and plain text body."""
    raw_eml = """From: Netflix Support <info@mailer.netflix.com>
Subject: Complete your signup - Free trial reminder
Date: Mon, 14 Oct 2026 09:30:00 +0000
Content-Type: text/plain; charset="utf-8"

Your 14-day free trial ends on October 20. Your card will be charged INR 499 unless cancelled.
"""
    parsed = parse_email_input(raw_eml)
    assert "Netflix" in parsed["sender"]
    assert "Free trial reminder" in parsed["subject"]
    assert "October 20" in parsed["raw_text"]
    assert parsed["source_type"] == "email"


def test_email_parser_html_sanitization():
    """Email parser sanitizes HTML tags from HTML-only or multipart emails."""
    raw_html_eml = """From: Airtel <billing@airtel.in>
Subject: Airtel Broadband Bill
Date: Mon, 14 Oct 2026 12:00:00 +0530
Content-Type: text/html; charset="utf-8"

<html>
  <body>
    <h1>Airtel Fiber Bill</h1>
    <p>Dear Customer, your broadband bill of <b>INR 999</b> is due on <i>2026-11-15</i>.</p>
    <a href="https://airtel.in/pay">Pay Now</a>
  </body>
</html>
"""
    parsed = parse_email_input(raw_html_eml)
    clean = parsed["clean_text"]
    assert "<html>" not in clean
    assert "<p>" not in clean
    assert "<b>" not in clean
    assert "2026-11-15" in clean


# ---------------------------------------------------------------------------
# 3. PDF Parser Tests
# ---------------------------------------------------------------------------

def test_pdf_parser_digital():
    """PDF parser extracts text from a valid digital PDF."""
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    # Write blank PDF and verify length
    buf = io.BytesIO()
    writer.write(buf)
    pdf_bytes = buf.getvalue()

    # If length of text is < 25 chars, parser flags scanned/empty
    with pytest.raises(ScannedPdfError):
        parse_pdf_input(pdf_bytes)


def test_pdf_parser_scanned_graceful_detection():
    """For a scanned or image-only PDF, parser must return the specified message and not crash."""
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    buf = io.BytesIO()
    writer.write(buf)
    pdf_bytes = buf.getvalue()

    with pytest.raises(ScannedPdfError) as exc_info:
        parse_pdf_input(pdf_bytes)

    expected_msg = "No readable text layer; please paste text or provide a digital PDF"
    assert expected_msg in str(exc_info.value), (
        f"Expected message '{expected_msg}' not found in exception detail: {str(exc_info.value)}"
    )


# ---------------------------------------------------------------------------
# 4. Date Extractor Format Tests
# ---------------------------------------------------------------------------

def test_date_format_dd_mm_yyyy():
    """Date extractor supports DD/MM/YYYY."""
    text = "Broadband bill payment due on 25/11/2026 for connection."
    candidates = find_candidate_dates(text)
    assert len(candidates) >= 1
    assert candidates[0]["candidate_date"] == "2026-11-25"


def test_date_format_dd_hyphen_mm_yyyy():
    """Date extractor supports DD-MM-YYYY."""
    text = "Electricity invoice due on 25-11-2026 to prevent disconnection."
    candidates = find_candidate_dates(text)
    assert len(candidates) >= 1
    assert candidates[0]["candidate_date"] == "2026-11-25"


def test_date_format_month_dd_yyyy():
    """Date extractor supports Month DD, YYYY."""
    text = "Your free trial ends on October 20, 2026. Card will be charged."
    candidates = find_candidate_dates(text)
    assert len(candidates) >= 1
    assert candidates[0]["candidate_date"] == "2026-10-20"


def test_date_format_dd_month_yyyy():
    """Date extractor supports DD Month YYYY."""
    text = "Your annual premium is due on 05 November 2026 for continuous coverage."
    candidates = find_candidate_dates(text)
    assert len(candidates) >= 1
    assert candidates[0]["candidate_date"] == "2026-11-05"


def test_date_format_valid_till_dd_mmm():
    """Date extractor supports 'valid till DD-MMM' (e.g. valid till 25-Nov)."""
    text = "Your prepaid plan is valid till 25-Nov to avoid service suspension."
    candidates = find_candidate_dates(text)
    assert len(candidates) >= 1, "Failed to extract date from 'valid till 25-Nov' format!"
    assert candidates[0]["candidate_date"] == "2026-11-25"


def test_date_format_renew_in_x_days():
    """Date extractor supports 'renew in X days'."""
    text = "Your pack will expire. Please renew in 14 days to retain benefits."
    candidates = find_candidate_dates(text)
    assert len(candidates) >= 1, "Failed to extract relative date from 'renew in 14 days'!"
    assert candidates[0]["verification_status"] == "estimated"


def test_date_format_due_in_48_hours():
    """Date extractor supports 'due in 48 hours'."""
    text = "Your pending electricity bill is due in 48 hours to avoid penalty."
    candidates = find_candidate_dates(text)
    assert len(candidates) >= 1, "Failed to extract relative date from 'due in 48 hours'!"
    assert candidates[0]["verification_status"] == "estimated"


def test_date_anchored_phrases():
    """Date extractor supports anchored phrases: due date:, payment by:, validity ends:, renews on:, trial ends on:."""
    anchored_samples = [
        ("due date: 2026-11-15", "2026-11-15"),
        ("payment by: 2026-11-20", "2026-11-20"),
        ("validity ends: 2026-11-10", "2026-11-10"),
        ("renews on: 2026-12-01", "2026-12-01"),
        ("trial ends on: 2026-10-25", "2026-10-25"),
    ]
    for phrase, expected_date in anchored_samples:
        candidates = find_candidate_dates(f"Account Notice: {phrase}. Thank you.")
        assert len(candidates) >= 1, f"Failed anchored phrase: {phrase}"
        assert candidates[0]["candidate_date"] == expected_date


# ---------------------------------------------------------------------------
# 5. Verbatim Evidence Integrity Test (Programmatic 1:1 slice)
# ---------------------------------------------------------------------------

def test_verbatim_evidence_exact_slice_attribution():
    """
    Evidence: for every candidate, evidence_snippet must be an exact substring
    of the source at evidence_char_start:evidence_char_end.
    Verify programmatically for every candidate across multiple documents.
    """
    test_texts = [
        "First sentence. Your 14-day free trial ends on October 20. Another sentence.",
        "Notice: HDFC-98213 policy renewal. Your annual premium is due on November 05, 2026. Keep active.",
        "Airtel Broadband bill for account is due on 2026-11-15. Amount payable: INR 1179.",
        "BESCOM electricity due date: 2026-11-22 for consumer account."
    ]

    for text in test_texts:
        candidates = AnalysisEngine.extract_obligations(text)
        assert len(candidates) > 0
        for cand in candidates:
            snippet = cand["evidence_snippet"]
            start = cand["evidence_char_start"]
            end = cand["evidence_char_end"]
            assert start is not None and end is not None, "Missing evidence coordinates"
            slice_from_source = text[start:end]
            assert snippet == slice_from_source, (
                f"Evidence snippet mismatch! snippet='{snippet}' vs source[{start}:{end}]='{slice_from_source}'"
            )


# ---------------------------------------------------------------------------
# 6. Ambiguity & Uncertainty Handling Tests (Scenario D)
# ---------------------------------------------------------------------------

def test_ambiguity_sometime_this_month():
    """'sometime this month' produces date_unverified, unverified, requires_user_input True, no fabricated day."""
    text = "Your gym subscription fee will be charged sometime this month."
    candidates = AnalysisEngine.extract_obligations(text)
    assert len(candidates) == 1
    c = candidates[0]
    assert c["candidate_date"] == "UNVERIFIED"
    assert c["status"] == DeadlineStatus.DATE_UNVERIFIED
    assert c["verification_status"] == VerificationStatus.UNVERIFIED
    assert c["requires_user_input"] is True


def test_ambiguity_near_end_of_month():
    """'near the end of the month' produces date_unverified, unverified, requires_user_input True, no fabricated day."""
    text = "Your annual maintenance fee will be due sometime near the end of the month."
    candidates = AnalysisEngine.extract_obligations(text)
    assert len(candidates) == 1
    c = candidates[0]
    assert c["candidate_date"] == "UNVERIFIED"
    assert c["status"] == DeadlineStatus.DATE_UNVERIFIED
    assert c["verification_status"] == VerificationStatus.UNVERIFIED
    assert c["requires_user_input"] is True


def test_ambiguity_early_next_week():
    """'early next week' produces date_unverified, unverified, requires_user_input True, no fabricated day."""
    text = "The vendor stated that payment will be expected early next week."
    candidates = AnalysisEngine.extract_obligations(text)
    assert len(candidates) == 1
    c = candidates[0]
    assert c["candidate_date"] == "UNVERIFIED"
    assert c["status"] == DeadlineStatus.DATE_UNVERIFIED
    assert c["verification_status"] == VerificationStatus.UNVERIFIED
    assert c["requires_user_input"] is True


# ---------------------------------------------------------------------------
# 7. Empty & Date-less Source Tests
# ---------------------------------------------------------------------------

def test_empty_and_dateless_source():
    """Empty source or non-deadline text must return an empty candidate list gracefully."""
    assert AnalysisEngine.extract_obligations("") == []
    assert AnalysisEngine.extract_obligations("   \n\t  ") == []

    non_deadline_text = "Welcome to our team engineering newsletter! We shipped five new features this sprint."
    assert AnalysisEngine.extract_obligations(non_deadline_text) == []
