# Phase 15 — Dynamic Capability Expansion Contract

## Purpose and authority

Step 59 activates operation-level readiness for the six analyses implemented in
Steps 57–58. It extends the existing Phase 14 readiness projection; it does not
create a second capability registry, execute financial calculations, or add a
new Manager route.

The authority chain remains:

```text
approved onboarding artifacts
  -> CapabilityDiscovery
  -> DynamicQueryBinder
  -> static SalesRecordExecutionAdapter validation
  -> operation readiness
```

Readiness is deterministic, dataset-specific, recomputed from current persisted
state and independent of LLM authority. Financial Core remains the only owner of
authoritative arithmetic and evidence.

## Closed operation catalog

`CapabilityDiscovery` consumes the binder's existing `SALES_RECORD` catalog as
its sole operation catalog. It evaluates exactly these entries, in catalog
order:

| Operation | Required confirmed semantics | Readiness measure |
|---|---|---|
| `SALES_RECORD_COUNT` | approved `SALES_RECORD` | registered source records |
| `SALES_SUMMARY` | `SALES` | at least one executable Sales value |
| `SALES_BY_COUNTRY` | `SALES`, `COUNTRY` | at least one executable Sales value; missing row labels use BUCKET by default |
| `SALES_BY_PERIOD` | `SALES`, `TRANSACTION_DATE` | at least one executable Sales value; default `MONTH` and BUCKET |
| `SALES_BY_SEGMENT` | `SALES`, `SEGMENT` | at least one executable Sales value; missing row labels use BUCKET by default |
| `SALES_BY_PRODUCT` | `SALES`, `PRODUCT` | at least one executable Sales value; missing row labels use BUCKET by default |
| `PROFIT_SUMMARY` | `PROFIT` | at least one executable supplied Profit value |
| `DISCOUNT_ANALYSIS` | monetary `DISCOUNT` | at least one executable supplied Discount value |
| `UNITS_SOLD_SUMMARY` | `UNITS_SOLD` | at least one executable quantity value |

There is no readiness-only allowlist and no copied role catalog. The binder's
closed descriptors provide operation names and required roles; adapter
validation remains authoritative for source, schema, canonicalization, currency,
quality and implementation compatibility.

## Domain anchors and isolated dependencies

The existing Phase 13 `SALES_RECORD` domain contract requires both
`TRANSACTION_DATE` and `SALES`. They are domain anchors, not merely optional
operation fields. Rejecting or unresolving either makes the mapping
`NEEDS_CONFIRMATION`; all dynamic execution and all nine readiness entries then
block until the domain is approved again. Step 59 does not bypass that contract.

While the domain remains approved, optional roles are isolated:

- `COUNTRY` affects only `SALES_BY_COUNTRY`;
- `SEGMENT` affects only `SALES_BY_SEGMENT`;
- `PRODUCT` affects only `SALES_BY_PRODUCT`;
- `PROFIT` affects only `PROFIT_SUMMARY`;
- monetary `DISCOUNT` affects only `DISCOUNT_ANALYSIS`;
- `UNITS_SOLD` affects only `UNITS_SOLD_SUMMARY`.

Missing values inside a confirmed column are data-quality facts, not missing
semantics. A grouped operation remains eligible when its confirmed dimension has
missing rows because its default BUCKET policy is executable. Summary/monetary
operations require at least one parsed measure during the non-executing probe;
partial missing or parse-failed values remain eligible and are disclosed later
by Financial Core. A direct typed execution may still return `NO_DATA`, but an
all-unavailable measure is not advertised as ready.

## Period readiness

`SALES_BY_PERIOD` uses only confirmed `TRANSACTION_DATE`. The binder defaults to
calendar `MONTH`; `YEAR` remains an allowed execution parameter. Readiness does
not inspect locale, current time, filenames or alternate date columns. Ambiguous
dates need the existing explicit format decision before domain approval. A
non-missing invalid date remains a controlled registration blocker; approved
missing markers are valid unavailable row values.

## Profit, Discount and Units Sold

Profit readiness consumes only supplied confirmed `PROFIT`; it never derives
Profit from Sales, COGS or another formula.

Discount readiness consumes only the confirmed `DISCOUNT` role whose closed
value kind is `MONETARY_AMOUNT`. Header text, percent-like values, formatting and
numeric range do not establish this role.

Units Sold readiness consumes only confirmed `UNITS_SOLD`. It is a quantity and
does not depend on currency state.

## Currency

`UNKNOWN` currency does not block otherwise valid source-denomination Sales,
Profit or Discount operations. `CONFIRMED` preserves its approved ISO code.
`CONFIRMED_MULTIPLE` follows the existing adapter blocker for scalar monetary
operations, while `SALES_RECORD_COUNT` and `UNITS_SOLD_SUMMARY` remain independent
of currency. No readiness path infers denomination.

## Readiness states and overall capability

Every catalog operation reports exactly one existing state:

- `SUPPORTED`: binder binding and adapter readiness validation both pass;
- `BLOCKED`: current semantics, artifacts, source, schema, currency, quality or
  adapter validation prevents execution;
- `UNSUPPORTED`: the binder explicitly reports the operation unsupported.

Controlled reasons identify the binder or adapter outcome without paths or
implementation details. `FINANCIAL_ANALYSIS` is `AVAILABLE_WITH_LIMITATIONS`
when at least one operation is `SUPPORTED`; no all-or-nothing promotion is used.
The limitation means a fixed nine-operation dynamic catalog, not parity with the
legacy 17 contracts and not arbitrary analysis.

## Trusted non-executing probe

The probe may authenticate workflow/registry/profile/mapping/source identities,
bind default parameters, validate the static adapter and canonicalize only the
operation-scoped fields. It inspects whether a required measure has at least one
executable value and delegates a dry-run to the same Financial Core operation so
trapped exact-arithmetic failures cannot be advertised as supported. The probe
discards that result: it publishes no financial values or evidence, mutates no
source data and never bypasses lifecycle gates for normal execution. The adapter
remains closed dispatch and owns no arithmetic.

## Revocation, recovery and integrity

Every semantic decision creates a new mapping version. Capability inspection
recomputes against the current mapping and persists a new readiness projection
only when it changes. Optional-role revocation/recovery affects only its operation.
Domain-anchor revocation blocks the whole approved domain as documented above.

Recovery reloads current persisted artifacts and reruns binder/adapter validation;
no in-memory availability token survives. Source fingerprint, schema, stable
column identity, workflow pointers, mapping/profile/registry digests and adapter
versions all fail closed. Restoring the exact approved source permits a fresh
probe to recover valid operations.

## Manager and CLI

`FinancialManagerAgent.execute_dataset_request` remains a thin delegate to the
existing binder and adapter. It can execute every operation reported supported,
but it neither chooses operations nor calculates values.

`python -m src.cli dataset capabilities <dataset_id>` and `--json` expose all
nine states, controlled blocked reasons, canonical domain, currency and fixed
limitations. Step 59 adds no `dataset analyze` command and no conversational or
fuzzy dataset discovery.

## Security and unchanged blockers

Dataset IDs, operation strings, parameters, headers and values remain inert
data. The expansion introduces no SQL, shell, subprocess, `eval`, `exec`, dynamic
import, untrusted attribute lookup, runtime code generation, dynamic adapter
loading, network, telemetry or external provider.

Dynamic Anomaly Detection, Cash Flow Forecasting and Document Retrieval/RAG
remain `BLOCKED`. No other canonical domain is activated or coerced to
`SALES_RECORD`.

## Step 60 boundary

Step 59 ends after focused validation and two-axis review of capability
activation. Full nine-operation onboarding-to-Manager acceptance, renamed
columns, malicious data, complete revocation/recovery and legacy regression are
validated in Step 60; Step 59 does not claim Phase 15 completion.
