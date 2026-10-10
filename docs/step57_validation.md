# Phase 15 — Step 57 validation

## Status

**PASS.** `SALES_BY_PERIOD`, `SALES_BY_SEGMENT` and `SALES_BY_PRODUCT` are
implemented and directly bindable for approved `SALES_RECORD` datasets. Step 59
readiness activation is intentionally unchanged.

## Implemented behavior

| Operation | Required confirmed roles | Parameters | Result |
|---|---|---|---|
| `SALES_BY_PERIOD` | `SALES`, `TRANSACTION_DATE` | `granularity=MONTH|YEAR`; `missing_dimension=BUCKET|EXCLUDE` | Exact Sales count/sum by calendar key |
| `SALES_BY_SEGMENT` | `SALES`, `SEGMENT` | `missing_dimension=BUCKET|EXCLUDE` | Exact Sales count/sum by source Segment |
| `SALES_BY_PRODUCT` | `SALES`, `PRODUCT` | `missing_dimension=BUCKET|EXCLUDE` | Exact Sales count/sum by source Product |

Period uses only the confirmed Phase 13 transaction-date role and approved date
format. Month is the default; year is the only alternative. Missing dates follow
the grouping policy. Ambiguous dates require explicit format confirmation and
non-missing invalid dates remain blocked by the existing registration gate. No
locale, current time, fiscal mapping or arbitrary date expression is inferred.

Segment and Product labels are preserved exactly, including case and SQL/shell/
import-shaped text. No hierarchy or taxonomy is created. All three operations
share one Core-owned fixed-role grouping primitive; callers cannot name a source
column or arbitrary dimension.

## Arithmetic, coverage and lineage

Sales aggregation uses precision-60 trapped Decimal arithmetic and fixed-point
strings. Missing/unparseable Sales and missing dimensions remain explicit in
measure/dimension coverage; negative values retain their sign. BUCKET keeps an
unavailable group last, while EXCLUDE records a dimension-first reason.

Each group lists contributing canonical record IDs. Top-level lineage retains
dataset, registry, profile, semantic mapping, canonical spec, source fingerprint,
sheet/row, participation and exclusion reason. UNKNOWN and explicitly CONFIRMED
currency states are preserved without geography/format inference.

## TDD and regression

Fourteen Step 57 tests cover monthly/yearly period grouping, renamed fields,
ambiguous dates, missing dates/Sales, exact decimals, UNKNOWN/CONFIRMED currency,
Segment/Product grouping, BUCKET/EXCLUDE, invalid policy, hostile values,
independent required roles, arbitrary-dimension rejection, negative Sales,
lineage, unchanged CF-03/05/06 behavior and the Step 59 activation boundary.
They also verify that an approved non-empty missing-date marker reaches the
unavailable bucket and that a Sales parse failure is not double-labelled as
`source_missing`.

The final focused onboarding/execution regression passed **90 tests** with no
failures or errors. The complete project regression passed **599 tests**. The
Phase 14 readiness assertion explicitly protects the still-activated
three-operation catalog; no runtime Phase 14 behavior was weakened.

