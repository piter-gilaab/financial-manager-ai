# Phase 10 — Step 31: clarification continuation

## Scope

`FinancialManagerSession` is a local Python in-memory session boundary over the
existing stateless `FinancialManagerAgent`. It does not replace manager routing,
the capability registry, Financial Core or `AnomalyService`.

The public operations are:

- `new_request(question)` — discard prior context and route an independent request;
- `answer(choice)` — resolve only the current allowlisted clarification;
- `cancel()` — delete the current interaction context without execution;
- `reset()` — delete all context and rotate the session identity; and
- `status()` — return detached lifecycle and bounded-context metadata.

The CLI remains unchanged and stateless. There is no persistence, server, REPL,
telemetry, network transport or external-provider session.

## State and lifecycle

The process-local record is a frozen, explicitly typed value containing schema
version `1.0`, an opaque session identifier, UTC creation/last-activity timestamps,
absolute expiry, and at most one active context. Its exact schema and closed
descriptor/clarification pairing are revalidated before reads and replacements.
Public status is a defensive data-only projection and contains no raw request or
result.

The session expires at the earlier of:

- 30 minutes after its last successful state transition; or
- four hours after session creation.

`status()` does not extend either lifetime. Invalid answers, missing pending
clarifications and failed reconstructed executions do not update activity.
Expiry deletes contextual state. `answer`/`cancel` then return a controlled
`SESSION_EXPIRED` outcome. A subsequent explicit `new_request` starts a new local
session record; `reset` always rotates the identity immediately.

The injected clock must return timezone-aware values and must not move backward
between observations. This makes inactivity and absolute deadlines deterministic
even when tests or host-clock behavior are abnormal.

State updates replace the active context. There is no turn list, transcript,
prior explanation, hidden summary or fallback context. Unexpected manager errors
during `answer` leave the prior pending clarification intact rather than exposing
a half-applied transition.

## Closed clarification types

### `CAPABILITY_CHOICE`

This descriptor is created only from the exact Step 18 `capability_required`
clarification and its two current registry choices:

- `FINANCIAL_ANALYSIS`;
- `ANOMALY_DETECTION`.

Finite code-owned display aliases include `financial analysis`, `financial
summary`, `anomaly detection`, `anomaly screening` and `statistical screening`.
The original vague request is not retained or concatenated.

An accepted answer becomes one canonical bounded request:

- Financial Analysis → `Summarize financial data.`
- Anomaly Detection → `Screen financial data for anomalies.`

The session calls `FinancialManagerAgent.ask` with that request. The ordinary
router may require a further target/dataset clarification; the session does not
invent one. Clarification types outside this Step 31 allowlist are returned to the
caller but not retained for continuation.

### `FINANCIAL_RECORD_COUNT`

This descriptor is created only when all of these hold:

- Step 18 selected Financial Analysis normally;
- Step 13 returned the exact `dataset_required` clarification and choices; and
- the transient input matches the small canonical record-count question set.

No raw question is stored. Accepted dataset aliases map only to
`receiver_general` or `company_financials`, then produce either `Receiver General
record count` or `Company Financials record count`. The complete canonical text
goes through fresh Step 18 and Step 13 routing before the Core executes.

Arbitrary measure, grouping, filter, period, screening-target and rephrasing
clarifications remain unsupported. They require `new_request` with a complete
question.

## Outcomes

Session operations return a small envelope with `conversation_version`,
`operation`, `status`, a detached manager `result` when execution/routing occurred,
and a controlled `error` otherwise.

- An invalid choice returns `INVALID_ANSWER`, retains pending state and does not
  execute or extend expiry.
- `answer` without pending state returns `NO_PENDING_CLARIFICATION`.
- Expired `answer`/`cancel` returns `SESSION_EXPIRED`.
- `cancel` returns `CANCELLED`; `reset` returns `RESET`.
- Successful routing/execution preserves the manager's existing status, including
  `CLARIFICATION_REQUIRED`, `SUCCESS` and `CAPABILITY_UNAVAILABLE`.

`new_request` and `answer` are different Python methods. Arbitrary prose is never
used to guess which operation the caller intended.

## Security and privacy boundary

Only application-created clarification objects whose exact code, field and choice
set match the closed contract can become state. Answers are exact strings mapped
by finite local alias tables. They cannot supply a capability implementation,
tool/query name, SQL, shell command, module, function or serialized plan.

Every accepted answer reaches only `manager.ask`, which constructs a fresh Step 18
plan and rechecks registry availability. The session never calls `execute`, a
registry delegate, Financial Core or anomaly code directly. Forecasting and
Document Retrieval remain blocked, and blocked/invalid outcomes create no reusable
context.

Session identifiers must be printable nonempty strings of at most 128 characters;
clocks must return timezone-aware datetimes. Returned state/result values are
defensive copies. Non-string request objects cannot trigger custom string hooks.
Instances do not share global context.

The state retains no question text, financial result, row, explanation, secret,
credential, environment variable, absolute path, database connection or external
provider state. Host process memory, shell history and caller-retained operation
results remain outside this application-state guarantee.

## Unsupported behavior

Step 31 does not provide evidence follow-ups, chat history, general pronoun
resolution, arbitrary clarification completion, preference memory, persistence,
multi-user isolation, CLI conversation, Forecasting or RAG. Step 32 may add only
the separately approved bounded evidence-reference behavior.
