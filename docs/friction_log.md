# Friction Log — Deadline Rescue (Amazon Developer Hackathon)

> **Judging Bonus Opportunity:** Up to 10% bonus for quality friction logs detailing developer experience with required track technologies (MCP SDK, Streamable HTTP, Alexa+ integration).

| Task Attempted | Steps Taken | Expected Result | Actual Result | Severity | Workaround / Mitigation | Actionable Suggestion |
|---|---|---|---|---|---|---|
| Streamable HTTP Transport with MCP Spec 2025-11-25 | Implemented async SSE endpoint and JSON-RPC tool router in Python MCP SDK | Smooth bidirectional streaming of tool call schemas and responses | Client connection timeouts occurred when SSE headers lacked explicit `Cache-Control: no-transform` | Medium | Injected explicit streaming headers and non-buffering chunk generator | Include standard FastAPI/ASGI middleware wrapper for Streamable HTTP in the official Python SDK samples |
| Tool Schema Serialization for Nested Objects | Registered tool `confirm_or_correct_deadline` with Pydantic model params | Automatic JSON schema generator conforming to MCP tool spec | Pydantic v2 `$defs` reference generation was not automatically dereferenced by some MCP client parsers | Low | Flat parameter schemas with explicit type hints and default fields | Provide pre-configured schema flattening helpers in the MCP SDK |

