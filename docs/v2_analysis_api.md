# V2 Phase 3 — Analysis and Anomaly API

Status: **IMPLEMENTED**.

`POST /api/v1/analysis` accepts exact `dataset_id`, one of the 27 frozen dynamic
financial operations and only compatible closed parameters: `MONTH|YEAR`,
`BUCKET|EXCLUDE` and strict `as_of_date` where applicable. It accepts no SQL,
formula, adapter, column, measure, filter or arbitrary grouping field.

All nine SALES_RECORD operations and all six operations each for PAYABLE,
RECEIVABLE and CASH_TRANSACTION delegate through `AnalysisApplication` to
`FinancialManagerAgent`. Aging/overdue still require the request date to equal
the approved dataset reference date. The response retains complete Manager
evidence, currency, coverage, exclusions, limitations, labels and lineage.

`POST /api/v1/anomalies` supports exactly `SALES_ANOMALY_SCREEN` and
`PROFIT_ANOMALY_SCREEN`. Scope/policy remain existing GLOBAL Tukey-IQR evidence.
`CANDIDATE` remains statistical selection for review, never fraud/risk scoring.

Representative tests compare serialized API evidence to direct Manager results
and exercise all 18 Phase 2 operations through HTTP.

