# Step 02 Validation — Multi-Domain Semantic & Query Contracts

Status: **PASS — CONTRACT ONLY**.

## Repository comparison

- V1 ontology uses shared `AMOUNT`, date, dimension, `STATUS` and
  `CASH_DIRECTION` roles; it does not use domain-prefixed amount roles.
- V1 already requires complete explicit `CASH_DIRECTION -> INFLOW|OUTFLOW`
  value mapping and never derives cash direction from DR/CR or sign.
- V1 `PAYABLE` recognition required invoice, supplier, due date, amount and
  status but had no adapter. V2 safely refines domain anchors to amount/due date
  and moves supplier/status to operation-specific gates.
- V1 `RECEIVABLE` and `CASH_TRANSACTION` were recognized but could not become
  semantically approved/executable under domain-specific minimums.
- V1 readiness/binder/adapter flow already supports current per-operation
  `SUPPORTED | BLOCKED | UNSUPPORTED` semantics and repeated integrity checks.
- V1 monetary dynamic execution permits `UNKNOWN` with disclosure, permits one
  `CONFIRMED` currency and blocks incompatible `CONFIRMED_MULTIPLE` aggregation.

## Decisions frozen

1. Reuse `AMOUNT` for all three domains; add only `CUSTOMER` to the role ontology.
2. Domain anchors are `AMOUNT+DUE_DATE` for payable/receivable and
   `TRANSACTION_DATE+AMOUNT+CASH_DIRECTION` for cash.
3. Aging/overdue require complete `OPEN|SETTLED|CANCELLED` status mapping,
   `OUTSTANDING_BALANCE` amount basis and an approved dataset reference date.
4. Aging requires explicit `as_of_date` equal to that approved reference date;
   machine current date and historical reconstruction are never used.
5. Buckets are `NOT_DUE`, `OVERDUE_1_30`, `OVERDUE_31_60`,
   `OVERDUE_61_90`, `OVERDUE_91_PLUS` with due-on-date in `NOT_DUE`.
6. Cash requires complete direction mapping plus one explicit amount convention;
   sign never determines direction.
7. `CONFIRMED_MULTIPLE` blocks monetary operations because V2 has no FX or
   currency-partition contract.
8. Query catalogs contain exactly six operations per new domain.
9. No payable/receivable/cash anomaly operation enters mandatory V2.

## Scenario review

| Scenario | Frozen outcome |
|---|---|
| Invoice due before reference date but status maps `SETTLED` | Not overdue; excluded from open aging. |
| Partially settled invoice with original invoice amount | Aging/overdue blocked unless amount is confirmed remaining balance. |
| Due exactly on reference date | `NOT_DUE`. |
| Requested date differs from approved dataset reference date | Operation blocked with `reference_date_mismatch`. |
| Missing/invalid due date | Excluded with coverage; never assigned an aging bucket. |
| Open zero/negative balance | Excluded as `non_positive_open_balance`; no invented credit/settlement meaning. |
| Cash amount `-100` with source direction `IN` | Invalid under both approved conventions; direction is not rewritten from sign. |
| Multiple confirmed currencies | Count supported; monetary operations blocked. |
| Unknown currency | Qualified source-denomination result with no inferred code/FX. |
| Customer column proposed as generic `ENTITY` | Does not unlock `RECEIVABLE_BY_CUSTOMER`; explicit `CUSTOMER` confirmation required. |

## Consistency and scope checks

- All operation inputs, outputs, required roles, value mappings, date/currency
  gates, minimum conditions and missing-value behavior are specified.
- Summary/due-period operations describe source amounts and do not claim open
  exposure; only aging/overdue use confirmed outstanding balances.
- No false payable/receivable symmetry substitutes customer for supplier.
- Net cash arithmetic is explicitly assigned to Financial Core.
- No arbitrary query language, new adapter, source code, test, dependency or
  anomaly algorithm was created.

Step 02 is sufficient to define the application/API transport in Step 03.
