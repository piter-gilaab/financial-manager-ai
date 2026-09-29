# Phase 6 — Step 17 validation

Implemented only the Main Financial Manager facade under the explicit Step 17
authorization. Architecture and usage are documented in
[Main Financial Manager Agent](main_financial_manager_agent.md).

## Registry and architecture decisions

| Capability | Availability | Delegation / reason |
|---|---|---|
| FINANCIAL_ANALYSIS | AVAILABLE | Existing `FinancialAnalysisAgent.ask`; its 17 contracts and routing remain unchanged |
| ANOMALY_DETECTION | AVAILABLE | Existing `AnomalyService.analyze`; algorithms, peer definitions, exact arithmetic and statuses remain unchanged |
| CASH_FLOW_FORECASTING | BLOCKED | No authoritative actual cash inflows/outflows; source currency unresolved; no model executed |
| DOCUMENT_RETRIEVAL | BLOCKED | No approved real production corpus; documented architecture remains DEFERRED for implementation; no retrieval executed |

One application facade composes two existing modules. The registry has exactly
four static identifiers, no dynamic discovery/registration, and no executable
forecasting/RAG handlers. Discovery returns detached metadata without querying
data or invoking providers. Explicit selection precedes availability checking,
request validation and a single delegated call. No automatic selection, fallback,
retry, multi-step planning or capability chaining was introduced.

Frozen metadata/enums and TypedDict request/response models describe the facade.
The complete delegated response is copied into `delegated_result`. Convenience
status, warning, error and clarification fields are separate copies; financial
values are never recalculated or numerically converted. Step 13 explanation text
passes through unchanged. Screening summaries contain returned status and neutral
candidate/abstention terminology, with all statistical evidence kept intact.

No new correlation IDs, model providers, dependencies, persistence, logging,
telemetry, credentials or external data flows were introduced.

## Test results

Focused command:

```sh
.venv/bin/python -B -m unittest discover -s tests -p test_manager.py -v
```

**31 passed, 0 failed, 0 errors, 0 skipped**, in **19.399 seconds**.

Full regression command:

```sh
.venv/bin/python -B -m unittest discover -s tests -v
```

| Suite | Passed | Failed | Errors | Skipped |
|---|---:|---:|---:|---:|
| Phase 3 database | 17 | 0 | 0 | 0 |
| Phase 4 financial tools | 37 | 0 | 0 | 0 |
| Phase 4 quality | 19 | 0 | 0 | 0 |
| Phase 4 currency/FX | 22 | 0 | 0 | 0 |
| Step 13 Financial Analysis Agent | 36 | 0 | 0 | 0 |
| Step 14 anomaly screening | 32 | 0 | 0 | 0 |
| Step 17 Main Financial Manager | 31 | 0 | 0 | 0 |
| **Total** | **194** | **0** | **0** | **0** |

Full run duration: **153.959 seconds**. All 163 previous tests remain unchanged
and pass. Counts refer to unittest methods, not expanded subtests. There were
no test discovery changes or skipped unavailable capabilities.

## Acceptance evidence

| Requirement | Verified outcome |
|---|---|
| Truthful capability discovery | Exactly four entries, two AVAILABLE and two BLOCKED; RAG reason retains architecture DEFERRED; order deterministic |
| Metadata isolation | Frozen internal records; modifying returned metadata does not change registry state |
| Explicit analysis delegation | Exact question/dataset/parameters passed once to the existing agent; no screening fallback |
| Complete analysis response | Actual partial Discount result equals direct agent response, including 53 placeholders, UNKNOWN currency, warnings, flags and digest |
| Explicit anomaly delegation | Actual RG amount, CF Sales and CF Profit responses equal direct service responses completely |
| Candidate evidence unchanged | Original observations, CANDIDATE/NOT_SELECTED/NOT_ASSESSED, references, thresholds, peer definitions and lineage preserved |
| Neutral summaries | Screening candidates require investigation; no accusation or probability is generated |
| Unavailable operations | Forecast/RAG return documented structured unavailability before payload inspection; neither existing dependency executes |
| Request validation | Unknown/missing/non-string capability, malformed objects and wrong analysis call shape return structured INVALID_REQUEST |
| Domain validation ownership | Existing selected implementation returns its own validation/unsupported errors; manager preserves those responses |
| Distinct outcomes | SUCCESS, PARTIAL, NO_DATA, clarification, provider failures, validation errors and quality blockers remain distinct |
| Anomaly abstentions | Actual 35-row monthly cohort retains all 35 peer NOT_ASSESSED observations and its PARTIAL status |
| Evidence isolation | Caller request protected from mutating test adapter; convenience warnings/summary cannot mutate nested evidence or original delegate object |
| Exact values | No monetary arithmetic or float coercion; exact strings retained and a test-only Decimal object survives copying unchanged |
| Failure transparency | Unexpected implementation exceptions propagate; unknown delegate statuses are not silently reported as success |
| No arbitrary execution | SQL-shaped requests are rejected by their owning validators; user-supplied module/function names cannot select handlers |
| Offline operation | Default facade executes both real implementations with socket creation disabled; no external provider needed |
| Previous implementations unchanged | Main module imports only public analysis/screening interfaces; all Phase 3–5 source/test hashes remain unchanged |

## File and dataset preservation

The pre-Step-17 SHA-256 inventory covered **103 existing files** across data,
source, tests, notebooks, documentation, README, AGENTS and CONTEXT. After the
full test run, **102 were unchanged**. The only intentionally modified existing
file is README.md, adding Step 17 links and scope description.

Production database, raw/processed datasets, historical cleaning artifacts,
approved-run/schema pins, all notebooks, query contracts, the Financial Core,
Step 13, Step 14 and all previous tests remained unchanged. No migration or
production synthetic records were created. Existing database tests continue
using disposable temporary databases.

Database SHA-256:
`8b9536867d7e1ee2e3fd8b0040d40f5806cf6ecb8afc38491cbc058de727c744`.

Created:

- `src/manager/__init__.py`
- `src/manager/agent.py`
- `src/manager/models.py`
- `src/manager/registry.py`
- `tests/test_manager.py`
- `docs/main_financial_manager_agent.md`
- `docs/step17_validation.md`

Modified: `README.md`. Pre-existing unrelated/untracked files were retained.

## Remaining limitations and stopping point

The manager requires explicit capability selection. Analysis still uses Step 13's
bounded grammar; screening retains Step 14's exploratory in-sample IQR rules and
peer limitations. Unknown currency, unresolved placeholders, missing company
identity, accounting grain/summary overlap, fiscal alignment and provenance
uncertainties are unchanged. Neither availability nor screening selection
certifies financial validity.

Forecasting requires authoritative cash data and a defensible target/history.
Document retrieval requires an approved real corpus and subsequent implementation.
Their documented blockers are not replaced by mock production capabilities.

Dependency injection remains trusted local configuration, not a sandbox or an
authentication system. No Step 19 security/privacy framework was implemented.

**Step 18 automatic capability routing and orchestration was not started.** It
is the next recommended separately scoped step. Forecasting, RAG, API/server,
frontend, deployment and other product work were not implemented.
