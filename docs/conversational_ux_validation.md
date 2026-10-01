# Phase 10 — bounded conversational UX

## Implemented surface

`src.manager.FinancialManagerSession` is a local, process-memory wrapper over the
stateless `FinancialManagerAgent`. It has explicit `new_request`, `answer`,
`follow_up`, `cancel`, `reset` and `status` operations. Callers, rather than free
text, choose the operation; the implementation does not infer whether a turn is a
new request, clarification answer or evidence follow-up.

This Phase 10 surface is a Python API only. The existing CLI remains a safe
one-shot interface. Adding a REPL/TUI or implicit chat loop would introduce input,
lifecycle and presentation decisions unnecessary for validating the bounded state
model.

Historical scope note: Phase 11 later approved and implemented those input,
lifecycle and presentation decisions as a thin explicit-command adapter. See the
[conversational CLI contract](conversational_cli_contract.md) and
[Step 35 validation](step35_validation.md). The Phase 10 state model described
here is unchanged.

## Supported behavior

Clarification continuation is restricted to:

- `CAPABILITY_CHOICE`, between Financial Analysis and Anomaly Detection, after the
  exact Step 18 top-level clarification; and
- `FINANCIAL_RECORD_COUNT`, between Receiver General and Company Financials,
  after the exact canonical record-count clarification.

An accepted answer selects a closed application-issued choice, constructs a
canonical complete request and sends it through fresh manager routing and registry
validation. Invalid answers do not execute, mutate state or refresh activity.
`new_request` always replaces the current context; it never answers a pending
clarification implicitly.

Evidence follow-up is restricted to explicit session-issued `ANOMALY_RECORD`
handles for displayed `CANDIDATE` assessments. `why_selected` and `record_detail`
both re-execute the canonical anomaly request and return exact fresh structured
detail. There is no implicit pronoun resolution or Financial Analysis record
reference.

## Lifecycle and outcomes

One session retains at most one active clarification or one anomaly evidence
context. Inactivity expires it after 30 minutes; absolute lifetime expires it
after four hours regardless of activity. `cancel` removes the current interaction,
while `reset` deletes all contextual state and rotates the session identity.

Controlled outcomes distinguish invalid answers, absent contexts, unsupported
follow-ups, unknown references, stale references, expiration and incompatible
state. `status()` exposes version, session/lifecycle timestamps and redacted
context structure/counts. It does not expose evidence handles, lineage, values or
prior request prose.

## Authority and evidence integrity

Conversation state is contextual only. Financial Core, AnomalyService, their
validated database snapshot and each fresh structured result remain authoritative.
Clarification and follow-up execution always traverse `FinancialManagerAgent.ask`,
Step 18 routing and the capability registry.

Evidence handles retain only bounded identity/provenance metadata. Resolution
verifies the issuing session, lifetime, logical snapshot binding, semantic result
digest and exact lineage identifier after deterministic re-execution. It excludes
the physical SQLite byte hash from logical equality, so an equivalent validated
rebuild is accepted while a changed approved artifact is stale. Prior summaries,
previews and explanation text never become factual input.

## Privacy, retention and security validation

The session is local and in memory. It creates no conversation files/database,
uses no telemetry, network or external provider, and holds no database connection,
SQL, callable, module, executable plan, full row/result collection or chat history.
State is a closed frozen schema and holds no more than ten references for the one
current evidence context.

Validation covers capability/tool-name injection, SQL- and shell-shaped answers,
unknown/altered/cross-session references, stale snapshots, malformed stored and
fresh evidence structures, bounded replacement, inactivity/absolute expiry and
reset. User text cannot supply a capability object, contract ID, SQL, function or
lineage ID for execution.

Cash Flow Forecasting and Document Retrieval remain registry-blocked. A later
request such as “Just use sales” is routed independently and cannot reinterpret
sales as receipts or unlock forecasting. Unrelated new requests inherit no prior
dataset, measure, filter or capability.

## Usability result

**PASS_WITH_LIMITATIONS.** Explicit operations and controlled outcomes make the
two Step 29 clarification gaps and anomaly-record inspection usable without
turning state into evidence. Expiry, reset, pending clarification, stale reference
and invalid-reference results are distinct and inspectable.

Limitations are intentional: Python API only; bounded English aliases; two
clarification types; anomaly-candidate references only; one current context; no
implicit “this one”; no general follow-up filters, period refinement, persistent
memory, multi-user service, forecasting or document retrieval.

## Related records

- [Conversation state contract](conversation_state_contract.md)
- [Clarification continuation](clarification_continuation.md)
- [Evidence-reference follow-ups](evidence_reference_followups.md)
- [Step 33 validation](step33_validation.md)
