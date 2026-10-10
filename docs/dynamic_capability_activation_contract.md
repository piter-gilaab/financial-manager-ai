# Phase 14 — Dynamic Capability Activation contract

## Purpose and authority

Dynamic capability activation is the deterministic, dataset-specific projection
of which approved onboarded operations can execute now. It is not a global
feature flag and it is not an LLM judgment. The authority chain is:

```text
source data
  -> approved Phase 13 semantics and registry
  -> operation-level capability readiness
  -> Step 53 dynamic query binder
  -> Step 52 static adapter
  -> Financial Core
  -> structured evidence
  -> Financial Manager
  -> optional presentation
```

The registry and approved mapping own dataset/domain meaning. The binder owns
structured dataset/operation association. The adapter owns current source,
schema, mapping and execution preconditions. Financial Core owns arithmetic,
coverage, ordering and result status. Capability discovery calls those existing
authorities; it does not recreate their rules or calculate financial facts.

## Dataset-specific capability model

The existing Phase 13 `ReadinessReport` remains the dataset capability model.
Version 1.1 adds:

- approved currency state/code disclosure;
- operation-level readiness within Financial Analysis;
- the state `AVAILABLE_WITH_LIMITATIONS` for a dataset with at least one
  validated dynamic operation but not the full legacy Financial Analysis set.

Each operation is `SUPPORTED`, `BLOCKED` or `UNSUPPORTED` and records its fixed
required semantic roles plus controlled reasons. `AVAILABLE_WITH_LIMITATIONS`
is derived when at least one candidate operation is `SUPPORTED`; it is never
stored as an independent manual Boolean. A report with no available capability
remains blocked under the existing registry lifecycle model.

This dataset readiness does not replace the legacy built-in manager catalog.
Legacy Company Financials and Receiver General Financial Analysis remain
`AVAILABLE` through their existing path. The new state describes only one
explicitly identified onboarded dataset.

## Activation conditions

Financial Analysis becomes `AVAILABLE_WITH_LIMITATIONS` only after all common
conditions and at least one operation-specific condition pass:

1. exact dataset identity resolves through an authenticated workflow;
2. current registry, profile and mapping artifacts pass digest/identity checks;
3. lifecycle and mapping state permit direct execution;
4. the approved canonical domain is exactly `SALES_RECORD`;
5. the production static registry resolves a version-compatible adapter;
6. Step 53 binds the exact domain/operation pair and parameters;
7. required roles are uniquely confirmed with their stable column identity;
8. the Step 52 adapter validates current preserved source fingerprint, schema,
   row population, canonicalization, currency eligibility and quality gates;
9. no dataset-level blocker invalidates that operation.

Semantic readiness or the `SALES_RECORD` label alone is insufficient. Readiness
is recomputed from current authenticated artifacts. Capability inspection does
not trust a previously persisted `AVAILABLE_WITH_LIMITATIONS` state as current
proof. A changed readiness projection is persisted as a new append-oriented
registry version and matching workflow state; an identical projection is a
no-op. An integrity failure yields a controlled all-blocked report without paths
or registry payloads.

## Closed operation readiness

The only candidate catalog is unchanged from Steps 52–53:

| Operation | Required semantics | Parameters | UNKNOWN currency |
|---|---|---|---|
| `SALES_RECORD_COUNT` | approved `SALES_RECORD`; no additional role | none | supported |
| `SALES_SUMMARY` | `SALES` | none | supported with source-denomination disclosure |
| `SALES_BY_COUNTRY` | `SALES`, `COUNTRY` | `missing_dimension=BUCKET|EXCLUDE` | supported with source-denomination disclosure |

An absent or revoked `COUNTRY` mapping blocks only `SALES_BY_COUNTRY`. Count and
summary remain eligible when the approved domain and their own requirements
remain valid. Revoking required `SALES` makes the Phase 13 domain mapping no
longer approved; under the existing domain contract, all execution is then
blocked until semantics are approved again.

`AVAILABLE_WITH_LIMITATIONS` always discloses that period, product, segment,
profit, discount and units-sold analysis, arbitrary filters/groupings/sorting,
and fuzzy dataset selection are unavailable. It never means parity with the 17
legacy Company Financials contracts.

## Recalculation and revocation

Capability discovery binds and invokes adapter validation for each candidate
operation. A trusted readiness-probe mode may inspect a previously blocked
dataset but cannot execute it; normal binder/adapter execution gates remain
closed. The probe performs no aggregation. A current source/schema mismatch,
mapping revision/rejection, artifact mismatch, adapter removal/incompatibility,
or operation removal changes the live projection to `BLOCKED` as appropriate.
Restoration requires the same deterministic checks to pass again; no sticky
availability token survives an incompatible change.

Phase 13 records the readiness projection when an approved mapping is
registered. Before that probe, the workflow is moved to the authenticated
`REGISTERED` transition so the binder never bypasses cross-artifact identity
checks. Later capability inspection recomputes current readiness. The adapter
also revalidates at execution time, closing the interval between inspection and
execution.

## Manager integration and routing boundary

`FinancialManagerAgent.execute_dataset_request(DynamicQueryRequest)` is the only
new Manager entry point. It accepts the existing frozen Step 53 request with an
exact `dataset_id`, allowlisted operation and bounded parameters. It delegates
unchanged to `DynamicQueryBinder.execute`, validates only the returned data
envelope, and wraps the existing adapter/Core evidence. It contains no source
mapping, financial arithmetic, adapter selection or currency logic.

The dynamic response uses Manager envelope version 1.1. Its existing
`capability_status` continues to describe the legacy Manager registry
(`FINANCIAL_ANALYSIS=AVAILABLE`); the separate `dataset_capability` field carries
the exact dataset's state, operation list, currency, domain and limitations. The
Manager refreshes this dataset projection before attempting execution.

The existing `execute`, `plan`, `ask`, session, mediation catalog, prompts and
natural-language routes are unchanged. They never select an onboarded dataset.
There is no filename, recency, alias, “latest file” or fuzzy selection. Step 54
therefore activates explicit structured Manager execution, not conversational
dataset discovery.

## Currency and evidence

Currency is copied from approved mapping metadata as `CONFIRMED` plus its code,
or `UNKNOWN` with no code. Country, symbols, formatting and column names never
infer currency. UNKNOWN does not block count or source-denomination sales
results because the existing adapter evidence gives the required disclosure.

The Manager preserves the complete adapter/Core result beneath
`delegated_result`, including exact Decimal strings, record accounting,
coverage, quality, registry/mapping/source identities and source-row lineage.
Capability discovery creates no financial evidence or lineage.

## Controlled failures and security

Malformed IDs/requests, unknown datasets, unsupported domains/operations,
missing roles, invalid parameters, stale/corrupt artifacts and unavailable
adapters remain controlled outcomes. User-facing reports and Manager responses
do not include filesystem paths, Python class names, registry payloads or stack
traces.

Dataset IDs, operation strings and parameters are inert data. Production
resolution remains the Step 52 static map. There is no `eval`, `exec`, SQL,
shell, subprocess, dynamic import, untrusted `getattr`, user-selected adapter or
LLM-selected implementation. Capability discovery is local, deterministic and
requires no network, model or provider.

## Explicitly unchanged capabilities

- Dynamic Anomaly Detection remains `BLOCKED`; no approved dynamic screening
  adapter/policy exists.
- Cash Flow Forecasting remains `BLOCKED`; sales are not actual cash and none of
  its data/model/holdout/currency gates are weakened.
- Document Retrieval remains `BLOCKED`; a tabular dataset is not a governed
  document corpus.
- Recognized `ACCOUNTING_TRANSACTION`, `PAYABLE`, `RECEIVABLE`,
  `CASH_TRANSACTION` and other domains have no dynamic execution adapter and are
  never coerced to `SALES_RECORD`.

## CLI and Step 55 boundary

The existing `python -m src.cli dataset capabilities <dataset_id>` command now
shows canonical domain, currency and supported/unavailable dynamic operations.
No new CLI execution command is added in Step 54: the typed Python Manager entry
is the narrow activation surface, and an end-to-end CLI execution workflow is a
Step 55 validation/design decision.

Step 54 adds no new SALES_RECORD operation, filter, grouping, API, frontend,
Forecasting, RAG, AP/AR logic or conversational route. Step 55 is not implemented
by this contract.
