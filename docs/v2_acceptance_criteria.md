# Financial Manager AI V2 — Frozen Acceptance Criteria

Status: **FROZEN — V2 RELEASE GATE**.

Every criterion A–Z is mandatory. Acceptance evidence must identify tests,
artifacts or reviewed documentation; unsupported claims and skipped mandatory
flows are failures. Final release requires zero unresolved BLOCKER and zero
unresolved HIGH correctness, security, privacy or integrity issue.

| ID | Criterion | Required evidence |
|---|---|---|
| A | V1 regression compatibility | Complete frozen V1 regression passes without changed V1 operation meaning. |
| B | `SALES_RECORD` remains stable | All nine dynamic Financial Analysis and two anomaly operations preserve contracts/evidence. |
| C | `PAYABLE` generic execution works | All six closed operations pass direct Manager and persisted end-to-end validation. |
| D | `RECEIVABLE` generic execution works | All six closed operations pass direct Manager and persisted end-to-end validation. |
| E | `CASH_TRANSACTION` generic execution works | All six closed operations pass direct Manager and persisted end-to-end validation. |
| F | Each domain uses closed query catalogs | Unknown/misplaced operations, parameters, measures, columns and expressions fail closed. |
| G | Readiness is operation-specific | Independent support/blocking, revocation, recovery and execution revalidation pass. |
| H | Semantic confirmation remains explicit | Suggestions never approve roles/domain/value mappings/qualifiers without user action/evidence. |
| I | Currency remains non-inferred | UNKNOWN/CONFIRMED/CONFIRMED_MULTIPLE behavior passes; no symbol/geography/model inference or FX. |
| J | Financial Core remains authoritative | Exact arithmetic, aging, overdue and net cash originate in Core-owned deterministic functions. |
| K | Manager remains orchestration-only | No financial/anomaly calculation or semantic/readiness duplication in Manager. |
| L | Application/API performs no authoritative arithmetic | Transport/application results are structure/evidence-preserving and Decimal-safe. |
| M | API supports primary workflows | Health, capabilities, datasets, onboarding, confirmation, readiness, analysis, anomalies and sessions pass. |
| N | Web onboarding works end to end | Upload through safe ingestion to explicit confirmation/readiness/capability display passes. |
| O | Web analysis works end to end | Every supported evidence shape renders exact values/coverage/currency/limitations without client calculation. |
| P | Web anomaly flow works for existing supported anomaly operations | Sales/Profit screen and bounded candidate follow-up pass with safe terminology. |
| Q | Web conversation works through approved backend contracts | Dataset selection, closed operations, clarification, grounding, reset/expiry and blocked states pass. |
| R | Security/privacy validation passes | Closed dispatch, safe upload, local data, injection/path/error/prompt and no-telemetry boundaries pass. |
| S | Data integrity/lineage passes | Source/profile/mapping/registry/adapter/catalog/policy lineage and stale rejection pass. |
| T | Fresh setup passes | Documented Python/API and pinned Node/web setup works from a clean supported environment. |
| U | Documentation/demo passes | Scope, setup, API, UI, examples and limitations match actual behavior in an exercised demo. |
| V | Complete regression passes | All V1+V2 tests complete with zero failure, error and skip of mandatory coverage. |
| W | No unresolved BLOCKER/HIGH release issue | Final issue/risk review records zero qualifying unresolved finding. |
| X | Forecasting remains deferred unless separately approved | No route/UI/handler/model or false capability activation exists. |
| Y | RAG remains deferred unless separately approved | No corpus/retrieval/route/UI or false capability activation exists. |
| Z | V2 scope has not expanded beyond the five frozen phases | Final inventory matches scope, roadmap, catalogs and authorized surfaces. |

## Required semantic edge cases

- due date equal to reference date is `NOT_DUE`;
- settled/cancelled records do not enter open aging/overdue;
- original invoice amount does not masquerade as outstanding balance after
  partial settlement;
- missing/invalid due date and amount remain unavailable;
- zero/negative open balance follows the frozen exclusion/quality contract;
- status mappings incomplete or historically invalid for `as_of_date` block;
- `as_of_date` different from approved `dataset_reference_date` blocks;
- cash direction never comes from sign and convention conflicts are disclosed;
- `CONFIRMED_MULTIPLE` blocks monetary aggregation;
- unknown currency stays qualified and unconverted; and
- supplier/customer roles are not substituted.

## Required interface edge cases

- API rejects SQL, formulas, adapter/function/path/import names, arbitrary
  grouping/filtering and unknown fields;
- upload applies all existing CSV/XLSX size/archive/formula/macro/link controls;
- Decimal values never become JSON/binary floats;
- known blocked/unsupported/no-data/provider states are not HTTP/UI 500;
- stale readiness/session/evidence references fail closed;
- frontend charts do not create authoritative derived financial facts; and
- no auth/multitenancy/SaaS assumption is required for local completion.

## Release decision

V2 is `COMPLETE` only when A–Z pass and no mandatory blocker remains. Phase-level
completion, documentation alone, a working UI mock or a subset of domain
operations cannot substitute for final acceptance.
