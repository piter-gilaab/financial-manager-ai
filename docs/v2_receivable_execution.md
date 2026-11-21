# V2 Phase 2 — RECEIVABLE Execution

Status: **IMPLEMENTED**.

The approved anchors are `AMOUNT` and `DUE_DATE`. `CUSTOMER` is a distinct role
required only by customer grouping; `SUPPLIER` and `ENTITY` never substitute for
it. Aging/overdue use the same explicit status, outstanding-balance and reference
state gates as PAYABLE.

The exact catalog is:

1. `RECEIVABLE_COUNT`
2. `RECEIVABLE_SUMMARY`
3. `RECEIVABLE_BY_CUSTOMER`
4. `RECEIVABLE_BY_DUE_PERIOD`
5. `RECEIVABLE_AGING`
6. `OVERDUE_RECEIVABLE_SUMMARY`

The five aging buckets and strict overdue rule are identical only where the
obligation mechanics are equivalent. No revenue, receipt, supplier or generic
entity meaning is inferred from a receivable.
