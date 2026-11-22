# V2 Phase 4 — Financial Analysis Workspace

`/analysis` is a control/result workspace rather than a KPI gallery. Dataset
selection uses exact registered IDs. The operation selector is populated from
dataset readiness and keeps blocked operations visible with backend reasons.

Closed controls are rendered only where supported:

- `MONTH | YEAR` period granularity;
- `BUCKET | EXCLUDE` missing-dimension policy; and
- explicit ISO `as_of_date` for aging/overdue operations.

The result module renders exact summary evidence, group/bucket tables,
presentation-only bars, coverage, backend limitations and safe technical
lineage. `Decimal` strings remain unchanged in metrics, tables and chart
tooltips. Only `lib/evidence.ts::toChartData` converts one already-calculated
string to a JavaScript number for chart geometry; it never reduces, sums,
averages or produces a displayed financial result.

The same renderer adapts to SALES_RECORD, PAYABLE, RECEIVABLE and
CASH_TRANSACTION evidence. Unknown denomination, confirmed ISO currency and
mixed confirmed currency remain distinct.
