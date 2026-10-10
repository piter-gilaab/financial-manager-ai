# Phase 14 — Dynamic Query Binding contract

## Purpose and authority

Dynamic query binding is the deterministic association of an explicit
structured operation with one registered dataset and one statically registered
execution adapter. It answers: “Can this request be mapped to a known adapter
operation?” It does not decide that the capability is globally available and it
does not calculate a financial result.

The authority chain is:

```text
user or LLM
  -> structured intent
  -> dynamic query binder
  -> approved dataset registry
  -> static execution adapter
  -> Financial Core
  -> structured evidence
```

User or model text has no direct entry to this interface. A future interpreter
may propose an approved operation key and explicit dataset identifier, but the
binder validates both as inert data. The registry is authoritative for dataset
identity, canonical domain and approved mapping. The adapter remains
authoritative for exact execution preconditions. Financial Core remains
authoritative for arithmetic, coverage and result semantics.

The binder may:

- validate a typed, bounded request;
- resolve an exact registered `dataset_id` without fuzzy matching;
- read authenticated registry, profile and mapping metadata;
- resolve the registry-approved canonical domain;
- select a domain/operation pair from a closed catalog;
- validate only the semantic roles required by that operation;
- validate the operation's closed parameters;
- resolve an adapter through the Step 52 static registry;
- construct a typed adapter request and record the approved versions used;
- execute immediately through that adapter when explicitly called.

The binder must not infer meaning, currency, company identity, source columns or
financial facts. It must not load source rows merely to bind, aggregate values,
generate SQL, evaluate code, import modules dynamically, select Python objects
from request data, bypass adapter validation, route natural language, or change
capability readiness.

## Module and interface

`src.execution.binding` owns one small interface:

```text
DynamicQueryBinder.bind(DynamicQueryRequest) -> BindingResult
DynamicQueryBinder.execute(DynamicQueryRequest) -> structured evidence
```

`bind` performs metadata-only resolution and returns either one controlled
failure or a frozen `BoundExecutionRequest`. `execute` binds afresh and, only for
a successful result, passes the contained `AdapterExecutionRequest` to the
existing adapter. It returns the adapter evidence unchanged. Callers cannot
submit a prior bound object for execution, so a stale binding cannot bypass the
adapter's current registry/source validation.

Construction may receive an application-configured adapter resolver for testing
or composition. That dependency is trusted application configuration, like the
existing manager module injections; it is never populated from request,
registry, source or LLM data. The production default is Step 52's static
`adapter_for` allowlist.

## Typed request and parameters

Version 1.0 accepts a frozen data-only `DynamicQueryRequest` containing:

- `dataset_id`: an exact Phase 13 dataset identifier;
- `operation`: an approved `SalesRecordOperation` value or its exact public key;
- `parameters`: frozen `DynamicQueryParameters` with only optional
  `missing_dimension`.

There are no request properties for raw SQL, source paths, source columns,
Python expressions, callables, class/module/function names, arbitrary measures,
grouping, sorting, formulas, filters or aggregation names. Unknown request or
parameter shapes fail closed.

`missing_dimension` is accepted only for `SALES_BY_COUNTRY`. Its allowlist is
`BUCKET | EXCLUDE`; omission defaults to `BUCKET`. The count and summary
operations accept no parameter. Step 53 adds no filtering.

## Dataset and domain resolution

The identifier must satisfy the existing exact Phase 13 `dataset_id` shape
before any artifact path is formed. A malformed value is `INVALID_REQUEST`; a
well-formed identifier with no current workflow/registry entry is
`DATASET_NOT_FOUND`. There is no recency, alias, filename, free-text or fuzzy
resolution.

Resolution authenticates the current workflow and registry plus their referenced
profile and mapping. Their dataset, registry, profile, mapping, source
fingerprint, ingestion-run, source-type and source-sheet identities must agree.
Corrupt artifacts are `BINDING_BLOCKED`; valid artifacts with inconsistent
current pointers are `STALE_MAPPING`.

The canonical domain comes only from the registry and must agree with the
approved mapping. Version 1.0 supports only `SALES_RECORD`. Recognized domains
such as `ACCOUNTING_TRANSACTION`, `PAYABLE`, `RECEIVABLE` and
`CASH_TRANSACTION` return `UNSUPPORTED_DOMAIN`; they are never coerced to sales
records.

## Closed operation catalog

The entire binding catalog is:

| Canonical domain | Dynamic operation | Adapter operation | Required semantic roles | Parameters |
|---|---|---|---|---|
| `SALES_RECORD` | `SALES_RECORD_COUNT` | `SALES_RECORD_COUNT` | none beyond approved domain identity | none |
| `SALES_RECORD` | `SALES_SUMMARY` | `SALES_SUMMARY` | `SALES` | none |
| `SALES_RECORD` | `SALES_BY_COUNTRY` | `SALES_BY_COUNTRY` | `SALES`, `COUNTRY` | optional `missing_dimension` |

This catalog is code-owned and keyed by enum values. It never concatenates an
operation into a method/function name and never uses a request string with
`getattr`, an import facility or a registry-provided class name.

The meanings remain aligned with CF-01, CF-02 and CF-04 in
[`query_contracts.md`](query_contracts.md): imported observation count, exact
supplied Sales count/sum with coverage, and exact supplied Sales count/sum by
source country label with dimension/measure coverage. This alignment does not
assert that an onboarded source is the legacy Company Financials dataset.

## Required semantics and lifecycle

Binding checks the operation requirements only. `PROFIT`, `DISCOUNT`,
`UNITS_SOLD`, `SEGMENT`, `PRODUCT` and unused dates cannot block a supported
operation. A required role must have exactly one `CONFIRMED` mapping with the
current stable column identity. Missing or unresolved required roles return
`MISSING_REQUIRED_SEMANTICS` before source execution.

The mapping must remain `SEMANTICALLY_APPROVED` for the registry domain. Eligible
lifecycle states are the states admitted by the Step 52 contract. In the current
pre-activation state, `BLOCKED` is eligible only when persisted Financial
Analysis readiness is `BLOCKED_NOT_IMPLEMENTED` with semantic and policy
readiness both `READY`. This permits direct infrastructure testing without
pretending global execution readiness is available.

Binding does not reload or parse the full source. Exact fingerprint/schema/value
validation remains with the adapter at execution time.

## Bound execution request

A successful `BindingResult` contains a frozen, data-only
`BoundExecutionRequest` with:

- `binding_version`;
- `dataset_id` and registry-approved `canonical_domain`;
- the typed Step 52 `AdapterExecutionRequest`;
- registry version;
- semantic mapping version and digest;
- expected adapter and canonical-model versions.

It stores no adapter instance, callable, source path, source column, Python class
name or executable plan. The version fields describe what was bound; they do not
authorize later execution. `execute` resolves the current adapter again, checks
compatibility, and the adapter revalidates the live artifacts.

## Binder, adapter and Core responsibilities

| Layer | Question answered | Explicit non-authority |
|---|---|---|
| Binder | Can this structured request map to a known domain/operation/adapter? | No source parsing, arithmetic, semantic inference or activation |
| Adapter | Can this exact currently registered dataset safely execute now? | No financial business arithmetic or semantic revision |
| Financial Core | What is the authoritative exact result and coverage? | No dataset/adapter selection or language interpretation |

The deliberate repeated checks are shallow metadata validation in the binder
and authoritative full validation in the adapter. Binder success is not an
execution guarantee.

## Controlled failure model

Binding outcomes are closed values:

| Outcome | Meaning |
|---|---|
| `BOUND` | A typed adapter request was created. |
| `INVALID_REQUEST` | The request or dataset identifier is not the typed bounded shape. |
| `DATASET_NOT_FOUND` | A valid exact dataset identifier has no registered current state. |
| `UNSUPPORTED_DOMAIN` | The approved canonical domain has no Step 53 binding catalog. |
| `UNSUPPORTED_OPERATION` | The operation is outside the closed catalog for the domain. |
| `MISSING_REQUIRED_SEMANTICS` | An operation role is absent, duplicated, conflicted or not confirmed. |
| `INVALID_PARAMETER` | A parameter name/value is not allowed for the operation. |
| `ADAPTER_UNAVAILABLE` | The static registry has no compatible adapter for an otherwise supported binding. |
| `STALE_MAPPING` | Authenticated current artifact identities disagree. |
| `BINDING_BLOCKED` | Registry integrity, lifecycle, mapping approval or compatibility blocks binding. |

Normal failures use fixed messages and do not expose paths, Python types/classes,
stack traces, registry payloads or source values. Execution maps request errors to
`INVALID_REQUEST`, unsupported combinations to `UNSUPPORTED`, and integrity/
readiness failures to `DATA_QUALITY_BLOCKER`. Successful execution returns the
adapter evidence without rewriting its status, result, currency, quality,
coverage, metadata or errors.

Failure precedence is request shape, dataset existence/integrity, stale current
identities, lifecycle/mapping approval, domain, operation, parameters, required
roles, then adapter availability/version compatibility. The adapter applies its
own Step 51 precedence after binding succeeds.

## Lineage and evidence

The binder adds no source lineage and fabricates no financial evidence. A
successful `execute` response is the existing adapter response, so its
`metadata.lineage` continues to preserve dataset, registry, profile, mapping,
canonical specification, source fingerprint, canonical-record and source-row
identities. Binding failures contain no source paths or internal artifacts.

## Privacy, security and performance

Binding and execution remain local, deterministic and independent of an LLM or
network. Dataset IDs, operation strings and parameter strings are data. Path-like
IDs, import-shaped operations and SQL-shaped policies cannot choose filesystem
locations, modules, attributes, functions or commands.

The binder uses no `eval`, `exec`, subprocess, shell, SQL, dynamic import or
untrusted `getattr`. It authenticates only bounded registry metadata during
`bind`; source loading and linear record processing occur only after explicit
`execute`, inside the existing bounded adapter.

## Step 53 activation boundary

Step 53 itself did not change Phase 13 `CapabilityDiscovery`, the manager capability
registry, `FinancialManagerAgent`, top-level routing, the Financial Analysis
Agent, mediation catalogs, prompts, CLI behavior or conversation state.
At its validation point, onboarded Financial Analysis therefore remained
`BLOCKED_NOT_IMPLEMENTED` with `execution_readiness=BLOCKED`. Step 54 subsequently
uses this binder as an authority for dataset-specific activation; it does not
alter the Step 53 binding contract. Step 55 end-to-end validation remains outside
this contract.
