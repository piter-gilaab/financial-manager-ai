# Phase 7 — Step 20: local CLI

The CLI is a single-command presentation layer over `FinancialManagerAgent`.
It parses command syntax, delegates unchanged questions, and displays results.
Routing, validation, queries, calculations and screening remain in existing
modules. It uses only the standard library and existing project code.

## Run from the repository root

Use the existing environment; no package installation or console-script setup
is required:

```sh
.venv/bin/python -m src.cli capabilities
.venv/bin/python -m src.cli plan "Find outliers in Profit"
.venv/bin/python -m src.cli ask "What were total sales by country?"
.venv/bin/python -m src.cli ask "Discount analysis" --json
.venv/bin/python -m src.cli ask "Screen profit" --json
.venv/bin/python -m src.cli ask "Screen profit" --full
.venv/bin/python -m src.cli ask "Forecast cash flow next month"
.venv/bin/python -m src.cli ask "What does invoice 123 say?"
.venv/bin/python -m src.cli ask "Check my financial data"
.venv/bin/python -m src.cli --help
```

`python -m src.cli` is equivalent when the existing environment is activated.
Quote the entire question as one shell argument. For double-quoted category
values inside a question, use shell single quotes around the whole question.
`--json` and `--full` work before or after the subcommand; they are mutually
exclusive. Each subcommand has `--help`.

| Command | Existing application interface | Behavior |
|---|---|---|
| `capabilities` | `list_capabilities()` | Registry names, availability, reasons and limitations |
| `plan QUESTION` | `plan(question)` | Routing preview only; no capability execution |
| `ask QUESTION` | `ask(question)` | Existing Step 18 orchestration and Step 17 delegation |

Financial Analysis delegates through Step 13 and its approved Core tools.
Screening delegates through Step 14. There is no CLI tool/capability registry,
SQL, direct database access, financial arithmetic or independent question parser.
The Python-only explicit `execute(...)` interface is unchanged.

## Output and application outcomes

Default human output uses labeled status/routing information, explanations and a
deterministic preview of structured evidence. Lists over 10 entries show their
first 10 entries in existing order and disclose returned, total and omitted counts.
Anomaly reference lists are the deliberate exception: they show every reference
named by the first 10 displayed assessments, in existing reference order, so the
displayed fences and peer evidence remain resolvable; omissions are still counted.
Financial amounts, record accounting, exclusions, coverage, UNKNOWN currency and
quality warnings stay visible. Exact duplicate warnings are shown once; distinct
warnings remain. Screening retains previewed values, reference fences, peer
definitions/sizes, lineage and CANDIDATE / NOT_SELECTED / NOT_ASSESSED. CANDIDATE
means a statistical screening candidate for investigation, not fraud or certainty.
Evidence is not recalculated, sorted, reclassified or mutated.

`--full` emits expanded human evidence using the prior representation and can be
large. `--json` remains the complete manager return value without a new wrapper.

Existing decimal strings remain unchanged; any finite Decimal objects serialize as exact
fixed-point strings, never binary floats. Non-data objects and nonfinite values
fail safely using the existing Step 19 data boundary. Human formatting may unwrap
the analysis envelope for display; JSON preserves the entire envelope and digest.
Formatters do not mutate either representation. Terminal controls are escaped
for display; JSON escapes them while retaining their decoded values.

Forecasting and Document Retrieval display BLOCKED and the registry's readiness
reason; neither executes. Ambiguous requests display the structured clarification
without guessing or prompting interactively. Unsupported, partial and no-data
responses retain the manager's status, warnings and explanation.

| Exit code | Meaning |
|---|---|
| `0` | Help or a completed structured application response, including BLOCKED, clarification, NO_DATA, PARTIAL, unsupported and application validation/blocker statuses |
| `2` | Invalid CLI syntax; no manager invocation |
| `1` | Cancellation or unexpected construction, invocation, serialization or output failure |

Automation must inspect the JSON application status to distinguish business
outcomes; exit 0 means a structured response was delivered, not that a query ran.
Invocation/syntax errors use fixed text on stderr (also with `--json`); stdout
contains results only. Raw exception bodies, stack traces and argument contents
are not printed as error diagnostics. Internal Python interfaces retain existing
development exceptions. Ctrl-C during command processing prints only
`Command cancelled.` and returns 1. An OS output failure can interrupt delivery; it cannot
guarantee a complete JSON document.

## Privacy and limits

The CLI adds no provider, network call, credential, telemetry, data write or
dependency. Step 19's controlled errors and local-only provider policy remain
authoritative. Questions/results can themselves be sensitive: protect terminal
output, redirects and shell history/process arguments. This is not a secret
redactor or OS/process security layer.

Language support is the existing bounded English grammar; see
[orchestration](orchestration.md) for exact screening scope and clarification rules.
There is no REPL, history, session memory, paging, UI/server, forecast or retrieval.
Concise mode is a fixed first-10 preview, not pagination or ranking. Expanded human
and JSON modes can be large; JSON preserves all evidence rather than hiding rows.
Advanced structured filters remain available through the Python API. See
[the Step 27 presentation contract](concise_cli_presentation.md).
