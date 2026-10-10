# Phase 15 — Dynamic Analysis Expansion Contract

## Purpose and authority

Phase 15 expands deterministic Financial Analysis for explicitly selected,
approved `SALES_RECORD` datasets. It does not redesign onboarding, reinterpret
source columns, create an arbitrary query system, or change the legacy Company
Financials path.

The authority chain remains:

```text
source data
  -> approved semantics
  -> canonical SALES_RECORD
  -> dynamic readiness
  -> query binder
  -> SALES_RECORD adapter
  -> Financial Core
  -> structured evidence
  -> Financial Manager
  -> optional LLM / presentation
```

Approved source semantics establish field meaning. The binder admits only a
closed operation and bounded parameters. The adapter authenticates artifacts and
translates confirmed roles into canonical records. Financial Core alone owns
authoritative aggregation, coverage, ordering, sign counts and result status.
The Manager and an LLM cannot select Python functions, infer missing semantics,
choose source columns, assign currency or create financial values.

## Closed operation catalog

The six additive dynamic operation keys are:

| Dynamic operation | Legacy semantic reference | Required confirmed roles | Bounded parameters |
|---|---|---|---|
| `SALES_BY_PERIOD` | CF-03 | `SALES`, `TRANSACTION_DATE` | `granularity=MONTH|YEAR` (default `MONTH`); `missing_dimension=BUCKET|EXCLUDE` (default `BUCKET`) |
| `SALES_BY_SEGMENT` | CF-05 | `SALES`, `SEGMENT` | `missing_dimension=BUCKET|EXCLUDE` (default `BUCKET`) |
| `SALES_BY_PRODUCT` | CF-06 | `SALES`, `PRODUCT` | `missing_dimension=BUCKET|EXCLUDE` (default `BUCKET`) |
| `PROFIT_SUMMARY` | CF-07 | `PROFIT` | none |
| `DISCOUNT_ANALYSIS` | ungrouped CF-08 | `DISCOUNT` with closed value kind `MONETARY_AMOUNT` | none |
| `UNITS_SOLD_SUMMARY` | CF-09 | `UNITS_SOLD` | none |

Together with the Phase 14 operations, these values form the complete dynamic
binding catalog for Steps 56–58. No operation accepts a source-column name,
arbitrary dimension, arbitrary measure, formula, filter, sort expression, SQL or
implementation name. The enum value is the adapter operation; it is never turned
into a function name or dynamically imported.

Requirements are operation-specific. Missing `PROFIT` cannot block
`SALES_BY_PRODUCT`; missing `SEGMENT` cannot block `PROFIT_SUMMARY`. Every role
must occur exactly once as `CONFIRMED`, retain its approved stable column ID and
belong to the current authenticated mapping/profile/source chain.

## Legacy semantic alignment

Alignment means preserving the bounded financial meaning and deterministic
calculation of CF-03/05/06/07/08/09, not copying the legacy SQLite schema or
claiming that an onboarded source is Company Financials.

- The three Sales groupings aggregate only confirmed supplied `SALES` values.
- Profit is the confirmed supplied `PROFIT` measure. It is never derived from
  Sales, COGS, Gross Sales, Discounts or another identity.
- For `SALES_RECORD`, the closed canonical role `DISCOUNT` means a recorded
  monetary discount amount and has code-owned value kind `MONETARY_AMOUNT`. A
  user confirmation of that exact role is the semantic authority consumed by
  the operation. It is not a
  percentage, rate, factor or inferred difference. A source whose approved
  semantics establish only a ratio/rate is not eligible for this operation and
  must remain unmapped/rejected for this role. Header text, percent-like values,
  formatting observations or numeric range cannot create the confirmation.
- Units Sold is the confirmed supplied `UNITS_SOLD` quantity. It is not money,
  record count, revenue or an inferred integer.

The dynamic operations deliberately expose one fixed measure each. Legacy
CF-03/05/06 can select multiple `SALES_MEASURES`, but that wider measure selector
is not copied into the dynamic interface. Dynamic discount analysis is the
ungrouped CF-08 result: `DISCOUNT_BAND` is not an approved Phase 13 semantic role,
so no band grouping is invented or required.

## Period semantics

`SALES_BY_PERIOD` requires the existing `SALES_RECORD` date authority:
`TRANSACTION_DATE`. `POSTING_DATE`, `DUE_DATE`, a header named “date”, the current
clock, locale, filename or another source column cannot substitute for it.

The mapping must confirm exactly one `TRANSACTION_DATE` and its approved format.
Phase 13 confirmation resolves `YYYY-MM-DD`, `DD/MM/YYYY` or `MM/DD/YYYY` before
execution. An ambiguous date without that confirmation remains blocked. The
adapter canonicalizes an approved date to ISO without using the system date or
locale.

The only granularities are calendar `MONTH` and `YEAR`, matching CF-03. `MONTH`
emits `YYYY-MM`; `YEAR` emits `YYYY`; both sort chronologically. There is no day,
week, quarter, fiscal-calendar expression, rolling period, proration, date filter
or synthetic empty period. Missing dates are unavailable dimension values and
are disclosed by status. `BUCKET` retains them in the final unavailable group;
`EXCLUDE` removes them from groups and records the dimension exclusion. The
unavailable bucket is last. A non-missing date that fails its approved format
does not reach grouping: the existing Phase 13 registration/canonical date gate
fails closed with a controlled parse failure rather than weakening approved date
semantics.

The operation groups approved source dates; unlike the legacy monthly Company
Financials source, a newly onboarded source is not claimed to have monthly grain.
The result reports observed records by the selected calendar key and does not
claim missing dates are zero activity.

## Dimension policy

`COUNTRY`, `SEGMENT`, `PRODUCT` and period grouping share one Core-owned fixed-
role grouping primitive. Its interface accepts a closed canonical dimension role,
not a caller-selected column. The policy is:

- `BUCKET`: retain unavailable dimension records under
  `{"value": null, "kind": "unavailable"}`;
- `EXCLUDE`: exclude them once with
  `dimension:<role>:<status>`;
- invalid policy text is a controlled request failure;
- source labels are preserved exactly and ordered by Unicode code point, with
  the unavailable bucket last;
- case, whitespace and SQL/shell/import-shaped text remain source data; no
  product hierarchy, segment taxonomy, country normalization or semantic rename
  is inferred.

Every grouped result contains dimension coverage, global Sales coverage,
per-group Sales coverage and contributing canonical record IDs. A record with an
unavailable dimension and unavailable Sales is accounted once at the applicable
dimension-first exclusion precedence.

## Profit summary

`PROFIT_SUMMARY` reproduces the bounded CF-07 meaning:

- candidate `record_count`;
- `profit.count` and exact `profit.sum` with coverage;
- `negative_count`, `zero_count` and `positive_count` over available numeric
  Profit values.

The sign counts partition numeric Profit exactly using Decimal comparison.
Negative values remain negative and do not become anomaly, fraud or company-loss
claims. Missing and unparseable values have unknown sign, are excluded with their
explicit status and never become zero. No average, minimum, maximum, margin or
derived Profit KPI is added.

## Discount analysis

`DISCOUNT_ANALYSIS` reproduces ungrouped CF-08 for a confirmed monetary Discount
amount. Its fixed result is candidate `record_count`, Discount `count`, exact
`sum`, six-place half-even `mean`, source-scale-preserving numeric `min`/`max`,
coverage, and an unavailable-value count. The unavailable count is diagnostic;
it is not added again to disjoint exclusion reasons.

No other role is required. In particular, Sales, Gross Sales and Discount Band
are irrelevant. The operation never derives a rate, converts percent formatting,
derives Discount from Gross Sales minus Sales, or treats a label such as `None`
as numeric zero. The binder and adapter accept only the exact confirmed
`DISCOUNT` role whose static `SALES_RECORD` role contract is
`MONETARY_AMOUNT`; no caller parameter can select or change its value kind.

## Units Sold summary

`UNITS_SOLD_SUMMARY` reproduces the default bounded CF-09 quantity summary:
`count`, exact `sum`, source-scale-preserving numeric `min` and `max`, and
coverage. The measure has `unit="quantity"` and the evidence envelope has
`currency=null`.

Fractional quantities are valid and preserved. No integer rounding, monetary
conversion, unit-of-measure claim, price multiplication, median or extra KPI is
introduced by this dynamic operation.

## Missing values, parse failures and status

The approved Phase 13 missing markers remain missing; they are not zero. A
non-missing value that cannot be parsed under the confirmed numeric/date format
is unavailable with `parsing_failed`, not guessed or partially incorporated into
an authoritative value. Strings such as `-`, `$-` and `N/A` never become zero:
`N/A` follows the existing missing-marker rule, while non-missing nonnumeric
tokens follow the explicit parse-failure rule.

Measure and dimension coverage use closed reasons such as:

```text
measure:profit:source_missing
measure:discount:parsing_failed
dimension:transaction_date:source_missing
dimension:product:source_missing
```

A result with at least one usable value and relevant exclusions is `PARTIAL`; an
eligible population with no usable measure is `NO_DATA`. Exact-arithmetic or
artifact-integrity failure returns `DATA_QUALITY_BLOCKER` with no partial
authoritative total. The implementation must not create a generic list of magic
placeholder strings beyond the existing profiling/canonicalization rules.

The current canonical mapper fail-closes a non-missing parse failure. To support
the explicit per-value accounting required here without weakening Phase 13 or
the three Phase 14 operations, Steps 57–58 add one bounded adapter-facing
canonicalization mode for only the six Phase 15 operations. For numeric measures
and text dimensions it uses the already approved field normalization rule and
returns `normalized_value` plus
`source_missing|kept|parsed|parsing_failed`; it never changes or persists the
source or mapping. Missing markers still come only from the existing Phase 13
predicate. Confirmed dates retain the stricter registration gate described
above. The default mapper mode and the Phase 14 operation behavior remain
fail-closed. Financial Core receives the value/status pair and owns its exclusion
reason, coverage and result status; the adapter does not calculate them.

## Exact arithmetic and currency

All six operations use deterministic Financial Core arithmetic. Monetary Sales,
Profit and Discount use `Decimal` under the existing precision-60 context with
`Inexact` and `Rounded` traps for exact sums. Units Sold uses the same exact
Decimal machinery as a non-monetary quantity. No authoritative binary float,
SQLite numeric aggregation or Pandas/NumPy float reduction is permitted.

Means and coverage percentages use the existing exact-rational, single-rounding,
six-place `ROUND_HALF_EVEN` rule. Sum and source extrema are not quantized.
Precision failure blocks the whole operation; no subtotal is emitted.

Sales, Profit and Discount copy only approved mapping-level currency metadata:
`UNKNOWN` with no code or `CONFIRMED` with its approved code/evidence. Country,
`$`, formatting, header, product and segment never establish currency. A scalar
operation remains blocked for confirmed multiple denominations because no
partition contract exists. Units Sold always has `currency=null`.

## Binder, adapter and Core seams

The Step 53 binder is extended with exactly the six domain/operation entries and
the parameters shown in the catalog. It authenticates current metadata, validates
the selected operation's roles and bounded enum parameters, then creates the
typed adapter request. It performs no source parsing or arithmetic.

The existing `SalesRecordExecutionAdapter` is extended; there is no adapter per
operation, plugin loading or request-derived dispatch. It reloads and validates
the current source, resolves confirmed canonical fields, retains source status
and lineage, and delegates a typed canonical record collection to Financial Core.
It does not calculate totals, means, coverage, groups or signs.

`src.financial.sales_records` remains the Core module for dynamic `SALES_RECORD`
calculations. Shared grouping and summary primitives may be deepened there where
the semantics are genuinely common, while public operation functions retain
closed domain names. There is no public “group by any column” or “summarize any
measure” interface.

## Lineage and evidence

All new results preserve the Phase 14 envelope and this chain:

```text
dataset_id
  -> registry version/digest
  -> profile version/digest
  -> semantic mapping version/digest
  -> canonical model/specification
  -> source fingerprint and sheet
  -> canonical_record_id
  -> source row number
  -> operation participation/exclusion
```

Grouped results list contributing canonical record IDs in source-row order.
Summary results retain every record's participation and exclusion reason in
`metadata.lineage.records`. No local source path or implementation detail is
added to evidence.

## Controlled failure and security model

The existing adapter/binder outcomes remain authoritative: missing or unresolved
required semantics, invalid parameters, unsupported operations, stale mapping,
invalid registry, schema mismatch, quality blocker and blocked dataset all fail
with fixed path-free messages. Date-format absence/ambiguity and unsafe numeric
meaning are required-semantic or controlled quality failures, never inferred.

Dataset IDs, headers, labels and cell values are inert data. The expansion adds
no `eval`, `exec`, subprocess, shell, raw SQL, dynamic import, untrusted `getattr`,
runtime code generation, dynamic adapter loading, network, external LLM,
telemetry or cloud storage.

## Step 59 activation boundary

Steps 57–58 implement and bind these operations, but do not add them to the Step
54 dataset capability projection. Through Step 58, operation-level readiness and
CLI capability discovery continue to expose only `SALES_RECORD_COUNT`,
`SALES_SUMMARY` and `SALES_BY_COUNTRY`; this avoids claiming activation merely
because direct typed binding exists.

Step 59 must explicitly:

1. add the six operations to the readiness candidate catalog;
2. update dataset limitations and CLI capability presentation;
3. evaluate every operation independently using this contract's role and
   parameter defaults;
4. validate revocation/recovery for each added role and date format;
5. preserve global Manager availability separately from dataset readiness; and
6. rerun security, lineage and partial-readiness acceptance before activation.

Dynamic Anomaly Detection, Forecasting and Document Retrieval/RAG remain
`BLOCKED`. Steps 59–60 and any conversational/fuzzy dataset route are outside
Steps 56–58.

