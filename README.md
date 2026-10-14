# Deadline Rescue ⏳🛡️

> **Amazon Developer Hackathon (2026)** — Primary Track: **Alexa+**  
> **Core Innovation:** Self-hosted MCP Server (MCP Spec 2025-11-25+ over Streamable HTTP) turning hidden obligations into evidence-backed follow-through tasks.  
> **Budget Rule:** Strict ₹0 out-of-pocket cost. 100% local-first, zero paid cloud services or credit traps.

---

## Overview

People frequently incur late fees, unwanted recurring subscription charges, or lapsed policies because obligations are buried across messages, emails, SMS, and PDF receipts. Standard reminders only work if you already know the exact date and remember to create a task.

**Deadline Rescue** bridges this gap:
1. **Ingests** unstructured sources (emails, bills, receipts, policy notices).
2. **Extracts** candidate obligations with **verbatim evidence quotes** (no hallucinated dates).
3. **Refuses false certainty**: ambiguous dates (e.g. *"sometime near the end of the month"*) are flagged as `date_unverified` and require confirmation.
4. **Follows through**: schedules advance reminders, prepares actionable next steps (official provider links and checklists), and tracks tasks to verified resolution.
5. **Observability**: every action is executed via official **Model Context Protocol (MCP)** tools over Streamable HTTP, with live JSON-RPC inspection in the UI.

---

## System Architecture

```text
React 19 + Vite Demo Client (Simulated Alexa+ Interface)
               │
               ▼
Application Backend / Agent Host (Python + FastAPI)
       │                         │
       │ MCP Client              │ Deterministic Parser & Extraction Engine
       ▼                         ▼
Self-Hosted MCP Server ◄─────────┘
(Streamable HTTP / Spec 2025-11-25)
       │
       ▼
Local SQLite Database (ACID, ₹0 cost)
```

---

## Project Structure

```text
├── backend/
│   ├── app/
│   │   ├── config.py           # Configuration & ₹0 budget settings
│   │   ├── database.py         # Async SQLite connection & migrations
│   │   ├── models.py           # Pydantic & database entity schemas
│   │   ├── parsers/            # Text, email, and PDF parsers
│   │   ├── engine/             # Date extraction & classification rules
│   │   ├── mcp_server/         # Real MCP tools & Streamable HTTP transport
│   │   ├── services/           # Deadline service & .ics calendar generator
│   │   └── main.py             # FastAPI entrypoint & API routes
│   ├── requirements.txt        # Pinned Python dependencies
│   └── run_server.py           # Backend startup runner
├── frontend/
│   ├── src/                    # React + Vite components & visualizer
│   ├── package.json
│   └── vite.config.js          # Dev proxy for API & MCP SSE
├── docs/
│   ├── friction_log.md         # MCP DX friction log (10% judging bonus)
│   └── product_feedback.md     # Devpost tool feedback
├── sample_data/                # Synthetic test documents for scenarios A-D
├── idea.md                     # Hackathon project proposal & brief
└── phases.txt                  # Complete 10-phase roadmap
```

---

## Quick Start (Local Setup)

### Prerequisites
- Python 3.11+
- Node.js 18+

### 1. Backend Setup
```bash
# In project root:
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r backend/requirements.txt
python backend/run_server.py
```
Backend runs at `http://127.0.0.1:8000` (API docs at `/docs`).

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Frontend runs at `http://localhost:5173`.
