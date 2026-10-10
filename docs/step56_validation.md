# Phase 15 — Step 56 validation

## Status

**PASS.** Step 56 is contract/design only;
no runtime operation, binder entry, adapter branch, readiness activation or
capability route is implemented by this step.

## Defined expansion

The contract fixes exactly six additive dynamic `SALES_RECORD` operations:
`SALES_BY_PERIOD`, `SALES_BY_SEGMENT`, `SALES_BY_PRODUCT`, `PROFIT_SUMMARY`,
`DISCOUNT_ANALYSIS` and `UNITS_SOLD_SUMMARY`.

Operation requirements are independent: Sales plus the selected date/dimension
for grouped Sales; Profit alone; monetary Discount alone; and quantity Units Sold
alone. Unused roles cannot block an operation.

## Semantic decisions

- Period uses only confirmed `TRANSACTION_DATE`, the date role already required
  by the `SALES_RECORD` domain. Approved Phase 13 date format is mandatory.
- Calendar month and year are the only granularities, matching CF-03.
- Segment/product/period use the established `BUCKET|EXCLUDE` policy with exact
  source values and no arbitrary group-by input.
- Profit is supplied `PROFIT`, never `Sales - COGS`; CF-07's total and sign
  distribution are preserved without added KPIs.
- `DISCOUNT` has the closed `SALES_RECORD` value kind `MONETARY_AMOUNT` and
  reproduces ungrouped CF-08. A ratio/rate cannot satisfy that confirmed role.
- Units Sold is exact quantity, may be fractional and has no currency.
- Existing missing markers stay missing; non-missing parse failures are disclosed
  as unavailable and neither class becomes zero.

The existing `CONTEXT.md` vocabulary was sufficient: this contract specializes
execution semantics without introducing a new glossary term or architectural
decision requiring an ADR.

## Integration seam

The binder owns closed operation/parameter validation, the single existing
adapter owns authenticated semantic translation, and Financial Core owns all
aggregation, coverage, status and ordering. Shared implementation is allowed
only behind fixed operation functions; no arbitrary measure/grouping interface
or plugin seam is approved.

## Activation boundary

The direct binding/implementation catalog and the Step 54 readiness candidate
catalog remain intentionally separate through Step 58. Step 59 must explicitly
activate the six operations, update limitations/presentation and validate
operation-specific revocation/recovery. This step does not alter dynamic
capability readiness.

## Review gate

The first required two-axis `code-review` found one Standards violation, two
Standards judgement calls and two Spec findings:

- the status claimed PASS before review completion;
- the validation repeated more contract detail than necessary;
- the exact-arithmetic text did not name coverage percentages precisely;
- monetary Discount meaning was not machine-checkable from the role contract;
- the path from parse failure to per-value status was underspecified.

The contract now defines `DISCOUNT` as the exact code-owned monetary-amount role,
requires explicit confirmation of that role, and rejects ratio/rate meaning. It
also defines an additive status-preserving canonicalization mode restricted to
the six Phase 15 operations, leaving existing mapper/Phase 14 fail-closed behavior
unchanged. The re-review reported **Standards: PASS** and **Spec: PASS**, with no
remaining findings. Focused pre-implementation regression for the existing
adapter/binder seams passed: **41 tests**, with no failures or errors.
`git diff --check` passed.

