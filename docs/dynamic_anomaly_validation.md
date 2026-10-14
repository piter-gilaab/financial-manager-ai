# Dynamic anomaly detection — Phase 16 validation

## Scope and outcome

Phase 16 validates one persisted, deterministic path for approved dynamic
`SALES_RECORD` datasets:

```text
local source → profile/mapping/domain approval → registry → current operation
readiness → typed Manager request → static dynamic adapter → exact Tukey-IQR
screening → structured evidence and statistical presentation
```

The complete operation catalog remains exactly `SALES_ANOMALY_SCREEN` and
`PROFIT_ANOMALY_SCREEN`. Profit is supplied and confirmed, never derived. Both
operations use GLOBAL scope, `tukey_iqr` v1.0, linear `(n - 1) × p` quartiles,
both tails, strict fences, at least 30 usable exact decimals and positive IQR.
No peer screen, arbitrary measure/algorithm or fraud classification exists.

## Primary persisted flow

The primary end-to-end fixture uses renamed `RevenueValue` and `NetOutcome`
columns, explicitly maps them to Sales and Profit, approves `SALES_RECORD`, and
persists the workflow/profile/mapping/registry before discovery and Manager
execution. Each measure contains 32 usable values, two unavailable values
(`source_missing` and `parsing_failed`), negative values and known candidates in
both tails.

Sales produces Q1 `6.75`, Q3 `22.25`, IQR `15.50`, lower fence `-16.500` and
upper fence `45.500`; `-100` and `100` are candidates. Supplied Profit produces
Q1 `-8.25`, Q3 `7.25`, IQR `15.50`, lower fence `-31.500` and upper fence
`30.500`; `-200` and `200` are candidates. Each result reconciles population
34 = 32 assessed + 2 not assessed, with 2 candidates and 30 not selected.

The Manager preserves response v1.1, exact adapter evidence, current dataset
capability, UNKNOWN denomination disclosure, `conversion_applied=false`, all 34
ordered assessment/lineage entries and two candidate references. The test
blocks socket creation and verifies no local path appears in normal output.

## Revocation, recovery and immutable source identity

Current readiness is recomputed on every discovery/Manager request. Mapping
revocation blocks the affected operation without delegated evidence; confirmed
restoration re-registers current semantics and permits fresh execution. Mapping
between approved columns demonstrates 30+ → 29 usable → 30+ and positive IQR →
zero IQR → positive IQR revocation/recovery without a cached readiness token or
fence.

Source bytes are immutable under one registered identity. Changing them after
approval fails fingerprint/registry validation; restoring the exact approved
bytes permits fresh reevaluation. A genuinely corrected different source is
onboarded as a new content-scoped dataset rather than silently replacing the
old identity. Schema/stable-column/profile/mapping/workflow/registry mismatches
all fail closed in the focused integrity suites.

## Candidate references and presentation

Adapter candidate references are preserved through the Manager. They are
dataset-scoped, deterministic, bounded to 20, contain only actual candidates
and carry non-executable canonical/source identity. Dynamic references are not
accepted as execution input and no conversational resolver/opaque session
handle was added. Consequently cross-dataset or stale-reference lookup cannot
occur on this path; dynamic conversational follow-up remains explicitly
deferred rather than reusing the incompatible legacy evidence schema.

Presentation states only that records met the statistical screening rule and
are candidates for review. It never converts `CANDIDATE` into fraud, error,
suspicious activity, misconduct, illegality or wrongdoing probability.

## Acceptance matrix

| ID | Scenario | Status | Validation evidence |
|---|---|---|---|
| A | Sales happy path | PASS | persisted primary Manager flow |
| B | Profit happy path | PASS | supplied-Profit primary Manager flow |
| C | renamed fields | PASS | `RevenueValue`/`NetOutcome` approved mappings |
| D | exactly 30 Sales | PASS | focused adapter/readiness tests |
| E | 29 Sales | PASS | readiness and Manager blocker tests |
| F | exactly 30 Profit | PASS | operation-specific readiness test |
| G | 29 Profit | PASS | operation-specific readiness test |
| H | zero IQR Sales | PASS | readiness/Manager blocker and recovery flow |
| I | zero IQR Profit | PASS | operation-specific readiness test |
| J | lower-tail candidate | PASS | primary Sales/Profit evidence |
| K | upper-tail candidate | PASS | primary Sales/Profit evidence |
| L | fence equality | PASS | strict lower/upper focused adapter test |
| M | missing values | PASS | primary flow: `NOT_ASSESSED/source_missing` |
| N | parse failures | PASS | primary flow: `NOT_ASSESSED/parsing_failed` |
| O | negative Sales | PASS | primary flow preserves `-100` and sign |
| P | negative Profit | PASS | primary flow preserves `-200` and sign |
| Q | UNKNOWN currency | PASS | primary and Manager currency tests |
| R | CONFIRMED currency | PASS | Manager ISO preservation test |
| S | multiple currency blocked | PASS | Manager readiness refusal |
| T | partial capability | PASS | CLI both/partial/blocked matrix |
| U | Sales revocation | PASS | domain-anchor readiness revocation test |
| V | Profit revocation | PASS | persisted Manager revocation test |
| W | recovery | PASS | mapping restoration and fresh execution |
| X | sample-size revocation/recovery | PASS | persisted semantic-column transition |
| Y | IQR revocation/recovery | PASS | persisted semantic-column transition |
| Z | source change | PASS | fingerprint failure and exact restoration |
| AA | schema change | PASS | execution stable-column/schema tests |
| AB | stale mapping/profile | PASS | focused adapter/readiness integrity tests |
| AC | stale registry/workflow | PASS | readiness/activation integrity tests |
| AD | arithmetic failure | PASS | readiness + Manager `exact_arithmetic_limit` |
| AE | Decimal integrity | PASS | high-scale/small/binary-sensitive exact tests |
| AF | malicious inputs | PASS | dataset ID, header, cell and operation tests |
| AG | safe candidate language | PASS | exact deterministic Manager summary test |
| AH | candidate references | PASS_WITH_LIMITATIONS | bounded evidence refs pass; conversational resolver deferred |
| AI | Manager response | PASS | v1.1, distinct global/dataset state, lossless evidence |
| AJ | CLI human capability | PASS | three-state E2E discovery |
| AK | CLI JSON capability | PASS | typed three-state E2E discovery |
| AL | legacy Receiver General | PASS | unchanged legacy suites |
| AM | legacy Company Financials | PASS | unchanged legacy suites and policy comparison |
| AN | dynamic Financial Analysis regression | PASS | all nine-operation integration suites |
| AO | Forecasting blocked | PASS | capability/readiness regressions |
| AP | RAG blocked | PASS | capability/readiness regressions |
| AQ | privacy | PASS | local synthetic/offline test and privacy suite |
| AR | security | PASS | exact-type protocol tests and static scan |
| AS | reproducibility | PASS | fingerprint + artifact identities + policy/version + exact code |
| AT | lineage | PASS | all records traced in primary persisted evidence |

The single limitation in AH does not weaken execution authority or evidence:
references are output-only and cannot be used to bypass current readiness.

## Compatibility and non-goals

Legacy Receiver General and Company Financials stay on their existing anomaly
paths. All nine dynamic Financial Analysis operations are unchanged. Forecasting
and Document Retrieval/RAG remain blocked. No anomaly execution CLI, external
LLM, network, telemetry, cloud service, API, frontend, authentication, Phase 17
work or source-data mutation was added.
