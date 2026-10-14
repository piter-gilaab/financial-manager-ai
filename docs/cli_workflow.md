# Local CLI workflow

The CLI retains the Phase 7 single-command presentation layer over
`FinancialManagerAgent` and adds the Phase 11 bounded interactive adapter over
`FinancialManagerSession`. It parses command syntax, delegates requests, and
displays results.
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
.venv/bin/python -m src.cli chat
.venv/bin/python -m src.cli dataset add company.csv
.venv/bin/python -m src.cli dataset status ds_...
.venv/bin/python -m src.cli dataset profile ds_...
.venv/bin/python -m src.cli dataset mappings ds_...
.venv/bin/python -m src.cli dataset capabilities ds_...
.venv/bin/python -m src.cli --help
```

`python -m src.cli` is equivalent when the existing environment is activated.
Quote the entire question as one shell argument. For double-quoted category
values inside a question, use shell single quotes around the whole question.
For `capabilities`, `plan` and `ask`, `--json` and `--full` work before or after
the subcommand and are mutually exclusive. Chat rejects both presentation flags.
Each subcommand has `--help`.

| Command | Existing application interface | Behavior |
|---|---|---|
| `capabilities` | `list_capabilities()` | Registry names, availability, reasons and limitations |
| `plan QUESTION` | `plan(question)` | Routing preview only; no capability execution |
| `ask QUESTION` | `ask(question)` | Existing Step 18 orchestration and Step 17 delegation |
| `chat` | `FinancialManagerSession` | Bounded process-local interactive session |
| `dataset ...` | `OnboardingManager` | Local source preservation, profiling, semantic decisions, registry and readiness |

Financial Analysis delegates through Step 13 and its approved Core tools.
Screening delegates through Step 14. There is no CLI tool/capability registry,
SQL, direct database access, financial arithmetic or independent question parser.
The Python-only explicit `execute(...)` interface is unchanged. Chat contains no
second router: plain text calls `new_request`, while slash commands select an
explicit session operation.

## Interactive chat

Chat uses concise human presentation only; `--json` and `--full` are rejected
with `chat`. Complete expanded or structured evidence remains available through
the one-shot `ask --full` and `ask --json` commands.

```text
Financial Manager > Check my financial data.
Clarification pending. Use one of:
/answer financial analysis
/answer anomaly screening
Financial Manager [clarification] > /answer anomaly screening
```

Supported commands are `/help`, `/status`, `/answer <value>`,
`/follow <reference> <why_selected|record_detail>`, `/cancel`, `/reset` and
`/exit`. Any non-command text is a new request, even while clarification is
pending; the CLI announces that replacement. Unknown slash commands do not
become financial requests. Evidence follow-ups accept only references issued by
the current session and delegate resolution entirely to the session API.

`/status` omits session identity and exposes only the public redacted lifecycle
and context projection. Inactivity expires after 30 minutes and absolute lifetime
after four hours. Expired continuation operations are not retried; enter a new
request or use `/reset`. Empty input is ignored. `/exit`, Ctrl+D/EOF and Ctrl+C
end chat cleanly without a traceback.

### Optional LLM mediation (Phase 12)

```sh
python -m src.cli chat --llm-model qwen2.5:7b-instruct \
  --llm-url http://127.0.0.1:11434/v1/chat/completions --llm-timeout 30
```

`--llm-model` enables mediation. `--llm-url` defaults to
`http://127.0.0.1:11434/v1/chat/completions` and must be loopback (`localhost`,
`127.0.0.0/8` or `::1`). `--llm-timeout` defaults to 30 seconds, with a maximum
of 120. Any other host, embedded credentials or an invalid timeout end with a
fixed exit-2 message that does not echo the URL. The same local-only options are
also accepted by `dataset add` for optional semantic suggestions. Without
`--llm-model`, chat is exactly the Phase 11 workflow above and onboarding uses
deterministic aliases plus manual decisions.

With mediation, plain text is interpreted by the local model. It may start an
approved request, answer the pending clarification with a canonical choice, or
follow up an issued `A1`–`A10` label. Slash commands keep their deterministic
meaning and are never sent to the model. When the model is unavailable or its
proposal or prose fails validation, the turn shows a one-line notice and the
standard Phase 11 output.

```text
Financial Manager > Como estão as vendas por país?
Os Estados Unidos apresentam o maior valor de vendas na base, com 25,03 milhões, …

País                      Vendas (total)  Registros
---------------------------------------------------
United States of America   25.029.830,18        140
Canada                     24.887.654,89        140
…
Notas:
- Moeda: UNKNOWN. A denominação da fonte não está estabelecida; …
Pedido interpretado: “Total sales by country”. Evidência completa: python -m src.cli ask "Total sales by country" --full
```

See the [LLM mediation contract](llm_mediation_contract.md).

## Dataset onboarding (Phase 13)

```sh
python -m src.cli dataset add company.csv [--sheet SHEET]
python -m src.cli dataset status ds_...
python -m src.cli dataset profile ds_...
python -m src.cli dataset mappings ds_...
python -m src.cli dataset confirm-domain ds_... SALES_RECORD --evidence "Data owner confirmation"
python -m src.cli dataset confirm ds_... Sales SALES --evidence "Data owner confirmation"
python -m src.cli dataset reject ds_... Sales --evidence "Incorrect suggestion"
python -m src.cli dataset capabilities ds_...
```

`dataset add` accepts only bounded local CSV (UTF-8/UTF-8-SIG) and constrained
XLSX. Multiple nonempty sheets require `--sheet`; formulas, macros, external
links, malformed/oversized inputs, symlinks and unsupported formats are rejected.
The original is never changed. Accepted bytes and typed versioned artifacts are
written under the Git-ignored local onboarding root.

`confirm` approves the proposed role when it matches or records a correction
when another allowlisted role is supplied. Critical source-value meanings use a
JSON `--value-map`, for example `'{"D":"DEBIT","C":"CREDIT"}'`. Currency
codes require explicit ISO evidence; symbols do not establish denomination.
Ambiguous date roles additionally require `--date-format DD/MM/YYYY` or
`--date-format MM/DD/YYYY`; no locale convention is guessed.
Every decision requires `--evidence`, creates a new mapping version, and can be
revised. `--json` is available on every dataset leaf command.

Capability output distinguishes semantic eligibility from actual execution.
For an eligible `SALES_RECORD`, Step 59 reports Financial Analysis as
`AVAILABLE_WITH_LIMITATIONS` and lists explicit states and controlled reasons for
the fixed nine-operation catalog. Each operation passes the existing binder and
adapter readiness probe independently, subject to the global approved-domain
anchors. Optional COUNTRY, SEGMENT, PRODUCT, PROFIT, DISCOUNT and UNITS_SOLD
semantics affect only their corresponding operations. Canonical domain and
approved currency state remain visible.

Phase 16 capability output also reports the two closed dynamic anomaly
operations independently in human and JSON output. At least one executable
operation produces `Anomaly Detection: AVAILABLE_WITH_LIMITATIONS`; it never
claims full anomaly coverage. Capability discovery does not run classifications
or expose candidates. Forecasting and Document Retrieval retain their blockers.

There is no `dataset analyze` or anomaly execution CLI. Explicit execution uses
the typed Python methods `FinancialManagerAgent.execute_dataset_request` for
Financial Analysis and `execute_dataset_anomaly_request` for the Phase 16 closed
anomaly catalog. At the Phase 16 boundary, natural-language and fuzzy dataset
selection were unavailable; the following Phase 17 addendum supersedes only the
natural-language statement.

Phase 17 Steps 66–67 change only mediated `chat`: a user may say `Use dataset
ds_…` and then request one of the nine fixed dynamic Financial Analysis
operations, or include the exact ID in the analysis turn. The ID must be a
current eligible catalog entry; filenames, paths, recency and fuzzy matching are
not accepted. `/status` shows only the opaque selected ID and last closed dynamic
operation. `/cancel`, `/reset` and expiry clear them.

Dynamic chat reuses `execute_dataset_request`; it adds no `dataset analyze`
subcommand. `MONTH|YEAR` and `BUCKET|EXCLUDE` are the only optional parameters.
Ambiguous datasets and unsupported follow-ups ask for clarification. At the
Steps 66–67 checkpoint, dynamic anomaly requests were deferred and executed
nothing; the Steps 68–69 behavior below supersedes that historical boundary.

Steps 68–69 supersede that final deferral: mediated `chat` may request only the
existing GLOBAL Sales or Profit anomaly screen. Candidate results use A1–A10 in
natural conversation and the existing opaque `/follow` command remains valid.
The feature adds no `dataset analyze` or anomaly execution subcommand. Readiness,
Tukey-IQR computation, candidate classification and fresh evidence resolution
remain in the existing deterministic Manager/adapter path.

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
development exceptions. For one-shot commands, Ctrl-C prints only
`Command cancelled.` and returns 1. In chat, Ctrl-C ends the process-local session
cleanly with exit code 0. An OS output failure can interrupt delivery; it cannot
guarantee a complete JSON document.

## Privacy and limits

The analysis/chat CLI adds no data write. Dataset onboarding deliberately writes
exact source bytes and typed manifests to its configured local, Git-ignored root;
it adds no telemetry, credential, external provider or dependency. Optional
semantic assistance remains loopback-only. Step 19's controlled errors and
local-only provider policy remain authoritative. Questions/results and onboarded
datasets can themselves be sensitive: protect terminal
output, redirects and shell history/process arguments. This is not a secret
redactor or OS/process security layer.

Without mediation, language support is the existing bounded English grammar; see
[orchestration](orchestration.md) for exact screening scope and clarification rules.
Chat retains one bounded context, not history or unrestricted memory. The
application adds no command history or transcript file; host terminal/shell
software may have its own retention behavior. There is no paging, UI/server,
forecast or retrieval.
Concise mode is a fixed first-10 preview, not pagination or ranking. Expanded human
and JSON modes can be large; JSON preserves all evidence rather than hiding rows.
Advanced structured filters remain available through the Python API. See
[the Step 27 presentation contract](concise_cli_presentation.md) and the
[Step 34 conversational contract](conversational_cli_contract.md).
