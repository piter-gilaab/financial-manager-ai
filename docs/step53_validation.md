# Phase 14 — Step 53 validation

## Status

**PASS.** A deterministic `DynamicQueryBinder` now maps an explicit registered
dataset and closed operation key to the existing Step 52 adapter request. It is
directly callable Python infrastructure only and does not change global
capability readiness, manager routing, mediation or conversation behavior.

## Implemented seam

`src.execution.binding` exposes:

- frozen `DynamicQueryRequest` and `DynamicQueryParameters` data contracts;
- closed `BindingOutcome` values and `BindingResult`;
- frozen `BoundExecutionRequest` identity/version metadata;
- `DynamicQueryBinder.bind(request)`;
- `DynamicQueryBinder.execute(request)`.

The binder's production resolver is the existing Step 52 `adapter_for` static
allowlist. An optional resolver dependency is trusted application configuration
for tests/composition; request, registry, source and model data cannot populate
it or name an implementation.

## Resolution and operation catalog

Binding follows one deterministic sequence:

1. validate the typed request and exact Phase 13 dataset-ID shape;
2. authenticate the current workflow, registry, profile and mapping;
3. reconcile current registry/mapping/source identity metadata;
4. enforce the direct-execution lifecycle/readiness gate;
5. take the canonical domain only from approved registry/mapping state;
6. resolve the domain/operation pair in the closed catalog;
7. validate the operation's parameter and required roles;
8. resolve and version-check the static adapter;
9. construct the typed Step 52 request.

The catalog contains only:

| Operation | Required roles | Parameters |
|---|---|---|
| `SALES_RECORD_COUNT` | none beyond approved `SALES_RECORD` identity | none |
| `SALES_SUMMARY` | `SALES` | none |
| `SALES_BY_COUNTRY` | `SALES`, `COUNTRY` | optional `missing_dimension=BUCKET|EXCLUDE` |

Missing `PROFIT` and other unused roles do not block these operations. A required
role must be uniquely confirmed and retain its approved stable column identity.
Recognized accounting, payable, receivable and cash domains are not coerced to
`SALES_RECORD`.

## Execution and evidence

`execute` binds afresh, re-resolves a compatible adapter, and passes only the
contained `AdapterExecutionRequest`. The adapter then performs the complete
Step 51/52 source, digest, schema, value and readiness checks. The binder never
loads source rows merely to bind and performs no financial calculation.

Successful evidence is returned unchanged, preserving exact Decimal results,
currency, coverage, quality and the complete adapter lineage from dataset and
registry versions through canonical record and source row. Binding failures use
fixed messages and existing evidence statuses without paths, classes, payloads
or stack traces.

## Security

Dataset IDs must match the existing exact `ds_` identifier contract before any
artifact path is formed. Operation and missing-dimension strings are exact
lookups in closed maps. SQL-shaped parameters, path traversal, import-shaped
operations and non-typed requests remain inert and fail before adapter
execution.

There is no SQL, shell, subprocess, `eval`, `exec`, dynamic import, untrusted
`getattr`, LLM or network path. Binding stores no adapter object, callable,
source path, source column or Python implementation name.

## Capability status

At the Step 53 validation point, Phase 13 `CapabilityDiscovery`, `FinancialManagerAgent`, capability registry,
routing, Financial Analysis Agent, mediation catalog/prompts, CLI and conversation
state are unchanged. Direct binding/execution still coexists with:

```text
FINANCIAL_ANALYSIS.state = BLOCKED_NOT_IMPLEMENTED
FINANCIAL_ANALYSIS.execution_readiness = BLOCKED
```

Step 54 subsequently became the activation authority without changing this
historical Step 53 result.

## Automated tests

Focused command:

`python -B -m unittest tests.test_dynamic_query_binding`

Result: **17 passed**. The scenarios cover:

- count, sales summary and sales-by-country binding;
- renamed fields and absence of unrelated `PROFIT` semantics;
- missing `SALES`/`COUNTRY` authority and incompatible stable column identity;
- exact dataset resolution, unknown identifiers and unsupported domains;
- valid default/explicit `BUCKET` and `EXCLUDE` policies;
- invalid/SQL-shaped policies and operation-specific parameter rejection;
- malicious operation/path strings as inert data;
- stale mapping pointers, mapping/profile/source identity mismatches and
  unavailable/incompatible adapters;
- direct exact execution with unchanged mapping/source-row lineage;
- unchanged global capability blocking.

Combined Steps 51–53 focused command: **41 passed**. Expanded
onboarding/execution/financial regression: **177 passed**.

Complete regression outside the managed loopback-socket restriction: **551
passed, 0 failed, 0 errors and 0 skipped** in 438.871 seconds. `git diff --check`
passed, and security scans found no SQL, shell, subprocess, dynamic import,
untrusted `getattr`, `eval` or `exec` path in the binder.

The final `code-review` gate reported **PASS** on both axes. Standards found no
remaining documented-rule or smell finding. Spec found no remaining requirement,
authority, security, activation or scope finding. The initial reviews identified
duplicated adapter compatibility checks and missing mapping→profile/profile→source
identity checks; both were fixed test-first and the final re-reviews passed.

## Limitations

- Dataset targeting is exact `dataset_id` only; there is no discovery or fuzzy
  “latest file” selection.
- There are no filters, arbitrary measures/groupings, sort expressions or new
  adapter operations.
- Only `SALES_RECORD` has a dynamic binding catalog.
- A bound result is descriptive metadata, not a durable executable token;
  `execute` binds and validates current state again.
- Financial Manager/LLM/CLI routing and capability activation remain absent.
- Anomaly Detection, Forecasting and RAG remain unchanged and blocked for new
  datasets.
