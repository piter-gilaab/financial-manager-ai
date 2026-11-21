# V2 Phase 3 — Conversation API

Status: **IMPLEMENTED**.

Routes create, inspect and operate isolated process-local sessions:

- `POST /api/v1/sessions`
- `GET /api/v1/sessions/{session_id}`
- `POST .../turns`, `.../answers`, `.../follow-ups`
- `POST .../reset`, `.../cancel`
- `DELETE /api/v1/sessions/{session_id}`

Session IDs are opaque navigation/correlation identifiers, not authentication.
No transcript or session is persisted; restart loses sessions. Existing
30-minute inactivity and four-hour absolute expiry remain authoritative. Reset
rotates identity and clears evidence/dataset context. Cancel clears active state;
delete removes the process-local entry.

Turns use `ConversationMediator` over `FinancialManagerSession`. Clarification
answers are revalidated by the session. Follow-ups are limited to
`why_selected|record_detail` and session-issued evidence handles. Provider
failure produces deterministic controlled fallback and never changes dataset,
domain or evidence. Tests cover grounded upload-to-conversation flow, isolation,
expiry, reset and cross-session reference rejection.

