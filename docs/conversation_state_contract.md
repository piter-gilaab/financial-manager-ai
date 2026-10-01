# Phase 10 — Step 30: conversation state contract

## Purpose and decision

This document defines the smallest conversational state that may later help the
Financial Manager reconstruct a request across user turns. It is a contract and
readiness artifact only: the current CLI and `FinancialManagerAgent` remain
stateless.

The central invariant is:

> Conversation state may help reconstruct a new request. Conversation state is
> never authoritative financial evidence and never grants execution authority.

The first implementation is **READY_WITH_PREREQUISITES** for clarification
continuation. The state boundary, eligible clarification behavior and safety
rules are sufficiently narrow, but the current one-command CLI has no long-lived
process in which in-memory state can survive. Step 31 must first approve either a
local interactive session surface or a Python-only session API and its ownership.
It must not add persistence merely to bridge separate CLI invocations.

## State principles

Conversation state is local, in-memory by default, session-scoped, bounded,
explicitly typed, inspectable in redacted form, resettable, expiring,
deterministic, data-only, non-executable and non-authoritative. It contains no
behavior: transition code and all capability implementations remain outside the
record.

Deterministic means that the same valid state, authoritative snapshot, user turn,
registry and supplied clock produce the same transition and routing result.
Opaque session identifiers need not be deterministic; identifier and clock
factories must be injectable in tests.

The first scope retains one active interaction context, not a transcript. It does
not learn preferences, infer financial meanings or silently inherit scope.

## Proposed minimal V1 schema

The conceptual record below is not a production type or authorization to add one.
Fields not listed are rejected rather than preserved.

```text
ConversationStateV1
  schema_version: "1.0"
  session_id: opaque local identifier
  lifecycle:
    created_at: UTC timestamp
    last_activity_at: UTC timestamp
    expires_at: UTC timestamp
    absolute_expires_at: UTC timestamp
  active_context: null | ActiveContextV1

ActiveContextV1
  routing_context:
    status: validated routing status
    reason_code: validated routing reason
    capability: registered capability identifier | null
    reconstruction_descriptor: ReconstructionDescriptorV1 | null
  supported_scope: SupportedScopeV1 | null
  pending_clarification: PendingClarificationV1 | null
  evidence_references: list[EvidenceReferenceV1]

ReconstructionDescriptorV1 (closed union for Step 31)
  { kind: "CAPABILITY_CHOICE" }
  | { kind: "FINANCIAL_RECORD_COUNT" }

SupportedScopeV1
  dataset: supported dataset identifier | null
  measure: supported source measure | null
  grouping: supported grouping | null
  filters: allowlisted normalized filters
  period: validated explicit period | null

PendingClarificationV1
  source: "STEP_18_ROUTER" | "FINANCIAL_ANALYSIS_AGENT"
  code: allowlisted clarification code
  field: one allowlisted missing field
  choices: non-empty list of allowlisted canonical values
  created_at: UTC timestamp
  expires_at: UTC timestamp

EvidenceReferenceV1
  handle: opaque session-local display handle
  kind: registered reference kind
  capability: registered available capability identifier
  dataset: supported dataset identifier
  authoritative_id: existing structured-evidence identifier
  assessment_mode: "global" | "peer" | null
  source_lineage: existing structured lineage key | null
  snapshot_binding: SnapshotBindingV1
  result_digest: existing or canonically derived structured-result digest | null

SnapshotBindingV1
  approved_run_id: approved run identifier
  dataset: supported dataset identifier
  schema_sha256: digest
  manifest_sha256: digest
  validation_sha256: digest
  flags_sha256: digest
  source_sha256: digest
  processed_sha256: digest
```

### Field decisions

| Field | Required | Authority source | Purpose and validation | Sensitivity and lifetime |
|---|---|---|---|---|
| `schema_version` | yes | conversation contract | Exact supported value; unknown versions fail closed. | Low; session lifetime. |
| `session_id` | yes | session boundary | Locally generated, opaque, unguessable and never accepted as an evidence ID. It keys isolation, not authorization. | Sensitive linkage metadata; session lifetime. |
| lifecycle timestamps | yes | injected local clock | UTC, monotonic transition checks, inactivity and absolute expiry. Failed/spoofed turns do not extend retention. | Low; session lifetime. |
| routing status/reason/capability | yes as applicable | latest fresh Step 18 result | Enum/code allowlists and current registry lookup on every read. Status is context, not permission. | Potentially business-sensitive; active-context lifetime. |
| `reconstruction_descriptor` | optional | canonical fields derived by a code-owned router/adapter from an accepted request | Closed Step 31 union: exactly `{kind: "CAPABILITY_CHOICE"}` or `{kind: "FINANCIAL_RECORD_COUNT"}`, with no extra keys. No raw question, executable plan, provider text or caller-defined key. It can build a candidate but cannot be delegated directly. | Potentially sensitive; active-context lifetime. |
| `supported_scope` | optional | validated specialized request/result metadata | Only dataset, measure, grouping, filters and explicit period already accepted by current contracts. It is omitted when unresolved and must not infer currency, cash semantics or company identity. | Financial context; active-context lifetime. |
| `pending_clarification` | optional; maximum one | current local router or Financial Analysis Agent clarification | Code, field and choices must match the eligible matrix below. Reconstruction uses the enclosing canonical descriptor; free-form/provider choices are rejected. | Potentially sensitive; until answered, cancelled, replaced or expired. |
| `evidence_references` | optional; bounded list | identifiers and lineage already present in structured evidence | Session-local handle maps one explicitly exposed evidence target to an existing structured ID plus capability, request and snapshot binding. Preview position is never identity; Step 32 must set a small hard count before implementation. | Sensitive navigation metadata; replaced with the active context or deleted earlier. |
| `result_digest` | optional | exact structured result, using an approved canonical digest procedure | Integrity guard only. It is not evidence and cannot recover a result. If no approved digest exists, omit it and do not fabricate one. | Sensitive correlation metadata; reference lifetime. |
| `snapshot_binding` | required for each evidence reference | validated Financial Core/AnomalyService result metadata | Exact logical identity described below. Missing binding means the handle is not eligible for follow-up. | Sensitive provenance metadata; reference lifetime. |

Session creation time, last activity and expiry belong in state. A separate boolean
`expired` does not: expiry is derived from the supplied clock and timestamps, and
expired records are deleted. Presentation mode (`concise`, `full` or JSON) also
does not belong in V1 state; it is a per-command display choice and has no role in
request reconstruction.

The reconstruction descriptor and supported scope are not competing authorities.
The former is the smallest code-owned recipe for a candidate request; the latter
is the allowlisted semantic scope confirmed by specialized validation. Neither
bypasses fresh routing or specialized validation.

## Authority hierarchy

1. **Authoritative evidence:** the validated local database snapshot and results
   produced by Financial Core or `AnomalyService`. A validated structured result
   is authoritative only for the execution and snapshot it identifies.
2. **Contextual state:** validated conversation state may identify a prior request,
   supported scope or evidence handle. It can propose a new complete candidate
   request but cannot establish a financial fact.
3. **Non-authoritative text:** generated explanations, summaries, CLI prose and
   user descriptions help humans understand or formulate a request. They are not
   evidence and are never parsed to recover facts.

When a follow-up needs a prior result, it must deterministically re-execute the
validated request against the same logical snapshot and resolve the stored
reference in the fresh structured result. Earlier explanation prose, concise
previews and state digests are never substituted for that result.

## Explicitly prohibited state

The conversation record must not contain:

- complete raw datasets, copied database rows, full result envelopes or full
  anomaly assessment collections;
- SQLite connections, cursors, database objects or mutable service instances;
- generated explanations or summaries represented as evidence;
- arbitrary tool/provider outputs, provider prompts or raw provider instructions;
- arbitrary chat history, hidden free-form summaries or unsupported assumptions;
- secrets, credentials, environment variables, absolute local paths or external
  provider/session state; raw question text is excluded because the application
  cannot reliably detect secrets embedded in free text;
- Python callables, classes, modules, import paths, live handles or custom
  containers;
- SQL, shell commands, executable plans, serialized `RoutingPlan` objects or
  caller-selected handler/capability references; or
- unrestricted filters, algorithms, peer definitions, query names or capability
  names outside the current registries and contracts.

The existing data-only check is a useful lower boundary, not a complete state
validator. State requires its own exact schema, enum, length, count and provenance
validation before every read and write.

## Lifecycle and bounded size

### Creation

A trusted local session boundary creates an empty version-1.0 record with a new
opaque identifier and clock values. Construction performs no query, routing or
provider call. State is never loaded from disk in the first implementation.

### Read and update

Every turn validates the complete state before use. Only a successful,
well-formed transition updates `last_activity_at`. Updates replace the single
active context atomically; they do not append history. Public inspection returns
a defensive, redacted data-only copy.

The first implementation has these hard structural bounds:

- one session record and one active interaction context;
- one canonical reconstruction descriptor, with no retained raw user request;
- one pending clarification for one field;
- no retained answer/transcript list; and
- a bounded evidence-handle list for the one active result context, with the hard
  count deferred to the separately authorized Step 32 contract.

Step 31 stores zero evidence handles. Step 32 must choose the smallest useful hard
count after defining whether one handle identifies a record, one assessment or one
reference; it must not retain hundreds of anomaly rows or derive identity from
preview position.

An implementation must set both a short inactivity window and a finite absolute
lifetime appropriate to its approved session surface. Exact durations remain a
Step 31 decision requiring workflow and privacy rationale; they are not financial
semantics. Neither an invalid answer nor reference spoofing extends either
deadline.

### Expiry, reset, cancellation and deletion

- On inactivity or absolute expiry, delete the active context and session record,
  return a controlled expired-context outcome, and ask the user to restate the
  required context. Do not fall back to a different or current snapshot.
- Reset deletes the whole record and starts a new session identifier only if the
  user continues.
- Cancel deletes the pending clarification and its active context. It performs no
  financial execution and retains no earlier context to fall back to.
- The session surface distinguishes operations explicitly. `answer` accepts only
  a choice/alias; `new request` clears pending context before fresh routing;
  `cancel` and `reset` have the meanings above. In an interactive CLI these may
  be distinct commands; in Python they may be distinct methods. Plain text is not
  guessed to be both an answer and an unrelated request.
- Process exit deletes all in-memory state. Python cannot promise physical memory
  zeroization, so the contract promises loss of application references and no
  recovery, not forensic erasure.

## Clarification contract for Step 31

Step 31 may retain only a clarification emitted by trusted local application code
with one missing field and a non-empty allowlist. The first implementation should
support only this narrow matrix:

| Source/code | Field and accepted canonical values | Reconstruction rule |
|---|---|---|
| Step 18 `capability_required` | `capability`: `FINANCIAL_ANALYSIS`, `ANOMALY_DETECTION` | Store exactly `{kind: "CAPABILITY_CHOICE"}`. Map an exact canonical value or a finite code-owned display alias (including “financial analysis” and “anomaly screening”) to a canonical intent candidate and route it again. The vague raw text is not retained or concatenated. A further measure/dataset clarification is valid and expected. |
| Financial Analysis `dataset_required` | `dataset`: `receiver_general`, `company_financials` | Eligible only when a code-owned parser can reduce the question to exactly `{kind: "FINANCIAL_RECORD_COUNT"}` without preserving free text. Combine that descriptor with the canonical dataset in a fixed template, then send the candidate through Step 18 and Step 13 again. Other dataset clarifications require restatement. |

Clarifications such as free-form period entry, rephrasing, conflicting parameters,
screening modifiers or ambiguous `extreme` direction are not eligible merely
because a clarification object exists. Until a separate deterministic adapter is
specified, they require a complete restatement and do not create continuation
state.

An accepted `answer` response is normalized only by a code-owned finite alias
table (for example whitespace/case normalization); state cannot add aliases. It
produces a candidate request, never a handler call. An invalid `answer` returns
the allowed choices without execution, mutation or expiry extension. A distinct
`new request` operation clears the pending interaction before routing its text;
there is no natural-language classifier deciding whether an invalid answer was an
unrelated request. Expiry and cancel behave as above.

“Complete candidate request” means a self-contained input to normal routing. It
does not promise execution: fresh routing or specialized validation may safely
return another clarification, `UNSUPPORTED`, `BLOCKED` or an ordinary validation
outcome. Thus choosing “anomaly screening” after “Check my financial data” may
correctly lead to a new request for the screening target; the choice alone cannot
invent Sales, Profit or accounting amount.

## Follow-up contract for Step 32

Step 32 is not authorized by this document. A future implementation may construct
a candidate from the latest validated scope only for these classes:

- add or replace one supported, explicit filter value for the same dataset;
- refine an explicit period using the existing period contract;
- reuse an already validated dataset, supported measure or grouping;
- resolve an explicitly selected evidence handle; or
- ask for explanation of an assessment already present in a freshly reproduced
  structured result.

Every candidate must be rendered through a deterministic, code-owned adapter and
pass fresh Step 18 routing, registry availability checks and specialized request
validation. A Canada refinement, for example, may reuse Company Financials,
Sales and country grouping only when those values came from the prior validated
request/result; Canada must be validated as a supported country filter. The layer
must query anew, not filter the concise preview.

Unsafe or ambiguous follow-ups require a full request or clarification: pronouns
without exactly one selected handle; a previous multi-capability result; a switch
of dataset or financial meaning; inferred currency; dependent calculations;
filtered/custom anomaly behavior; unsupported grouping/measure/filter; or any
reference whose session, request, capability, snapshot or identifier does not
match. No prior unsupported assumption may be carried forward.

## Evidence references

A safe handle is navigation metadata scoped to one session and result context. It
maps to identifiers already emitted by authoritative structured evidence, such as
an anomaly item's lineage `record_id` and its `global` or `peer` `reference_id`.
The handle itself may be opaque, but it must not invent a transaction, company,
document or business identity. Display order, phrases such as “this one”, and a
CLI preview index are not identifiers.

Resolution performs all of the following or returns a controlled stale/unknown
reference outcome without execution based on old evidence:

1. validate the state schema, current session and handle membership;
2. validate the capability against the current registry and availability;
3. reconstruct and freshly route the stored validated request;
4. re-execute through `FinancialManagerAgent` and the existing capability;
5. require the same logical snapshot binding;
6. find the exact lineage/reference identifier in the new structured result; and
7. derive any explanation solely from that fresh structured evidence.

Unknown, invented, ambiguous, expired, cross-session, cross-result and
changed-snapshot references are rejected. A digest is only an integrity/staleness
guard; it is not the result and cannot make explanation text authoritative.

## Snapshot semantics

For this architecture, “same authoritative snapshot” means the same approved run,
dataset and logical artifact identity after the existing complete snapshot
validation. The binding uses:

- approved `run_id` and dataset;
- `schema_sha256`;
- `manifest_sha256`, `validation_sha256` and `flags_sha256`; and
- dataset `source_sha256` and `processed_sha256`.

These fields already arise from the approved bundle/database validation and
structured result metadata. An evidence handle may be issued only when the
required run/dataset identity is available from the authoritative result (for
example result metadata or consistent source lineage).

`database_sha256` is retained in current results as useful exact-instance audit
metadata but is deliberately not part of logical snapshot equality. Step 24
proved that a clean, valid reconstruction can have different SQLite bytes because
`ingested_at` records build time. Requiring byte equality would reintroduce that
reproducibility defect. Conversely, matching logical digests without passing the
existing schema, approved-bundle and full database validation is insufficient.

If any logical identity field is missing or differs, the old reference is stale.
The system must not silently resolve it against rebuilt, newer or different data.

## Routing and capability boundary

The only permitted execution flow is:

```text
new user turn
  -> validate bounded conversation state
  -> construct a complete data-only candidate request
  -> fresh Step 18 routing
  -> current registry availability validation
  -> FinancialManagerAgent public facade
  -> existing specialized capability and its validation
```

The prohibited flow is `state -> stored plan/handler/tool/function execution`.
Even state written by trusted code is untrusted on its next read. A stored
capability name is contextual data; only the current closed registry can select
an implementation.

Current availability does not change:

- Financial Analysis — **AVAILABLE**;
- Anomaly Detection — **AVAILABLE**;
- Cash Flow Forecasting — **BLOCKED**; and
- Document Retrieval — **BLOCKED**.

Blocked, unsupported and invalid results create no reusable execution scope and
clear any previous active continuation context. After “Forecast cash flow,” a
later “Just use the sales data” is routed as a standalone request. State must not
reinterpret Sales as cash receipts, supply missing currency/cash semantics or
unlock a forecasting handler. The same rule prevents conversation from creating
a document corpus or RAG capability.

## Security threat review

| Threat | Required control |
|---|---|
| Stale context | Inactivity and absolute expiry; one replaceable context; snapshot-bound references; no fallback to newer data. |
| Context confusion | Only the explicit `answer` operation and an exact eligible choice continue clarification. A distinct `new request` operation discards pending state first; invalid answers retain it. Ambiguous pronouns clarify. |
| Cross-session leakage | Opaque session-local handles, exact session membership checks, no global mutable context and deletion/identifier rotation on reset. |
| State poisoning | Exact schema and plain-container validation; code-owned enum/alias tables; no executable strings, provider instructions, plans or dynamic lookup. |
| Reference spoofing | Accept only handles issued in the current context and re-resolve authoritative IDs after same-snapshot execution. |
| Capability bypass | Fresh Step 18 routing plus current registry and specialized validation on every execution; state never delegates. |
| Unbounded growth | One active context, one canonical descriptor, one clarification, a small hard handle cap before Step 32, length limits and no transcript/result storage. |
| Sensitive-data retention | Metadata and references instead of values/rows, short expiry, no persistence/telemetry/network, explicit reset and process-exit deletion. |
| Mutation/replay confusion | Defensive copies, state version check, atomic replacement and an injected clock; equivalent accepted inputs produce inspectable transitions. |

This is not a sandbox or server security framework. Any future API/server requires
authentication, authorization, tenant isolation, audit/redaction and a new
retention review before reusing the contract.

## Privacy and retention

The first implementation is local, in-memory, single-session and offline. It has
no persistence, telemetry, network synchronization or external provider state.
Actual financial values are unnecessary and therefore prohibited from state;
retain the smallest validated request metadata and opaque evidence navigation
needed for the active interaction.

Filters, dataset/measure choices and lineage/reference keys can still reveal
financial context. The state schema never harvests credentials, environment
variables or arbitrary free text, and callers must not supply secrets as financial
filter values; content-level secret detection is not claimed. Redacted inspection
should expose structure, version, expiry and counts while masking filter values
and opaque handles unless the local user explicitly requests full diagnostic
output. The application cannot protect shell history, redirected CLI output,
swap, process dumps or host memory; those remain host-operational boundaries.

## Versioning and transitions

`schema_version: "1.0"` is required. Unknown or missing versions are rejected and
deleted after a controlled incompatible-state outcome; they are never interpreted
as the current schema. No migration, downgrade or persistence infrastructure is
part of Step 30 or the first implementation.

Each internal transition should be inspectable in tests as data containing the
prior schema version, transition kind, accepted field/choice or reference kind,
fresh routing status and resulting state shape. It must exclude financial values,
free-form explanation text, secrets and executable objects. This is an ephemeral
diagnostic return, not retained history or telemetry.

## Implementation prerequisites and acceptance conditions

Before Step 31 writes production code:

1. approve the owner and user surface for a long-lived local session: either a
   local interactive CLI process or a Python-only session API; separate one-shot
   CLI processes cannot share in-memory state;
2. make `answer`, `new request`, `cancel` and `reset` distinct operations so an
   invalid answer is never guessed to be an unrelated request;
3. set documented short inactivity and finite absolute-retention durations for
   that surface and require an injectable clock.

Step 31 implementation and acceptance must then:

1. implement only the two closed descriptor/clarification adapters above, with no
   generic text concatenation or direct execution;
2. define controlled outcomes for expired, cancelled, invalid-choice and
   incompatible-version cases using the existing presentation conventions; and
3. add behavior tests for isolation, replacement, expiry, mutation resistance,
   fresh routing, blocked capabilities, provider/network absence and the example
   that requires a second clarification rather than an invented measure.

Evidence-handle issuance and canonical result digests are prerequisites for Step
32, not Step 31, and must not be pulled forward.

## Non-goals

Step 30 does not implement conversation state, continuation, evidence follow-ups,
persistent memory, a session database, a transcript store, external LLM/provider
integration, an API/frontend, authentication, forecasting, RAG, new Financial
Core contracts, changed anomaly algorithms or a general-purpose chat framework.
It does not change presentation behavior or make explanations authoritative.
