# Phase 14 — Execution Adapter contract

## Purpose and authority

An execution adapter is a deterministic translation layer between an approved
onboarded dataset and Financial Core operations. It resolves approved semantic
roles, validates the exact registered artifacts, constructs a bounded canonical
view, and asks Financial Core logic to calculate. It is not a second Financial
Core and it does not make an arbitrary dataset executable.

The authority chain is:

```text
source data
  -> approved onboarding semantics
  -> canonical domain model
  -> execution adapter
  -> Financial Core
  -> structured evidence
  -> Financial Manager
  -> LLM / presentation
```

The source bytes are authoritative for source facts. The current confirmed
semantic mapping is authoritative for field meaning. The adapter may translate
only those meanings. Financial Core owns arithmetic, coverage and financial
result semantics. The manager and an LLM may orchestrate or explain but cannot
change any of these authorities.

An adapter may:

- read the current dataset registry entry and its referenced ingestion, profile
  and semantic-mapping artifacts;
- validate registry, fingerprint, digest, schema, lifecycle, domain and
  operation-specific semantic preconditions;
- map confirmed canonical roles to source fields without depending on their
  literal names;
- expose a supported canonical record view to Financial Core logic;
- preserve registry, mapping, canonical-record and source-row lineage;
- return closed, controlled validation and execution outcomes.

An adapter must not infer or revise semantics, currency, signs, debit/credit,
cash direction, company identity or source values. It must not impute values,
delete records, modify outliers, calculate financial totals, generate SQL,
execute model-authored code, select an implementation from dataset content, or
change capability readiness.

## Module and seam

`src.execution` is the execution-adapter module. Its small public interface is:

```text
domain
adapter_version
canonical_model_version
supported_operations()
validate(request)
execute(request)
```

`validate` returns a data-only readiness outcome. `execute` either returns an
existing-style structured financial evidence envelope or the corresponding
controlled failure. The adapter hides registry reconciliation, source reload,
role resolution and canonical lineage construction behind this interface.

Adapters are registered in one static allowlist keyed by canonical domain.
There is no plugin discovery, entry point, dynamic import or import path stored
in data. One `SALES_RECORD` adapter is the only implementation in Step 52; the
small registry exists to enforce a closed dispatch rule, not to establish a
general plugin framework.

Financial arithmetic remains in `src.financial`. The adapter provides typed
canonical inputs to a Core-owned calculation function and never reproduces its
sum, coverage percentage, status or ordering rules.

## Typed request

Version 1.0 accepts a frozen data-only request with:

- `dataset_id`: a Phase 13 dataset identifier;
- `operation`: one value from the closed `SalesRecordOperation` enum;
- `missing_dimension`: `BUCKET` or `EXCLUDE`, applicable only to the grouped
  country operation and defaulting to `BUCKET`.

There are deliberately no request fields for raw SQL, expressions, callables,
module/class names, source paths, source column names, arbitrary grouping,
arbitrary measures or filters. Each operation fixes its grouping and measure.
Filtering and broader dynamic query binding belong to Step 53.

## Deterministic preconditions

Every operation requires all of the following:

1. the dataset identifier is valid and resolves to the current registry entry;
2. the entry has a valid registry schema and digest;
3. the entry is `REGISTERED` or is `BLOCKED` only because Financial Analysis has
   semantic/policy readiness but no activated execution path; `READY`, if
   introduced by a later authorized activation step, is also structurally
   eligible; a semantic/quality/policy-blocked dataset cannot bypass readiness;
4. the referenced profile and semantic mapping exist, have valid digests and
   exactly match the registry versions/digests;
5. the mapping remains `SEMANTICALLY_APPROVED` for `SALES_RECORD`;
6. the preserved source reloads through the Phase 13 safe ingestor, its bytes
   match the registered fingerprint and its ingestion run, sheet, ordered
   columns and row count reconcile with registry/profile facts;
7. canonical model version `1.0`, adapter version `1.0` and the current
   mapping version/digest are compatible;
8. every role required by the selected operation has exactly one confirmed
   source field with a matching stable column ID;
9. non-missing values of a required measure are exactly parseable as Decimal;
10. no conflict remains for a role required by the selected operation.

Lifecycle `BLOCKED` is not by itself sufficient: an approved current mapping
and coherent artifacts must still pass every check. `NEEDS_CONFIRMATION`,
`REJECTED`, stale artifacts and a semantically blocked mapping fail closed.
Unresolved semantics on a field unused by the selected operation do not block
that operation.

Canonicalization is operation-scoped. After the approved mapping is validated,
the adapter builds a canonical specification containing only the roles required
by the selected operation. It must not normalize a confirmed but unused field.
Consequently, an invalid `PROFIT` value cannot block record count, sales summary
or sales by country. This pruning changes neither the stored mapping nor the
meaning of any field; it only limits the execution view.

## Initial SALES_RECORD operations

Step 52 implements only this minimal vertical slice:

| Operation | Required operation roles | Result | Rationale |
|---|---|---|---|
| `SALES_RECORD_COUNT` | No field beyond approved `SALES_RECORD` identity | Count of registered source observations | Proves safe registry/source execution without inventing measure requirements. Phase 13 domain approval still independently requires `TRANSACTION_DATE` and `SALES`. |
| `SALES_SUMMARY` | `SALES` | Exact count and sum with measure coverage | Smallest useful monetary aggregation and direct analogue of the default sales measure in CF-02. |
| `SALES_BY_COUNTRY` | `SALES`, `COUNTRY` | Exact count/sum by source country label plus dimension and measure coverage | Smallest useful grouped slice and direct analogue of CF-04. |

The adapter does not require `PROFIT`, `DISCOUNT`, `UNITS_SOLD`, `SEGMENT`,
`PRODUCT` or a date merely because those roles can occur in `SALES_RECORD`.
Their missingness or unresolved meaning cannot affect these operations unless it
invalidates the approved domain itself.

Sales by period is deferred because it needs an explicit period/granularity
request contract and temporal quality policy. Segment/product grouping, profit,
units sold and discount analysis are deferred to avoid multiplying operations
before dynamic binding exists. Filters, ranking, ratios, margins, growth,
conversion and arbitrary measure selection are unsupported.

## Core calculation and result contract

The adapter result reuses the existing evidence concepts and status vocabulary:

- `status`, `result`, `currency`, `records`, `filter_diagnostics`, `quality`,
  `errors` and `metadata` retain their Financial Core meanings;
- monetary amounts and percentages are fixed-point Decimal strings, never
  binary floats;
- `records` reconciles `population`, `filtered_out`, `filter_unavailable`,
  `candidates`, `used`, `excluded` and exclusion reasons;
- measure coverage reconciles candidates, used, excluded and reasons;
- grouped results use deterministic source-label ordering, with an unavailable
  bucket last when requested;
- `quality` contains only findings relevant to the selected operation;
- `metadata.lineage` contains registry/artifact identity and per-record source
  references in the schema defined below;
- metadata identifies the adapter/canonical/mapping/registry versions and value
  basis without exposing a local path.

Normal success statuses are `SUCCESS`, `PARTIAL` and `NO_DATA`. A controlled
adapter failure maps validation outcome `UNSUPPORTED_OPERATION` to evidence
status `UNSUPPORTED`; every other validation failure maps to
`DATA_QUALITY_BLOCKER`. It leaves `result` unset and places the validation
outcome in `errors[0].code`. This is an additive source adapter for the same
evidence vocabulary, not a second incompatible evidence format.

Financial Core owns exact count/sum and coverage calculation. Step 52 may
extract a reusable calculation primitive from existing Core arithmetic but must
not change the 17 legacy contracts or their results.

## Currency

Currency is copied only from the approved current semantic mapping. `UNKNOWN`
produces a valid source-denomination monetary summary with the existing unknown-
currency disclosure. `CONFIRMED` carries its approved ISO code and mapping
evidence. Symbols, formatting, country labels and source column names never set
currency. `INFERRED` is accepted only if an approved onboarding contract later
supplies the code and evidence; Step 52 does not create that state.

A mapping with multiple confirmed denominations cannot be collapsed into one
scalar sum without a partition contract, so the initial monetary operations
validate as `QUALITY_BLOCKER` and execute returns an evidence envelope with
`status=DATA_QUALITY_BLOCKER` and `errors[0].code=QUALITY_BLOCKER`. Record count
remains non-monetary and has `currency` null.

## Missing data and quality

A blank canonical measure is missing, not zero. It is excluded from that
measure and appears in record/measure coverage with an explicit reason. A
nonblank value that cannot be represented as an exact Decimal is a quality
blocker; the adapter does not coerce or discard it.

For `SALES_BY_COUNTRY`, a missing country is either retained as the explicit
unavailable bucket (`BUCKET`) or excluded with a dimension reason (`EXCLUDE`).
Country labels remain exact source values: no translation, code conversion,
case folding or geographic inference occurs. Sorting is deterministic lexical
ordering of source values, with the unavailable bucket last.

Unknown currency is disclosed but does not make an exact source-denomination
sum partial. Relevant missing measure/dimension coverage does. Unused-field
findings are not promoted into blockers or warnings.

## Lineage

Every response carries this chain without an internal file path:

```text
dataset_id
  -> registry version/digest
  -> profile version/digest
  -> semantic mapping version/digest
  -> canonical model version
  -> canonical_record_id
  -> source sheet + source row number
```

Record references also state whether the record was used or excluded for the
selected operation and why. Canonical record IDs use the approved Phase 13
deterministic identity rule. Aggregation never replaces or obscures the source
row association.

The chain is stored at `metadata.lineage`:

```text
dataset_id
registry_version + registry_digest
profile_version + profile_digest
semantic_mapping_version + semantic_mapping_digest
canonical_model_version + canonical_spec_digest
source_fingerprint + source_sheet
records[]:
  canonical_record_id
  source_row_number
  participation = USED | EXCLUDED
  exclusion_reason = null | closed reason
```

For grouped results, each group additionally contains
`canonical_record_ids` in source-row order. These IDs reference the same
top-level lineage records rather than copying source values. The record-count
operation marks every source record `USED`; a summary excludes only records
missing `SALES`; country grouping first applies its dimension policy, then
measure availability. This makes aggregate-to-row traceability explicit and
bounded by the existing ingestion row limit.

## Version compatibility and stale state

The initial compatibility tuple is:

```text
adapter_version = 1.0
canonical_model_version = 1.0
registry_schema_version = 1.0
current semantic mapping version + digest = registry references
operation-scoped canonical spec digest = freshly derived from those exact inputs
```

`canonical_model_version` is the Phase 13 `CanonicalMappingSpec.version`; a
separately derived `canonical_spec_digest` seals its operation-scoped fields and
lineage policy. Adapter 1.0 accepts only canonical model 1.0, registry schema
1.0 and semantic mappings that pass the current Phase 13 mapping-schema/digest
loader. It does not use a numeric semantic-mapping version as a compatibility
shortcut.

Mapping version numbers alone are insufficient: the digest must match. Any
mapping correction, changed source fingerprint, profile/schema change or
unsupported canonical model version invalidates old execution assumptions.
Execution always resolves the current registry entry and never silently falls
back to an older artifact.

## Controlled failure model

Validation outcomes are closed values:

| Outcome | Meaning |
|---|---|
| `READY_FOR_EXECUTION` | All preconditions for this operation passed. |
| `UNSUPPORTED_OPERATION` | The operation/policy is outside the closed Step 52 interface. |
| `MISSING_SEMANTIC_FIELD` | A role required by this operation has no unique confirmed mapping. |
| `UNRESOLVED_SEMANTICS` | The approved domain or a required role is unresolved/conflicted. |
| `INVALID_REGISTRY` | Registry or referenced artifacts are corrupt, missing or inconsistent. |
| `SCHEMA_MISMATCH` | Reloaded source columns/rows do not match the approved profile/mapping. |
| `QUALITY_BLOCKER` | Required values cannot be safely calculated, including mixed confirmed denominations. |
| `STALE_MAPPING` | Current registry and mapping/profile/source versions or digests do not agree. |
| `DATASET_BLOCKED` | Lifecycle or domain state is not eligible for execution. |

Expected failures return fixed messages and never serialize raw exception text,
paths or source values. Unexpected programming defects remain developer errors;
they are not converted into successful evidence.

When more than one condition is observed, validation reports exactly one outcome
using this precedence (highest first):

1. `UNSUPPORTED_OPERATION` for a request outside the closed interface;
2. `INVALID_REGISTRY` when the current registry entry or an artifact cannot be
   authenticated/loaded at all;
3. `STALE_MAPPING` when individually valid current artifacts disagree in
   version, digest, fingerprint or registry reference;
4. `DATASET_BLOCKED` for an ineligible lifecycle or canonical domain;
5. `UNRESOLVED_SEMANTICS` for an unapproved mapping or required-role conflict;
6. `MISSING_SEMANTIC_FIELD` when an otherwise approved mapping lacks the role
   needed by the selected operation;
7. `SCHEMA_MISMATCH` when the reloaded ordered source schema/row population does
   not match the approved profile or role-to-column identity;
8. `QUALITY_BLOCKER` when compatible data cannot support safe arithmetic.

`validate` returns that outcome. `execute` preserves it as the first error code
and applies only the status mapping defined in the result section; no second
classification pass occurs.

## Privacy, security and scale

Execution is local, offline and deterministic. It invokes no LLM, provider,
network, SQL engine, shell, `eval`, `exec` or dynamic import. Dataset identifiers,
headers, sheet names, country labels and cell values are inert data and cannot
choose an adapter, attribute, function or operation. Dispatch uses enums and
closed maps owned by application code.

Step 52 inherits the ingestion bound of 100,000 rows and executes one selected
source plus its current artifacts at a time. It performs a linear pass and may
materialize the canonical records and result lineage once. No records are sent
to an LLM and no premature caching or concurrency abstraction is introduced.

## Semantic readiness is not execution readiness

This contract and the Step 52 adapter create directly testable execution
infrastructure only. They do not change `CapabilityDiscovery`, the manager
catalog, routing, intent mediation or conversational behavior. Financial
Analysis for onboarded datasets does **not** become globally `AVAILABLE`.

Step 53 owns dynamic query binding. Step 54 owns controlled capability
activation. Until those steps are separately authorized and completed, Phase
13 readiness continues to report onboarded Financial Analysis as blocked/not
implemented even when direct adapter tests pass.
