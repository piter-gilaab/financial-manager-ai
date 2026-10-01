# Phase 11 — conversational CLI validation

## Validation status

**PASS_WITH_LIMITATIONS.** The implemented conversational CLI works as a complete
local user-facing path over the bounded Phase 10 session. The limitations are the
approved scope boundaries, not failed behavior: there is no unrestricted memory,
implicit answer/reference interpretation, persistent session, Forecasting or RAG.

## Validated workflow

Validation exercised the real entry point `python -m src.cli chat` in child
processes:

```text
terminal input
  -> conversational CLI command/text boundary
  -> FinancialManagerSession
  -> FinancialManagerAgent
  -> fresh routing and current registry
  -> existing deterministic capability
  -> Step 27 concise presentation
```

The subprocess coverage includes startup/prompt, `/help`, normal requests,
clarification, anomaly references and follow-up, `/status`, `/cancel`, `/reset`,
`/exit`, EOF and an actual Ctrl+C signal. Deterministic injected clocks cover
inactivity and absolute expiry where waiting four wall-clock hours would be
inappropriate.

## Financial analysis and context

“Show sales by country” routes to `FINANCIAL_ANALYSIS`, executes the existing
Company Financials contract and displays the exact Canada total
`24887654.89`. UNKNOWN denomination remains explicit. Structured evidence is
present under the concise human result; the CLI performs no calculation.

An unrelated Receiver General amount-by-debit/credit request then selects its own
contract without inheriting Company Financials scope. A request following blocked
Forecasting is routed independently and does not reinterpret Sales as cash
receipts.

## Clarification behavior

The top-level capability clarification and canonical financial-record-count
dataset clarification both work through explicit `/answer`. The record-count
continuation returns the authoritative Company Financials count of 700 after fresh
routing.

An invalid answer returns `INVALID_ANSWER`, executes no capability and leaves the
approved clarification pending. Plain text while clarification is pending is
visibly treated as a new request and replaces the old context. `/cancel` clears
the context without financial execution. These CLI scenarios are combined with
the public-session tests that verify activity timestamps do not change after an
invalid answer.

## Anomaly screening and evidence follow-up

“Find unusual Profit values” selects only `ANOMALY_DETECTION`. The output is
PARTIAL because five Profit placeholders remain unresolved, preserves CANDIDATE
and NOT_ASSESSED terminology, explicitly rejects fraud/error certainty and bounds
the 700-item evidence to a first-10 preview with 690 omissions disclosed.

The real process exposes at most ten opaque `ANOMALY_RECORD` handles. A live handle
resolves through `/follow <handle> why_selected` to fresh structured detail with
logical snapshot metadata, semantic result digest, lineage, assessments and fence
references. Existing Phase 10 tests additionally prove deterministic re-execution,
same-snapshot validation and that mutated prior explanation text is ignored.

Modified, unknown, reset, expired and cross-session references fail through the
controlled outcomes. A new process cannot reuse an old handle. No handle becomes
a direct database identifier or query path.

## Lifecycle and bounded state

`/status` displays the approved redacted projection without session ID, handle,
lineage, raw evidence, path, secret, connection or executable state. `/reset`
rotates identity in the authoritative session API, removes evidence context and
prevents old-handle resolution. Repeated interactions retain only one active
context and at most ten handles; no transcript accumulates.

Thirty-minute inactivity expiry, four-hour absolute expiry despite successful
activity every twenty minutes, and expiry while waiting at a clarification prompt
all produce controlled state loss. Stale clarification prompts are removed and
continuation is not silently recreated.

## Blocked capabilities and input safety

Forecasting and Document Retrieval remain BLOCKED and execute no capability.
SQL-shaped, shell-shaped, module/import-shaped, fake tool and fake capability
inputs remain ordinary rejected data. Unknown slash commands are refused by the
closed CLI vocabulary. Child-process audit hooks fail any attempted network,
subprocess, shell or OS-exec boundary; no attempt occurred. No traceback or raw
exception detail was exposed.

## Presentation

Chat reuses the existing concise renderer. Validation confirms bounded item and
reference previews, reconciled omission counts, UNKNOWN currency, visible distinct
warnings, deduplicated-warning presentation, exact decimal strings and the
approved CANDIDATE / NOT_ASSESSED explanations. Full and JSON evidence remain on
the existing one-shot `ask` command rather than becoming chat mode state.

## Privacy, persistence and data integrity

The validation records the repository application-file set and SHA-256 hashes of
all files under `data/` and `notebooks/` before conversational scenarios and
requires exact equality afterward. No source, processed artifact, SQLite database,
notebook or cleaning artifact changed. No session file, chat log, history database
or telemetry artifact appeared.

Conversation state remains local process memory. Terminal/shell software outside
the application may retain input or output; that host behavior is not controlled
or erased by the CLI.

## Remaining limitations

- Plain text is always a new request; continuation requires explicit commands.
- Only the two approved clarification types can be continued.
- Evidence follow-up supports only current session-issued anomaly-record handles.
- There is no arbitrary pronoun/coreference resolution or general chat history.
- Sessions do not persist or cross processes.
- Chat is concise-only; use one-shot `ask --full` or `ask --json` for complete
  alternative presentation.
- Forecasting and Document Retrieval remain blocked; no capability was added.

