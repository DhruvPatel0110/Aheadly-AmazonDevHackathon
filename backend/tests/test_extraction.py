"""
Curated test suite for Phase 3: Parsing, Evidence Extraction & Deterministic Analysis Engine.
Includes 16 rigorous tests validating date accuracy, verbatim evidence attribution,
uncertainty handling (Scenario D), and file parsers.
"""
import pytest
from app.parsers.text_parser import parse_text_input
from app.parsers.email_parser import parse_email_input
from app.parsers.pdf_parser import parse_pdf_input, ScannedPdfError
from app.engine.date_extractor import find_candidate_dates
from app.engine.category_rules import extract_amount_and_currency, detect_provider, classify_obligation
from app.engine.obligation_classifier import AnalysisEngine
from app.models import DeadlineCategory, ObligationType, DeadlineStatus, VerificationStatus


# ---------------------------------------------------------------------------
# Test 1: Scenario A - Free-Trial Renewal Cancellation
# ---------------------------------------------------------------------------
def test_scenario_a_free_trial_extraction():
    text = (
        "Thank you for signing up for Netflix Premium. "
        "Your 14-day free trial ends on 2026-10-20. "
        "Your credit card will be charged INR 649 per month unless cancelled before."
    )
    results = AnalysisEngine.extract_obligations(text)
    assert len(results) >= 1
    trial_cand = results[0]
    assert trial_cand["provider_name"] == "Netflix"
    assert trial_cand["category"] == DeadlineCategory.SUBSCRIPTION
    assert trial_cand["obligation_type"] == ObligationType.TRIAL_ENDING
    assert trial_cand["candidate_date"] == "2026-10-20"
    assert trial_cand["amount"] == 649.0
    assert trial_cand["currency"] == "INR"
    assert "Your 14-day free trial ends on 2026-10-20" in trial_cand["evidence_snippet"]
    assert trial_cand["official_url"] == "https://www.netflix.com/youraccount"


# ---------------------------------------------------------------------------
# Test 2: Scenario B - Annual Health Insurance Premium
# ---------------------------------------------------------------------------
def test_scenario_b_insurance_premium():
    text = (
        "Dear Customer, Policy No. HDFC-99214. "
        "Your annual health insurance renewal premium of Rs. 14,250 is due on 05 November 2026. "
        "Pay on time to prevent policy lapse and retain your No Claim Bonus (NCB)."
    )
    results = AnalysisEngine.extract_obligations(text)
    assert len(results) >= 1
    ins_cand = results[0]
    assert ins_cand["provider_name"] == "HDFC ERGO"
    assert ins_cand["category"] == DeadlineCategory.INSURANCE
    assert ins_cand["obligation_type"] == ObligationType.RENEWAL
    assert ins_cand["candidate_date"] == "2026-11-05"
    assert ins_cand["amount"] == 14250.0
    assert "due on 05 November 2026" in ins_cand["evidence_snippet"]


# ---------------------------------------------------------------------------
# Test 3: Scenario C1 - Broadband Wi-Fi Bill
# ---------------------------------------------------------------------------
def test_scenario_c1_broadband_bill():
    text = (
        "Airtel Broadband Bill Notice: Your Wi-Fi bill for October is INR 999. "
        "Payment due date: 15/11/2026. Avoid late fee by paying before the due date."
    )
    results = AnalysisEngine.extract_obligations(text)
    assert len(results) >= 1
    bb = results[0]
    assert bb["provider_name"] == "Airtel"
    assert bb["category"] == DeadlineCategory.BROADBAND
    assert bb["obligation_type"] == ObligationType.PAYMENT_DUE
    assert bb["candidate_date"] == "2026-11-15"
    assert bb["amount"] == 999.0


# ---------------------------------------------------------------------------
# Test 4: Scenario C2 - Mobile Plan Validity Expiry
# ---------------------------------------------------------------------------
def test_scenario_c2_mobile_validity():
    text = (
        "Jio Alert: Your 1.5GB/day pack validity ends on 2026-10-28. "
        "Recharge with ₹299 to continue unlimited calling and high-speed data."
    )
    results = AnalysisEngine.extract_obligations(text)
    assert len(results) >= 1
    mob = results[0]
    assert mob["provider_name"] == "Jio"
    assert mob["obligation_type"] == ObligationType.VALIDITY_EXPIRY
    assert mob["candidate_date"] == "2026-10-28"
    assert mob["amount"] == 299.0


# ---------------------------------------------------------------------------
# Test 5: Scenario C3 - Electricity Utility Bill
# ---------------------------------------------------------------------------
def test_scenario_c3_electricity_bill():
    text = (
        "Tata Power Electricity Bill. Consumer ID: 8871239. "
        "Bill Amount: ₹ 2,340.00. Payment by: 2026-11-02. "
        "Disconnection notice applies after grace period."
    )
    results = AnalysisEngine.extract_obligations(text)
    assert len(results) >= 1
    elec = results[0]
    assert elec["provider_name"] == "Tata Power"
    assert elec["category"] == DeadlineCategory.UTILITY
    assert elec["obligation_type"] == ObligationType.PAYMENT_DUE
    assert elec["candidate_date"] == "2026-11-02"
    assert elec["amount"] == 2340.0


# ---------------------------------------------------------------------------
# Test 6: Scenario D - Uncertainty Handling (Refusal to Fabricate Date)
# ---------------------------------------------------------------------------
def test_scenario_d_uncertainty_handling():
    text = (
        "Hi, just reminding you that your annual maintenance fee for the club "
        "will be due sometime near the end of the month."
    )
    results = AnalysisEngine.extract_obligations(text)
    assert len(results) == 1
    vague_item = results[0]
    assert vague_item["candidate_date"] == "UNVERIFIED"
    assert vague_item["status"] == DeadlineStatus.DATE_UNVERIFIED
    assert vague_item["verification_status"] == VerificationStatus.UNVERIFIED
    assert vague_item["requires_user_input"] is True
    assert "near the end of the month" in vague_item["evidence_snippet"]


# ---------------------------------------------------------------------------
# Test 7: Scenario D2 - Another Vague Expression ("early next week")
# ---------------------------------------------------------------------------
def test_scenario_d2_vague_expression():
    text = "Please submit the quarterly progress report early next week."
    results = AnalysisEngine.extract_obligations(text)
    assert len(results) == 1
    assert results[0]["candidate_date"] == "UNVERIFIED"
    assert results[0]["status"] == DeadlineStatus.DATE_UNVERIFIED


# ---------------------------------------------------------------------------
# Test 8: Non-Deadline Document (Spam / Newsletter)
# ---------------------------------------------------------------------------
def test_non_deadline_document():
    text = (
        "Check out our new weekly recipes and home decoration ideas! "
        "Enjoy cooking delicious meals with fresh ingredients. Click here to unsubscribe."
    )
    results = AnalysisEngine.extract_obligations(text)
    assert len(results) == 0


# ---------------------------------------------------------------------------
# Test 9: DTH Television Renewal
# ---------------------------------------------------------------------------
def test_dth_renewal():
    text = "Tata Play Recharge Notice: Subscriber ID 10928392. Recharge by 2026-10-31 for uninterrupted TV."
    results = AnalysisEngine.extract_obligations(text)
    assert len(results) >= 1
    dth = results[0]
    assert dth["provider_name"] == "Tata Play"
    assert dth["category"] == DeadlineCategory.DTH
    assert dth["candidate_date"] == "2026-10-31"


# ---------------------------------------------------------------------------
# Test 10: E-commerce Return Window
# ---------------------------------------------------------------------------
def test_return_window_deadline():
    text = "Your order has been delivered. Return window closes on 2026-11-10. Items must be in original packaging."
    results = AnalysisEngine.extract_obligations(text)
    assert len(results) >= 1
    ret = results[0]
    assert ret["category"] == DeadlineCategory.RETURN_WINDOW
    assert ret["obligation_type"] == ObligationType.RETURN_DEADLINE
    assert ret["candidate_date"] == "2026-11-10"


# ---------------------------------------------------------------------------
# Test 11: 100% Verbatim Evidence Matching
# ---------------------------------------------------------------------------
def test_verbatim_evidence_integrity():
    text = (
        "Spotify Premium notification. Your student discount is ending soon. "
        "Your monthly renewal date is 2026-10-24. Charge will be ₹119."
    )
    results = AnalysisEngine.extract_obligations(text)
    assert len(results) >= 1
    for item in results:
        # Every snippet must literally be a substring of text
        assert item["evidence_snippet"] in text
        # If candidate date is concrete, original_date_str must appear in the evidence
        if item["candidate_date"] != "UNVERIFIED":
            assert item["original_date_str"] in item["evidence_snippet"]


# ---------------------------------------------------------------------------
# Test 12: Character Offset Bounds Validation
# ---------------------------------------------------------------------------
def test_character_offset_accuracy():
    text = "Important: Electricity bill due on 2026-11-04 for INR 1500."
    dates = find_candidate_dates(text)
    assert len(dates) >= 1
    cand = dates[0]
    start = cand["evidence_char_start"]
    end = cand["evidence_char_end"]
    extracted_slice = text[start:end].strip()
    assert extracted_slice == cand["evidence_snippet"]


# ---------------------------------------------------------------------------
# Test 13: Text Parser Functionality
# ---------------------------------------------------------------------------
def test_text_parser():
    raw = "Subject: Wi-Fi Bill Alert\n\nPlease pay your broadband invoice."
    parsed = parse_text_input(raw)
    assert parsed["title"] == "Wi-Fi Bill Alert"
    assert len(parsed["file_hash"]) == 64
    assert parsed["clean_text"] == raw.strip()

    # Empty text raises error
    with pytest.raises(ValueError):
        parse_text_input("   ")


# ---------------------------------------------------------------------------
# Test 14: Email Parser with HTML & Headers
# ---------------------------------------------------------------------------
def test_email_parser():
    eml_sample = (
        "From: billing@netflix.com\r\n"
        "Subject: Your Free Trial is Ending\r\n"
        "Date: Wed, 14 Oct 2026 10:00:00 +0000\r\n"
        "Content-Type: text/html; charset=utf-8\r\n"
        "\r\n"
        "<html><body><h1>Netflix Notice</h1><p>Your trial ends on 2026-10-20.</p></body></html>"
    )
    parsed = parse_email_input(eml_sample)
    assert parsed["title"] == "Your Free Trial is Ending"
    assert "From: billing@netflix.com" in parsed["clean_text"]
    assert "Your trial ends on 2026-10-20." in parsed["clean_text"]
    assert "<html>" not in parsed["clean_text"]  # HTML stripped


# ---------------------------------------------------------------------------
# Test 15: PDF Parser & Scanned PDF Detection
# ---------------------------------------------------------------------------
def test_pdf_parser_scanned_detection():
    # Empty or fake byte stream should raise ValueError or ScannedPdfError
    with pytest.raises(ValueError):
        parse_pdf_input(b"Not a valid PDF byte string")


# ---------------------------------------------------------------------------
# Test 16: Currency and Amount Extraction Robustness
# ---------------------------------------------------------------------------
def test_amount_extraction_cases():
    amt1, curr1 = extract_amount_and_currency("Total amount due is ₹ 1,450.50 only.")
    assert amt1 == 1450.50
    assert curr1 == "INR"

    amt2, curr2 = extract_amount_and_currency("Monthly subscription fee: $14.99 charged to card.")
    assert amt2 == 14.99
    assert curr2 == "USD"

    amt3, curr3 = extract_amount_and_currency("Invoice amount: Rs. 999.00 due soon.")
    assert amt3 == 999.0
    assert curr3 == "INR"

    amt4, _ = extract_amount_and_currency("There is no money mentioned here.")
    assert amt4 is None
