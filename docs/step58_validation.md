# Phase 15 — Step 58 validation

## Status

**PASS.** `PROFIT_SUMMARY`, `DISCOUNT_ANALYSIS` and `UNITS_SOLD_SUMMARY` are
implemented and directly bindable for approved `SALES_RECORD` datasets. No
capability-readiness expansion from Step 59 is implemented.

## Profit summary

The operation requires only confirmed supplied `PROFIT`. It returns candidate
record count, Profit count/exact sum/coverage and Decimal sign counts for
negative, zero and positive values, matching CF-07. Profit is never derived.
Negative values remain valid; missing and parse-failed values have unknown sign
and are not zero.

## Discount analysis

The operation requires only the closed `DISCOUNT` role, whose code-owned
`SALES_RECORD` value kind is `MONETARY_AMOUNT`. It implements ungrouped CF-08:
candidate record count, unavailable-value count, Discount count/sum/mean/min/max
and coverage. A ratio/rate-like field without explicit monetary-role confirmation
is blocked. No percent, Discount Band, Sales identity or formatting inference is
used.

## Units Sold summary

The operation requires only confirmed `UNITS_SOLD` and returns quantity
count/sum/min/max with coverage. Fractional and large exact values are retained.
The result has `unit=quantity` and `currency=null`, including when the mapping has
a confirmed monetary currency.

## Missing values and exact arithmetic

Existing Phase 13 markers such as `N/A` remain `source_missing`. Non-missing
nonnumeric tokens such as `-` and `$-` are preserved as `parsing_failed`
exclusions for the six Phase 15 operations and never coerced to zero. The
status-preserving canonical mode is additive; the original mapper and Phase 14
operation behavior remain fail-closed.

Sums use precision-60 trapped Decimal arithmetic. Discount mean and coverage
percentages use the existing exact-rational, one-rounding six-place rule.
Arithmetic overflow returns a controlled blocker and no partial authoritative
total. No binary float is authoritative.

## TDD and compatibility

Twelve Step 58 tests cover positive/negative/zero/missing/parse-failed Profit,
renamed measure columns, UNKNOWN/CONFIRMED currency, Discount statistics and
coverage, ambiguous rate semantics, Units Sold fractional/large/missing values,
currency null, malicious headers, arbitrary-measure rejection, arithmetic
failure and unchanged CF-07/08/09 behavior.

Together with Step 57 and the Phase 14 adapter/binder/readiness tests, the focused
onboarding/execution regression passed **90 tests** with no failures or errors.
Complete project regression passed **599 tests** with no failures, errors or skips. The
one loopback-process test cannot create its audit socket inside the workspace
sandbox; it passed in the unrestricted local-test context where its own audit
hook refuses the attempted loopback connection before any network exchange.

## Final code review

The two-axis review finished with **Standards: PASS** and **Spec: PASS**. The
Spec review found and resolved two issues: recognized non-empty date missing
markers now bypass date-range parsing and reach period BUCKET/EXCLUDE behavior,
while genuinely invalid dates still fail closed; and the guide now distinguishes
the historical three-operation Step 53 binder from the current nine-operation
binder and pending Step 59 activation. A related TDD correction prevents Sales
parse failures from also being reported as `source_missing`. No Standards
violations remain.

## Capability boundary

The binder and adapter know all six new operations. `CapabilityDiscovery`,
dataset CLI presentation and Manager dataset readiness continue to activate only
`SALES_RECORD_COUNT`, `SALES_SUMMARY` and `SALES_BY_COUNTRY`. Dynamic Anomaly
Detection, Forecasting and Document Retrieval/RAG remain blocked.

