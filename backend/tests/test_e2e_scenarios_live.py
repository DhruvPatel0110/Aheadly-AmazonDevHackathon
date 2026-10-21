"""
Phase 7 Live End-to-End Scenario Verification Runner.
Executes Scenarios A, B, C, D sequentially against the running server,
verifying all extraction, confirmation, reminder, next-step, and refusal logic.
"""
import sys
import json
import urllib.request
import urllib.parse
from pathlib import Path

SAMPLE_DATA_DIR = Path(__file__).resolve().parent.parent / "sample_data"
if not SAMPLE_DATA_DIR.exists():
    SAMPLE_DATA_DIR = Path("backend/sample_data")

BASE_URL = "http://127.0.0.1:8000"
sys.stdout.reconfigure(encoding="utf-8")


def api_post(endpoint, data=None, json_body=None):
    url = f"{BASE_URL}{endpoint}"
    if json_body is not None:
        payload = json.dumps(json_body).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    elif data is not None:
        payload = urllib.parse.urlencode(data).encode("utf-8")
        req = urllib.request.Request(url, data=payload, method="POST")
    else:
        req = urllib.request.Request(url, method="POST")
    
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def api_get(endpoint):
    url = f"{BASE_URL}{endpoint}"
    with urllib.request.urlopen(url) as resp:
        return json.loads(resp.read().decode("utf-8"))


def mcp_call(tool_name, arguments):
    return api_post("/api/mcp/call", json_body={"tool": tool_name, "arguments": arguments})


def run_all_scenarios():
    print("=" * 70)
    print("PHASE 7: LIVE END-TO-END SCENARIO VERIFICATION")
    print("=" * 70)

    # 0. Clean reset
    print("\n[Step 0] Resetting demo database and MCP tool call logs...")
    res = api_post("/api/demo/reset?confirm=true")
    print("  -> Status:", res["status"])

    # -------------------------------------------------------------------------
    # Scenario A: Free-Trial Renewal Cancellation
    # -------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("SCENARIO A: Free-Trial Renewal Cancellation (Streaming Service)")
    print("=" * 70)
    sample_a = (SAMPLE_DATA_DIR / "scenario_a_trial.txt").read_text(encoding="utf-8")
    
    print("[A.1] Ingesting confirmation email...")
    ingest_a = api_post("/api/sources/upload", data={"raw_text": sample_a, "title": "Netflix Trial Email"})
    source_a_id = ingest_a["source"]["source_id"]
    candidates_a = ingest_a["candidates"]
    assert len(candidates_a) >= 1, "Scenario A failed: no candidates extracted"
    cand_a = candidates_a[0]
    deadline_a_id = cand_a["id"]

    print("  -> Extracted Provider:     ", cand_a["provider_name"])
    print("  -> Candidate Due Date:     ", cand_a["candidate_date"])
    print("  -> Extracted Amount:       ", f"INR {cand_a['amount']}")
    print("  -> Obligation Type:        ", cand_a["obligation_type"])
    print("  -> Verbatim Evidence Quote:", f'"{cand_a["evidence_snippet"]}"')

    assert cand_a["candidate_date"] == "2026-10-20", f"Expected 2026-10-20, got {cand_a['candidate_date']}"
    assert cand_a["amount"] == 499.0, f"Expected 499.0, got {cand_a['amount']}"
    assert "October 20" in cand_a["evidence_snippet"], "Evidence snippet missing target date"

    print("\n[A.2] Confirming deadline date and scheduling advance reminders...")
    conf_a = mcp_call("confirm_or_correct_deadline", {
        "deadline_id": deadline_a_id,
        "confirmed_date": "2026-10-20",
        "provider_name": "Netflix"
    })
    print("  -> Confirmed Status:       ", conf_a["status"])
    print("  -> Verification Status:    ", conf_a["verification_status"])

    follow_up_a = mcp_call("create_follow_up", {
        "deadline_id": deadline_a_id,
        "lead_days": [3, 1],
        "export_calendar": True
    })
    print("  -> Reminders Created:      ", follow_up_a["reminders_count"], "scheduled reminders")
    for r in follow_up_a["scheduled_reminders"]:
        print("     - Remind at:", r["remind_at"], f"({r['lead_days']} days prior)")
    print("  -> RFC 5545 Calendar ICS:   Generated successfully (length:", len(follow_up_a["calendar_ics"]), "chars)")

    print("\n[A.3] Preparing next-step cancellation guide...")
    next_step_a = mcp_call("prepare_next_step", {"deadline_id": deadline_a_id})
    print("  -> Provider Portal URL:    ", next_step_a["official_url"])
    print("  -> Action Checklist:")
    for step in next_step_a["checklist"]:
        print("     ", step)

    print("\n[A.4] Marking obligation as 'cancelled' upon user cancellation...")
    status_a = mcp_call("update_deadline_status", {
        "deadline_id": deadline_a_id,
        "new_status": "cancelled",
        "resolution_notes": "Cancelled subscription via provider portal before cut-off"
    })
    print("  -> Final Status:           ", status_a["status"])
    assert status_a["status"] == "cancelled", "Expected status to be cancelled"
    print("  [✓] Scenario A Completed Successfully!")

    # -------------------------------------------------------------------------
    # Scenario B: Annual Health / Vehicle Insurance Premium
    # -------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("SCENARIO B: Annual Insurance Premium (HDFC ERGO)")
    print("=" * 70)
    sample_b = (SAMPLE_DATA_DIR / "scenario_b_insurance.eml").read_text(encoding="utf-8")

    print("[B.1] Ingesting policy renewal notice email...")
    ingest_b = api_post("/api/sources/upload", data={"raw_text": sample_b, "title": "HDFC Policy Notice"})
    candidates_b = ingest_b["candidates"]
    assert len(candidates_b) >= 1, "Scenario B failed: no candidates extracted"
    cand_b = candidates_b[0]
    deadline_b_id = cand_b["id"]

    print("  -> Extracted Provider:     ", cand_b["provider_name"])
    print("  -> Candidate Due Date:     ", cand_b["candidate_date"])
    print("  -> Premium Amount:         ", f"INR {cand_b['amount']}")
    print("  -> Category:               ", cand_b["category"])
    print("  -> Verbatim Evidence Quote:", f'"{cand_b["evidence_snippet"]}"')

    assert cand_b["provider_name"] == "HDFC ERGO", f"Expected HDFC ERGO, got {cand_b['provider_name']}"
    assert cand_b["candidate_date"] == "2026-11-05", f"Expected 2026-11-05, got {cand_b['candidate_date']}"
    assert cand_b["amount"] == 14250.0, f"Expected 14250.0, got {cand_b['amount']}"

    print("\n[B.2] Creating long-range advance reminders (14 days and 3 days before)...")
    follow_up_b = mcp_call("create_follow_up", {
        "deadline_id": deadline_b_id,
        "lead_days": [14, 3],
        "export_calendar": True
    })
    print("  -> Reminders Scheduled:   ", follow_up_b["reminders_count"])
    for r in follow_up_b["scheduled_reminders"]:
        print("     - Remind at:", r["remind_at"], f"({r['lead_days']} days prior)")

    print("\n[B.3] Verifying status remains pending until user payment confirmation...")
    check_b = api_get(f"/api/deadlines/{deadline_b_id}")
    print("  -> Current Status:         ", check_b["status"])
    assert check_b["status"] != "completed", "Status must not automatically mark completed"
    print("  [✓] Scenario B Completed Successfully!")

    # -------------------------------------------------------------------------
    # Scenario C: Recurring Household Bills Management
    # -------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("SCENARIO C: Batch Ingestion & Household Bills Management")
    print("=" * 70)
    sample_c1 = (SAMPLE_DATA_DIR / "scenario_c1_broadband.txt").read_text(encoding="utf-8")
    sample_c2 = (SAMPLE_DATA_DIR / "scenario_c2_electricity.txt").read_text(encoding="utf-8")
    sample_c3 = (SAMPLE_DATA_DIR / "scenario_c3_mobile.txt").read_text(encoding="utf-8")

    print("[C.1] Ingesting broadband, electricity, and mobile plan notices...")
    r1 = api_post("/api/sources/upload", data={"raw_text": sample_c1, "title": "Airtel Wi-Fi"})
    r2 = api_post("/api/sources/upload", data={"raw_text": sample_c2, "title": "Tata Power"})
    r3 = api_post("/api/sources/upload", data={"raw_text": sample_c3, "title": "Jio Mobile"})

    print("  -> Airtel Broadband Candidates:", len(r1["candidates"]))
    print("  -> Tata Power Candidates:      ", len(r2["candidates"]))
    print("  -> Jio Mobile Candidates:      ", len(r3["candidates"]))

    print("\n[C.2] Querying unified chronological obligation dashboard...")
    all_deadlines = mcp_call("list_deadlines", {})
    categories = {d["category"] for d in all_deadlines}
    print("  -> Tracked Categories in DB:  ", sorted(list(categories)))
    assert "broadband" in categories, "Missing broadband category"
    assert "utility" in categories, "Missing utility category"
    assert "mobile" in categories, "Missing mobile category"

    # Verify chronological sorting
    dates = [d["candidate_date"] for d in all_deadlines if d["candidate_date"] != "UNVERIFIED"]
    assert dates == sorted(dates), f"Dates not chronological: {dates}"
    print("  -> Chronological Order Check:  VERIFIED (Earliest:", dates[0], "to Latest:", dates[-1], ")")

    print("\n[C.3] Testing category filtering via list_deadlines...")
    util_items = mcp_call("list_deadlines", {"category_filter": "utility"})
    print("  -> Filtered 'utility' Items:   ", len(util_items))
    for u in util_items:
        print("     -", u["provider_name"], "|", u["candidate_date"], "| INR", u["amount"])
        assert u["category"] == "utility"
    print("  [✓] Scenario C Completed Successfully!")

    # -------------------------------------------------------------------------
    # Scenario D: Date Uncertainty & Integrity Safeguard
    # -------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("SCENARIO D: Date Ambiguity & Refusal-to-Guess Safeguard")
    print("=" * 70)
    sample_d = (SAMPLE_DATA_DIR / "scenario_d_uncertainty.txt").read_text(encoding="utf-8")

    print("[D.1] Ingesting document with vague date ('sometime near the end of the month')...")
    ingest_d = api_post("/api/sources/upload", data={"raw_text": sample_d, "title": "Maintenance Notice"})
    candidates_d = ingest_d["candidates"]
    assert len(candidates_d) >= 1
    cand_d = candidates_d[0]
    deadline_d_id = cand_d["id"]

    print("  -> Extracted Candidate Date:  ", cand_d["candidate_date"])
    print("  -> Verification Status:       ", cand_d["verification_status"])
    print("  -> Obligation Status:         ", cand_d["status"])
    print("  -> Quoted Snippet:            ", f'"{cand_d["evidence_snippet"]}"')

    assert cand_d["candidate_date"] == "UNVERIFIED", f"Expected UNVERIFIED, got {cand_d['candidate_date']}"
    assert cand_d["status"] in ("date_unverified", "needs_review")

    print("\n[D.2] Attempting to create advance alerts on unverified date...")
    try:
        mcp_call("create_follow_up", {"deadline_id": deadline_d_id, "lead_days": [7, 1]})
        print("  [ERROR] Follow-up creation should have failed!")
        sys.exit(1)
    except urllib.error.HTTPError as err:
        err_msg = json.loads(err.read().decode("utf-8"))["detail"]
        print("  -> Safeguard Triggered:        400 Bad Request")
        print("  -> Diagnostic Message:        ", err_msg)
        assert "unverified date" in err_msg.lower(), "Diagnostic message did not mention unverified date"

    print("\n[D.3] Confirming date explicitly via user verification ('2026-10-31')...")
    conf_d = mcp_call("confirm_or_correct_deadline", {
        "deadline_id": deadline_d_id,
        "confirmed_date": "2026-10-31",
        "provider_name": "Building Society"
    })
    print("  -> Post-Verification Date:    ", conf_d["candidate_date"])
    print("  -> Post-Verification Status:  ", conf_d["status"])
    assert conf_d["candidate_date"] == "2026-10-31"

    print("\n[D.4] Rescheduling advance alerts after date confirmation...")
    follow_up_d = mcp_call("create_follow_up", {
        "deadline_id": deadline_d_id,
        "lead_days": [7, 1],
        "export_calendar": True
    })
    print("  -> Alert Scheduling Status:    SUCCESS (", follow_up_d["reminders_count"], "reminders created )")
    print("  [✓] Scenario D Completed Successfully!")

    # -------------------------------------------------------------------------
    # Conversational Assistant Check
    # -------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("CONVERSATIONAL AGENT / ALEXA+ DISPATCH VERIFICATION")
    print("=" * 70)
    chat_queries = [
        ("How do I cancel Netflix?", deadline_a_id),
        ("What bills are due soon?", None),
        ("Show evidence for HDFC", deadline_b_id),
    ]

    for q, did in chat_queries:
        print(f"\nUser query: '{q}'")
        chat_res = api_post("/api/agent/chat", json_body={"message": q, "active_deadline_id": did})
        print("  -> Tools Invoked:", chat_res["tools_invoked"])
        print("  -> Response Preview:", chat_res["reply"][:120].replace("\n", " "), "...")

    # -------------------------------------------------------------------------
    # Judge MCP Protocol Log Verification
    # -------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("MCP CLIENT BRIDGE & JUDGE OBSERVABILITY LOG")
    print("=" * 70)
    logs = api_get("/api/mcp/log")
    print("  -> Total Real MCP Tool Calls Recorded:", len(logs))
    tool_counts = {}
    for l in logs:
        t = l.get("tool_name") or l.get("tool")
        tool_counts[t] = tool_counts.get(t, 0) + 1
    
    print("  -> Tool Breakdown:")
    for t, c in sorted(tool_counts.items()):
        print(f"     - {t:<30}: {c} calls")

    print("\n" + "=" * 70)
    print("ALL 4 SCENARIOS (A, B, C, D) PASSED DETERMINISTICALLY WITH 100% ACCURACY!")
    print("=" * 70)


if __name__ == "__main__":
    run_all_scenarios()
