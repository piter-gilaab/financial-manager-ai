# V1 acceptance — Phase 7, Step 21

**Status: PASS.** All 19 acceptance tests and the complete 291-test regression
suite pass, with no failures, errors or skips. Acceptance is limited to the existing
local, single-command V1 and approved data snapshot. Step 22 is not included.

## Scope and decisions

`tests/test_acceptance.py` invokes the real `python -B -m src.cli` entry point in
fresh subprocesses, using the existing interpreter. No manager, router, provider,
Core or anomaly implementation is mocked. The path is CLI → manager → top-level
routing/registry → Step 13 analysis or Step 14 screening → approved snapshot →
structured evidence → CLI output.

Expected financial evidence comes from explicitly selected approved Core contracts
and the anomaly service, with selected fixed baseline facts as additional anchors.
Tests compare complete nested evidence, not recalculated financial totals. This
validates integration; existing module tests remain responsible for arithmetic
and statistical correctness. JSON float/nonfinite tokens are rejected in financial
responses. Human output is checked separately for essential facts/disclosures.

| User workflow | Acceptance requirement |
|---|---|
| `capabilities` | Actual registry: Analysis/Anomaly AVAILABLE; Forecasting/Retrieval BLOCKED |
| `plan "Sales by country"` | Capability-only routing preview; no database connection or result |
| RG / CF record counts | 9,282 / 700 source records; no currency assigned to counts |
| Sales summary; country grouping in May 2014 | Exact Core evidence, supported period/filter scope and UNKNOWN currency |
| RG amount summary; department groups | Exact amount strings and explicit missing-dimension coverage |
| Discount analysis | 53 placeholders remain excluded; coverage and warnings preserved |
| RG highest two amounts | Descriptive values and source lineage, without screening labels |
| RG accounting screening; CF Profit screening | Full global/peer references, thresholds, peer sizes, lineage and three assessment statuses |
| Combined sales summary + sales screening | Analysis then screening; separate evidence equal to independent services; repeatable output |
| No matching country | NO_DATA with null monetary total, not a zero substitute |
| Forecast / invoice question | Documented blocker, no model/retrieval or query execution |
| Vague intent / ambiguous dataset | Top-level or Step 13 clarification; no guessed answer or query |
| Unsupported financial meaning / executable instruction | Controlled rejection, no financial evidence or database access |
| Missing local data / malformed input | Controlled blocker or validation/syntax response, without private diagnostics |

Human and JSON outputs are both exercised. Exit 0 means a delivered application
outcome, including blocked, partial, no-data and clarification responses; malformed
CLI syntax returns 2. See [CLI workflow](cli_workflow.md) for the complete policy.

## Security, privacy and integrity

A temporary test-only `sitecustomize` audit hook runs inside each CLI subprocess.
It records and denies Python socket events and shell/child-process launches;
planning, blocked, clarification and rejection cases also deny SQLite connections.
Tests require the hook's startup marker and an empty violation log, even if the
application were to swallow a denied-operation exception. Application modules and
business logic are unchanged. This is test instrumentation, not a shipped security
framework or OS sandbox; it does not certify arbitrary native/injected Python.

Executable-shaped questions are passed as argument-list data, never through a
shell. Temporary file and environment canaries check that instructions neither
execute nor disclose environment values. Missing-artifact errors are exercised in
a temporary code-only copy, without moving or changing production assets. Decoded
JSON contains only data, with complete service evidence and no live connection.
Caller text and legitimate lineage remain sensitive; no blanket redaction is claimed.

SHA-256 inventories of `data/` and `notebooks/` are compared during class cleanup,
including when tests fail. They cover raw/processed data, the SQLite database and
historical cleaning artifacts. A separate pre/post validation inventory checks all
existing source, test and documentation files. See [validation](step21_validation.md)
for final counts, review and integrity results.

## Accepted scope and limits

Acceptance does not expand the existing bounded English grammar or 17 analysis
contracts. RG amounts are accounting entries, not verified expenses/revenue/cash
flows. Company Financials contains sales records without company identity. Currency,
missingness, placeholders, fiscal alignment and provenance limitations remain.
Screening candidates require investigation; NOT_SELECTED is not a validity finding,
and NOT_ASSESSED remains an abstention under the existing peer/minimum-size policy.

Forecasting remains BLOCKED without verified actual cash-flow data; document
retrieval remains BLOCKED without an approved production corpus. No external LLM,
FX, network service, new dependency, API/frontend, deployment or persistent session
was introduced. Tests cover representative approved workflows, not every English
paraphrase, OS, terminal, concurrency condition or deployment threat model.
