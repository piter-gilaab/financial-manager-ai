# Financial Manager AI V2 — Multi-Domain Semantic Contract

Status: **FROZEN CONTRACT — IMPLEMENTED AND RELEASE-VALIDATED**.

This contract extends the V1 onboarding/execution model to the mandatory V2
domains without creating a universal financial transaction. It is read together
with [the closed query catalog](v2_query_catalog.md).

## Preserved principles

- A structural observation or model suggestion is not financial authority.
- Domain, role, critical value mapping and semantic qualifiers require explicit,
  evidence-bearing confirmation.
- Exact `Decimal` is mandatory; binary float is not financial authority.
- Missing, invalid and unparseable values remain unavailable, not zero.
- Currency is never inferred and no mandatory V2 operation applies FX.
- Financial Core owns arithmetic; adapters translate authenticated artifacts.
- Readiness is operation-specific, current and revocable.
- Operation catalogs and parameters are closed.
- Every result retains source/artifact/mapping/operation lineage.

## V2 ontology decision

V2 reuses the existing roles `AMOUNT`, `TRANSACTION_DATE`, `DUE_DATE`,
`SUPPLIER`, `STATUS`, `CURRENCY`, `ACCOUNT`, `CATEGORY`, `DESCRIPTION`, `ENTITY`,
`INVOICE_ID` and `CASH_DIRECTION`.

V2 adds exactly one mandatory semantic role:

- `CUSTOMER`: the debtor/customer associated with a `RECEIVABLE` record.

`CUSTOMER` is not replaced by `ENTITY`: the existing role does not establish
which party owes the company. The requested names `PAYABLE_AMOUNT`,
`RECEIVABLE_AMOUNT` and `CASH_AMOUNT` are represented by the existing `AMOUNT`
role within an explicitly approved canonical domain. This avoids three aliases
for the same exact monetary representation while preserving domain meaning.

No V2 operation needs a new `ISSUE_DATE`, `PAYMENT_DATE`, `RECEIPT_DATE`,
`COUNTERPARTY` or `TRANSACTION_ID` role. Such source columns remain unassigned or
may use an already-correct metadata role such as `DESCRIPTION`/`ENTITY`; they do
not affect readiness or execution. Adding a future role requires a separately
approved ontology change.

## Critical semantic qualifiers

Roles identify columns; the following closed qualifiers identify meanings that
cannot safely be inferred from the column name or values.

### Settlement status mapping

For `PAYABLE` and `RECEIVABLE`, any operation that distinguishes open from
settled records requires one confirmed `STATUS` column and a complete mapping of
every observed non-missing source value to exactly one of:

- `OPEN`: still financially outstanding at the reference date;
- `SETTLED`: fully liquidated at or before the reference date; or
- `CANCELLED`: not an outstanding obligation and not a settlement.

Partially paid/received source states may map to `OPEN` only when the confirmed
`AMOUNT` basis is the remaining balance. Disputed, held or other statuses may
map to `OPEN` only with evidence that they remain outstanding. Missing/unmapped
status values make aging and overdue operations `BLOCKED`; the system does not
guess.

### Amount basis

The `AMOUNT` role alone means the exact monetary amount represented by the
source record. It does not establish original invoice value, outstanding balance,
paid amount or cash movement.

`PAYABLE_AGING`, `OVERDUE_PAYABLE_SUMMARY`, `RECEIVABLE_AGING` and
`OVERDUE_RECEIVABLE_SUMMARY` additionally require the closed qualifier:

```text
amount_basis = OUTSTANDING_BALANCE
```

The confirmation evidence must establish that the value is the remaining
payable or receivable balance at the requested reference date. Original invoice
amount plus a status is insufficient when partial settlement can exist.

### Dataset reference state

Aging and overdue also require one explicitly approved dataset-level qualifier:

```text
dataset_reference_date = YYYY-MM-DD
```

Its evidence must establish that the confirmed settlement statuses and
outstanding balances describe that date. The request's `as_of_date` must equal
this approved date. V2 does not reconstruct historical open state from a later
snapshot because it has no approved settlement-date/history roles.

### Cash amount convention

All monetary `CASH_TRANSACTION` operations require one explicitly confirmed
convention:

- `MAGNITUDE_WITH_DIRECTION`: `AMOUNT >= 0`; confirmed `CASH_DIRECTION` supplies
  inflow/outflow meaning.
- `SIGNED_WITH_DIRECTION`: confirmed inflows use `AMOUNT >= 0`, confirmed
  outflows use `AMOUNT <= 0`; direction remains authoritative and the Core uses
  the exact absolute outflow magnitude only for the approved arithmetic.

The complete `CASH_DIRECTION` mapping accepts only `INFLOW` and `OUTFLOW` and is
required independently of the amount convention. Sign never creates or changes
direction. Original signed value, normalized magnitude, mapping version and
source row remain in lineage. Convention-inconsistent records are unavailable
with a quality reason; they are not silently sign-flipped.

## PAYABLE semantic model

| Classification | Roles | Contract meaning |
|---|---|---|
| Domain anchors | `AMOUNT`, `DUE_DATE` | Required to approve the V2 `PAYABLE` domain. Amount is not automatically outstanding balance. |
| Operation requirement | `SUPPLIER` | Required only by `PAYABLE_BY_SUPPLIER`. |
| Operation requirement | `STATUS` + complete settlement mapping | Required only by aging and overdue operations. |
| Operation qualifier | `amount_basis=OUTSTANDING_BALANCE`; `dataset_reference_date` | Required only by aging and overdue monetary exposure. |
| Optional dimension/metadata | `INVOICE_ID`, `CURRENCY`, `ACCOUNT`, `CATEGORY`, `DESCRIPTION` | Preserved when confirmed; does not unlock an operation in the frozen catalog. Currency controls monetary comparability. |

`INVOICE_ID` and `SUPPLIER` are no longer domain anchors: a payable dataset can
legitimately lack an invoice identifier or supplier dimension while still
supporting a bounded amount/due-date operation. This intentionally refines the
stricter recognized-but-non-executable V1 `PAYABLE` minimum.

## RECEIVABLE semantic model

| Classification | Roles | Contract meaning |
|---|---|---|
| Domain anchors | `AMOUNT`, `DUE_DATE` | Required to approve the V2 `RECEIVABLE` domain. Amount is not automatically outstanding balance. |
| Operation requirement | `CUSTOMER` | Required only by `RECEIVABLE_BY_CUSTOMER`. |
| Operation requirement | `STATUS` + complete settlement mapping | Required only by aging and overdue operations. |
| Operation qualifier | `amount_basis=OUTSTANDING_BALANCE`; `dataset_reference_date` | Required only by aging and overdue monetary exposure. |
| Optional dimension/metadata | `INVOICE_ID`, `CURRENCY`, `ACCOUNT`, `CATEGORY`, `DESCRIPTION` | Preserved when confirmed; does not unlock another frozen operation. Currency controls comparability. |

Symmetry with `PAYABLE` is limited to shared due/settlement mechanics. Customer
and supplier are distinct roles, and neither receipts nor revenue are inferred
from receivable records.

## CASH_TRANSACTION semantic model

| Classification | Roles | Contract meaning |
|---|---|---|
| Domain anchors | `TRANSACTION_DATE`, `AMOUNT`, `CASH_DIRECTION` | All three and a complete direction mapping are required to approve executable V2 cash semantics. |
| Operation qualifier | `cash_amount_convention` | Required by every monetary cash operation. |
| Optional dimensions | `CATEGORY`, `ACCOUNT` | Unlock only their matching grouped operations. |
| Optional metadata | `DESCRIPTION`, `CURRENCY`, `ENTITY` | Preserved when confirmed; `ENTITY` may describe a counterparty but unlocks no V2 operation. |

A cash transaction records an actual movement of cash; it is not inferred from
sales, revenue, expense, payable, receivable, DR/CR or settlement expectation.

## Aging contract

Both aging operations require an explicit request parameter:

```text
as_of_date: YYYY-MM-DD
```

There is no default to wall-clock “today” and no implicit dataset date. The
request date must equal the explicitly approved `dataset_reference_date`; both
the date and confirmation evidence/version are included in lineage. A mismatch
is `BLOCKED` with `reference_date_mismatch`.

Only records mapped to `OPEN`, with a valid due date and positive confirmed
outstanding balance, enter an aging bucket. Buckets and boundaries are frozen:

| Bucket | Exact rule |
|---|---|
| `NOT_DUE` | `due_date >= as_of_date` |
| `OVERDUE_1_30` | `1 <= as_of_date - due_date <= 30` days |
| `OVERDUE_31_60` | `31 <= as_of_date - due_date <= 60` days |
| `OVERDUE_61_90` | `61 <= as_of_date - due_date <= 90` days |
| `OVERDUE_91_PLUS` | `as_of_date - due_date >= 91` days |

A due date exactly equal to `as_of_date` is `NOT_DUE`. `SETTLED` and
`CANCELLED` records are excluded with separate counts. Missing/invalid due dates
and missing/invalid amounts are unavailable and reported in coverage. Zero or
negative open balances are excluded as `non_positive_open_balance`; they are not
treated as debt, credit or settlement. If no eligible positive open balance
exists, execution returns `NO_DATA`; if deterministic validation cannot establish
the contract, readiness is `BLOCKED`.

## Overdue contract

A record is overdue only when all of the following are established:

1. the approved domain is `PAYABLE` or `RECEIVABLE` as appropriate;
2. `STATUS` is completely and explicitly mapped;
3. the record's mapped status is `OPEN` at `as_of_date`;
4. `AMOUNT` is confirmed as `OUTSTANDING_BALANCE` and is positive;
5. `DUE_DATE` is valid; and
6. `due_date < as_of_date`.

`due_date < as_of_date` alone is never sufficient. A record explicitly settled
at the reference date is not overdue. Because V2 does not add settlement-date
roles, a dataset whose status describes only its present state can execute only
for its explicitly approved `dataset_reference_date`. Missing reference-state
evidence is `reference_state_not_established`; a different request date is
`reference_date_mismatch`.

## Currency contract

V2 preserves onboarding currency states:

| State | Monetary operation behavior |
|---|---|
| `UNKNOWN` | May execute over source-denomination values only, with `code=null`, `conversion_applied=false` and a mandatory non-comparability limitation. |
| `CONFIRMED` | May execute with the one approved ISO code and `conversion_applied=false`. |
| `CONFIRMED_MULTIPLE` | Record count may execute; every frozen monetary operation is `BLOCKED` because no approved currency partition or FX contract exists. |

No scalar total combines confirmed incompatible currencies. Country, symbol,
format, supplier/customer, account and model output never assign currency.

## Readiness contract

Each operation projection contains:

- exact dataset ID and approved domain;
- operation identifier and catalog version;
- required confirmed roles and critical value mappings;
- required semantic qualifiers;
- currency state requirements;
- date/reference requirements;
- current artifact, schema, source and mapping versions/digests;
- minimum executable-data checks;
- `SUPPORTED`, `BLOCKED` or `UNSUPPORTED` state;
- stable reason codes and user-safe limitations.

State meanings are:

- `SUPPORTED`: the operation applies to the domain and all current binding,
  semantic, policy, adapter, currency, date and minimum-data checks pass.
- `BLOCKED`: the operation applies, but one or more remediable current gates fail.
- `UNSUPPORTED`: the operation is not in the approved catalog for that domain.

Readiness is recomputed from current authenticated artifacts. It is never a
stored authorization token. Execution repeats validation and fails closed if
source, schema, domain, role/value mapping, qualifier, adapter or policy changed.

## Closed execution and anomaly limits

No V2 domain request accepts arbitrary SQL, formulas, measures, dimensions,
group-by, source columns, filters, statistical methods, adapters, imports or
runtime expressions. The only inputs are those explicitly listed in the query
catalog.

V2 adds no anomaly operation for `PAYABLE`, `RECEIVABLE` or
`CASH_TRANSACTION`. The V1 `SALES_ANOMALY_SCREEN` and
`PROFIT_ANOMALY_SCREEN` remain supported unchanged. A future multi-domain
anomaly catalog belongs to V2.x/V3 unless separately approved.
