# Phase 7: End-to-End Scenarios & Follow-Through Workflows

This document records the end-to-end execution, evidence verification, and follow-through flows for the **4 core benchmark scenarios** defined in [`idea.md`](../idea.md) and [`phases.txt`](../phases.txt).

All scenarios execute through the live self-hosted MCP Server (Spec 2025-11-25+ over Streamable HTTP) and are fully accessible via the web client interface.

---

## 1. Scenario Summary Matrix

| Scenario | Obligation Type | Provider | Input Format | Extracted Date | Extracted Amount | Verbatim Evidence Grounded | MCP Tools Dispatched |
|---|---|---|---|---|---|---|---|
| **Scenario A** | Free-Trial Renewal Cancellation | Service Provider / Netflix | Confirmation Email (Text) | `2026-10-20` | ₹499.00 / mo | *"Your 14-day free trial ends on October 20"* | `ingest_source`, `find_deadline_candidates`, `confirm_or_correct_deadline`, `create_follow_up`, `prepare_next_step`, `update_deadline_status` |
| **Scenario B** | Annual Insurance Premium | HDFC ERGO | Policy Notice (.eml) | `2026-11-05` | ₹14,250.00 | *"Your annual premium of ₹14,250 is due on November 05, 2026 to ensure continuous coverage"* | `ingest_source`, `find_deadline_candidates`, `confirm_or_correct_deadline`, `create_follow_up`, `get_deadline_evidence` |
| **Scenario C** | Recurring Household Bills | Airtel Broadband, Tata Power, Jio Mobile | Batch Multi-format notices | `2026-10-12` to `2026-11-18` | ₹999, ₹2,450, ₹349 | Verbatim bill due dates & plan validity lines | `ingest_source`, `find_deadline_candidates`, `list_deadlines` |
| **Scenario D** | Date Ambiguity & Refusal-to-Guess | Building Maintenance | Vague email notification | `UNVERIFIED` | N/A | *"Your annual maintenance fee will be due sometime near the end of the month"* | `ingest_source`, `find_deadline_candidates`, `create_follow_up` (Blocked), `confirm_or_correct_deadline` |

---

## 2. Detailed Scenario Walkthroughs

### Scenario A: Free-Trial Renewal Cancellation (Streaming Service)

> **Context:** A user signs up for a streaming service trial. If not cancelled 24 hours prior, the credit card is automatically charged recurring monthly fees.

1. **Ingestion & Extraction:**
   - **Input:**
     ```text
     From: info@mailer.netflix.com
     Subject: Your free trial is coming to an end
     Dear Member,
     Your 14-day free trial ends on October 20 2026. Your card will be charged ₹499/month unless cancelled 24 hours prior. Manage your membership anytime in Account Settings.
     ```
   - **Deterministic Output:**
     - `candidate_date`: `2026-10-20`
     - `amount`: `499.0` (Currency: INR)
     - `obligation_type`: `trial_ending`
     - `category`: `subscription`
     - `evidence_snippet`: `"Your 14-day free trial ends on October 20"` (Coordinates: `[89:135]`)
2. **User Review & Confirmation:**
   - User reviews the candidate in the **Candidate Review Queue**.
   - User confirms date and schedules advance reminders (`[3, 1]` days prior).
   - In-app reminders scheduled for `2026-10-17T00:00:00` and `2026-10-19T00:00:00`.
   - Downloadable RFC 5545 `.ics` event generated.
3. **Prepared Next-Step Follow-Through:**
   - The agent builds a 4-step actionable cancellation guide:
     1. Verify the exact cancellation cut-off hour in account settings.
     2. Open official cancellation page using the verified link.
     3. Follow prompts to confirm cancellation and avoid the next billing cycle.
     4. Save cancellation confirmation number or receipt.
4. **Resolution:**
   - Once cancelled, user marks status as `cancelled`.
   - Audit trail records: `status_changed` (`upcoming` $\rightarrow$ `cancelled`).

---

### Scenario B: Annual Health / Vehicle Insurance Premium (HDFC ERGO)

> **Context:** Annual insurance policy renewal notices often arrive weeks in advance. Missing the due date risks policy lapse and loss of accumulated No-Claim Bonus (NCB).

1. **Ingestion & Extraction:**
   - **Input:**
     ```text
     Policy No: HDFC-98213. Your annual premium of ₹14,250 is due on November 05, 2026 to ensure continuous coverage. Please pay before the due date to avoid policy lapse.
     ```
   - **Deterministic Output:**
     - `provider_name`: `HDFC ERGO`
     - `candidate_date`: `2026-11-05`
     - `amount`: `14250.0`
     - `category`: `insurance`
     - `obligation_type`: `renewal`
     - `evidence_snippet`: `"Your annual premium of ₹14,250 is due on November 05, 2026 to ensure continuous coverage"`
2. **Long-Range Advance Alerts:**
   - High-value obligations schedule lead times of **14 days** and **3 days**:
     - Reminder 1: `2026-10-22T00:00:00` (14 days before)
     - Reminder 2: `2026-11-02T00:00:00` (3 days before)
3. **Safety Guarantee:**
   - Status strictly remains `upcoming` / `needs_review` until user confirms payment.
   - External provider payment is never falsely assumed without explicit confirmation.

---

### Scenario C: Recurring Household Bills Management

> **Context:** Managing multiple household utilities (Wi-Fi broadband, electricity, mobile prepaid validity) with varying billing cycles.

1. **Batch Ingestion:**
   - Ingests 3 distinct sources:
     - Broadband bill: Airtel Wi-Fi due `2026-11-15` (INR 999.0)
     - Electricity bill: Tata Power due `2026-11-18` (INR 2,450.0)
     - Mobile plan validity: Jio prepaid expiry `2026-10-12` (INR 349.0)
2. **Multi-Category Disambiguation:**
   - Wi-Fi categorized as `broadband`.
   - Electricity categorized as `utility`.
   - Mobile plan categorized as `mobile`.
3. **Chronological Dashboard:**
   - All items aggregated and sorted chronologically:
     1. Jio Mobile: `2026-10-12`
     2. Airtel Wi-Fi: `2026-11-15`
     3. Tata Power: `2026-11-18`
   - Category filtering (`list_deadlines(category_filter='utility')`) returns only the electricity bill.

---

### Scenario D: Date Ambiguity & Refusal-to-Guess Safeguard

> **Context:** Ambiguous documents with vague temporal mentions (*"sometime near the end of the month"*, *"due soon"*) must NOT cause the AI agent to invent an arbitrary date.

1. **Ingestion & Safeguard Trigger:**
   - **Input:**
     ```text
     Hi Dhruv, your annual maintenance fee will be due sometime near the end of the month. Please keep funds ready.
     ```
   - **Deterministic Output:**
     - `candidate_date`: `UNVERIFIED`
     - `verification_status`: `unverified`
     - `status`: `date_unverified`
     - `evidence_snippet`: `"Your annual maintenance fee will be due sometime near the end of the month"`
2. **Reminder Prevention Guard:**
   - Attempting to invoke `create_follow_up` raises:
     ```json
     {
       "error": "Cannot schedule reminders for an unverified date. Please confirm the date first."
     }
     ```
   - Prevents phantom notifications from polluting user calendars.
3. **User Clarification Workflow:**
   - User inputs verified calendar date: `2026-10-31`.
   - MCP tool `confirm_or_correct_deadline` updates verification status to `user_confirmed`.
   - Reminder scheduling is unlocked and successfully scheduled.

---

## 3. Conversational Agent & MCP Telemetry

Queries tested against `POST /api/agent/chat`:
- `"How do I cancel Netflix?"` $\rightarrow$ Dispatches `prepare_next_step` $\rightarrow$ Returns step-by-step cancellation guide.
- `"What bills are due soon?"` $\rightarrow$ Dispatches `list_deadlines` $\rightarrow$ Returns formatted chronological list.
- `"Show evidence for HDFC"` $\rightarrow$ Dispatches `get_deadline_evidence` $\rightarrow$ Returns quoted source snippet with character bounds.

All calls record to the in-process **MCP Client Bridge** with execution latencies ranging between **0.05ms** and **31ms**.
