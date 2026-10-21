# Comprehensive Full-Stack Audit Report: Deadline Rescue
**Project:** Deadline Rescue  
**Hackathon Track:** Amazon Developer Hackathon 2026 — Alexa+ Track  
**Audit Mode:** Read-Only Diagnostic Mode (Zero Code Modifications Applied)  
**Budget Constraint Verified:** Strict ₹0 out-of-pocket baseline  
**Date of Audit:** October 21, 2026  
**Auditor:** Senior QA Engineer, Backend Test Engineer & MCP Protocol Auditor  

---

## 1. Executive Summary

### 1.1 Overall Audit Outcome
A rigorous, evidence-based full-stack audit of the **Deadline Rescue** repository was conducted across all backend services, SQLite persistence models, the deterministic extraction engine, the self-hosted MCP server, FastAPI REST endpoints, and the React 19 frontend integration. 

While the application features an aesthetically rich UI, a functional 8-tool MCP server over JSON-RPC 2.0, and 104 passing pytest unit tests when invoked from the repository root, the audit identified **critical defects in date extraction, evidence integrity, calendar generation, and frontend-to-MCP integration** that directly threaten the core value proposition of an "evidence-backed, zero-hallucination" deadline tracker.

Most critically:
1. **Date Extraction Year Corruption (`BE-001`):** The date extractor's anchored context regular expression halts at commas (`,`), which causes dates formatted as `"Month DD, YYYY"` (e.g., `"due on November 05, 2027"`) to discard the explicit year and falsely infer the current year (`2026-11-05`), inventing an incorrect deadline.
2. **Single-Digit Date Format Rejection (`BE-002`):** Standard dates lacking leading zeroes (e.g., `5/11/2026`, `15/5/2026`, `2026-5-1`) fail extraction completely, returning zero candidates.
3. **Evidence Snippet Truncation on Currency Decimals (`BE-003`):** Sentence boundary detection splits on all period characters, treating decimal points in numbers (e.g., `"fee of 50.00 is due on Nov 5"`) as sentence breaks, truncating evidence to `"00 is due on Nov 5"`.
4. **Silent Date Fabrication in Calendar Export (`BE-004`):** When generating an `.ics` calendar file for an unverified deadline (`candidate_date = "UNVERIFIED"`), `calendar_service.py` silently fabricates a date exactly 7 days in the future and sets an alarm for tomorrow, violating the strict anti-hallucination mandate.
5. **Simulated MCP Tool-Call Activity in UI (`FE-001`):** `McpActivityCard.jsx` hardcodes mock tool calls (`ingest_source 14ms`, `find_deadline_candidates 22ms`, `get_deadline_evidence 31ms`) with dynamic timestamps when the log is empty, presenting them under the header `"MCP activity (live)"`.
6. **Orphaned / Disconnected Frontend Components (`FE-002`, `FE-004`, `FE-005`):** `EvidenceViewerModal` is passed `source={null}` from `App.jsx`, disabling full document context and coordinate highlighting. MCP tool `prepare_next_step` is never called by the UI cards, and the 487-line `DeadlineList.jsx` and `AlexaAssistantPanel.jsx` components are completely unused.

### 1.2 Test Execution Metrics
- **Total Tests Executed:** 115
  - Existing Automated Pytest Suite: 104 tests
  - Automated Benchmark Suite: 1 test (evaluating 25 ground-truth documents)
  - Diagnostic & Integration Proof Executions: 10 targeted tests
- **Tests Passed:** 109
- **Tests Failed / Errored:** 6 (5 failures when pytest is executed from `backend/` working directory due to path sensitivity; 1 failure demonstrating single-digit date rejection)
- **Tests Blocked / Untested:** 3 (Live Amazon Echo/Alexa+ hardware delivery, multi-client real-time SSE event propagation, automated end-to-end browser click-through)
- **Confirmed Defects:** 16
- **Likely Defects:** 3
- **Potential Risks:** 4
- **Missing Requirements:** 3

### 1.3 Readiness Assessment for Hackathon Demo
**Verdict:** **Conditionally Ready for Scripted Demo; Unready for Unconstrained User Testing.**  
The curated four demo scenarios (A, B, C, D) succeed on their exact predefined fixtures because their wording avoids the single-digit regex trap and decimal period truncation. However, if a judge enters unpadded dates, dates across years with commas, or tests `.ics` export on ambiguous dates, the system will fail or fabricate calendar dates.

---

## 2. Environment and Test Coverage

### 2.1 Runtime Environment
- **Operating System:** Windows 10 / 11 (AMD64)
- **Python Version:** 3.14.5
- **Node.js Version:** v24.18.0
- **npm Version:** 11.16.0
- **Virtual Environment:** `.\venv\Scripts\python.exe`
- **Core Python Dependencies:**
  - `fastapi`: 0.143.0
  - `uvicorn`: 0.54.0
  - `mcp`: 2.3.0
  - `mcp-types`: 2.3.0
  - `pydantic`: 2.14.1
  - `aiosqlite`: 0.22.1
  - `pypdf`: 6.20.1
  - `icalendar`: 7.3.0
  - `httpx`: 0.28.1
  - `sse-starlette`: 3.5.0
  - `pytest`: 9.1.1
  - `pytest-asyncio`: 1.4.0
- **Core Frontend Dependencies:**
  - `react`: 19.2.8
  - `react-dom`: 19.2.8
  - `vite`: 8.3.4
  - `lucide-react`: 1.56.0
  - `oxlint`: 1.81.0

### 2.2 Commands Executed During Audit
1. `.\venv\Scripts\python.exe --version; node --version; npm --version`
2. `.\venv\Scripts\pip.exe list`
3. `npm run lint` (in `frontend/`, oxlint scanner)
4. `npm run build` (in `frontend/`, Vite production bundle validation)
5. `..\venv\Scripts\pytest.exe -v` (executed from `backend/` directory)
6. `.\venv\Scripts\pytest.exe backend/tests -v` (executed from project root)
7. `.\venv\Scripts\python.exe -c "..."` (isolated synthetic executions testing single-digit date extraction, decimal period truncation, comma truncation in anchor regex, unverified `.ics` generation, unverified reminder creation, 8-tool MCP lifecycle, duplicate source extraction, and multipart upload)
8. `git status --short` (verified zero modifications to project source files)

### 2.3 Environmental Constraints & Limitations
- **No Paid Cloud APIs:** In strict adherence to Rule C (₹0 budget), no paid external APIs (OpenAI, Anthropic, AWS Bedrock) were invoked.
- **Local Ollama Daemon:** Local Ollama was offline during testing; deterministic engine fallback was validated.
- **Live Alexa+ Echo Skill:** Testing was performed against the self-hosted MCP server and web client; no physical Echo or proprietary Amazon Alexa+ cloud skill integration was tested.

---

## 3. Backend Findings

### 3.1 Startup and Configuration
- **Status:** **PASS** (with configuration sensitivity).
- `backend/app/config.py` correctly reads `DEADLINE_RESCUE_DB_PATH` from environment variables, defaulting to `backend/data/deadline_rescue.db`.
- `cors_origins` permits `localhost:5173`, `127.0.0.1:5173`, `localhost:3000`, and `127.0.0.1:3000`.
- Lifespan handler in `backend/app/main.py:24-29` initializes database schema on startup.

### 3.2 Database Layer (`backend/app/database.py`, `models.py`)
- **Status:** **PARTIAL**
- **Schema & Constraints:** Four tables (`sources`, `deadlines`, `reminders`, `audit_logs`) enforce SQLite `CHECK` constraints on enums and `FOREIGN KEY (..., ON DELETE CASCADE)`. Indexes exist on `status`, `candidate_date`, `source_id`, and `file_hash`.
- **Defect `DB-001` (Duplicate Deadlines on Re-Extraction):** While `sources` table uses `file_hash` to deduplicate ingested text, calling `find_deadline_candidates(source_id)` repeatedly unconditionally inserts new rows into `deadlines` with new UUIDs. Reprocessing the same document produces duplicate deadlines.
- **Defect `DB-002` (Migration Foreign Key Inconsistency):** In `database.py:134-152`, table migration executes `PRAGMA foreign_keys = OFF;`, but `SCHEMA_SQL` immediately turns foreign keys back `ON` at line 14 before data copy. Furthermore, `INSERT OR IGNORE` risks silently dropping records that fail new constraints.

### 3.3 Models and Schemas (`backend/app/schemas.py`, `models.py`)
- **Status:** **PASS**
- Pydantic models separate DB entities from API payloads.
- `DeadlineCreate`, `DeadlineUpdate`, `SourceCreate`, and `ReminderCreate` provide field validation. Enums prevent invalid obligation types, categories, and verification statuses.
- `models.py:69-75` implements a custom `__getattr__` lazy-loader to resolve circular dependencies between schemas and models cleanly.

### 3.4 Text, Email, and PDF Parsers
- **Status:** **PARTIAL**
- **Text Parser (`text_parser.py`):**
  - **Defect `BE-006`:** Line 43 contains faulty classification logic:
    ```python
    "source_type": "manual" if len(cleaned) < 300 and "sms" not in cleaned.lower() else "email"
    ```
    If text contains `"sms"`, the condition evaluates to `False`, classifying the snippet as `"email"`. Any pasted text over 300 characters is also classified as `"email"`. It is impossible for `source_type` to ever be `"sms"`.
- **Email Parser (`email_parser.py`):**
  - Handles multipart text and HTML emails, sanitizing HTML via `HTMLTextExtractor`. Correctly parses `.eml` bytes or header text.
- **PDF Parser (`pdf_parser.py`):**
  - Uses `pypdf.PdfReader`. Extracts text across digital pages. Accurately raises `ScannedPdfError` when text length is <25 characters ("No readable text layer; please paste text or provide a digital PDF").

### 3.5 Date Extraction Engine (`backend/app/engine/date_extractor.py`)
- **Status:** **FAIL**
- **Defect `BE-001` (Critical - Comma Truncation in Anchor Regex):**
  - `ANCHOR_REGEX` (lines 12-18) uses `[^\n\r,\.;]+` to isolate the target date clause following keywords like `"due on"`, `"due date"`.
  - When text uses standard English comma-separated dates (e.g. `"due on November 05, 2027 to ensure coverage"`), the regex halts at the comma.
  - The date parser receives only `"November 05"`, loses the explicit year `2027`, and falls back to inferring the current year `2026`.
  - **Reproduction:** `find_candidate_dates("Your premium is due on November 05, 2027 to ensure coverage.")` extracts `'2026-11-05'` instead of `'2027-11-05'`.
- **Defect `BE-002` (High - Single-Digit Day/Month Rejection):**
  - `DATE_PATTERNS` regexes require 2 digits:
    - `re.compile(r'\b(20\d{2}[-/](?:0[1-9]|1[0-2])[-/](?:0[1-9]|[12]\d|3[01]))\b')`
    - `re.compile(r'\b((?:0[1-9]|[12]\d|3[01])[-/](?:0[1-9]|1[0-2])[-/](?:20\d{2}))\b')`
  - Any date written with a single digit without leading zero (e.g., `5/11/2026`, `15/5/2026`, `2026-5-1`) fails matching entirely.
  - **Reproduction:** `find_candidate_dates("Due date: 5/11/2026")` returns `[]`.

### 3.6 Evidence Integrity
- **Status:** **PARTIAL**
- **Defect `BE-003` (High - Sentence Truncation on Float Periods):**
  - `extract_evidence_sentence` (lines 57-86) determines sentence boundaries via:
    ```python
    prev_period = max(text.rfind('.', 0, start), text.rfind('\n', 0, start))
    ```
  - When the text before the date contains a float amount with a decimal point (e.g., `"Your fee of 50.00 is due on November 05, 2026."`), `rfind('.')` selects the period between `50` and `00`.
  - The extracted snippet is truncated to `"00 is due on November 05, 2026"`, destroying the evidence context and corrupting downstream amount extraction.

### 3.7 Obligation Classification (`backend/app/engine/category_rules.py`, `obligation_classifier.py`)
- **Status:** **PASS**
- Successfully maps catalog providers (Netflix, Spotify, Amazon Prime, Airtel, Jio, Tata Power, BESCOM, HDFC ERGO, ICICI Lombard, Tata Play) to verified URLs and categories.
- Extracts Indian Rupee amounts formatted with commas (`₹14,250`, `INR 999`, `Rs. 499`).
- Ambiguous phrases ("near the end of the month", "sometime this month") produce `candidate_date: "UNVERIFIED"`, `verification_status: "unverified"`, and `status: "date_unverified"` with `confidence: 0.40`.

### 3.8 Deadline and Calendar Services (`backend/app/services/deadline_service.py`, `calendar_service.py`)
- **Status:** **PARTIAL**
- **Defect `BE-004` (Medium - Silent Date Fabrication in .ics Generator):**
  - In `calendar_service.py:28`, when `deadline.candidate_date` cannot be parsed (e.g., `"UNVERIFIED"`), the fallback is:
    ```python
    dt = datetime.now(timezone.utc) + timedelta(days=7)
    ```
  - An `.ics` calendar event is silently generated for 7 days in the future with a 1-day advance alarm, directly contradicting the anti-hallucination guarantee.
- **Defect `BE-005` (Medium - Unhandled ValueError in create_reminders):**
  - `DeadlineService.create_reminders` attempts `datetime.strptime(deadline.candidate_date[:10], "%Y-%m-%d")` without verifying whether the date is `"UNVERIFIED"`, crashing with an uncaught `ValueError`.
- **Missing Delivery Mechanism:**
  - Reminder rows are created in `reminders` table with status `'scheduled'`, but no background scheduler or polling worker exists to transition reminders to `'fired'` or dispatch notifications.

### 3.9 FastAPI Routes (`backend/app/main.py`)
- **Status:** **PASS** (with minor vulnerability).
- Implements `/api/health`, `/api/info`, `/api/mcp/tools`, `/api/mcp/log`, `/api/mcp/call`, `/api/demo/reset`, `/api/stats`, `/api/sources/upload`, `/api/agent/chat`, `/api/deadlines`, `/api/deadlines/{id}/ics`.
- **Defect `SEC-001`:** `/api/demo/reset` and DELETE routes lack authorization or confirmation tokens.
- **Defect `SEC-002`:** `upload_source` calls `await file.read()` into memory without content-length validation.

---

## 4. MCP Findings

### 4.1 Protocol Compliance & Transport Behavior
- **Protocol Version Advertised:** `2025-11-25`
- **Transport Endpoints:**
  - `POST /mcp`: Receives JSON-RPC 2.0 payloads (`initialize`, `tools/list`, `tools/call`, `notifications/initialized`).
  - `GET /mcp`: Provides Server-Sent Events (SSE) using `sse-starlette` with anti-buffering headers (`Cache-Control: no-cache, no-transform`, `X-Accel-Buffering: no`) and 15s ping keep-alives.
- **Defect `MCP-001` (Missing Session Management):** The server does not issue or track `Mcp-Session-Id` headers. Every POST request is treated statelessly, and the GET SSE connection is not bound to client session state.
- **Defect `MCP-002` (Decoupled SSE Event Stream):** While GET `/mcp` emits an initial `endpoint` event and periodic `ping` comments, it does not broadcast live tool execution events occurring on `POST /mcp` to connected SSE clients.

### 4.2 Tool Discovery & Schemas
- Discovery endpoint `tools/list` returns all 8 registered tools matching the hackathon brief:
  1. `ingest_source`
  2. `find_deadline_candidates`
  3. `get_deadline_evidence`
  4. `confirm_or_correct_deadline`
  5. `create_follow_up`
  6. `prepare_next_step`
  7. `update_deadline_status`
  8. `list_deadlines`
- Parameter schemas generated via Pydantic match Python handler signatures.
- Argument validation in `validate_tool_arguments()` returns standard `-32602` error for missing required arguments or type mismatches.

### 4.3 Tool Execution & Workflow Integrity
- Sequence `ingest_source` → `find_deadline_candidates` → `get_deadline_evidence` → `confirm_or_correct_deadline` → `create_follow_up` → `prepare_next_step` → `update_deadline_status` → `list_deadlines` was executed end-to-end against an isolated test database and confirmed functional.
- All actions perform real database reads/writes and append entries to `audit_logs`.
- Invalid methods return JSON-RPC `-32601` ("Method not recognized").
- Malformed JSON returns `-32700` ("Parse error").

### 4.4 Real vs. Simulated Tool Calls & Observability
- **Backend Logging:** `MCPClientBridge` logs real outgoing calls, arguments, latencies (<50ms), and results in an in-memory ring buffer exposed via `/api/mcp/log`.
- **Frontend Defect `FE-001`:** In `frontend/src/components/McpActivityCard.jsx:6-28`, when no tool calls exist, the component renders three fake mock tool records with hardcoded latencies (14ms, 22ms, 31ms) and dynamic timestamps. The UI presents these mock rows as live tool execution.

---

## 5. Frontend Integration Findings

### 5.1 Runtime and Build Health
- `npm run lint` (oxlint): 50 warnings, 0 errors.
- `npm run build` (vite build): Succeeded in 1.85s (dist bundle 294 kB JS, 17.7 kB CSS).
- React 19 is functional with modern aesthetic styling, CSS variables, and Lucide icons.

### 5.2 Integration Disconnects & Dead Code
- **Defect `FE-002` (Hardcoded Null Source in Evidence Modal):**
  - In `App.jsx:665-670`:
    ```jsx
    {selectedForEvidenceModal && (
      <EvidenceViewerModal
        deadline={selectedForEvidenceModal}
        source={null}
        onClose={() => setSelectedForEvidenceModal(null)}
      />
    )}
    ```
  - Because `source={null}` is hardcoded, `EvidenceViewerModal.jsx:126` (`{rawText && ...}`) evaluates to false. The full source context and `<mark>` coordinate highlighting are never rendered.
- **Defect `FE-003` (Candidate Dismissal Fails to Update Database):**
  - In `App.jsx:205-207`, `handleDismissCandidate` only filters the React state array `candidateQueue`.
  - The dismissed candidate remains in the SQLite database with `status = 'needs_review'`. Subsequent calls to `fetchDeadlines()` continue to return the dismissed candidate in the main list.
- **Defect `FE-004` (prepare_next_step Tool Never Called by UI):**
  - In `App.jsx:288`, `handlePrepareNextStep` is declared but never passed to any component or invoked.
  - `EvidenceNextStepCard.jsx` displays a static 3-bullet checklist rather than the dynamic 4-step provider checklist returned by `prepare_next_step`.
- **Defect `FE-005` (Orphaned Components):**
  - `DeadlineList.jsx` (487 lines) is imported in `App.jsx:12` but never rendered.
  - `AlexaAssistantPanel.jsx` (230 lines) and `Navbar.jsx` (100 lines) are unreferenced across the codebase.
- **Defect `FE-006` (Mock Data Flash on Load):**
  - In `App.jsx:32` and `SummaryCards.jsx:9-44`, stats default to `{ total_tracked: 14, needs_review: 5, upcoming: 3, completed: 2 }`, momentarily flashing false data before `/api/stats` responds.

---

## 6. End-to-End Scenario Results

### Scenario A — Free-Trial Renewal Cancellation
- **Input:** Netflix free trial notice (`"Your 14-day free trial ends on October 20 2026. Your card will be charged ₹499/month unless cancelled 24 hours prior."`).
- **Expected:** Provider: Netflix, Date: 2026-10-20, Category: Subscription, Obligation: trial_ending, Amount: ₹499.00, Recurrence: monthly, Status: needs_review.
- **Observed:** **PASS.** All parameters extracted accurately. Verbatim quote matched.
- **Limitation:** System extracts the stated end date (2026-10-20) and does not compute the 24-hour advance cut-off date (October 19th). Next-step instructions note this distinction.

### Scenario B — Insurance Premium Renewal
- **Input:** HDFC ERGO policy renewal (`"Policy No: HDFC-98213. Your annual premium of ₹14,250 is due on November 05, 2026 to ensure continuous coverage."`).
- **Expected:** Provider: HDFC ERGO, Date: 2026-11-05, Category: Insurance, Obligation: renewal, Amount: ₹14,250.00, Recurrence: annual.
- **Observed:** **PASS on standard fixture.**
- **Edge-Case Failure (`BE-001`):** If the input states `"due on November 05, 2027"`, the comma halts `ANCHOR_REGEX`, and the extracted date is corrupted to `2026-11-05`.

### Scenario C — Household Bills Management
- **Inputs:**
  1. Broadband: `scenario_c1_broadband.txt` (`"Airtel Broadband bill ... due on 2026-11-15. Amount: ₹1,179"`).
  2. Electricity: `scenario_c2_electricity.txt` (`"Tata Power electricity bill of ₹2,450 ... due on 2026-11-18"`).
  3. Mobile: `scenario_c3_mobile.txt` (`"Jio prepaid plan validity of ₹299 expires on 2026-11-10"`).
- **Expected:** Separate source and deadline records, categories 'broadband', 'utility', 'mobile', correct amounts, chronological sorting.
- **Observed:** **PASS.** Chronological sorting in `PriorityDeadlinesCard` orders Jio (Nov 10) → Airtel (Nov 15) → Tata Power (Nov 18).
- **UI Anomaly:** Clicking "Cancel Subscription" on an electricity bill marks its status as `cancelled` with audit note `"Subscription cancelled by user"`.

### Scenario D — Date Uncertainty Handling
- **Input:** Maintenance fee notice (`"Your annual maintenance fee will be due sometime near the end of the month."`).
- **Expected:** Rejection of date fabrication, `candidate_date: "UNVERIFIED"`, `status: "date_unverified"`, user prompted to confirm exact date, reminders blocked.
- **Observed:** **PASS on extraction, FAIL on calendar export (`BE-004`).** Extraction engine correctly marks date unverified. However, downloading `.ics` silently invents a date 7 days in the future.

---

## 7. Security, Privacy, and Reliability Audit

| Category | Finding | Classification | Risk Level |
|---|---|---|---|
| **API Security** | `/api/demo/reset` and state-changing endpoints lack authentication, CSRF validation, or rate limiting. | Potential Risk (`SEC-001`) | Medium |
| **Input Security** | `/api/sources/upload` reads files into RAM via `await file.read()` without maximum file size limits, risking memory exhaustion. | Potential Risk (`SEC-002`) | Low |
| **Privacy** | Complete raw document text is retained unredacted in `_TOOL_CALL_LOGS` in-memory and exposed via `/api/mcp/log`. | Confirmed Defect (`SEC-003`) | Low |
| **Data Integrity** | Reprocessing an identical source creates duplicate deadline records in SQLite. | Confirmed Defect (`DB-001`) | High |
| **Reliability** | Pytest commands executed from within `backend/` directory fail 4 scenario tests and 1 benchmark due to hardcoded relative paths. | Confirmed Defect (`TEST-001`) | Medium |
| **SQL Injection** | All queries utilize parameterized queries (`?`) with `aiosqlite`. Dynamic columns in `update_deadline` are guarded by Pydantic schema keys. | Verified Secure | None |
| **Path Traversal** | Uploaded files are processed in memory and never written to disk paths. | Verified Secure | None |

---

## 8. Requirements Compliance Matrix

| # | Requirement (from Section 9) | Status | Evidence | Finding ID |
|---|---|---|---|---|
| 1 | Strict ₹0, local-first execution | **PASS** | Local SQLite storage, local regex/dateutil parsing, no cloud API dependencies. | — |
| 2 | React/Vite frontend integration | **PARTIAL** | Builds in 1.85s, but `DeadlineList` and `AlexaAssistantPanel` are orphaned dead code; `source={null}` breaks modal. | `FE-002`, `FE-005` |
| 3 | FastAPI application layer | **PASS** | Complete REST and streaming routing mounted with CORS and Lifespan startup. | — |
| 4 | SQLite persistence and integrity | **PARTIAL** | Foreign keys and indexes enforced; but duplicate deadlines created on repeated ingestion, and candidate dismiss doesn't delete. | `DB-001`, `FE-003` |
| 5 | Text, email, and PDF parsing | **PARTIAL** | Digital PDF & email parsing work; but `text_parser.py` misclassifies SMS and snippets >300 chars as email. | `BE-006` |
| 6 | Deterministic date extraction | **FAIL** | Comma in anchor dates corrupts year (`2027` -> `2026`); single-digit dates (`5/11/2026`) return empty. | `BE-001`, `BE-002` |
| 7 | Verbatim evidence and accurate offsets | **PARTIAL** | Character offsets captured; but decimal periods in amounts truncate evidence snippet; modal passed `source=null`. | `BE-003`, `FE-002` |
| 8 | Explicit handling of ambiguous dates | **PARTIAL** | Extraction sets `"UNVERIFIED"`; but calendar service silently invents date 7 days away. | `BE-004` |
| 9 | All eight expected MCP tools | **PASS** | All 8 tools registered in `server.py` and implemented in `tools.py` with schemas. | — |
| 10 | MCP specification 2025-11-25 or later | **PARTIAL** | Protocol version string matches; lacks `Mcp-Session-Id` session lifecycle management. | `MCP-001` |
| 11 | Streamable HTTP transport | **PARTIAL** | `POST /mcp` and `GET /mcp` (SSE) exist; but SSE stream does not push tool execution events. | `MCP-002` |
| 12 | Genuine MCP tool invocation | **PARTIAL** | Status updates and confirmations route through `/mcp`; but `prepare_next_step` is never called by UI. | `FE-004` |
| 13 | Accurate JSON-RPC errors | **PASS** | Correctly formats `-32700`, `-32600`, `-32601`, `-32602`, `-32603`. | — |
| 14 | Reminder creation and status management | **PARTIAL** | Reminders persisted; but no background scheduler exists to fire them. Cancel button applies subscription text to utilities. | `BE-005` |
| 15 | Valid `.ics` export | **PARTIAL** | Valid RFC 5545 format; but silently invents dates for unverified deadlines. | `BE-004` |
| 16 | Evidence-backed next-step preparation | **PARTIAL** | Tool logic exists; never invoked or displayed by frontend UI. | `FE-004` |
| 17 | Real MCP observability | **FAIL** | Visual inspector displays hardcoded simulated tool calls when log is empty under "MCP activity (live)". | `FE-001` |
| 18 | Synthetic scenarios A–D | **PASS** | All 4 sample fixtures present, preloaded in UI, and passing unit tests. | — |
| 19 | Automated testing and benchmarking | **PARTIAL** | 104 tests pass from root; 5 fail from `backend/` directory due to relative path bugs. | `TEST-001` |
| 20 | Privacy and safe handling of imported documents | **PARTIAL** | Zero cloud leakage; but unredacted raw source text stored in MCP tool log. | `SEC-003` |

---

## 9. Detailed Defect Register

### `BE-001`: Comma Truncation in Anchor Regex Causes Incorrect Year Inference
- **Severity:** Critical
- **Confidence:** Confirmed
- **Component & File:** Date Extraction Engine (`backend/app/engine/date_extractor.py:16`)
- **Description:** `ANCHOR_REGEX` defines target clauses as `[^\n\r,\.;]+`, halting at the first comma. In standard English date strings with commas before the year (e.g., `"due on November 05, 2027"`), the parser receives only `"November 05"` and infers the current year (`2026`).
- **Expected Behavior:** Extract `2027-11-05` as the candidate date.
- **Actual Behavior:** Extracts `2026-11-05`.
- **Steps to Reproduce:**
  ```python
  from app.engine.date_extractor import find_candidate_dates
  find_candidate_dates("Your premium is due on November 05, 2027 to ensure continuous coverage.")
  ```
- **Impact:** Erroneously changes future-year deadlines to the current year, misleading users.
- **Related Requirements:** Req 6, Req 7.

---

### `BE-002`: DATE_PATTERNS Regex Rejects Dates with Single-Digit Day or Month
- **Severity:** High
- **Confidence:** Confirmed
- **Component & File:** Date Extraction Engine (`backend/app/engine/date_extractor.py:33-35`)
- **Description:** Numeric regex patterns enforce strict 2-digit padding (`(?:0[1-9]|[12]\d|3[01])` and `(?:0[1-9]|1[0-2])`). Any date formatted without leading zeroes (e.g. `5/11/2026`, `15/5/2026`, `2026-5-1`) fails matching.
- **Expected Behavior:** Match single- or double-digit day and month (`(?:0?[1-9]|[12]\d|3[01])`).
- **Actual Behavior:** Returns an empty candidate list `[]`.
- **Steps to Reproduce:**
  ```python
  from app.engine.date_extractor import find_candidate_dates
  find_candidate_dates("Due date: 5/11/2026")
  ```
- **Impact:** System fails to detect valid deadlines from bills using unpadded dates.
- **Related Requirements:** Req 5, Req 6.

---

### `BE-003`: Evidence Snippet Boundary Splits on Decimal Points in Currency
- **Severity:** High
- **Confidence:** Confirmed
- **Component & File:** Evidence Sentence Extraction (`backend/app/engine/date_extractor.py:64`)
- **Description:** `extract_evidence_sentence()` searches backward for periods (`text.rfind('.', 0, start)`) to locate sentence starts. When a payment amount contains a decimal point before the date (e.g. `₹50.00 is due on Nov 5`), it splits on the period in `50.00`.
- **Expected Behavior:** Evidence snippet captures the full sentence: `"Your fee of 50.00 is due on November 05, 2026."`
- **Actual Behavior:** Snippet is truncated to `"00 is due on November 05, 2026"`.
- **Steps to Reproduce:**
  ```python
  from app.engine.date_extractor import find_candidate_dates
  find_candidate_dates("Your fee of 50.00 is due on November 05, 2026.")
  ```
- **Impact:** Corrupts evidence attribution and breaks amount extraction from snippets.
- **Related Requirements:** Req 7.

---

### `BE-004`: Silent Date Fabrication in Calendar Service for Unverified Deadlines
- **Severity:** Medium
- **Confidence:** Confirmed
- **Component & File:** Calendar Service (`backend/app/services/calendar_service.py:28`)
- **Description:** When generating an `.ics` file, if `candidate_date` is `"UNVERIFIED"`, the exception handler defaults to `dt = datetime.now(timezone.utc) + timedelta(days=7)`, creating a concrete calendar event 7 days away with a 1-day advance alarm.
- **Expected Behavior:** Raise a `ValueError` or return an HTTP 400 error stating that calendar files cannot be exported for unverified dates.
- **Actual Behavior:** Generates an `.ics` file with an invented start date.
- **Steps to Reproduce:** Request `/api/deadlines/{id}/ics` for an unverified deadline record.
- **Impact:** Violates the zero-hallucination constraint by inventing a calendar date.
- **Related Requirements:** Req 8, Req 15.

---

### `BE-005`: DeadlineService.create_reminders Crashes on "UNVERIFIED" Dates
- **Severity:** Medium
- **Confidence:** Confirmed
- **Component & File:** Deadline Service (`backend/app/services/deadline_service.py:322`)
- **Description:** `DeadlineService.create_reminders()` executes `datetime.strptime(deadline.candidate_date[:10], "%Y-%m-%d")` directly. When invoked on an unverified deadline, it crashes with `ValueError: time data 'UNVERIFIED' does not match format '%Y-%m-%d'`.
- **Expected Behavior:** Explicit validation error explaining that reminders cannot be scheduled for unverified dates.
- **Actual Behavior:** Unhandled `ValueError`.
- **Related Requirements:** Req 8, Req 14.

---

### `BE-006`: Text Parser Boolean Logic Misclassifies SMS and Pasted Content as Email
- **Severity:** Medium
- **Confidence:** Confirmed
- **Component & File:** Text Parser (`backend/app/parsers/text_parser.py:43`)
- **Description:** Expression `"manual" if len(cleaned) < 300 and "sms" not in cleaned.lower() else "email"` evaluates to `"email"` whenever `"sms"` appears in the text, and classifies any text over 300 characters as `"email"`.
- **Expected Behavior:** Accurately classify text containing "SMS" as `"sms"`, and pasted snippets as `"manual"`.
- **Actual Behavior:** Assigns `source_type: "email"`.
- **Related Requirements:** Req 4, Req 5.

---

### `DB-001`: Duplicate Deadlines Created on Repeated Ingestion of Same Source
- **Severity:** High
- **Confidence:** Confirmed
- **Component & File:** Tool Handler (`backend/app/mcp_server/tools.py:75-97`) & `deadline_service.py`
- **Description:** When an already-ingested document is re-uploaded or re-processed, `find_deadline_candidates()` generates new candidate deadline records and calls `DeadlineService.create_deadline()`, inserting duplicate rows into SQLite.
- **Expected Behavior:** Check for existing records matching `(source_id, candidate_date, provider_name)` before inserting, or update existing candidates idempotently.
- **Actual Behavior:** Multiplies deadline entries on every extraction run.
- **Steps to Reproduce:** Run `find_deadline_candidates` twice with the same `source_id`.
- **Impact:** Clutters dashboard and reminders with duplicate tasks.
- **Related Requirements:** Req 4.

---

### `DB-002`: Inconsistent Foreign Key Toggling and Data Loss Risk in Pre-Migration
- **Severity:** Medium
- **Confidence:** Likely
- **Component & File:** Database Schema Initialization (`backend/app/database.py:134-152`)
- **Description:** Migration script executes `PRAGMA foreign_keys = OFF;`, but `SCHEMA_SQL` immediately executes `PRAGMA foreign_keys = ON;`. Furthermore, `INSERT OR IGNORE` during table migration risks silently discarding rows that fail new constraints.
- **Impact:** Potential data corruption or failed migrations during schema updates.
- **Related Requirements:** Req 4.

---

### `FE-001`: McpActivityCard Displays Fabricated/Mock Tool Invocations
- **Severity:** High
- **Confidence:** Confirmed
- **Component & File:** Frontend Visualizer (`frontend/src/components/McpActivityCard.jsx:6-28`)
- **Description:** When no tool logs exist in the backend, `displayLogs` falls back to hardcoded mock records (`ingest_source` 14ms, `find_deadline_candidates` 22ms, `get_deadline_evidence` 31ms) with dynamic timestamps (`new Date().toISOString()`), presented under the card title `"MCP activity (live)"`.
- **Expected Behavior:** Display an empty state message (e.g., *"No tool calls recorded yet. Ingest a document or chat to trigger tools."*).
- **Actual Behavior:** Displays fabricated tool execution metrics.
- **Impact:** Misleads judges into believing static mocks are live MCP tool calls.
- **Related Requirements:** Req 12, Req 17.

---

### `FE-002`: EvidenceViewerModal Passed Hardcoded Null Source
- **Severity:** High
- **Confidence:** Confirmed
- **Component & File:** Frontend Root (`frontend/src/App.jsx:667`)
- **Description:** `App.jsx` renders `<EvidenceViewerModal deadline={selectedForEvidenceModal} source={null} />`. Because `source` is null, `rawText` is empty, disabling the document context box and `<mark>` coordinate highlighting.
- **Expected Behavior:** Fetch the source by `deadline.source_id` and pass `source` object to the modal.
- **Actual Behavior:** Only the isolated snippet is displayed; full document context and character-offset highlighting never render.
- **Impact:** Feature cannot demonstrate source coordinate attribution in the UI.
- **Related Requirements:** Req 2, Req 7.

---

### `FE-003`: Candidate Dismissal Does Not Remove Candidate from Database
- **Severity:** Medium
- **Confidence:** Confirmed
- **Component & File:** Candidate Review (`frontend/src/App.jsx:205-207`)
- **Description:** Clicking "Dismiss" on a candidate review card only removes the item from the in-memory React state `candidateQueue`. The deadline remains in SQLite as `needs_review` and reappears in the Priority Deadlines card.
- **Expected Behavior:** Call backend API or MCP tool to delete or mark the candidate as dismissed in SQLite.
- **Actual Behavior:** Deadline remains persisted and active.
- **Impact:** Dismissed candidates cannot be removed from the active dashboard.
- **Related Requirements:** Req 4, Req 12.

---

### `FE-004`: prepare_next_step MCP Tool Never Invoked by Frontend UI
- **Severity:** Medium
- **Confidence:** Confirmed
- **Component & File:** Next Steps Integration (`frontend/src/App.jsx:288`, `EvidenceNextStepCard.jsx`)
- **Description:** Function `handlePrepareNextStep` in `App.jsx` is declared but never called. `EvidenceNextStepCard.jsx` displays a static 3-bullet list rather than calling the `prepare_next_step` MCP tool.
- **Expected Behavior:** The UI card calls `prepare_next_step` to retrieve provider-specific checklists and verified URLs.
- **Actual Behavior:** Static hardcoded checklist is displayed; tool is bypassed.
- **Related Requirements:** Req 12, Req 16.

---

### `FE-005`: Multiple Orphaned Dead-Code Components in Frontend
- **Severity:** Low
- **Confidence:** Confirmed
- **Component & File:** `frontend/src/components/DeadlineList.jsx`, `AlexaAssistantPanel.jsx`, `Navbar.jsx`
- **Description:** 487-line `DeadlineList.jsx` is imported but never rendered. `AlexaAssistantPanel.jsx` and `Navbar.jsx` are present in the filesystem but completely unreferenced.
- **Expected Behavior:** Unused components should either be integrated into the navigation or removed to maintain clean architecture.
- **Actual Behavior:** Large unused components remain in codebase.
- **Related Requirements:** Req 2.

---

### `FE-006`: Initial Hardcoded Stats State Flashes Mock Values
- **Severity:** Low
- **Confidence:** Confirmed
- **Component & File:** `frontend/src/App.jsx:32`, `SummaryCards.jsx:9-44`
- **Description:** `useState` initializes stats with `{ total_tracked: 14, needs_review: 5, upcoming: 3, completed: 2 }`, causing a brief visual flash of mock metrics prior to the first API response.
- **Expected Behavior:** Initialize with zeroes or loading spinners.
- **Actual Behavior:** Flashes mock numbers on load.
- **Related Requirements:** Req 2.

---

### `MCP-001`: Lack of Mcp-Session-Id Header Handling in Streamable HTTP Transport
- **Severity:** Medium
- **Confidence:** Confirmed
- **Component & File:** MCP Transport Router (`backend/app/mcp_server/transport.py`)
- **Description:** Does not generate or validate `Mcp-Session-Id` headers as specified in the MCP 2025-11-25 Streamable HTTP transport specification.
- **Impact:** Multi-client environments cannot isolate distinct client agent sessions.
- **Related Requirements:** Req 10, Req 11.

---

### `MCP-002`: SSE Stream Does Not Broadcast Live Tool Invocations
- **Severity:** Medium
- **Confidence:** Confirmed
- **Component & File:** MCP Transport Router (`backend/app/mcp_server/transport.py:39-74`)
- **Description:** The `GET /mcp` SSE endpoint only emits connection metadata and periodic ping comments. It does not publish tool call notifications when `POST /mcp` executes tools.
- **Impact:** True push-based streaming observability over SSE is not functional; client relies on REST polling (`/api/mcp/log`).
- **Related Requirements:** Req 11, Req 17.

---

### `TEST-001`: Brittle Relative Paths in Pytest Fixtures
- **Severity:** Medium
- **Confidence:** Confirmed
- **Component & File:** Test Suites (`backend/tests/test_scenarios.py:88`, `test_benchmark.py:22`)
- **Description:** Test files use `Path("backend/sample_data/...")` relative paths. When pytest is executed with CWD `backend/`, the path resolves to `backend/backend/sample_data/...`, causing 5 test errors.
- **Expected Behavior:** Construct paths relative to file location (`Path(__file__).resolve().parent.parent / "sample_data"`).
- **Actual Behavior:** Pytest fails unless run from repository root.
- **Related Requirements:** Req 19.

---

### `SEC-001`: Unprotected State-Reset Endpoint
- **Severity:** Medium
- **Confidence:** Potential
- **Component & File:** FastAPI Routes (`backend/app/main.py:120-125`)
- **Description:** `POST /api/demo/reset` wipes all SQLite tables and clears MCP logs without requiring authentication or confirmation headers.
- **Impact:** Any client on the local network or cross-site request can wipe application data.
- **Related Requirements:** Req 4.

---

### `SEC-002`: Unbounded File Upload Ingestion
- **Severity:** Low
- **Confidence:** Potential
- **Component & File:** Upload Route (`backend/app/main.py:150`)
- **Description:** `await file.read()` loads uploaded files entirely into memory without a size ceiling.
- **Impact:** Oversized file uploads can trigger Out-Of-Memory denial of service.
- **Related Requirements:** Req 5.

---

### `SEC-003`: Unredacted Source Text Stored in Memory and API Logs
- **Severity:** Low
- **Confidence:** Confirmed
- **Component & File:** Observability Bridge (`backend/app/services/mcp_client.py:66`)
- **Description:** Ingested raw text is stored verbatim in `_TOOL_CALL_LOGS` and returned by `/api/mcp/log`.
- **Impact:** Potentially sensitive personal data in emails or bills is stored unredacted in memory and exposed over the inspection API.
- **Related Requirements:** Req 20.

---

## 10. Missing and Untested Functionality

### 10.1 Missing Functionality
1. **Background Reminder Delivery Engine:** While reminders are persisted with `remind_at` dates, no cron job, background task, or notification listener exists to mark them as `fired` or send alerts.
2. **GET /api/sources/{id} Endpoint:** The FastAPI backend has no route to retrieve an ingested source by ID, preventing the frontend from fetching the original text for evidence modal highlighting.
3. **Session-Aware MCP Streamable HTTP Transport:** No session token or `Mcp-Session-Id` header handling exists in `transport.py`.
4. **Candidate Deduplication:** No unique index or duplicate check exists on `deadlines` for `(source_id, candidate_date)`.

### 10.2 Untested Areas Due to Environmental Constraints
1. **Physical Echo / Alexa+ Cloud Skill Integration:** The hackathon brief permits a web-hosted simulated client for developers without direct Amazon Echo Developer beta access. Live voice device streaming was not tested.
2. **Local Ollama Semantic Layer:** Tested deterministic fallback while Ollama was offline. Local semantic LLM pass was verified skipped.
3. **Multi-User Concurrent SQLite Contention:** High-concurrency writes were not load-tested; SQLite write locks under heavy parallel load remain unverified.

---

## 11. Recommended Remediation Order — NO IMPLEMENTATION

> **IMPORTANT:** In strict compliance with the prompt's instructions, no code fixes have been applied. The following is a prioritized remediation roadmap for subsequent implementation phases.

```mermaid
graph TD
    P0_Date[BE-001 / BE-002: Fix Date Regex & Comma Truncation] --> P0_Evid[BE-003: Fix Float Period Sentence Splitting]
    P0_Evid --> P0_Cal[BE-004: Reject Calendar Export for Unverified Dates]
    P0_Cal --> P1_FE[FE-001: Remove Mock Invocations from McpActivityCard]
    P1_FE --> P1_Modal[FE-002: Pass Source to EvidenceViewerModal & Add GET Route]
    P1_Modal --> P1_Prep[FE-004: Wire prepare_next_step MCP Tool into UI Card]
    P1_Prep --> P2_Dedup[DB-001: Deduplicate Deadlines on Ingestion]
    P2_Dedup --> P2_Dismiss[FE-003: Persist Candidate Dismissal to SQLite]
    P2_Dismiss --> P3_Clean[TEST-001 & FE-005: Clean Dead Code & Relative Paths]
```

### P0 — Critical Correctness, Safety & Integrity Issues (Immediate Fixes)
1. **Fix `BE-001` (Comma Truncation in Anchor Regex):** Modify `ANCHOR_REGEX` in `date_extractor.py:16` to permit commas when followed by a 4-digit year (e.g. `(?:,\s*20\d{2})`).
2. **Fix `BE-002` (Single-Digit Day/Month Regex):** Update `DATE_PATTERNS` in `date_extractor.py:33-35` from `(?:0[1-9]|...)` to `(?:0?[1-9]|...)` so single-digit dates (`5/11/2026`) are parsed.
3. **Fix `BE-003` (Float Period Evidence Boundary):** In `date_extractor.py:64`, ensure periods within currency amounts (preceded and followed by digits) are not treated as sentence delimiters.
4. **Fix `BE-004` (Silent Date Fabrication in Calendar Service):** In `calendar_service.py:28`, raise an explicit `ValueError` when `candidate_date == "UNVERIFIED"`, and update the FastAPI endpoint to return HTTP 400.

### P1 — Major Functional & Track-Compliance Issues
5. **Fix `FE-001` (Remove Fake Mock MCP Logs):** Replace hardcoded fallback rows in `McpActivityCard.jsx:6-28` with an authentic empty-state message.
6. **Fix `FE-002` (Connect Source to Evidence Modal):** Add `GET /api/sources/{id}` in `main.py`, fetch source text in `App.jsx`, and pass `source` to `EvidenceViewerModal`.
7. **Fix `FE-004` (Wire `prepare_next_step` into UI):** Call `handlePrepareNextStep` in `EvidenceNextStepCard` to display authentic MCP tool checklist items.
8. **Fix `DB-001` (Deduplicate Deadlines on Ingestion):** Check existing `deadlines` by `source_id` before inserting new candidates in `find_deadline_candidates`.

### P2 — Important Integration & Reliability Issues
9. **Fix `FE-003` (Candidate Dismissal):** Wire "Dismiss" button to delete or set status to `cancelled` in the database.
10. **Fix `BE-005` (Unverified Reminder Creation):** Add an explicit check in `DeadlineService.create_reminders` to reject `"UNVERIFIED"` dates cleanly.
11. **Fix `BE-006` (Text Parser Logic):** Correct the boolean expression in `text_parser.py:43`.
12. **Fix `TEST-001` (Test Path Sensitivity):** Anchor paths in `test_scenarios.py` and `test_benchmark.py` using `Path(__file__).resolve().parent.parent`.

### P3 — Minor Cleanup & Hardening
13. **Fix `FE-005` (Clean Orphaned Components):** Remove or integrate `DeadlineList.jsx`, `AlexaAssistantPanel.jsx`, and `Navbar.jsx`.
14. **Fix `FE-006` (Initial Stats Flash):** Initialize stats with `null` and show skeleton loaders.
15. **Fix `SEC-001` & `SEC-002` (Hardening):** Add upload file-size limit (e.g. 10MB) and require confirmation token for demo reset.

---

## 12. Final Readiness Assessment

| Evaluation Dimension | Readiness Status | Evidence-Supported Summary |
|---|---|---|
| **Frontend UI** | **READY** | Visual design is polished, responsive, and matches hackathon aesthetic guidelines. Clean palette, badges, and layout. |
| **Frontend/Backend Integration** | **PARTIAL** | Core confirmation and status updates route to backend; but evidence modal lacks source text, `prepare_next_step` is orphaned, and candidate dismissal is UI-only. |
| **Backend Correctness** | **UNREADY** | Critical regex defects truncate dates with commas (corrupting years) and fail single-digit dates entirely. |
| **Database Integrity** | **PARTIAL** | ACID compliance and foreign keys enforced; but duplicate deadlines are created on repeated extractions. |
| **Extraction & Evidence Accuracy** | **PARTIAL** | Benchmark achieves 100% on curated dataset; but evidence boundary logic breaks on decimal floats and dates with single digits fail. |
| **MCP Protocol Compliance** | **READY** | Adheres to JSON-RPC 2.0 framing, advertises spec 2025-11-25, and provides standard error codes. |
| **MCP Tool Execution** | **READY** | All 8 tools execute real business logic and persist records to SQLite without mock returns. |
| **End-to-End Scenarios** | **READY (Scripted)** | Scenarios A, B, C, D pass reliably on their specific fixtures, making them demo-safe if scripted. |
| **Security and Privacy** | **PARTIAL** | Safe local execution with zero cloud exposure; lacks endpoint rate/size limits and stores raw text in memory logs. |
| **Zero-Cost Compliance** | **READY (100%)** | Fully local stack (SQLite, Python, Vite); zero paid services or promotional credit dependencies. |
| **Overall Hackathon Demo Readiness** | **CONDITIONALLY READY** | Demo video can be recorded using exact curated scenario fixtures; P0 and P1 remediations are strongly advised before interactive judging. |

---
*Report generated strictly in read-only diagnostic mode. No application code, configuration, or database files were modified during this audit.*
