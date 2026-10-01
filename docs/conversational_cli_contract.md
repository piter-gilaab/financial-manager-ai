# Phase 11 — Step 34: conversational CLI contract

## Purpose and boundary

The conversational CLI is a local interactive adapter over the existing
`FinancialManagerSession`. It does not add a conversation engine, router,
financial calculation, anomaly rule, evidence resolver or database query.

```text
terminal input
  -> explicit CLI operation selection
  -> FinancialManagerSession
  -> FinancialManagerAgent
  -> current routing, registry and specialized capability
  -> existing CLI presentation
```

Conversation state remains contextual rather than authoritative. Every financial
request and evidence follow-up keeps the Phase 10 fresh-routing and fresh-evidence
rules. The CLI never reconstructs a clarification or resolves an evidence handle
itself.

## Entry point and compatibility

The additive entry point is:

```sh
python -m src.cli chat
```

`capabilities`, `plan`, `ask`, `--json` and `--full` retain their existing syntax
and behavior. Chat has one fixed presentation policy in this first version:
concise human output. `--json` and `--full` are not accepted with `chat`; complete
evidence remains available through the existing one-shot `ask --json` and
`ask --full` commands. The chat does not retain a presentation mode in session
state.

## Input semantics

After startup, the ordinary prompt is:

```text
Financial Manager > 
```

When the public session status reports a supported pending clarification, the
prompt becomes:

```text
Financial Manager [clarification] > 
```

Every nonempty input that does not begin with `/` is an independent operation:

```text
session.new_request(input_text)
```

It is never guessed to be an answer, follow-up, reset or cancellation. If a
clarification is pending, the CLI says that the pending clarification is being
replaced before submitting the new request. This makes the Phase 10 distinction
visible while preserving `new_request` replacement semantics.

An input beginning with `/` is reserved for the closed command vocabulary. An
unknown or malformed slash command produces a controlled usage message without
calling a session operation; it is not submitted as financial text.

Empty or whitespace-only input performs no operation and displays the next
prompt.

## Explicit commands

The complete first-version command set is:

| Command | Session behavior |
|---|---|
| `/help` | Display the bounded command vocabulary and plain-text rule; no session operation. |
| `/status` | Call `session.status()` and display only its safe projection. |
| `/answer <value>` | Call `session.answer(value)` exactly once. |
| `/follow <reference> <intent>` | Call `session.follow_up(reference=..., intent=...)` exactly once. |
| `/cancel` | Call `session.cancel()` exactly once. |
| `/reset` | Call `session.reset()` exactly once. |
| `/exit` | End the process loop without another session operation. |

`/help`, `/status`, `/cancel`, `/reset` and `/exit` accept no arguments.
`/answer` requires a nonempty value; internal spaces are preserved for the
session's existing normalization. `/follow` requires exactly one reference token
and one intent token. The only supported intents are the Phase 10 values
`why_selected` and `record_detail`; the session remains responsible for rejecting
other values.

There are no aliases, command abbreviations, shell escapes or dynamic commands.

## Clarification continuation

When a new request or accepted answer produces a supported pending clarification,
the CLI displays the existing concise manager response, states that clarification
is pending, lists the choices exposed by the redacted public session status, and
shows concrete `/answer` forms. Current supported examples include:

```text
/answer financial analysis
/answer anomaly screening
```

and, for the eligible record-count clarification:

```text
/answer receiver general
/answer company financials
```

The display aliases are guidance only. `FinancialManagerSession.answer` owns
choice normalization, request reconstruction, state retention and fresh routing.
Invalid answers preserve the pending clarification according to Phase 10 and the
CLI displays the controlled error plus available canonical choices.

If the manager returns a clarification that the session does not retain, the CLI
states that `/answer` cannot continue it and asks for a complete new request.
The CLI does not broaden the two approved clarification types.

## Evidence-reference follow-ups

When `session.new_request` returns session-issued anomaly references, the CLI
displays every returned `{handle, kind}` pair in its existing authoritative order
and shows:

```text
/follow <reference> why_selected
/follow <reference> record_detail
```

The reference token is opaque. Display order is not identity, user-supplied
record IDs are not accepted as authority, and the CLI neither queries the
database nor searches prior output. Both commands delegate to
`FinancialManagerSession.follow_up`; the returned single-record structured detail
is rendered with the existing safe exact structured-value renderer.

Starting any new request replaces the evidence context under the Phase 10 rules.
Unknown, changed, cross-session, expired and stale references retain the existing
controlled session outcomes.

## Lifecycle and status

One `FinancialManagerSession` is created when chat starts. It remains process
local and is destroyed naturally when the process exits.

`/status` displays only:

- conversation version and lifecycle status;
- lifecycle timestamps already exposed by the public session projection; and
- the redacted active-context structure, supported scope and reference count.

It omits the opaque session identifier. It never displays Python representations,
absolute paths, connections, secrets, evidence handles, lineage identifiers,
financial values or complete evidence collections. Status inspection does not
extend lifetime.

`/cancel` discards the current active context through the session API and performs
no financial execution. `/reset` rotates session identity and clears context
through the session API; the CLI does not emulate either transition.

The existing lifecycle limits remain exact:

- 30 minutes since the last successful state transition; and
- four hours since session creation.

An expired `/answer`, `/follow` or `/cancel` displays `SESSION_EXPIRED` and tells
the user to enter a complete new request or use `/reset`. The CLI does not retry
the operation, recreate its prior context or claim continuity. A later plain-text
turn is an explicit `new_request`; the session may start a new identity as defined
by Phase 10. `/reset` is the other explicit way to create a fresh session record.

## Presentation and controlled errors

Manager results from `new_request` and successful clarification continuation use
the Step 27 concise human `answer` renderer. Follow-up detail, status metadata,
session errors and reference lists use the existing safe exact structured-value
renderer plus short fixed labels. Terminal control characters are escaped by the
existing presentation boundary before output.

The chat loop contains no arithmetic, evidence transformation, sorting, ranking,
currency inference, routing or status reclassification. It does not mutate a
session result. Unexpected construction, session or output failures end chat with
the existing fixed CLI failure diagnostic and exit code 1; raw exception text and
tracebacks are not printed.

Normal `/exit`, EOF and Ctrl+C end chat cleanly with exit code 0 and a short
`Chat ended.` message. Ctrl+C does not translate into `/cancel` or another state
transition. A process ending during an operation retains no cross-process state.
Invalid slash-command syntax is recoverable inside the loop and does not end the
chat.

## Privacy

Chat is local, offline and process-memory only. It adds no telemetry, persistence,
transcript file, application-managed command history, external provider or
network transport. It does not automatically save conversation input or output.

Questions and financial results remain sensitive. Terminal emulators, shells,
redirects, process inspection, swap or host software may independently retain
input/output; those facilities are outside the application's control. The CLI
does not claim to configure or erase them.

## Supported and unsupported conversation

Supported:

- independent bounded financial-analysis questions;
- independent bounded anomaly-screening questions;
- the two approved clarification continuations;
- session-issued anomaly-record follow-ups with `why_selected` or
  `record_detail`; and
- help, status, cancellation, reset and exit lifecycle operations.

Unsupported:

- unrestricted chat memory or a transcript;
- implicit answer/follow-up detection;
- arbitrary pronoun, coreference or “that one” resolution;
- arbitrary evidence or record identifiers;
- clarification types outside the Phase 10 allowlist;
- persistent or cross-process sessions;
- Forecasting, RAG or blocked-capability bypass;
- arbitrary tools, SQL, shell execution or database access; and
- new natural-language routing rules for chat.

