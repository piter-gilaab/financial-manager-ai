# Financial Manager AI V2 — Final Scope Freeze

Status: **FROZEN V2.0.0 RELEASE-CANDIDATE SCOPE** (2026-11-22).

This is the current product-scope authority. Phase 5 release remediation may fix
defects inside this boundary, but V2 is not a final release until the remediation
audit and release gates pass.

V2 is the local-first, multi-domain financial analysis platform implemented by
the repository. It safely onboards approved CSV and constrained XLSX datasets,
requires explicit financial-semantic confirmation, recomputes operation-specific
readiness, and delegates closed requests to deterministic financial/statistical
authorities. The same evidence is projected through CLI-compatible workflows,
the Application Layer, local FastAPI `/api/v1`, the Web Financial Workspace and
optional local conversational mediation.

## Frozen executable domains and surfaces

- `SALES_RECORD`
- `PAYABLE`
- `RECEIVABLE`
- `CASH_TRANSACTION`

Surfaces: CLI, Application Layer, FastAPI `/api/v1`, Web Financial Workspace and
optional process-local conversation. Legacy Receiver General and Company
Financials remain frozen V1 snapshot paths, not generic V2 domains.

## Frozen financial catalogs

| Domain | Operations |
|---|---|
| `SALES_RECORD` (9) | `SALES_RECORD_COUNT`, `SALES_SUMMARY`, `SALES_BY_COUNTRY`, `SALES_BY_PERIOD`, `SALES_BY_SEGMENT`, `SALES_BY_PRODUCT`, `PROFIT_SUMMARY`, `DISCOUNT_ANALYSIS`, `UNITS_SOLD_SUMMARY` |
| `PAYABLE` (6) | `PAYABLE_COUNT`, `PAYABLE_SUMMARY`, `PAYABLE_BY_SUPPLIER`, `PAYABLE_BY_DUE_PERIOD`, `PAYABLE_AGING`, `OVERDUE_PAYABLE_SUMMARY` |
| `RECEIVABLE` (6) | `RECEIVABLE_COUNT`, `RECEIVABLE_SUMMARY`, `RECEIVABLE_BY_CUSTOMER`, `RECEIVABLE_BY_DUE_PERIOD`, `RECEIVABLE_AGING`, `OVERDUE_RECEIVABLE_SUMMARY` |
| `CASH_TRANSACTION` (6) | `CASH_TRANSACTION_COUNT`, `CASH_INFLOW_SUMMARY`, `CASH_OUTFLOW_SUMMARY`, `NET_CASH_BY_PERIOD`, `CASH_BY_CATEGORY`, `CASH_BY_ACCOUNT` |

The V2 multi-domain addition is exactly 18 operations. No operation was added in
Phase 5.

## Frozen anomaly catalog

Exactly `SALES_ANOMALY_SCREEN` and `PROFIT_ANOMALY_SCREEN`: GLOBAL, two-sided
Tukey-IQR v1.0, minimum 30 usable values, positive IQR, candidate-only language.

## Deferred, not implemented

Cash Flow Forecasting; Financial Document RAG; new anomaly domains; peer/dynamic
anomaly algorithms; ML anomaly detection; fraud detection/scoring; arbitrary SQL,
formulas, grouping or financial query DSL; banking/payment execution; ERP
integrations; authentication; users/organizations; multitenancy; SaaS;
PostgreSQL migration; cloud storage; additional external LLM providers; mobile.

Blocked Forecasting/document intents in the legacy conversational catalog are
harmless negative-capability metadata: they return controlled unavailability and
do not activate a route, handler or execution module. No accidental executable
scope was found.

## Change policy

V2.0.0 is closed. Future work requires separate approval and belongs to V2.x or
V3. Recognition, documentation or an issue does not authorize implementation.
