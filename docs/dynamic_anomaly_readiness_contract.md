# Dynamic anomaly readiness contract

## Scope

This contract activates dataset-scoped readiness for the Step 61 dynamic anomaly
catalog. It does not add Manager execution, conversational routing, an anomaly
execution CLI, peer screening or another measure/policy.

The complete catalog is:

| Operation | Domain | Confirmed measure | Scope | Policy |
|---|---|---|---|---|
| `SALES_ANOMALY_SCREEN` | `SALES_RECORD` | `SALES` | `GLOBAL` | `tukey_iqr` v1.0 |
| `PROFIT_ANOMALY_SCREEN` | `SALES_RECORD` | supplied `PROFIT` | `GLOBAL` | `tukey_iqr` v1.0 |

Each operation has one of the existing typed operation states: `SUPPORTED`,
`BLOCKED` or `UNSUPPORTED`.

## Readiness authority

`CapabilityDiscovery` is the sole dynamic readiness authority. For an approved
current `SALES_RECORD`, it invokes the statically registered
`DynamicAnomalyAdapter.validate(..., readiness_probe=True)` interface. The probe
authenticates the current workflow, registry, profile, mapping, source,
stable-column identity and canonical model; verifies the selected supplied role,
currency state and adapter/policy versions; and computes only reference
eligibility under exact arithmetic.

The probe does not publish, persist or cache fences or record classifications.
Readiness is recalculated from current artifacts and is never an authorization
token for later execution.

## Operation state

An operation is `SUPPORTED` only when all of the following are true:

- the canonical domain is currently approved `SALES_RECORD`;
- its one measure role is uniquely confirmed (`SALES` or supplied `PROFIT`);
- every authenticated artifact and stable column identity is current;
- the dynamic adapter and `tukey_iqr` v1.0 policy are compatible;
- currency is `UNKNOWN` or one valid `CONFIRMED` denomination;
- at least 30 selected measure values are usable exact decimals;
- the exact global IQR is positive; and
- precision-60 threshold arithmetic completes without an `Inexact` or `Rounded`
  condition.

An approved operation is `BLOCKED` when current semantics, artifacts, data,
currency or arithmetic prevent execution. Closed reasons include
`missing_confirmed_sales`, `missing_confirmed_profit`,
`insufficient_numeric_records`, `zero_iqr`, `exact_arithmetic_limit`,
`incompatible_currency` and authenticated adapter/artifact outcomes.

An operation is `UNSUPPORTED` when the domain is outside `SALES_RECORD` or the
compatible code-owned adapter/policy catalog is unavailable. There is no
arbitrary measure, algorithm, source column, class, function or grouping input.

## Capability state and independence

Dataset-scoped `ANOMALY_DETECTION` is `AVAILABLE_WITH_LIMITATIONS` when at least
one operation is `SUPPORTED`; it is `BLOCKED` when neither is executable. It is
never advertised as full anomaly coverage.

Sales and Profit readiness are evaluated independently after the shared
`SALES_RECORD` domain gate. Missing, unusable or zero-IQR Profit does not block
Sales. Missing, unusable or zero-IQR Sales does not block supplied Profit while
the existing canonical domain anchors remain approved. Revoking the confirmed
Sales or Transaction Date anchor invalidates the current domain and therefore
blocks both; Profit is never derived from Sales, COGS or another field.

UNKNOWN denomination permits qualified source-denomination screening.
CONFIRMED preserves the approved ISO code. CONFIRMED_MULTIPLE blocks both scalar
operations; readiness performs no inference, partition or FX conversion.

## Revocation and recovery

Every discovery call revalidates current persisted state. Readiness is revoked
when a required mapping is rejected or changed; source bytes, fingerprint,
sheet, schema, stable column identity, profile, mapping, workflow or registry
becomes stale; currency becomes incompatible; usable values fall below 30; IQR
becomes zero; exact arithmetic becomes infeasible; or the adapter/policy becomes
unavailable or incompatible.

Corrected approved state may recover only after a fresh evaluation. No previous
candidate decision, fence or readiness result participates in recovery.

## Presentation and boundaries

`python -m src.cli dataset capabilities <dataset_id>` and its `--json` form show
the capability state, the two operation states, controlled reasons and
limitations. They do not execute screening or expose candidate classifications.

The existing global Manager anomaly capability continues to describe the legacy
Receiver General/Company Financials service. This dataset projection remains
separate. This Step 63 readiness contract does not itself define Manager/evidence
execution; that later seam is governed by the Step 64 Manager integration
contract. Forecasting and Document Retrieval/RAG remain blocked.
