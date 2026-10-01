# Phase 10 — Step 30 validation

## Scope and repository evidence

Step 30 is a documentation-only contract/readiness change. The review reconstructed
the implemented system from `AGENTS.md`, `CONTEXT.md`, `README.md`, the central
technical guide, Steps 18, 19, 24, 27 and 29 documentation/validation, CLI and user
evaluation documents, the current manager/agent/anomaly/Financial Core/CLI source,
relevant tests, and the working-tree status/diff.

Repository evidence confirmed:

- `FinancialManagerAgent` is the single facade and remains stateless;
- Step 18 creates routing plans locally and executes only through the public
  manager facade and closed capability registry;
- Financial Core and `AnomalyService` own deterministic query/calculation results;
- structured delegated evidence is preserved while explanation and concise
  presentation are convenience views;
- snapshot validation exposes logical approved-artifact digests as well as the
  physical database digest;
- Step 24 intentionally permits logically identical rebuilt databases with
  different bytes caused by build timestamps;
- the CLI performs one command per process and therefore cannot retain an
  in-memory session across separate invocations; and
- Financial Analysis and Anomaly Detection are AVAILABLE, while Cash Flow
  Forecasting and Document Retrieval are BLOCKED.

The pre-change validated baseline supplied for this step is **316 passed, 0
failed, 0 errors, 0 skipped**.

## Readiness result

**READY_WITH_PREREQUISITES.** The bounded schema, authority hierarchy, lifecycle,
eligible clarification matrix, routing boundary and privacy/security controls are
defined sufficiently to constrain Step 31. Production implementation must not
begin until the owner/surface of the long-lived local in-memory session is chosen:
an interactive local CLI process or a Python-only session API. Persistence is not
an acceptable implicit solution for the current one-shot CLI.

Step 31 is also limited to Step 18 `capability_required` and Financial Analysis
`dataset_required`, both with code-owned choices and reconstruction adapters. A
capability answer may safely produce another clarification; it must not invent a
dataset or measure to force execution.

## Contract findings

- State contains one versioned, local, expiring interaction context, one canonical
  reconstruction descriptor, at most one eligible clarification, no raw question
  and no transcript.
- Step 31 retains no evidence handles. A future Step 32 must choose a small hard
  limit after defining record/assessment/reference handle semantics; handles must
  bind to existing structured IDs and a logical snapshot, never full results or
  assessment collections.
- Financial values, rows, generated explanations, arbitrary outputs, secrets,
  paths, SQL, plans, callables, modules and provider state are prohibited.
- The authoritative hierarchy is database/Financial Core/AnomalyService validated
  structured results, then contextual validated state, then non-authoritative
  human explanation text.
- Every continued request undergoes fresh Step 18 routing, current registry
  availability checking and specialized validation. State never invokes a tool.
- Expiry, reset, cancellation, process exit and unrelated replacement remove the
  active context. Expired state asks for restatement and never falls forward to a
  different snapshot.

## Snapshot and evidence review

Logical snapshot equality is the approved run and dataset plus schema, manifest,
validation, flags, source and processed digests, after existing full database
validation. `database_sha256` remains exact-instance audit metadata but is not the
logical equality key, avoiding the old timestamp-dependent byte-hash defect.

A future evidence follow-up must re-execute the validated request on that same
logical snapshot and resolve an existing structured lineage/reference identifier.
Unknown, stale, cross-session and spoofed identifiers fail closed. Explanation
text and concise preview positions never become evidence.

## Domain-modeling result

Scenario analysis tested vague capability choice, dataset clarification, a Canada
filter refinement, stale anomaly references and a blocked forecast followed by a
Sales request. The contract preserves the glossary's distinctions among financial
facts, cash movement, sales observations, anomaly candidates and documentary
evidence.

Conversation state, session handle and snapshot binding are application contract
terms rather than new financial-domain concepts. In accordance with the glossary
rules and the Step 29 conclusion, `CONTEXT.md` was not changed. The contract is
reversible documentation and does not justify a new ADR.

## Architecture, privacy and security review

The focused two-axis review is recorded after drafting the contract. It checks the
working-tree documentation change against repository standards and the Step 30
specification, with special attention to routing bypass, mutable evidence,
explanation authority, cross-session leakage, blocked-capability bypass, stale
references and unnecessary retention.

### Standards

The initial review found one hard minimum-retention inconsistency: the request was
duplicated in active and pending state. It also questioned unsupported exact TTL
and evidence-handle limits. A follow-up found that the reconstruction descriptor
was not yet a closed type. The contract now retains no raw question, uses one
two-variant descriptor union with no extra keys, and leaves exact retention/Step
32 handle counts to their evidence-bearing scopes. The final Standards review
reported **zero remaining findings** and no applicable production-code smell.

### Spec

The initial review found three specification gaps: invalid answers could not be
distinguished deterministically from unrelated requests, raw question retention
could capture embedded secrets, and that text was duplicated. A follow-up also
required the reconstruction descriptor's exact variants and clearer separation of
pre-implementation decisions from Step 31 acceptance work. The contract now uses
distinct `answer`/`new request`/`cancel`/`reset` operations, excludes raw free text,
defines exactly `CAPABILITY_CHOICE` and `FINANCIAL_RECORD_COUNT`, and separates
prerequisites from acceptance conditions. The final Spec review reported **zero
remaining findings**, no scope creep and no Step 31–33 implementation.

## Validation

No production or test code changed, so no conceptual tests or full regression were
added. Final validation checks required-document existence, internal links,
terminology and capability statuses, plus `git diff --check`. The 316-test baseline
is not claimed as rerun unless a later validation entry explicitly records it.

## Files created or modified

- `README.md`
- `docs/conversation_state_contract.md` (created)
- `docs/step30_validation.md` (created)

Pre-existing unrelated untracked files and data remain untouched.

## Unresolved questions and prerequisites

1. Will Step 31 own an interactive local CLI session or expose a Python-only
   session API first?
2. How will that surface expose distinct answer/new-request/cancel/reset
   operations without guessing user intent from nonmatching text?
3. What short inactivity and finite absolute-retention durations are appropriate
   for that selected surface?
4. What exact controlled status/code names should the implementation use for
   expiry, cancellation, invalid choice and incompatible state version?

These choices do not authorize persistence, Step 32 evidence-reference handling
or broader clarification adapters.

## Scope confirmation

Steps 31–33 were not implemented. No conversation state, clarification
continuation, evidence-reference follow-up, persistence, capability, dependency,
database, provider, Financial Core, anomaly, production source or test changed.
