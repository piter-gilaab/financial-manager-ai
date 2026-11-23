# Financial Manager AI V2 — Closed Query Catalog

Status: **FROZEN CONTRACT — IMPLEMENTED; CATALOG CLOSED**.

This catalog is exhaustive for the three new V2 executable domains. The nine V1
`SALES_RECORD` Financial Analysis operations remain unchanged and are not
duplicated here.

## Common request and evidence rules

Every request contains exactly `dataset_id`, one operation identifier and only
the operation parameters listed below. Unknown fields and misplaced parameters
are `INVALID_REQUEST`. Domain/operation mismatch is `UNSUPPORTED`.

Every response preserves the existing evidence shape concepts:

- `status`: `SUCCESS | PARTIAL | NO_DATA | INVALID_REQUEST | UNSUPPORTED |
  DATA_QUALITY_BLOCKER`;
- operation and dataset identity;
- `result` with all monetary/decimal values serialized as base-10 strings;
- record and measure coverage, exclusion reasons and missing/invalid counts;
- currency state/code/basis and `conversion_applied=false` where monetary;
- quality warnings and limitations;
- source/artifact/profile/mapping/registry/adapter/catalog lineage; and
- controlled errors without internal paths.

Summary statistics are the closed set `count`, `sum`, `mean`, `median`, `min`,
`max`. They use exact Core arithmetic and V1 rounding rules for derived means.
Missing/invalid measures are excluded and disclosed, never replaced by zero.

Grouped results contain ordered `groups`; each group has a source or unavailable
key, `record_count`, exact measures and coverage. The only missing-dimension
policy is `BUCKET | EXCLUDE`, default `BUCKET`. The only period granularity is
`MONTH | YEAR`, default `MONTH`.

`UNKNOWN` currency permits a qualified source-denomination result;
`CONFIRMED` permits the approved single currency; `CONFIRMED_MULTIPLE` blocks
all monetary operations. Record-count operations are currency-independent.

## PAYABLE catalog

The exact catalog is:

1. `PAYABLE_COUNT`
2. `PAYABLE_SUMMARY`
3. `PAYABLE_BY_SUPPLIER`
4. `PAYABLE_BY_DUE_PERIOD`
5. `PAYABLE_AGING`
6. `OVERDUE_PAYABLE_SUMMARY`

### Operation contracts

| Operation | Inputs | Required semantics/mappings | Result | Missing/value behavior |
|---|---|---|---|---|
| `PAYABLE_COUNT` | none | approved `PAYABLE` domain | `record_count` of authenticated source records | Counts records even when optional fields are missing; no monetary aggregation/currency. |
| `PAYABLE_SUMMARY` | none | `AMOUNT` | exact amount statistics and coverage over all source records | Missing/invalid amounts excluded and disclosed. Amount is labeled source payable amount, not open balance. |
| `PAYABLE_BY_SUPPLIER` | `missing_dimension=BUCKET|EXCLUDE` | `AMOUNT`, `SUPPLIER` | ordered supplier groups with record count, exact amount statistics and coverage | Missing supplier follows policy; missing/invalid amount excluded per measure. |
| `PAYABLE_BY_DUE_PERIOD` | `granularity=MONTH|YEAR`; `missing_dimension=BUCKET|EXCLUDE` | `AMOUNT`, `DUE_DATE` with approved format | ordered due-period groups with record count, exact amount statistics and coverage | Missing/invalid due date follows dimension policy; missing/invalid amount excluded. Population is all source records, not inferred open exposure. |
| `PAYABLE_AGING` | required `as_of_date=YYYY-MM-DD`, equal to approved dataset reference date | `AMOUNT`, `DUE_DATE`, `STATUS`; complete settlement map; `amount_basis=OUTSTANDING_BALANCE`; approved `dataset_reference_date` | all five frozen buckets in order, each with open-record count, exact balance sum and coverage; excluded-status/value counts | Only eligible positive `OPEN` balances bucketed. Missing/invalid due date/amount and non-positive balances excluded/disclosed; settled/cancelled separated. |
| `OVERDUE_PAYABLE_SUMMARY` | required `as_of_date=YYYY-MM-DD` | same as aging | `open_record_count`, `overdue_record_count`, exact overdue balance statistics, coverage and exclusions | Overdue means eligible `OPEN`, positive outstanding balance and `due_date < as_of_date`. Due-on-date is not overdue. |

Minimum data: count is supported for an authenticated approved dataset, summary
and groups require at least one valid operation measure to be executable, and
aging/overdue require at least one record that can be deterministically assessed
under the approved reference-state contract. A valid population with zero
matching overdue records returns `NO_DATA`, not a readiness invention.

## RECEIVABLE catalog

The exact catalog is:

1. `RECEIVABLE_COUNT`
2. `RECEIVABLE_SUMMARY`
3. `RECEIVABLE_BY_CUSTOMER`
4. `RECEIVABLE_BY_DUE_PERIOD`
5. `RECEIVABLE_AGING`
6. `OVERDUE_RECEIVABLE_SUMMARY`

### Operation contracts

| Operation | Inputs | Required semantics/mappings | Result | Missing/value behavior |
|---|---|---|---|---|
| `RECEIVABLE_COUNT` | none | approved `RECEIVABLE` domain | `record_count` of authenticated source records | Counts records even when optional fields are missing; no monetary aggregation/currency. |
| `RECEIVABLE_SUMMARY` | none | `AMOUNT` | exact amount statistics and coverage over all source records | Missing/invalid amounts excluded and disclosed. Amount is labeled source receivable amount, not open balance. |
| `RECEIVABLE_BY_CUSTOMER` | `missing_dimension=BUCKET|EXCLUDE` | `AMOUNT`, `CUSTOMER` | ordered customer groups with record count, exact amount statistics and coverage | Missing customer follows policy; missing/invalid amount excluded per measure. |
| `RECEIVABLE_BY_DUE_PERIOD` | `granularity=MONTH|YEAR`; `missing_dimension=BUCKET|EXCLUDE` | `AMOUNT`, `DUE_DATE` with approved format | ordered due-period groups with record count, exact amount statistics and coverage | Missing/invalid due date follows policy; missing/invalid amount excluded. Population is all source records, not inferred open exposure. |
| `RECEIVABLE_AGING` | required `as_of_date=YYYY-MM-DD`, equal to approved dataset reference date | `AMOUNT`, `DUE_DATE`, `STATUS`; complete settlement map; `amount_basis=OUTSTANDING_BALANCE`; approved `dataset_reference_date` | all five frozen buckets in order, each with open-record count, exact balance sum and coverage; excluded-status/value counts | Only eligible positive `OPEN` balances bucketed. Missing/invalid due date/amount and non-positive balances excluded/disclosed; settled/cancelled separated. |
| `OVERDUE_RECEIVABLE_SUMMARY` | required `as_of_date=YYYY-MM-DD` | same as aging | `open_record_count`, `overdue_record_count`, exact overdue balance statistics, coverage and exclusions | Overdue means eligible `OPEN`, positive outstanding balance and `due_date < as_of_date`. Due-on-date is not overdue. |

The payable minimum-data rules apply symmetrically, but customer and supplier
semantics are never substituted. A receivable is not revenue or cash receipt.

## CASH_TRANSACTION catalog

The exact catalog is:

1. `CASH_TRANSACTION_COUNT`
2. `CASH_INFLOW_SUMMARY`
3. `CASH_OUTFLOW_SUMMARY`
4. `NET_CASH_BY_PERIOD`
5. `CASH_BY_CATEGORY`
6. `CASH_BY_ACCOUNT`

### Operation contracts

| Operation | Inputs | Required semantics/mappings | Result | Missing/value behavior |
|---|---|---|---|---|
| `CASH_TRANSACTION_COUNT` | none | approved `CASH_TRANSACTION` domain | `record_count` of authenticated source records | Counts records independent of currency; domain approval already requires the three anchors. |
| `CASH_INFLOW_SUMMARY` | none | `AMOUNT`, `CASH_DIRECTION`; complete direction map; approved amount convention | exact statistics over confirmed inflow magnitudes and coverage | Missing/invalid direction or amount and convention-inconsistent values excluded/disclosed. No inflow records yields `NO_DATA`. |
| `CASH_OUTFLOW_SUMMARY` | none | same as inflow | exact statistics over confirmed outflow magnitudes and coverage | Original negative signs remain in lineage; output magnitude is non-negative. No outflow records yields `NO_DATA`. |
| `NET_CASH_BY_PERIOD` | `granularity=MONTH|YEAR`; `missing_dimension=BUCKET|EXCLUDE` | `TRANSACTION_DATE`, `AMOUNT`, `CASH_DIRECTION`; direction map; amount convention | ordered periods with inflow sum, outflow sum, `net_cash`, directional counts and coverage | Core computes `net_cash = inflow magnitude - outflow magnitude`. Missing/invalid date follows policy; invalid direction/amount excluded. |
| `CASH_BY_CATEGORY` | `missing_dimension=BUCKET|EXCLUDE` | `CATEGORY`, `AMOUNT`, `CASH_DIRECTION`; direction map; amount convention | ordered category groups with inflow sum, outflow sum, net cash, counts and coverage | Missing category follows policy; invalid direction/amount excluded and disclosed. |
| `CASH_BY_ACCOUNT` | `missing_dimension=BUCKET|EXCLUDE` | `ACCOUNT`, `AMOUNT`, `CASH_DIRECTION`; direction map; amount convention | ordered account groups with inflow sum, outflow sum, net cash, counts and coverage | Missing account follows policy; invalid direction/amount excluded and disclosed. |

`NET_CASH_BY_PERIOD`, `CASH_BY_CATEGORY` and `CASH_BY_ACCOUNT` arithmetic belongs
exclusively to Financial Core. Mediation, Manager, API and UI transport/render the
returned values and must not recompute net cash.

Minimum data: count requires an authenticated approved dataset. Monetary cash
operations require at least one convention-consistent amount/direction record;
otherwise readiness is `BLOCKED`. A supported directional summary with no rows
for that direction returns `NO_DATA`.

## Operation readiness matrix

For every catalog entry, readiness evaluates in this order:

1. valid exact dataset identity and authenticated current artifacts;
2. approved matching canonical domain;
3. operation exists in that domain catalog;
4. all operation roles are confirmed exactly once;
5. all required critical value mappings/qualifiers are complete;
6. date format, approved dataset reference date and exact request-date match pass;
7. currency state permits the operation;
8. compatible static adapter/catalog/Core contract exists;
9. minimum executable data passes; and
10. current source/schema/mapping identity still matches.

Failure before step 3 is `BLOCKED` or `UNSUPPORTED` according to the semantic
contract. A previously `SUPPORTED` result has no authority after any artifact or
mapping change; execution performs the checks again.

## Explicit exclusions

There are no operation-specific arbitrary filters, date ranges, sorting, top-N,
custom statistics, status selectors, user-chosen measures/dimensions, formulas,
SQL, runtime expressions or request-selected adapters. No new anomaly operation
is part of this catalog.
