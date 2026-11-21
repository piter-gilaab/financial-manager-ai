# V2 Phase 2 — PAYABLE Execution

Status: **IMPLEMENTED**.

The approved anchors are `AMOUNT` and `DUE_DATE`. `SUPPLIER` is required only by
supplier grouping. Aging and overdue additionally require confirmed `STATUS`
with a complete `OPEN | SETTLED | CANCELLED` mapping,
`amount_basis=OUTSTANDING_BALANCE`, an approved `dataset_reference_date` and an
equal explicit request `as_of_date`.

The exact catalog is:

1. `PAYABLE_COUNT`
2. `PAYABLE_SUMMARY`
3. `PAYABLE_BY_SUPPLIER`
4. `PAYABLE_BY_DUE_PERIOD`
5. `PAYABLE_AGING`
6. `OVERDUE_PAYABLE_SUMMARY`

Summary and grouped source-amount evidence preserve zero and negative values.
Missing dimensions use the closed `BUCKET` default or explicit `EXCLUDE`.
Due-period grouping accepts only `MONTH` or `YEAR`.

Aging contains all five frozen buckets in order. Only positive open outstanding
balances with valid due dates participate. Settled, cancelled, missing/invalid
and non-positive records are separately accounted. Overdue is strictly
`due_date < as_of_date`; due today is not overdue. No present state is projected
to an arbitrary historical date.
