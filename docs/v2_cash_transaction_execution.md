# V2 Phase 2 — CASH_TRANSACTION Execution

Status: **IMPLEMENTED**.

The approved anchors are `TRANSACTION_DATE`, `AMOUNT` and `CASH_DIRECTION`.
Direction must be completely mapped to `INFLOW | OUTFLOW`; sign never establishes
or changes direction. Monetary operations require one approved convention:

- `MAGNITUDE_WITH_DIRECTION`: non-negative source magnitude plus direction;
- `SIGNED_WITH_DIRECTION`: non-negative inflow and non-positive outflow, with
  Core-derived non-negative magnitudes and preserved source signs.

Convention contradictions are excluded or block minimum-data readiness; they are
never repaired by guessing.

The exact catalog is:

1. `CASH_TRANSACTION_COUNT`
2. `CASH_INFLOW_SUMMARY`
3. `CASH_OUTFLOW_SUMMARY`
4. `NET_CASH_BY_PERIOD`
5. `CASH_BY_CATEGORY`
6. `CASH_BY_ACCOUNT`

Financial Core exclusively computes `net_cash = inflow_magnitude -
outflow_magnitude`. Period is observed history with `MONTH | YEAR`, not a
forecast. Category and account are confirmed labels used only for grouping.
