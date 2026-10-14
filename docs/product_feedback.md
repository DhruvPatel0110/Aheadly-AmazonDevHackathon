# Product Feedback — Tools & SDKs (Devpost Submission Requirement)

This document satisfies the hackathon submission requirement: *"Product feedback for every tool, API, or SDK used: purpose, what worked, what needs improvement, onboarding experience, and whether we would use it again."*

---

### 1. Model Context Protocol (MCP) Python SDK
- **Purpose:** Expose core application capabilities (`ingest_source`, `find_deadline_candidates`, `get_deadline_evidence`, etc.) as standardized MCP tools accessible over Streamable HTTP for the Alexa+ hackathon track.
- **What Worked:** 
  - Standardized JSON-RPC 2.0 tool definitions and schema generation.
  - Consistent tool registration decorators making tool discovery straightforward.
- **What Needs Improvement:**
  - Clearer documentation and reference starter implementations for Streamable HTTP / SSE transport in standard ASGI (FastAPI) applications.
  - Handling of long-lived connections and heartbeats over HTTP without WebSocket fallback.
- **Onboarding Experience:** Good for basic stdio, moderate learning curve for custom Streamable HTTP endpoints.
- **Would Use Again:** Yes. Standardizing AI agent tools through protocol-level abstractions avoids brittle custom routing.

---

### 2. FastAPI & Uvicorn
- **Purpose:** Serve the REST API, SSE streaming endpoints, and proxy requests between the React frontend and the MCP server.
- **What Worked:** Exceptionally fast, native asynchronous request handling, automatic OpenAPI/Swagger documentation, and clean Pydantic integration.
- **What Needs Improvement:** ASGI streaming responses need careful configuration for immediate chunk flushing across proxies.
- **Onboarding Experience:** Excellent; comprehensive documentation.
- **Would Use Again:** Yes; default choice for modern Python services.

---

### 3. Vite + React
- **Purpose:** Build the simulated Alexa+ demo client, interactive candidate review interface, and live MCP tool-call inspector.
- **What Worked:** Instant HMR, zero-friction build pipeline, clean project structuring.
- **What Needs Improvement:** Default configs need manual proxy adjustments for full SSE streaming without buffering.
- **Onboarding Experience:** Seamless and modern.
- **Would Use Again:** Yes, industry-standard for web demos.
