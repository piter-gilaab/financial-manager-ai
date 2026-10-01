# Phase 9 — Step 29: conversational UX readiness

## Decision

**READY_WITH_PREREQUISITES.** A small, local, session-scoped continuation layer
could safely improve clarification and narrowly scoped follow-ups, but the current
CLI and manager remain stateless and no conversational behavior is implemented.
Step 28 completed the higher-priority presentation work identified in Step 26 and
confirmed that clarification and evidence references are understandable enough to
define a bounded continuation contract. It did not authorize a chat-history system.

The governing flow must remain:

```text
prior structured request/result metadata
    -> bounded conversation state
    -> fresh Step 18 routing decision
    -> fresh deterministic execution
```

Generated explanation text is never financial evidence, routing authority or an
executable instruction. Financial Core, anomaly, registry and manager responses
remain authoritative for their existing responsibilities.

## Current limitation and user value

V1 accepts one bounded-English request at a time. It has no session identity,
history, selected-result state or clarification continuation. A user must replace
pronouns and resubmit all relevant scope, for example changing a clarification
reply into a complete request. This is predictable and safe, but creates observed
friction in Step 25. Step 28 solved the larger output-volume problem and preserved
real evidence references, making bounded follow-up a reasonable next design topic.
The value is moderate: it improves continuity but adds a new sensitive state and
does not expand the supported financial or anomaly capabilities.

## Follow-up scenarios

| Sequence | Safe bounded behavior | Required refusal or clarification |
|---|---|---|
| `Show sales by country.` then `What about only Canada?` | For Financial Analysis only, carry the validated prior dataset/measure/grouping as inspectable metadata, add the explicit supported Canada filter, then route and execute a newly constructed complete request. | Clarify if the prior turn had multiple capabilities/results, Canada is not a valid value, the snapshot changed incompatibly, or `only` could refer to another dimension. Never filter the displayed preview as if it were complete evidence; filtered anomaly follow-ups remain unsupported by automatic routing. |
| `Find unusual Profit values.` then `Why was this one selected?` | With an explicit session-issued reference, re-execute the stored validated request against the same authoritative snapshot, verify its identity/digest, resolve the reference in that fresh structured result, and explain its recorded status, values, peers and fences without conversation-layer recalculation or reclassification. | `this one` alone is ambiguous unless the interface supplied one selected reference. Unknown, omitted, stale, cross-result or changed-snapshot references are rejected or require a new request. CANDIDATE remains statistical screening for investigation—not fraud, error, misconduct, probability or certainty. |
| `Check my financial data.` then `I meant anomaly screening.` | Retain a bounded pending clarification, validate the reply against its allowed field/choices, construct a complete question/request and pass it through fresh Step 18 routing. | A reply that still omits the supported dataset/measure or requests unsupported screening modifiers remains clarification/unsupported. The stored plan is never executed directly. |

Follow-ups requiring forecasts, document retrieval, custom anomaly algorithms or
peers, candidate-only reranking, arbitrary SQL, inferred currency, or new financial
semantics remain blocked or unsupported. An unrelated prior turn, expired session,
ambiguous pronoun, multiple possible result targets, or changed dataset scope must
not be resolved by guessing.

## Minimal state boundary

The first contract should retain at most one active interaction context and use a
versioned, data-only record containing:

- an opaque session identifier plus contract version and deterministic lifecycle
  metadata;
- the previous user request and the latest validated capability/routing-decision
  metadata, never a caller-supplied executable plan;
- approved dataset, measure, grouping, period and supported filters that were
  explicit in the validated request;
- the result snapshot/version or digest needed to detect stale references;
- a bounded map of safe display references to existing structured evidence
  references; and
- one pending clarification field, its allowlisted choices and the original
  request context needed to construct a new complete request.

Do not retain arbitrary result rows, complete JSON responses, generated
explanations, free-form hidden summaries, database objects or tool/function
references. A future UI may keep an explicit selected evidence reference, but the
CLI must not infer selection from what happened to appear in a preview.

## Evidence-reference model

References must point to identifiers already present in authoritative evidence or
to a session-local opaque handle mapped to such an identifier. The mapping binds
the capability, result/step, snapshot digest and reference kind. Resolution must
reject unknown, ambiguous, expired, cross-session and stale references. A handle
is navigation metadata, not a transaction ID, company ID, business identity or
proof that a candidate is erroneous.

The first scope does not retain a prior assessment payload. It re-executes the
stored validated request, requires the authoritative snapshot identity/digest to
match, and resolves the reference in that fresh structured result. If the same
snapshot cannot be reproduced or the reference no longer resolves, the follow-up
fails as stale and asks for a new request. A digest is a guard, not a result store.
The resolver must not parse the earlier human explanation, treat a concise preview
as the full population, calculate a new fence, or silently substitute a current
snapshot for a referenced older result.

## Clarification continuation

A clarification state records only the validated original request, clarification
field, allowed choices where present, and expiry. A reply supplies that missing
field; the continuation layer validates it, builds a complete data-only request,
and calls the existing router again. The fresh decision may still clarify, block or
reject. Replies cannot name a handler, capability implementation, SQL statement or
serialized plan. Explicit cancel/reset, expiry and process exit discard the state.

## Privacy, retention and security

Questions, filters, evidence references and clarification answers can reveal
sensitive financial context. The first scope should therefore be:

- local and in-memory only, isolated per opaque session;
- bounded to one active context with a short, documented inactivity expiry;
- deleted on reset, expiry or process exit, with no recovery promise;
- absent from telemetry and external providers, and not persisted by default;
- protected by maximum lengths/counts and data-only serialization checks; and
- reproducible from a redacted state description, input turn and repository data
  snapshot without relying on wall-clock or hidden model state.

The CLI cannot protect shell history, redirected output or host memory. Any future
server transport would require authentication, authorization, cross-session
isolation, audit/redaction and retention design before it could reuse this model.
Optional persistence is not part of the first scope and would require a separate
privacy/security readiness decision.

Stored capability names and reference labels are untrusted data on read. Every
turn must validate enums and fields against the current registry and request
contracts, recheck capability availability, and use Step 18 to create a new plan.
State must never enable dynamic import, handler lookup, arbitrary SQL, filesystem
access, network access or execution of text from prior users/results.

## Determinism and inspectability

The state contract needs a schema version, deterministic transition rules and an
injectable clock for expiry tests. Each transition should expose the previous
state version, accepted user input, resolved reference/clarification field, fresh
routing response and resulting bounded state. Equivalent state, data snapshot and
input must yield the same routing/execution behavior. Mutable public dictionaries
must remain detached from internal state, following the existing manager boundary.

## Prerequisites before implementation

1. Approve a versioned state schema and the single-active-context size limit.
2. Define opaque session identity, isolation, inactivity expiry, reset and cancel.
3. Approve carry-forward fields and fresh-request construction for supported
   filters/grouping; prohibit inference of dataset, currency or financial meaning.
4. Define reference kinds, snapshot binding, stale-reference behavior and explicit
   selection; require same-snapshot deterministic re-execution and reference
   resolution for the first scope, and do not use preview position as identity.
5. Require fresh Step 18 routing and registry validation on every turn.
6. Define deterministic transition/replay records and controlled public errors.
7. Add scenario tests for ambiguity, expiry, stale/cross-session references,
   clarification continuation, blocked capabilities, exact evidence preservation,
   mutation isolation and network/provider absence.
8. Repeat privacy/security and two-axis code review before enabling the feature.

## Explicit non-goals

This assessment does not implement memory, a REPL/chat UI, persistence, a large
history store, arbitrary natural-language inference, an external LLM, forecasting,
RAG, API/frontend, authentication, new financial contracts, anomaly changes or
cross-user context. It does not make prior explanation text authoritative.

## Recommended next scope

If separately authorized, specify and validate only in-memory continuation for one
pending clarification and one explicit evidence-reference follow-up. Keep the
stateless manager unchanged behind a small session boundary. Defer general filter
inheritance, multi-turn history and persistence until that narrow contract has
privacy, security and deterministic acceptance evidence.
