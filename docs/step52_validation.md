# Phase 14 — Step 52 validation

## Status

**PASS.** A local deterministic `SALES_RECORD` adapter now executes the three
operations approved by the Step 51 contract directly against validated Phase 13
artifacts. It does not change manager routing or global capability readiness.

## Implemented seam

`src.execution` exposes the frozen `AdapterExecutionRequest`, closed operation
and missing-dimension enums, validation outcomes, a static canonical-domain
registry and `SalesRecordExecutionAdapter` with:

- `domain`;
- `adapter_version` and `canonical_model_version`;
- `supported_operations()`;
- `validate(request)`;
- `execute(request)`.

The only static registration is `SALES_RECORD ->
SalesRecordExecutionAdapter`. Dataset content cannot provide an adapter name,
module, attribute or function.

## Operations and required roles

| Operation | Required roles | Behavior |
|---|---|---|
| `SALES_RECORD_COUNT` | approved `SALES_RECORD` domain; no extra operation field | Counts source observations; no monetary currency. |
| `SALES_SUMMARY` | confirmed `SALES` | Exact count/sum and independent measure coverage. |
| `SALES_BY_COUNTRY` | confirmed `SALES` and `COUNTRY` | Exact per-label count/sum, dimension/measure coverage and `BUCKET`/`EXCLUDE` missing-country policy. |

Canonical specifications are built from required roles only. An invalid or
missing unused `PROFIT`, `DISCOUNT`, `SEGMENT`, `PRODUCT` or other role does not
block these operations.

## Financial Core authority

The adapter validates and translates records. `src.financial.sales_records`
owns count, aggregation, grouped ordering, coverage accounting and result
status. It reuses the existing `src.financial.arithmetic` exact context,
precision-60 sum and `src.financial.quality.coverage` percentage rule. The
legacy strict decimal parser remains unchanged; an additive canonical parser
accepts exact Decimal text produced by the approved mapper.

No binary float is used or returned. Negative source sales remain negative.
An exact-arithmetic precision failure returns a controlled quality blocker with
no partial total.

## Registry, schema and lineage

Execution revalidates workflow, registry entry/digest, profile/digest, semantic
mapping version/digest, source fingerprint, ingestion run, source type/sheet,
ordered columns, row count, stable column IDs and the Phase 13 Financial
Analysis semantic/policy readiness gate. Stale valid mapping or profile pointers
return `STALE_MAPPING`; corrupt registry/source artifacts return
`INVALID_REGISTRY`; a mismatched stable schema identity returns
`SCHEMA_MISMATCH`.

`metadata.lineage` carries dataset, registry, profile, mapping, canonical model
and canonical-spec identities plus every canonical record ID, source sheet/row,
participation and exclusion reason. Group objects reference their contributing
canonical record IDs. No local source path is exposed.

## Currency and missing data

UNKNOWN currency remains a valid unverified source-denomination summary with
the established warning. A single explicitly confirmed currency retains its
approved ISO code and mapping-version evidence. Multiple confirmed currencies
block scalar monetary aggregation; country and formatting never select a code.

Blank and Phase 13-approved `NA`/`N/A`/`null`/`none` markers become missing,
not zero. A shared Phase 13 missing-value predicate now keeps profiling and
canonicalization consistent. Missing sales and country values produce explicit
coverage, quality warnings, participation and closed exclusion reasons. Country
labels are returned and sorted as source values, including SQL-shaped text.

## Security and scope

The implementation contains no SQL, shell, `eval`, `exec`, dynamic import,
model call or network access. Requests accept enums, not user-selected column,
measure, class or function names. Malicious headers, values and SQL-shaped
country labels remain inert data. Non-typed requests and unsupported operations
produce controlled `UNSUPPORTED_OPERATION` evidence.

Execution scans the bounded Phase 13 records linearly and sorts only distinct
group keys for deterministic grouped output. Count/sum arithmetic is one-pass;
it does not sort or duplicate the measure population. There is no adapter cache,
concurrency framework or broader plugin mechanism.

## Automated tests

Focused command:

`python -B -m unittest tests.test_execution_adapter_contract tests.test_sales_record_adapter`

Result: **24 passed**. The tests cover:

- normal count/summary/country grouping;
- renamed and malicious source columns;
- UNKNOWN, confirmed and multiple confirmed currencies;
- blank and marker missing values, missing-country bucket/exclusion;
- retained duplicate-row candidates with explicit disclosure;
- unresolved required roles and revised `SALES` semantics;
- stale mapping/profile pointers, registry tampering, changed source fingerprint
  and incompatible stable column identity;
- SQL-shaped source labels, exact decimal precision, negative sales and
  arithmetic overflow;
- closed operations/registration, non-typed input and unchanged capability
  readiness;
- result-level semantic comparison with the legacy Company Financials Core path.
  Both summary and grouped missing-dimension accounting are compared.

Expanded focused execution/onboarding/financial regression: **160 passed**.

Complete regression outside the managed socket sandbox: **534 passed, 0 failed,
0 errors and 0 skipped** in 409.645 seconds. The first managed-sandbox run
executed all 534 tests but its loopback-only mediation subprocess was denied by
the sandbox before the test audit hook could observe the attempt. That isolated
test passed outside the sandbox, as did the complete rerun; this is the same
environmental constraint recorded by the Phase 13 validation. `git diff
--check` passed.

The final `code-review` gate reported **PASS** on both axes: Standards found no
hard-rule or code-quality findings, and Spec found no remaining Phase 14
contract violations. Earlier findings about shared evidence/accounting helpers,
readiness validation, stale profile identity and duplicate-row disclosure were
fixed before this final review.

## Capability status and limitations

`CapabilityDiscovery`, `FinancialManagerAgent`, routing, intent catalogs,
conversation and legacy Company Financials execution are unchanged. Direct
adapter success still coexists with `FINANCIAL_ANALYSIS =
BLOCKED_NOT_IMPLEMENTED` and `execution_readiness = BLOCKED` for onboarded
datasets. Step 53 must provide separately reviewed dynamic query binding; Step
54 remains the capability-activation authority.

Deferred: filters, period/segment/product grouping, profit/discount/units
operations, mixed-currency partitioning, arbitrary measures, manager routing,
Anomaly Detection, Forecasting and RAG.
