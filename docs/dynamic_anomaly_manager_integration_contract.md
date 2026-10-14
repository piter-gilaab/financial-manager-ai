# Dynamic anomaly Manager integration contract

Historical boundary note: this Step 64 contract did not extend conversational
candidate follow-up. Phase 17 Steps 68–69 later added that bounded route under
`conversational_dynamic_anomaly_contract.md`; the explicit Manager interface and
authority rules below remain unchanged.

## Scope and vocabulary

This contract activates explicit Manager execution for the two approved dynamic
anomaly operations and no others:

| Operation | Confirmed measure | Scope | Policy |
|---|---|---|---|
| `SALES_ANOMALY_SCREEN` | `SALES` | `GLOBAL` | `tukey_iqr` v1.0 |
| `PROFIT_ANOMALY_SCREEN` | supplied `PROFIT` | `GLOBAL` | `tukey_iqr` v1.0 |

A dynamic anomaly request contains only the exact Phase 13 `dataset_id` and one
closed operation. It cannot provide a source column, measure, formula, policy,
threshold, grouping, SQL, implementation or adapter. Filename, alias, recency,
fuzzy and natural-language dataset selection are not supported.

## Manager seam and authority

`FinancialManagerAgent.execute_dataset_anomaly_request(DynamicAnomalyRequest)`
is the sole new public Manager seam. It performs this sequence:

1. validate the typed closed request and exact dataset target;
2. recompute dataset/operation-specific anomaly readiness from current
   persisted artifacts;
3. refuse an operation whose current state is not `SUPPORTED`;
4. invoke the statically configured `DynamicAnomalyAdapter`;
5. let that adapter independently reauthenticate the current source, workflow,
   registry, profile, mapping, stable column identity and canonical records;
6. return the adapter result unchanged inside the existing dynamic Manager
   response envelope.

Readiness is therefore a current gate, not a stored authorization token. The
adapter remains authoritative if state changes between discovery and execution.
The Manager does not calculate quartiles, IQR, fences, sample eligibility or
record classifications and does not infer semantics or currency.

## Response and evidence

The method reuses `DynamicManagerResponse` version 1.1 because its schema and
field meanings do not change. `capability_status` remains the legacy/global
Manager registry availability for Anomaly Detection; `dataset_capability` is
the separately recomputed dynamic dataset projection. Successful and partial
execution preserves the complete adapter envelope as `delegated_result`,
including exact thresholds, reconciled counts, currency, quality disclosures,
ordered assessments, bounded candidate references, lineage and limitations.

When readiness blocks an operation, no screening result, threshold or
classification is fabricated. Invalid identifiers and operations receive
controlled data-only errors without paths, artifact payloads, Python details or
stack traces.

## Presentation and references

Manager presentation is deterministic and says only that records met the
statistical screening rule and are candidates for review under Tukey-IQR.
`CANDIDATE` never means fraud, error, suspicious activity, manipulation,
misconduct, illegality, business risk or probability of wrongdoing.

The adapter's existing candidate references are preserved losslessly. They are
dataset-scoped, deterministic, bounded to 20, non-executable and include only
actual `CANDIDATE` records with canonical/source lineage. Step 64 does not add a
second reference framework.

At the Step 64 checkpoint, the existing conversational follow-up mechanism was
not extended to dynamic anomaly evidence because it was coupled to legacy
evidence and natural-language `ask()` re-execution. Phase 17 Steps 68–69 later
added a separately validated fresh-evidence session path for this explicit
request/evidence shape. Callers can still inspect the authoritative ordered
assessments and candidate references in the explicit Manager response.

## Safety and compatibility

UNKNOWN denomination permits qualified source-denomination screening;
CONFIRMED preserves the approved ISO code; incompatible CONFIRMED_MULTIPLE
blocks scalar screening. No currency is inferred and no FX conversion occurs.

The method is local and deterministic. It adds no execution CLI, conversational
route, dynamic import, raw SQL, shell, subprocess, `eval`, `exec`, peer screen,
arbitrary measure/algorithm, external LLM, network service, telemetry or cloud
transmission. Legacy Receiver General and Company Financials anomaly execution,
the nine dynamic Financial Analysis operations, Forecasting and Document
Retrieval/RAG remain unchanged.
