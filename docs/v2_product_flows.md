# Financial Manager AI V2 — Frozen Product Flows

Status: **IMPLEMENTED AND VALIDATED — PHASE 4 COMPLETE**.

## 1. First local use

1. User starts the separately implemented local API and web workspace.
2. Workspace checks `/api/v1/health` and loads safe capabilities/datasets.
3. If no ready dataset exists, Overview directs the user to Dataset Onboarding.
4. No sample, provider, cloud account or automatic download is required.

The UI does not start either process automatically in Phase 1 and this flow is
not an authorization to implement startup tooling before its roadmap phase.

## 2. Dataset onboarding

1. User selects one `.csv` or `.xlsx` up to 10 MiB and optional sheet/provenance
   note.
2. API streams it to temporary storage and calls the existing safe ingestion
   pipeline.
3. UI displays deterministic profile, warnings and safe examples/patterns.
4. UI displays semantic suggestions as unconfirmed.
5. User explicitly confirms/corrects/rejects roles and supplies evidence.
6. User supplies complete closed critical mappings/qualifiers where required.
7. User explicitly approves one canonical domain.
8. API recomputes readiness for every domain operation.
9. UI shows supported/blocked/unsupported operations and exact limitations.
10. “Analyze” is enabled only for a currently supported operation.

At no point does upload, profile or suggestion silently create financial
authority.

## 3. Dataset inspection and remediation

1. User selects an exact dataset ID from Datasets.
2. Detail shows current domain, mapping versions, currency, quality and
   operation readiness.
3. A blocked operation identifies missing role/mapping/qualifier, currency,
   stale artifact or data-quality reason.
4. If the issue is semantically remediable, user records a new explicit decision.
5. Readiness is recomputed; old readiness is never reused.

The UI cannot “force run” a blocked operation.

## 4. Structured Financial Analysis

1. User selects an exact dataset.
2. UI retrieves current supported operations.
3. User selects one operation and only its closed parameters.
4. API delegates through application/Manager/readiness/binder/adapter/Core.
5. UI receives complete structured evidence.
6. UI renders exact values, currency, coverage, limitations, quality and lineage.

Examples:

- `PAYABLE_SUMMARY`: no free-form grouping/filter.
- `RECEIVABLE_AGING`: explicit `as_of_date` matching the approved dataset
  reference date; no implicit today or reconstructed historical state.
- `NET_CASH_BY_PERIOD`: `MONTH|YEAR`; net is returned by Core.
- `SALES_BY_COUNTRY`: unchanged V1 dynamic operation.

## 5. Existing anomaly screening

1. User selects a ready `SALES_RECORD` dataset.
2. UI lists only ready Sales/Profit anomaly operations.
3. User runs one exact operation; no algorithm/threshold/measure selector exists.
4. UI presents “Statistical candidates for review,” policy/fences/coverage and
   candidate evidence.
5. User may request `why_selected` or bounded `record_detail` using an issued
   reference; API/session revalidates fresh evidence.

No payable, receivable or cash anomaly screen is offered.

## 6. Conversation

1. Chat creates one process-local session.
2. User selects or names an exact eligible dataset, or receives clarification.
3. A turn is mediated to a closed operation only.
4. Manager executes under current readiness and returns structured evidence.
5. Chat renders evidence plus grounded prose.
6. Reset/cancel/expiry clears the corresponding context; process restart creates
   a new session.

Unsupported language or blocked readiness produces a controlled state, not a
fallback calculation.

## 7. Currency states

- `UNKNOWN`: UI shows the mandatory unverified source-denomination limitation
  next to values/charts.
- `CONFIRMED`: UI shows the approved ISO code and no-conversion state.
- `CONFIRMED_MULTIPLE`: UI disables monetary execution and displays the blocker;
  record count may remain available.

No UI control guesses currency or enables FX.

## 8. Stale/change flow

1. Current source/schema/mapping no longer matches authenticated artifacts.
2. Readiness/execution returns a stable stale/blocker code.
3. UI stops analysis, clears result-as-current indicators and links to dataset
   remediation.
4. Only a fresh approved artifact/mapping/readiness path can restore support.

The prior result may remain visibly labeled historical in current page memory,
but cannot authorize a new execution.

## 9. No-data and known errors

`NO_DATA` is a valid completed analysis with no eligible records and distinct
from a blocked operation. Known unsupported, missing-role, multiple-currency,
data-quality, provider and session states display their specific code and safe
message. Unexpected 500 responses use a generic safe message only.
