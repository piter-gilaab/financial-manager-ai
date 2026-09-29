# Financial Data Analysis Query Contracts

Phase 4 — Step 09. Contract version **1.0**. Design only, 2026-09-28.

This document specifies the read-only interface that future Financial Data
Analysis tools will expose to the Financial Manager. No tools, agent, FX,
schema migration, data transformation, API, UI, ML or RAG are implemented here.
`READY` below means the documented source-record question can be implemented
safely **after explicit implementation approval**. It does not mean implemented
or approved for execution as an operational financial tool.

## 1. Authority, scope and evidence

The implemented [DDL](../src/database/schema.sql), inspected SQLite tables and
[connection arithmetic](../src/database/connection.py) are authoritative.
Reviewed context includes [AGENTS.md](../AGENTS.md), [CONTEXT.md](../CONTEXT.md),
[V1 direction](planning/v1-direction.md), [the orchestration ADR](adr/0001-financial-manager-com-ferramentas-especializadas.md),
[semantic model](data_model.md), [schema documentation](database_schema.md),
[loaders](../src/database/loaders.py), [initialization](../src/database/initialize.py),
[validation](../src/database/validation.py), [database tests](../tests/test_database.py),
and [Phase 3 validation](phase3_validation.md).

The only eligible cleaning run is `20260928T190320706702Z_0a18cf5b`, pinned by
[approved_run.json](../src/database/approved_run.json). Evidence from that run:
[manifest](../data/processed/20260928T190320706702Z_0a18cf5b/cleaning_manifest.json),
[cleaning validation](../data/processed/20260928T190320706702Z_0a18cf5b/cleaning_validation_report.json),
[review flags](../data/processed/20260928T190320706702Z_0a18cf5b/cleaning_review_flags.csv),
and [database validation report](../data/database/load_validation_report.json).
An older processed directory is not another eligible population. Directory
recency must never select data. BRL and single-company assumptions in early
planning are not facts about these extracts.

| Dataset identifier | Actual fact table | Record meaning | Validated baseline |
|---|---|---|---|
| `receiver_general` | `receiver_general_accounting_record` | Imported accounting record; detail/summary overlap unresolved | 9,282 rows; effective dates 2023-04-03 through 2024-01-03 |
| `company_financials` | `company_financial_sales_record` | Sales record, without company identity | 700 rows; 16 monthly periods, 2013-09 through 2014-12 |

Shared tables are `schema_version`, `dataset_source`, `processing_run`,
`run_dataset`, `source_record`, and `data_quality_flag`. They provide provenance
and quality, not a business relationship between the two fact tables.

### Design principles

1. Queries are read-only, including database metadata and source artifacts.
2. Identical normalized requests against the same pinned snapshot produce the
   same ordered values, counts, flags and statuses.
3. Financial arithmetic preserves exact source decimal values.
4. Currency uncertainty is always explicit for monetary output.
5. Missingness never silently becomes zero.
6. Every exclusion is counted and explained.
7. Quality flags remain available to the caller, including flags unrelated to
   the requested metric.
8. Dataset-specific meaning and record grain remain explicit.
9. Accounting and sales are separate domains, not a homogeneous financial table.
10. Unsupported business interpretations are rejected rather than guessed.
11. Validation, selection, arithmetic and status decisions are deterministic
    independently of an LLM.
12. The Financial Manager may later interpret requests and explain tool output;
    calculations belong to tools/database logic.

The interface concentrates these rules in the Financial Data Analysis module.
The single Financial Manager calls named contracts; it supplies neither SQL nor
calculation logic. No additional agents or speculative adapters are needed.

## 2. Common request and physical field mapping

Every request has `contract_version: "1.0"`, `query_name`, and `dataset` matching
the named contract. Optional common inputs are `filters: {}`, `period: null`,
and `quality_detail: "summary" | "full"` (default `summary`). The run is fixed
by this version and is echoed in responses; callers cannot select another run,
a database path, table, expression or join. Unknown request properties are
invalid. Contract-specific options below are the complete additional allowlist.

Public names on the left are translated using this closed mapping. Aliases do
not imply additional stored columns. Every source field listed has its actual
`_raw` and `_status` companions in its domain table.

| Dataset | Public field | Physical field | Type / permitted use |
|---|---|---|---|
| RG | `effective_date` | `accounting_effective_date` | ISO date; chronological filter/group |
| RG | `fiscal_year` | `fiscal_year` | Exact string label; filter only in 1.0 |
| RG | `fiscal_month` | `fiscal_month` | Integer 1–12; filter only in 1.0 |
| RG | `debit_credit` | `credit_debit_code` | String `DR` or `CR`; filter/group |
| RG | `voucher_type` | `journal_voucher_type_code` | String; filter/group |
| RG | `department` | `department_number` | String, preserving leading zeros; filter/group |
| RG | `general_ledger_account` | `general_ledger_account_code` | String; filter/group |
| RG | `subledger_account` | `subledger_account_identifier` | String; filter/group |
| RG | `financial_coding_block` | `financial_coding_block` | Opaque string; filter/group |
| RG | `control_data_type` | `control_data_type` | String; filter/group |
| RG | `accounting_amount` | `journal_voucher_item_amount` | Decimal TEXT; monetary observation |
| CF | `period` | `period_date` | ISO first-of-month period label; filter/group |
| CF | `country` | `country` | String; filter/group |
| CF | `segment` | `segment` | String; filter/group |
| CF | `product` | `product` | String; filter/group |
| CF | `discount_band` | `discount_band` | String; filter/group; literal `None` is a category |
| CF | `gross_sales` | `gross_sales` | Decimal TEXT; monetary observation |
| CF | `discounts` | `discounts` | Nullable decimal TEXT; monetary observation |
| CF | `sales` | `sales` | Decimal TEXT; monetary observation, not renamed company revenue |
| CF | `cogs` | `cogs` | Decimal TEXT; monetary observation |
| CF | `profit` | `profit` | Nullable signed decimal TEXT; monetary observation |
| CF | `units_sold` | `units_sold` | Decimal TEXT; quantity, including fractions |

RG/CF in tables abbreviate the dataset identifiers above. CF `year`,
`month_number`, `month_name`, `sale_price`, and `manufacturing_price` exist, but
are not independent filters or measures in 1.0. Date shortcuts use `period_date`.
RG `accounting_summary_transaction_line_count` is not a row multiplier or a
COUNT substitute. Voucher/control identifiers and `gbs_control_number` are
lineage/context, not groupings or business identities. No contract needs a new
column, table, company entity or schema change.

## 3. Filter, period and grouping rules

### Filters

`RG_FILTERS` means the nine categorical RG fields in the mapping: fiscal year,
fiscal month, debit/credit, voucher type, department and the four account/control
dimensions. `effective_date` is supplied only through
`period`. `CF_FILTERS` means country, segment, product and discount band. All
contracts for a dataset accept its complete filter set and its period input.

Each categorical field accepts exactly one of the following forms:

| Form | Semantics |
|---|---|
| `{"eq":"037"}` | Exact equality; default `nulls: "exclude"` |
| `{"in":["037","001"]}` | Membership; OR within this list; default null exclusion |
| `{"eq":"037","nulls":"include"}` | Equality OR SQL NULL |
| `{"in":["037","001"],"nulls":"include"}` | Membership OR SQL NULL |
| `{"nulls":"only"}` | Only SQL NULL; no `eq` or `in` |
| `{"nulls":"exclude"}` | Any non-null value; no value predicate |
| `{"nulls":"include"}` | All records for that field; explicit no-op |

Different fields and `period` combine with AND. No nested Boolean expressions,
negation, wildcard/regex, numeric amount filters, arbitrary SQL, SQL fragments,
caller expressions, arbitrary sort expressions or raw-column access are allowed.
The future tool generates parameterized value predicates from static mappings.
Column/group names are selected from the allowlist, never interpolated from SQL
submitted by the user or LLM.

Validation is strict: lists contain 1–100 distinct values of one declared type;
duplicates normalize away before the size check. Strings must be nonempty and
match their stored standardized form, without implicit trimming/case folding or
numeric coercion. Null is not a list member or equality operand. Identifiers
such as `"037"` must remain strings. Fiscal year accepts the literal `YYYY/YYYY`
shape (for example `"2023/2024"`), without deriving a calendar interval. Fiscal
month accepts JSON integers 1–12, excluding booleans. Debit/credit accepts only
`DR`/`CR`. A well-typed but absent category or fiscal label returns `NO_DATA`,
not a validation error. Invalid syntax/types/operators produce `INVALID_REQUEST`.

Equality/membership on an unavailable field has an **unknown** predicate result,
unless `nulls: include` makes it true. Explicit null-only/null-exclusion tests
always have a known result: their exclusions are deliberate. For an AND request,
any false predicate makes the record a known non-match; otherwise any unknown
makes it unassessable; otherwise it matches. This rule prevents multi-filter
missingness from being counted repeatedly or mistaken for a known non-match.

### Periods

`period` is absent/null for the whole extract, or uses exactly one form:

- `{"start_date":"2023-05-01","end_date":"2023-05-31"}`: both endpoints
  required, inclusive, real ISO Gregorian dates with start <= end.
- `{"year":2023}`: complete calendar year.
- `{"year":2023,"month":5}`: complete calendar month, month integer 1–12.

Years must be integers 1–9999, booleans rejected. Month without year, combined
forms, timestamps, timezones, relative dates and natural-language dates are
invalid. Normalize shortcuts to explicit bounds and echo them. The tools never
interpret “May” without a year or silently choose the current year.

RG bounds compare `accounting_effective_date`; daily/monthly/yearly grouping
uses that date. Fiscal fields remain independent labels and may be filtered
alongside date bounds; their intersection is applied without asserting alignment.
Fiscal month 1 is never mapped into January or April. Contradictory but valid
filters simply have no matching data.

CF periods describe monthly observations, not daily sale events. A date-range
request must span whole months (first day through last day), even across years.
A valid but partial-month request is `UNSUPPORTED` (`monthly_grain_only`), not a
prorated result. Grouping supports calendar month or year, never day. Month/year
are derived from `period_date`, not alternate source calendar columns.

A null date follows the same unknown-predicate rule when a period filter is
present. No date predicate means it remains a candidate. Date grouping uses the
missing-dimension rule below. Version 1.0 does not accept a null-policy option
inside `period`; date ranges require known dates. Missing time periods are omitted, never filled
with zero. Echo both requested bounds and observed non-null candidate date
range; dates beyond extract coverage do not imply zero business activity. Emit
`period_coverage_limited` if requested bounds extend beyond coverage: RG uses
observed date bounds; CF uses the full first/last observed months. This warning
does not assert that every day/month inside the bounds is fully observed.

### Groupings and order

Exactly one grouping dimension is permitted when a contract defines grouping.
No arbitrary combinations, technical IDs, source row numbers or raw/status
columns are groupings. Fixed-name contracts imply their grouping; `group_by`
must not be supplied to them. Only RG-07 and CF-08 accept `group_by`, as listed
below. Period contracts accept `granularity`, not SQL date expressions.

| Dataset | Allowed groups | Contract |
|---|---|---|
| RG | debit/credit, voucher type, department | RG-03, RG-04, RG-05 respectively |
| RG | effective-date day, calendar month, calendar year | RG-06 |
| RG | general ledger, subledger, financial coding block, control data type | RG-07 |
| CF | period calendar month/year, country, segment, product | CF-03 through CF-06 |
| CF | no group, or discount band | CF-08 |

Group contracts accept `missing_dimension: "bucket" | "exclude"`, default
`bucket`. A missing bucket has `key: {"value": null, "kind": "unavailable"}`;
a real category has `key: {"value": "None", "kind": "source_value"}`. Display
labels such as “UNAVAILABLE” must not be written into source data or treated as
source categories. Period keys use `YYYY-MM-DD`, `YYYY-MM` or `YYYY` as appropriate.

Category order is ascending Unicode code-point order, matching SQLite BINARY
for these strings; periods sort chronologically; the unavailable bucket is last.
Return all observed groups, including groups whose selected measure is entirely
null. Never silently truncate groups. No synthetic empty groups or grand-total
rows. RG-08 has a separate explicit limit and deterministic numeric ordering.

Fiscal grouping, multi-dimensional grouping and price statistics are deferred
extensions, not accepted parameters of version 1.0.

## 4. Record accounting and missingness

All counts refer to imported rows, never unique companies, vouchers, payments,
underlying transactions or expanded summary lines. No deduplication, imputation,
placeholder resolution, sign reconstruction or derived replacement happens at
query time.

The common `records` object contains:

| Field | Definition |
|---|---|
| `population` | All rows of the pinned run and selected dataset before filters |
| `filtered_out` | Rows with at least one known-false filter predicate |
| `filter_unavailable` | No false predicate, but at least one unknown predicate |
| `candidates` | Rows for which all predicates are true; before grouping/measure exclusions |
| `used` | Candidate rows contributing to at least one requested analytical measure; for count contracts, all candidates |
| `excluded` | Candidates contributing to no requested measure |
| `exclusion_reasons` | Disjoint counts explaining `excluded` |
| `filter_unavailable_reasons` | Disjoint counts explaining `filter_unavailable` |

Invariants: `population = filtered_out + filter_unavailable + candidates` and
`candidates = used + excluded`. Also return `filter_diagnostics`, one entry for
each predicate with `field`, `matched`, `nonmatching`, `unavailable` over the
population. These per-predicate counts overlap across predicates and must not be
summed. Filtered-out rows are intentional selection, not missing measure values.

For disjoint unavailable-filter reasons, assign a record to its first unknown
predicate in ascending public-field order (`period` uses its public date field).
Use reason `field:status`, e.g. `department:source_missing`. For candidate
exclusions apply this priority: missing grouping dimension when policy is
`exclude`, then no available requested measure. Reasons are respectively
`dimension:<field>:<status>` and `no_requested_measure_available`. A single-measure
contract instead uses `measure:<field>:<status>` for that second reason.
Independent quality counts still disclose every affected field/status.

Every requested measure, globally and in each group, returns its own `coverage`:
`candidates`, `used`, `excluded`, `exclusion_reasons`, and `percentage`.
Global measure candidates equal common candidates, so dimension exclusions
appear there too. Group measure candidates equal that group's candidate count
after the dimension policy. Reasons use dimension-first priority followed by
`measure:<field>:<status>`. A record with both problems is excluded once.

For multiple measures, top-level `used` is the union of rows contributing to any
measure, not the sum or intersection of measure counts. Measures are evaluated
independently: asking for Sales and Discounts must not discard Sales on the 53
rows with missing Discounts. Do not calculate financial identities between totals
with different coverage or use them to fill missing values.

Each grouped response additionally has `dimension_coverage` with `candidates`,
`available`, `unavailable`, `unavailable_by_status`, `percentage`, and `policy`,
measured before the dimension policy. Missing dimensions cause a disclosure and
`PARTIAL` when relevant, even when their amounts remain in an unavailable bucket.
There is no minimum coverage threshold that automatically blocks sparse groups.
Global per-measure coverage in grouped responses is returned as
`result.measure_coverage`, keyed by the requested measure name. Per-group
coverage is nested inside each measure object. This accounts for dimension
exclusions without inventing a grand-total group or aggregating group means.

Null measures never become zero. Valid statuses for numeric participation are
`kept`, `parsed`, `standardized` with a finite canonical decimal value.
`source_missing`, `unresolved_placeholder`, and a representable future
`parsing_failed` mean unavailable. A null with a present-value status, malformed
decimal or non-null value with a missing-value status is an integrity blocker,
not an ordinary skipped value. Approved import parser failures are currently zero.

An empty numeric population has `sum`, `min`, `max`, `mean`, `median` set to null
when requested; numeric count is zero. A real numeric zero remains a decimal
string. Entirely unavailable numeric queries return `NO_DATA` even if record
counts exist. A mixed-measure query with at least one usable measure returns
`PARTIAL` if another requested measure is unavailable.

RG-08 accounting covers all eligible ranking records, not just returned rows.
It adds `returned`, `not_returned`, and `selection_reason: "limit"`;
`used = returned + not_returned`. Records below the limit are neither quality
exclusions nor hidden anomalies. Quality summaries cover all candidates.
Its numeric amount coverage is `result.measure_coverage.accounting_amount`.
Missing context drives warnings/PARTIAL only for returned items; context flags
on non-returned candidates remain available with `relevant: false` unless the
field also participates in a filter.

## 5. Exact arithmetic and supported aggregations

Input authority is the stored fixed-point decimal TEXT, decoded directly to
Python `Decimal` without any binary float intermediate. SQLite built-in `SUM`,
`TOTAL`, `AVG`, numeric casts/operators on amount TEXT, and lexical numeric
ordering are forbidden for financial calculations. Float-based Pandas/NumPy
reductions are likewise not authoritative.

Phase 3's `DECIMAL_SUM` uses Decimal precision **60** with both `Inexact` and
`Rounded` traps. Preserve that behavior. Feed rows in ascending
`source_record.source_row_number` for reproducibility. A trap or precision limit
must fail the request with `DATA_QUALITY_BLOCKER` / `exact_arithmetic_limit`;
never fall back to float, skip an offending row or silently round a sum.

| Operation | Allowed input / meaning | Null / precision rule | Future execution responsibility |
|---|---|---|---|
| COUNT | Imported rows; numeric count for a requested measure | Integer count; `COUNT(*)` and non-null numeric count are distinct | SQLite for rows; validated numeric availability in tool logic |
| SUM | RG accounting amount; CF gross sales, discounts, sales, COGS, profit; Units Sold quantity | Exact available values; preserve signs and maximum participating scale; all-null => null | Existing `DECIMAL_SUM` registration or equivalent trapped Decimal accumulation |
| MIN / MAX | Same measures | Compare Decimal numerically, return stored winning value verbatim; tie by source row | Python Decimal, not SQLite text MIN/MAX |
| MEAN | Same measures where the individual contract allows it | Unweighted exact sum / numeric count; one final rounding to 6 fractional places, ROUND_HALF_EVEN | Python deterministic rational/Decimal calculation |
| MEDIAN | RG-02 and CF-09 only | Numeric sort, odd middle verbatim; even exact mean of middle two; no 2-decimal quantization | Python Decimal; exact precision-60 operations, trap on loss |
| PERCENTAGE | Availability coverage only in 1.0 | `100 * used / candidates`; 6 fractional places, ROUND_HALF_EVEN; denominator zero => null | Python exact integer rational calculation |
| SHARE / financial RATIO | No public monetary share, margin, discount rate or growth metric in 1.0 | Deferred: currency comparability, denominator/coverage/sign interpretation must be specified first | No implicit SQL/LLM calculation |

For an even median, average via exact halving of the middle values and exact
addition under the trapped precision-60 policy. The result can have an extra
fractional digit, e.g. `1.005` from `1.00` and `1.01`. No rounding is permitted.
MEAN is explicitly a record average, not a company average or weighted price.

Mean and percentage rounding must be a **single** rounding of the exact rational
number to 6 decimal places. The future implementation can use integer
coefficient/scale division and remainder to decide ties, or prove equivalent
Decimal precision. Dividing first under an insufficient context and then
quantizing is not acceptable. The response identifies this rounding policy;
expected rounding of these derived metrics is not a quality failure. Sum and
median retain their stricter no-rounding policy.

`coverage.percentage` always divides available records by the explicit candidate
count of that coverage object. `dimension_coverage.percentage` divides named
dimension availability by candidates. These are record coverage, never money
coverage or confidence probabilities. Independently rounded percentages need
not sum to exactly 100. Empty denominators return null with the zero counts;
there is no division-by-zero substitute.

Do not sum `sale_price` or `manufacturing_price`, average identifiers, aggregate
raw tokens, reinterpret quantity as money, sign RG amounts using DR/CR, or
multiply amounts by summary line counts. Do not derive Profit from Sales minus
COGS or Discounts from Gross Sales minus Sales. Soft cleaning checks are not
permission to repair values.

All decimal results serialize as JSON **strings**, fixed point, no exponent,
thousands separators, currency symbol, NaN or Infinity. Counts are JSON integers;
unavailable results are JSON null. Preserve stored scalar sign/scale, sum scale,
and additional exact median scale. Means and percentages have exactly six
fractional places. No automatic conversion to cents or currency minor units.

## 6. Currency contract

Every envelope has `currency`. It is null only for pure counts or quantity-only
results. Monetary queries return:

```json
{
  "code": null,
  "status": "UNKNOWN",
  "source": null,
  "basis": "unverified_source_denomination",
  "conversion_applied": false
}
```

This applies even to monetary `NO_DATA` responses for the approved snapshot.
The basis permits descriptive sums of supplied numeric observations in one
source, **not a claim that all rows have a verified common denomination**.
All monetary result profiles must disclose: “Currency denomination is unknown;
values summarize source records and are not verified comparable monetary totals.”

No CAD for RG, USD from `$`, currency from country, BRL default, FX, combined
datasets, or cross-source monetary ranking. A business request to convert or
assign a currency is unsupported; adding an unrecognized currency parameter to
these tool requests is `INVALID_REQUEST`, like any unknown property.

The physical row vocabulary includes `UNKNOWN`, `INFERRED`, `CONFIRMED`, but this
approved run accepts only UNKNOWN. INFERRED would require explicit evidence and
an approved interpretation; CONFIRMED authoritative denomination evidence. Tools
must not promote states. Unexpected known-currency rows in the pinned snapshot
are a snapshot/quality blocker, not permission to change this contract silently.

`MIXED` is **not** a current stored or emitted state. A future contract could use
it at envelope level only, with amounts partitioned by currency code and evidence
state, separate UNKNOWN buckets, per-partition counts and evidence/version.
It must not expose a scalar mixed-currency sum, mean, ranking or share. An FX
contract would need separately approved rates, dates, evidence and rounding;
that work is outside this document. Different country labels do not prove MIXED.

## 7. Quality flags and warnings

Warnings are disclosures attached to a result, never hard errors. Flags are
preserved evidence. The actual current flag spelling is
`source_semantics_unresolved`, including `field="provenance"`; do not invent or
rename stored flags to `semantic_unresolved` or `provenance_unresolved`.

| Condition / warning code | Trigger and relevance | Continue? / required disclosure |
|---|---|---|
| `source_missing` | Missing field used by a filter, requested group, measure or returned RG-08 context | Yes; field, status, candidate/filtered-unavailable count, policy and coverage; unrelated sparse fields do not make a count partial |
| `unresolved_placeholder` | Relevant null with that status; currently Discounts 53 and Profit 5 over the full CF extract | Yes on available values; affected measure, numeric count, placeholder count, coverage; never infer zero |
| `currency_unknown` | Any monetary output, including an empty monetary result | Yes for source-value descriptions only; currency object and required text from §6 |
| `fiscal_alignment_unresolved` | RG period grouping/filtering or fiscal filters | Yes for independent fields; no fiscal-calendar mapping; preserve dataset-scoped flag |
| `source_semantics_unresolved` / `record_granularity` | All queries over either dataset | Yes for imported-record descriptions; RG detail/summary overlap and CF grain unresolved; sums are not deduplicated economic totals |
| `source_semantics_unresolved` / `provenance` | All queries | Yes; local hash/run lineage is known but acquisition provenance remains incomplete |
| `source_semantics_unresolved` / `entity_scope` | All CF queries | Yes for sales records; no company identity or company panel |
| `source_semantics_unresolved` / `units_sold` | CF-09 | Yes; fractional source quantity retained; `$` formatting does not make it money or prove a unit of measure |
| `source_semantics_unresolved` / `profit` | Any CF Profit request | Yes; approved parenthesis sign convention and raw token remain available; 5 unresolved placeholders separately disclosed |
| `parsing_failed` | Future representable null/status on a relevant field | Not present in this import. A separately validated future snapshot could exclude/count it; unexpected occurrence here fails snapshot validation |
| Other preserved flag, e.g. `key_conflict`, `semantic_unresolved`, `provenance_unresolved` | Vocabulary is not constrained by `data_quality_flag.flag`; not currently present | Preserve original name/reason; no inferred deduplication; unreviewed changes to this pinned snapshot block execution |
| `period_coverage_limited` | Requested interval extends beyond observed extract coverage | Yes; return requested/observed bounds and limit interpretation to imported coverage |

Actual validated baseline: 29,876 RG source-missing **cells**, 58 CF unresolved
placeholder **cells**, 2 currency flags, 7 source-semantic flags and 1 fiscal
alignment flag. These are not counts of distinct defective records.

`quality.flags` contains every dataset-scoped flag for this source/run, plus all
record/field flags for candidates and `filter_unavailable` records, even if their
fields are not selected. Never join flags directly into an amount aggregation:
one-to-many flag joins would duplicate records and money. Fetch/aggregate flags
independently using the same row set. Dataset flags count once, not once per row.

For `quality_detail: "summary"`, summarize by original `(scope, field, rule_id,
flag, status, reason)` with `flag_count`, `affected_records` (null for dataset
scope), `flag_row_numbers` and `relevant`. Preserve original strings, sorted by
minimum original flag row number. For `full`, return each original flag with
`flag_row_number`, `record_id`, `scope`, `field`, `rule_id`, `flag`, `status`,
`raw_value`, `reason`, `source_row_number`, `source_file`, `source_sha256`,
`run_id`, `source_id`, and `relevant`, sorted by flag row number. This exposes
existing evidence without another query contract. Do not truncate flags silently.

Each warning is `{code, field, scope, affected_records, message,
flag_row_numbers}`. `field` is the stored flag field when derived from evidence,
otherwise the public query field. Dataset warnings have null affected count,
because a dataset condition is not a claim of a defect on every record. Relevant
field warnings count distinct affected records in candidates plus
filter-unavailable rows; coverage/count objects identify exactly where they were
used or excluded. RG-08 returned-context warnings use only returned rows, except
when the same field is also a filter. Warning order is `(code, field, scope)`;
absent field sorts first.

Unknown currency or unresolved semantics alone do not force `PARTIAL`: a fully
computed descriptive answer may be `SUCCESS` with warnings. Missing requested
information, unresolved filter membership or limited requested period coverage
does make an otherwise usable result `PARTIAL`. Missing fields unrelated to a
request remain flags without changing status.

## 8. Shared response envelope and status model

All tools return this logical shape; there is no separate ad hoc error format:

```json
{
  "contract_version": "1.0",
  "query_name": "company_financials_record_count",
  "dataset": "company_financials",
  "status": "SUCCESS",
  "result": {"record_count": 700},
  "currency": null,
  "records": {
    "population": 700,
    "filtered_out": 0,
    "filter_unavailable": 0,
    "candidates": 700,
    "used": 700,
    "excluded": 0,
    "exclusion_reasons": {},
    "filter_unavailable_reasons": {}
  },
  "filter_diagnostics": [],
  "quality": {
    "warnings": [],
    "flags": [],
    "detail": "summary"
  },
  "errors": [],
  "metadata": {
    "run_id": "20260928T190320706702Z_0a18cf5b",
    "schema_version": 1,
    "snapshot": {},
    "filters": {},
    "group_by": null,
    "period": null,
    "observed_period": {"start_date": "2013-09-01", "end_date": "2014-12-01"},
    "options": {},
    "value_basis": "imported_source_records",
    "arithmetic": {
      "decimal_precision": 60,
      "exact_operations_trap_rounding": true,
      "derived_decimal_places": 6,
      "rounding": "ROUND_HALF_EVEN",
      "serialization": "fixed_point_decimal_strings"
    }
  }
}
```

This is a **shape illustration**: empty `quality` lists and `snapshot` are
placeholders here, not the actual baseline response. A real baseline count must
include the applicable grain/provenance/entity warnings and all scoped flags.
`metadata.snapshot` is mandatory for executed queries and contains
`database_sha256`, `schema_sha256`, `manifest_sha256`, `validation_sha256`,
`flags_sha256`, `source_sha256`, and `processed_sha256`. Schema/run/source hashes
come from the metadata tables; database hash identifies the read-only artifact.
The current database SHA-256 is
`8b9536867d7e1ee2e3fd8b0040d40f5806cf6ecb8afc38491cbc058de727c744`.
Future execution must read a validated immutable snapshot consistently; a changed
artifact or unresolved metadata mismatch is a blocker, not another default run.

Metadata echoes normalized filters, normalized inclusive period or null, actual
grouping, explicit defaults/options and observed candidate non-null date bounds
(null if none). No execution timestamp is needed for the deterministic response.

`result` shapes are count, summary, grouped summary, profit summary or ranked
records as specified below. A numeric measure object has `unit: "monetary"` or
`"quantity"`, requested statistic keys, and `coverage` as defined in §4. The
`count` statistic is numeric-record count and equals coverage used. Group objects
contain `key`, `record_count` (all group candidates) and `measures`. Grouped
responses also contain `dimension_coverage`. No global financial total is implied
by adding grouped averages, medians or per-measure counts.

| Status | Deterministic condition | Result / errors |
|---|---|---|
| `SUCCESS` | Requested descriptive result available with complete relevant coverage | Result populated; warnings allowed; errors empty |
| `PARTIAL` | At least one requested analytical result available, but relevant measure/dimension/filter/period coverage incomplete | Result and exact coverage populated; warnings explain limits; errors empty |
| `NO_DATA` | No matched rows, no group-eligible rows, or no usable numeric values for any requested measure | Preserve zero counts/coverage; summary statistics null, groups empty if no groups; `metadata.no_data_reason` explains; errors empty |
| `INVALID_REQUEST` | Malformed input, unknown field/contract/version, bad types, dates, null-policy conflict or limits | `result`, `records`, `currency` null; one or more structured errors; no fabricated counts |
| `UNSUPPORTED` | Well-formed request for unavailable business semantics, grouping/metric, conversion, dataset combination or daily sales interpretation | `result`, `records`, `currency` null; structured reason; no approximate replacement |
| `DATA_QUALITY_BLOCKER` | Snapshot/schema/lineage/status inconsistency or failure of exact arithmetic prevents a trustworthy answer | `result` null; counts only if independently established, otherwise null; structured error; never a misleading subtotal |

Processing precedence: input validation; unsupported-operation checks; snapshot
and integrity checks; execution; exact-arithmetic failure; then NO_DATA,
PARTIAL, SUCCESS in that order. Unsupported operations with malformed parameters
are invalid first. Errors are `{code, field, message}` with field null when
global; they are distinct from warnings. No-data reasons are `no_matching_records`,
`no_group_eligible_records` or `no_numeric_values`, in that precedence order.
Existing all-null groups retain their rows and null statistics under NO_DATA.
Count contracts return `record_count: 0` when no rows match. Technical execution
failure must propagate as an execution error; it must never masquerade as NO_DATA.
For operation options, a recognized operation used outside its permitted scope
(for example CF day grouping or a monetary share statistic) is UNSUPPORTED;
unknown operation spellings and malformed option types are INVALID_REQUEST.

## 9. Receiver General contracts

All eight contracts accept RG_FILTERS and the RG period rules. All monetary
contracts use `accounting_amount` and UNKNOWN currency, and expose source-record
arithmetic without asserting common denomination, non-overlap or net activity.
All inherit the common exclusions, flags, statuses and versioning rules.

**Example convention for §§9–10:** each request/response is a structured
**projection**: common version/dataset/request defaults, snapshot/metadata,
filter diagnostics, full coverage objects and flags are omitted for readability.
They remain mandatory on the actual wire envelope. `warnings` shown inside
`quality` are projections containing just `code`/`field`; real entries use §7.
All figures in these per-contract examples are **synthetic**, not database
answers or newly written data.

The RG example fixture has four rows, accounting amounts `100.00`, `200.00`,
`300.00`, `0.00`, all in May 2023. Respectively: DR/CR/DR/DR; voucher A/A/null/A;
department 037/037/null/001; ledger L1/L1/null/L2; dates May 1/1/2/2. Other RG-07
dimensions follow the same availability pattern for illustrating coverage.
All monetary examples inherit currency/grain/provenance warnings; time examples
also inherit fiscal-alignment disclosure. Missing fixture values have
`source_missing` status. A null-filter projection sets candidates accordingly.

### RG-01 — `receiver_general_record_count` — READY

Purpose: count imported accounting rows, including rows with absent non-filter
dimensions. Inputs: common inputs only. Filters: RG_FILTERS/period. Grouping:
none. Output: `record_count`. Currency: null. Exclusions: only filter selection
and unavailable filter membership; an unrelated null voucher is counted.
Disclosures: grain/provenance, fiscal uncertainty when period/fiscal filters are
used, and missing relevant filters. Unsupported: unique vouchers, payments,
transactions or summing summary line counts as a record count.

Request and response projection:

```json
{"query_name":"receiver_general_record_count","filters":{"debit_credit":{"eq":"DR"}}}
```
```json
{"status":"SUCCESS","result":{"record_count":3},"currency":null,"records":{"population":4,"filtered_out":1,"filter_unavailable":0,"candidates":3,"used":3,"excluded":0,"exclusion_reasons":{},"filter_unavailable_reasons":{}}}
```

### RG-02 — `receiver_general_amount_summary` — READY

Purpose: describe recorded amounts. Additional input: `statistics`, nonempty
unique list from `count`, `sum`, `mean`, `median`, `min`, `max`; default
`["count","sum","min","max"]`. Canonical output order follows that allowlist.
Filters: RG_FILTERS/period. Grouping: none. Output: accounting_amount measure
with selected statistics and coverage. Exclusions: unavailable amount only;
unrelated sparse dimensions do not reduce numeric coverage. Disclosures: currency,
grain/provenance and relevant missingness. Unsupported: total expenditure,
revenue, cash flow, balance or deduplicated accounting activity.

```json
{"query_name":"receiver_general_amount_summary","statistics":["count","sum","mean","median","min","max"]}
```
```json
{"status":"SUCCESS","currency":{"code":null,"status":"UNKNOWN","source":null,"basis":"unverified_source_denomination","conversion_applied":false},"result":{"measures":{"accounting_amount":{"unit":"monetary","count":4,"sum":"600.00","mean":"150.000000","median":"150.00","min":"0.00","max":"300.00","coverage":{"candidates":4,"used":4,"excluded":0,"exclusion_reasons":{},"percentage":"100.000000"}}}}}
```

### RG-03 — `receiver_general_amount_by_debit_credit` — READY

Purpose: separate recorded amounts by source DR/CR code. Additional input:
`missing_dimension` only. Filters: RG_FILTERS/period. Fixed grouping:
`debit_credit`. Output: groups with record_count and accounting_amount
`count`/`sum`/coverage, plus dimension coverage. Exclusions: common dimension
policy and unavailable amount. Disclosures: currency, grain/provenance, relevant
missingness. Unsupported: DR=expense, CR=revenue, CR negation, DR-minus-CR net
cash, or trial-balance interpretation.

```json
{"query_name":"receiver_general_amount_by_debit_credit"}
```
```json
{"status":"SUCCESS","result":{"groups":[{"key":{"value":"CR","kind":"source_value"},"record_count":1,"measures":{"accounting_amount":{"count":1,"sum":"200.00"}}},{"key":{"value":"DR","kind":"source_value"},"record_count":3,"measures":{"accounting_amount":{"count":3,"sum":"400.00"}}}]}}
```

### RG-04 — `receiver_general_amount_by_voucher_type` — READY

Purpose: amount and record distribution by supplied voucher type. Additional
input: `missing_dimension`. Filters: RG_FILTERS/period. Fixed grouping:
`voucher_type`. Output: record_count, accounting_amount count/sum/coverage per
group and dimension coverage. Exclusions: common policy; default retains null
voucher as an unavailable bucket. Disclosures: 26 missing types in the full
current extract, recomputed under filters; currency and common semantics.
Unsupported: deriving transaction purpose or payment status from voucher codes.

```json
{"query_name":"receiver_general_amount_by_voucher_type","missing_dimension":"bucket"}
```
```json
{"status":"PARTIAL","result":{"dimension_coverage":{"candidates":4,"available":3,"unavailable":1,"unavailable_by_status":{"source_missing":1},"percentage":"75.000000","policy":"bucket"},"groups":[{"key":{"value":"A","kind":"source_value"},"record_count":3,"measures":{"accounting_amount":{"count":3,"sum":"300.00"}}},{"key":{"value":null,"kind":"unavailable"},"record_count":1,"measures":{"accounting_amount":{"count":1,"sum":"300.00"}}}]},"quality":{"warnings":[{"code":"source_missing","field":"journal_voucher_type_code"}]}}
```

### RG-05 — `receiver_general_amount_by_department` — READY

Purpose: describe amounts by supplied department code. Additional input:
`missing_dimension`. Filters: RG_FILTERS/period. Fixed grouping: `department`.
Output: record_count, accounting_amount count/sum/coverage per group and
dimension coverage. Exclusions: common policy; default unavailable bucket;
`exclude` reports exactly how many amounts lack a department. Disclosures:
26 missing departments over the full current extract, recomputed per request,
currency and unresolved grain. Unsupported: department names, hierarchy, cost
centers, spending or responsibility attribution not established by the source.

```json
{"query_name":"receiver_general_amount_by_department","missing_dimension":"exclude"}
```
```json
{"status":"PARTIAL","records":{"population":4,"filtered_out":0,"filter_unavailable":0,"candidates":4,"used":3,"excluded":1,"exclusion_reasons":{"dimension:department:source_missing":1},"filter_unavailable_reasons":{}},"result":{"dimension_coverage":{"candidates":4,"available":3,"unavailable":1,"unavailable_by_status":{"source_missing":1},"percentage":"75.000000","policy":"exclude"},"groups":[{"key":{"value":"001","kind":"source_value"},"record_count":1,"measures":{"accounting_amount":{"count":1,"sum":"0.00"}}},{"key":{"value":"037","kind":"source_value"},"record_count":2,"measures":{"accounting_amount":{"count":2,"sum":"300.00"}}}]}}
```

### RG-06 — `receiver_general_amount_by_period` — READY

Purpose: chronology of recorded amounts using Accounting Effective Date.
Additional inputs: `granularity: "day" | "month" | "year"` (default `month`),
`missing_dimension`. Filters: RG_FILTERS/period. Fixed effective-date grouping.
Output: record_count, accounting_amount count/sum/coverage per period and
dimension coverage. Exclusions: unavailable amount; absent date handled by
group policy when not already excluded by a date filter. Disclosures: currency,
fiscal alignment, grain/provenance, missing dates and limited interval coverage.
Unsupported: Fiscal Month-to-calendar mapping or payment/recognition dates.

```json
{"query_name":"receiver_general_amount_by_period","granularity":"day"}
```
```json
{"status":"SUCCESS","result":{"groups":[{"key":{"value":"2023-05-01","kind":"source_value"},"record_count":2,"measures":{"accounting_amount":{"count":2,"sum":"300.00"}}},{"key":{"value":"2023-05-02","kind":"source_value"},"record_count":2,"measures":{"accounting_amount":{"count":2,"sum":"300.00"}}}]},"quality":{"warnings":[{"code":"fiscal_alignment_unresolved","field":"fiscal_period"}]}}
```

### RG-07 — `receiver_general_accounting_dimension_summary` — READY

Purpose: inspect amount coverage/distribution of sparse accounting labels.
Required additional input: `group_by`, exactly one of `general_ledger_account`,
`subledger_account`, `financial_coding_block`, `control_data_type`. Optional:
`missing_dimension`. Filters: RG_FILTERS/period. Output: record_count,
accounting_amount count/sum/coverage per group and dimension coverage.
Exclusions: common policy, no minimum-coverage gate. Disclosures: numeric and
dimension coverage separately; currency/grain/provenance. Unsupported: parsing
coding-block substrings, account hierarchies, account meaning, balances, or
inferring source record types from sparse patterns.

Current availability is 191/9,282 ledger values, 7,096 subledger, 282 coding
blocks and 9,104 control-data types. Their missing counts are respectively
9,091, 2,186, 9,000 and 178. Sparse does not mean zero or not applicable.

```json
{"query_name":"receiver_general_accounting_dimension_summary","group_by":"general_ledger_account","missing_dimension":"exclude"}
```
```json
{"status":"PARTIAL","result":{"dimension_coverage":{"candidates":4,"available":3,"unavailable":1,"unavailable_by_status":{"source_missing":1},"percentage":"75.000000","policy":"exclude"},"groups":[{"key":{"value":"L1","kind":"source_value"},"record_count":2,"measures":{"accounting_amount":{"count":2,"sum":"300.00"}}},{"key":{"value":"L2","kind":"source_value"},"record_count":1,"measures":{"accounting_amount":{"count":1,"sum":"0.00"}}}]},"quality":{"warnings":[{"code":"source_missing","field":"general_ledger_account_code"}]}}
```

### RG-08 — `receiver_general_extreme_amount_records` — READY

Purpose: retrieve largest/smallest source amounts for inspection. Additional
inputs: `direction: "highest" | "lowest"` (default `highest`), `limit` integer
1–100 (default 10, booleans invalid). Filters: RG_FILTERS/period. Grouping: none.
Sort numerically on Decimal amount descending/ascending, ties by ascending
source row then record_id. Return exactly min(limit, eligible count), with
`ties_policy: "truncate_by_source_row"`. No absolute-value ranking.

Each returned item includes `rank`, stored `record_id`, lineage
`source_row_number`, `processed_row_number`, `accounting_amount`, its raw/status,
`effective_date`, `debit_credit`, `voucher_type`, `department`, and statuses of
those four context fields. Their raw companions and original flags are available
through `quality_detail: full` only where represented by flags; arbitrary raw
column retrieval is not a new contract. Source/run hashes are in metadata.
Exclusions: unavailable amount; missing context is retained as null with its
status and warning, not discarded. Numeric coverage covers all ranking
candidates, plus returned/not_returned counts. Disclosures: currency, common
semantics, context missingness, explicit selection limit. Unsupported: anomaly
detection, fraud, risk score, exceptional business event or materiality judgement.

```json
{"query_name":"receiver_general_extreme_amount_records","direction":"highest","limit":1}
```
```json
{"status":"PARTIAL","records":{"population":4,"filtered_out":0,"filter_unavailable":0,"candidates":4,"used":4,"excluded":0,"exclusion_reasons":{},"filter_unavailable_reasons":{},"returned":1,"not_returned":3,"selection_reason":"limit"},"result":{"ties_policy":"truncate_by_source_row","items":[{"rank":1,"source_row_number":3,"accounting_amount":"300.00","accounting_amount_status":"parsed","effective_date":"2023-05-02","debit_credit":"DR","voucher_type":null,"department":null,"voucher_type_status":"source_missing","department_status":"source_missing"}]}}
```

The example is PARTIAL because requested context is unavailable; selecting one
of four records by an explicit limit alone would not make it partial.

## 10. Company Financials contracts

These are sales-record analyses. All nine accept CF_FILTERS and the CF period
rules. `SALES_MEASURES` is exactly `gross_sales`, `discounts`, `sales`, `cogs`,
`profit`, with canonical output order in that sequence. `measures` is a nonempty
unique list from that allowlist; default `["sales"]` where allowed. Monetary
currency is UNKNOWN. Units Sold has no currency assignment.

The synthetic CF fixture has three monthly sales rows: Sales `100.00`, `200.00`,
`300.00`; Profit `20.00`, `-10.00`, null; Discounts `10.00`, null, `30.00`;
Units Sold `1.00`, `2.50`, `3.00`. Countries Canada/Canada/France, segments
Government/Government/Enterprise, products A/A/B, discount bands Low/None/High,
periods 2014-01/2014-01/2014-02. Null measures are unresolved placeholders.
All examples inherit grain/provenance/entity disclosures; monetary ones inherit
UNKNOWN currency; Profit/Units Sold add their respective semantic flags.

### CF-01 — `company_financials_record_count` — READY

Purpose: count sales observations. Inputs: common only. Filters:
CF_FILTERS/period. Grouping: none. Output: record_count, currency null.
Exclusions: filter rules only; unavailable Discounts/Profit do not exclude rows
from a record count. Placeholder behavior: flags remain available, unrelated
placeholders do not make this count partial. Disclosures: source grain,
provenance and absent company identity. Unsupported: number of companies,
customers, invoices, individual sales transactions or physical units.

```json
{"query_name":"company_financials_record_count","filters":{"discount_band":{"eq":"None"}}}
```
```json
{"status":"SUCCESS","currency":null,"result":{"record_count":1},"records":{"population":3,"filtered_out":2,"filter_unavailable":0,"candidates":1,"used":1,"excluded":0,"exclusion_reasons":{},"filter_unavailable_reasons":{}}}
```

### CF-02 — `company_financials_sales_summary` — READY

Purpose: exact descriptive aggregation of selected supplied sales measures.
Additional inputs: `measures` and `statistics`, the latter a nonempty unique
list of `count`, `sum`, `mean`, `min`, `max`; default `["count","sum"]`.
Filters: CF_FILTERS/period. Grouping: none. Output: selected measure objects
with per-measure coverage. Exclusions: each measure's own nulls, independently.
Placeholder behavior: 53 Discounts and 5 Profit absences in the full extract,
not a global complete-case row deletion. Disclosures: currency, grain/entity/
provenance, relevant measure flags. Unsupported: statements, consolidated
revenue, recomputing Profit, filling Discounts, sums of prices or a total formed
by adding different measures together.

```json
{"query_name":"company_financials_sales_summary","measures":["sales","discounts"]}
```
```json
{"status":"PARTIAL","records":{"population":3,"filtered_out":0,"filter_unavailable":0,"candidates":3,"used":3,"excluded":0,"exclusion_reasons":{},"filter_unavailable_reasons":{}},"result":{"measures":{"discounts":{"count":2,"sum":"40.00","coverage":{"candidates":3,"used":2,"excluded":1,"exclusion_reasons":{"measure:discounts:unresolved_placeholder":1},"percentage":"66.666667"}},"sales":{"count":3,"sum":"600.00","coverage":{"candidates":3,"used":3,"excluded":0,"exclusion_reasons":{},"percentage":"100.000000"}}}}}
```

### CF-03 — `company_financials_sales_by_period` — READY

Purpose: sales measure distribution by monthly period or calendar year.
Additional inputs: `measures`, `granularity: "month" | "year"` (default month),
`missing_dimension`. Filters: CF_FILTERS/period. Fixed grouping: period_date.
Output: group record_count and selected count/sum/coverage; dimension coverage.
Exclusions: common dimension policy and independent measure nulls. Placeholder
behavior: retain each measure's available values per period. Disclosures:
currency, monthly grain, placeholders, provenance/entity, date coverage.
Unsupported: daily sales, proration, fiscal calendar, company growth or filling
absent months with zero. This contract reports levels, not growth rates.

```json
{"query_name":"company_financials_sales_by_period","measures":["sales"],"granularity":"month"}
```
```json
{"status":"SUCCESS","result":{"groups":[{"key":{"value":"2014-01","kind":"source_value"},"record_count":2,"measures":{"sales":{"count":2,"sum":"300.00"}}},{"key":{"value":"2014-02","kind":"source_value"},"record_count":1,"measures":{"sales":{"count":1,"sum":"300.00"}}}]}}
```

### CF-04 — `company_financials_sales_by_country` — READY

Purpose: selected sales measures by supplied country label. Additional inputs:
`measures`, `missing_dimension`. Filters: CF_FILTERS/period. Fixed grouping:
country. Output: group record_count, selected count/sum/coverage and dimension
coverage. Exclusions/placeholders: common policy and independent null measures.
Disclosures: currency, grain/provenance/entity, relevant missingness. Unsupported:
inferring local currency from country, country-company identity or GDP/revenue
interpretation. Countries are labels, not currency partitions.

```json
{"query_name":"company_financials_sales_by_country","measures":["sales"]}
```
```json
{"status":"SUCCESS","result":{"groups":[{"key":{"value":"Canada","kind":"source_value"},"record_count":2,"measures":{"sales":{"count":2,"sum":"300.00"}}},{"key":{"value":"France","kind":"source_value"},"record_count":1,"measures":{"sales":{"count":1,"sum":"300.00"}}}]}}
```

### CF-05 — `company_financials_sales_by_segment` — READY

Purpose: selected sales measures by source segment. Additional inputs:
`measures`, `missing_dimension`. Filters: CF_FILTERS/period. Fixed grouping:
segment. Output: group record_count, selected count/sum/coverage and dimension
coverage. Exclusions/placeholders: common policy and independent null measures.
Disclosures: UNKNOWN currency, source grain/entity/provenance and relevant
missingness. Unsupported: segment as a company, industry classification,
subsidiary or consolidated business unit without source evidence.

```json
{"query_name":"company_financials_sales_by_segment","measures":["sales"]}
```
```json
{"status":"SUCCESS","result":{"groups":[{"key":{"value":"Enterprise","kind":"source_value"},"record_count":1,"measures":{"sales":{"count":1,"sum":"300.00"}}},{"key":{"value":"Government","kind":"source_value"},"record_count":2,"measures":{"sales":{"count":2,"sum":"300.00"}}}]}}
```

### CF-06 — `company_financials_sales_by_product` — READY

Purpose: selected sales measures by source product. Additional inputs:
`measures`, `missing_dimension`. Filters: CF_FILTERS/period. Fixed grouping:
product. Output: group record_count, selected count/sum/coverage and dimension
coverage. Exclusions/placeholders: common policy and independent null measures.
Disclosures: currency, grain/entity/provenance and relevant missingness.
Unsupported: stock, product margins, product-company identity, deduplication or
ranking “best product” without an explicitly supported measure and comparison.

```json
{"query_name":"company_financials_sales_by_product","measures":["profit"]}
```
```json
{"status":"PARTIAL","result":{"groups":[{"key":{"value":"A","kind":"source_value"},"record_count":2,"measures":{"profit":{"count":2,"sum":"10.00","coverage":{"candidates":2,"used":2,"excluded":0,"exclusion_reasons":{},"percentage":"100.000000"}}}},{"key":{"value":"B","kind":"source_value"},"record_count":1,"measures":{"profit":{"count":0,"sum":null,"coverage":{"candidates":1,"used":0,"excluded":1,"exclusion_reasons":{"measure:profit:unresolved_placeholder":1},"percentage":"0.000000"}}}}]}}
```

### CF-07 — `company_financials_profit_summary` — READY

Purpose: recorded Profit total and sign distribution. Inputs: common only.
Filters: CF_FILTERS/period. Grouping: none. Output: candidate `record_count`,
Profit count/sum/coverage, `negative_count`, `zero_count`, `positive_count`.
Sign counts partition available numeric Profit exactly, using Decimal comparison
to zero; preserve negative values and treat signed numeric zero as zero.
Exclusions/placeholders: 5 unresolved Profit placeholders in the full extract
are unknown signs, not zeros; Discounts availability is irrelevant. Disclosures:
currency, sign convention, missing Profit, source grain/entity/provenance.
Unsupported: anomalies, loss-making companies, net income certification or
imputing missing Profit. Current baseline: 695 numeric, 58 negative, 0 zero,
637 positive, 5 unresolved; total available Profit `16893702.29`.

```json
{"query_name":"company_financials_profit_summary"}
```
```json
{"status":"PARTIAL","result":{"record_count":3,"measures":{"profit":{"count":2,"sum":"10.00","coverage":{"candidates":3,"used":2,"excluded":1,"exclusion_reasons":{"measure:profit:unresolved_placeholder":1},"percentage":"66.666667"}}},"negative_count":1,"zero_count":0,"positive_count":1},"quality":{"warnings":[{"code":"unresolved_placeholder","field":"profit"}]}}
```

### CF-08 — `company_financials_discount_analysis` — READY

Purpose: recorded Discounts and their availability, optionally by source band.
Additional inputs: `group_by: null | "discount_band"` (default null);
`missing_dimension` is accepted only with grouping. Filters: CF_FILTERS/period.
Output: Discounts count/sum/mean/min/max/coverage, explicit
`unresolved_placeholder_count`, and candidate record_count, globally or per
group; dimension coverage when grouped. The placeholder count is the count of
Discounts placeholders in the measure's candidates, even if a dimension policy
also excludes some of them. It is a diagnostic, not another disjoint exclusion.
For grouped requests, also return global `record_count`,
`unresolved_placeholder_count` and `measure_coverage` beside `groups`; global
counts refer to all candidates before the dimension policy. Each group's
placeholder count refers to its own candidates. Do not sum these diagnostics
into `exclusion_reasons`.

Exclusions: no numerical use of unresolved values; default retains all bands.
Literal `discount_band="None"` is a real category, separate from a null band,
and proves neither a numeric zero nor a resolved discount. Disclosures:
currency, numeric/placeholder counts, record coverage, grain/entity/provenance.
Unsupported: effective discount rates, missing-to-zero substitution, derived
discounts or asserting that the observed sum is the complete dataset discount.

Full current extract: 647 numeric of 700, 53 unresolved, coverage `92.428571`,
available sum `9205248.27`. Recompute these under filters. The current `None`
band selects 53 rows with zero numeric Discounts: that monetary request returns
NO_DATA with null statistics, 53 placeholders and `0.000000` coverage.

```json
{"query_name":"company_financials_discount_analysis","group_by":null}
```
```json
{"status":"PARTIAL","result":{"record_count":3,"unresolved_placeholder_count":1,"measures":{"discounts":{"count":2,"sum":"40.00","mean":"20.000000","min":"10.00","max":"30.00","coverage":{"candidates":3,"used":2,"excluded":1,"exclusion_reasons":{"measure:discounts:unresolved_placeholder":1},"percentage":"66.666667"}}}},"quality":{"warnings":[{"code":"unresolved_placeholder","field":"discounts"}]}}
```

### CF-09 — `company_financials_units_sold_summary` — READY

Purpose: describe source quantities. Additional input: `statistics`, nonempty
unique list of `count`, `sum`, `mean`, `median`, `min`, `max`; default
`["count","sum","min","max"]`. Filters: CF_FILTERS/period. Grouping: none.
Output: units_sold measure, `unit: "quantity"`, selected statistics and coverage;
currency null. Exclusions: unavailable quantity only; Discounts/Profit
placeholders do not exclude quantity records. Placeholder behavior: preserve
any future unavailable quantity under the common rule, with no imputation.
Disclosures: fractional quantities, unresolved measurement semantics,
grain/entity/provenance. Unsupported: `$` as money, currency conversion, integer
rounding of units, revenue interpretation or summing inferred physical units
with established comparability. Current descriptive quantity sum: `1125806.00`.

```json
{"query_name":"company_financials_units_sold_summary","statistics":["count","sum","mean","median","min","max"]}
```
```json
{"status":"SUCCESS","currency":null,"result":{"measures":{"units_sold":{"unit":"quantity","count":3,"sum":"6.50","mean":"2.166667","median":"2.50","min":"1.00","max":"3.00","coverage":{"candidates":3,"used":3,"excluded":0,"exclusion_reasons":{},"percentage":"100.000000"}}}},"quality":{"warnings":[{"code":"source_semantics_unresolved","field":"units_sold"}]}}
```

## 11. Consolidated contract table

Every name is a stable future Python-tool name, not an implemented function.
`Base` quality means grain/provenance, plus entity-scope for CF; `M` adds unknown
currency and requested-measure flags; `D` adds dimension coverage/missingness;
`T` adds temporal coverage and RG fiscal uncertainty when relevant. Every row
also inherits filter and per-measure accounting; summaries and groups retain
all scoped flags, including those not driving warnings.

| Contract | Dataset | Measure | Filters | Grouping | Currency Disclosure | Quality Disclosure | Status |
|---|---|---|---|---|---|---|---|
| RG-01 `receiver_general_record_count` | RG | Rows | RG_FILTERS + period | None | null | Base, relevant filters/T | READY |
| RG-02 `receiver_general_amount_summary` | RG | Accounting amount statistics | RG_FILTERS + period | None | UNKNOWN | Base + M | READY |
| RG-03 `receiver_general_amount_by_debit_credit` | RG | Amount count/sum | RG_FILTERS + period | DR/CR | UNKNOWN | Base + M + D | READY |
| RG-04 `receiver_general_amount_by_voucher_type` | RG | Amount count/sum | RG_FILTERS + period | Voucher type | UNKNOWN | Base + M + D | READY |
| RG-05 `receiver_general_amount_by_department` | RG | Amount count/sum | RG_FILTERS + period | Department | UNKNOWN | Base + M + D | READY |
| RG-06 `receiver_general_amount_by_period` | RG | Amount count/sum | RG_FILTERS + period | Day/month/year | UNKNOWN | Base + M + D + T | READY |
| RG-07 `receiver_general_accounting_dimension_summary` | RG | Amount count/sum | RG_FILTERS + period | One allowed account/control dimension | UNKNOWN | Base + M + D; sparse coverage | READY |
| RG-08 `receiver_general_extreme_amount_records` | RG | Numeric ranking of amount | RG_FILTERS + period | None | UNKNOWN | Base + M; context and ranking coverage | READY |
| CF-01 `company_financials_record_count` | CF | Rows | CF_FILTERS + period | None | null | Base, relevant filters/T | READY |
| CF-02 `company_financials_sales_summary` | CF | SALES_MEASURES statistics | CF_FILTERS + period | None | UNKNOWN | Base + M; independent coverage | READY |
| CF-03 `company_financials_sales_by_period` | CF | SALES_MEASURES count/sum | CF_FILTERS + period | Month/year | UNKNOWN | Base + M + D + T | READY |
| CF-04 `company_financials_sales_by_country` | CF | SALES_MEASURES count/sum | CF_FILTERS + period | Country | UNKNOWN | Base + M + D | READY |
| CF-05 `company_financials_sales_by_segment` | CF | SALES_MEASURES count/sum | CF_FILTERS + period | Segment | UNKNOWN | Base + M + D | READY |
| CF-06 `company_financials_sales_by_product` | CF | SALES_MEASURES count/sum | CF_FILTERS + period | Product | UNKNOWN | Base + M + D | READY |
| CF-07 `company_financials_profit_summary` | CF | Profit total/sign counts | CF_FILTERS + period | None | UNKNOWN | Base + M; Profit placeholders/signs | READY |
| CF-08 `company_financials_discount_analysis` | CF | Discounts statistics/coverage | CF_FILTERS + period | None/discount band | UNKNOWN | Base + M; 53 placeholders; D if grouped | READY |
| CF-09 `company_financials_units_sold_summary` | CF | Quantity statistics | CF_FILTERS + period | None | null | Base; quantity semantics/coverage | READY |

## 12. Unsupported questions and qualified alternatives

Reject the unsupported interpretation; do not silently substitute the alternative.
The future Financial Manager may explain the limitation and ask for a supported
source-record question. These are design classifications, not extra tool names.

| Request | Reason / required response | Supported alternative, if explicitly selected |
|---|---|---|
| RG “total expenses”, “total revenue” | UNSUPPORTED: recognition/category semantics absent; DR/CR do not supply them | Source accounting-amount summary or by DR/CR, qualified |
| RG “net cash”, “balance”, “payments”, “outstanding payable” | UNSUPPORTED: no verified cash accounts, balance, obligation/settlement semantics | Imported-row descriptions only |
| RG “unique transactions” or deduplicated economic total | UNSUPPORTED: summary/detail overlap and event grain unresolved | Imported row count and descriptive numeric aggregates |
| RG “Fiscal Month 1 sales in January” or conversion to fiscal calendar | UNSUPPORTED: no fiscal-calendar mapping | Independent fiscal-label filters and effective-date grouping |
| RG “fraudulent/anomalous largest records” | UNSUPPORTED: ordering has no anomaly model or fraud evidence | Highest/lowest source amount retrieval, explicitly qualified |
| CF “which company performed best”, “company growth” | UNSUPPORTED: no company identifier/panel | Sales observations by supported source categories/periods |
| CF “assets”, “liabilities”, “equity”, balance sheet | UNSUPPORTED: no such facts | None |
| CF “revenue”, “net income”, “profit margin” as a certified statement metric | UNSUPPORTED: source Sales/Profit are not a financial statement; margin not contracted | Named supplied measure and coverage |
| CF daily sales or partial-month totals | UNSUPPORTED: monthly period labels; no event dates or proration basis | Whole-month/year summaries |
| CF “all discounts are zero in None band” | UNSUPPORTED: literal category is not a numeric value; 53 placeholders unresolved | Discount availability and nullable summary |
| CF negative Profit means anomaly/company loss | UNSUPPORTED: sign is not a model result or verified company outcome | Sign counts of recorded Profit |
| Sum/mean of Sale Price as business total or average realized price | UNSUPPORTED in 1.0: prices are not additive; weighting/population not defined | No price contract yet |
| “Combined money across both datasets”, business join | UNSUPPORTED: separate domains, no relationship, uncertain grain and denomination | Separate clearly qualified reports only |
| “Convert to BRL/USD/CAD”, infer currency from `$`/country | UNSUPPORTED: no confirmed denomination or approved FX | UNKNOWN source-denomination result |
| Budget variance, forecast, RAG or ML detection | UNSUPPORTED by this interface: required sources/models/contracts absent | None in Step 09 |
| Arbitrary SQL, internal-ID grouping, caller expression | INVALID_REQUEST for unrecognized input fields; UNSUPPORTED for a recognized but disallowed operation value | Named allowlisted contract |

The financial layer must not let an LLM reconstruct an unsupported ratio,
currency conversion, company identity or financial classification from otherwise
valid tool outputs and present it as a supported tool calculation.

## 13. Future interactions (no agent or prompts implemented)

1. **“How much was recorded by department in May?”** The future Financial
   Manager needs a dataset and year if not already in context. With RG and May
   2023 established, call `receiver_general_amount_by_department`, period
   `{"year":2023,"month":5}`, default missing bucket. The current database
   has 1,063 candidates and no missing departments in that interval (the full
   extract's 26 must not be copied into this filtered answer). Return exact
   groups, UNKNOWN currency, grain/provenance and fiscal-alignment disclosures.
   The later explanation calls these recorded source amounts, not expenditure.

2. **“Compare debit and credit recorded amounts.”** Call RG-03. Current baseline
   is CR: 2,051 records, `51882502310.23`; DR: 7,231 records,
   `3009406489818.93`. Currency remains UNKNOWN; neither group is labeled
   revenue/expense and no signed net is derived. These are descriptive source
   values with unresolved summary/detail overlap.

3. **“Total discounts and how complete is that figure?”** Call CF-08 without
   filters. Return PARTIAL: 700 candidates, 647 numeric used, 53 excluded
   unresolved placeholders, sum `9205248.27`, coverage `92.428571` percent and
   UNKNOWN currency. The explanation says “sum of available recorded Discounts”,
   not a complete total with inferred zero discounts.

4. **“Sales and Profit by product.”** Call CF-06 with measures sales/profit.
   Return each product's Sales and Profit with independent coverage. The five
   full-extract Profit placeholders must not discard otherwise valid Sales.
   Negative values remain signed. The later explanation cannot invent companies
   or declare negative records anomalous.

5. **“How many units were sold?”** Call CF-09 with count/sum. Full-extract result
   has 700 available quantity observations, sum `1125806.00`, currency null,
   and the source quantity/grain disclosures. The LLM does not attach `$` or
   round away fractional units.

6. **“Total discounts for discount band None.”** CF-08 with the exact category
   filter returns NO_DATA for numeric Discounts, despite 53 matched records.
   Sum/mean/min/max are null; placeholder count is 53; coverage is `0.000000`.
   A CF-01 count for the same filter can independently return SUCCESS with 53.

7. **“Combine those sales with government expenditure in CAD.”** Return
   UNSUPPORTED: no supported expenditure classification, relationship, common
   denomination or FX contract. Do not call both tools and add their amounts.

## 14. Versioning, acceptance checks and readiness

`contract_version: "1.0"` versions this interface, independently of SQLite schema
version 1 and the cleaning run. New optional fields or new names can be introduced
in a documented minor version; changing a default, meaning, scale/rounding,
population, null policy, status semantics or existing output shape requires a
major version. Never silently repoint 1.0 at a differently interpreted dataset.
An unknown version is INVALID_REQUEST. Only 1.0 is specified here.

When implementation is approved, behavior should be tested through these named
contracts at the Financial Manager/tool interface. Prior art is the existing
database behavior tests. No test implementation is added now. Required future
acceptance scenarios include:

- Decimal `0.10 + 0.20 = "0.30"`, exact large totals, precision-limit failure,
  numeric rather than lexical extrema, median `1.005`, single-rounding ties,
  and no financial float serialization.
- No matching rows versus all-null measures versus real zero, including the
  actual 53-row None-band discount case and the five Profit placeholders.
- Bucket/exclude grouping, 26 missing RG departments, sparse ledger coverage,
  missing filter predicates with AND/OR/null policies, and disjoint accounting.
- Multi-measure union counts and independent coverage; no multiplication by
  flag joins or summary line counts; no candidate-key deduplication.
- Full preservation of dataset/field flags, scope-aware counts, unselected flags
  available without changing unrelated query status, and deterministic ordering.
- UNKNOWN monetary currency, currency null for quantity/count, invalid/unsupported
  input separation, monthly CF dates and independent RG fiscal fields.
- Explicit extreme-value limits and ties, negative Profit retention, unchanged
  database/data hashes, correct run/hash metadata and read-only access.

### Step 09 validation

The physical field mapping and each contract were checked against the actual
SQLite schema and Phase 3 files. Current counts, sparse dimensions, placeholder
counts, currency states and quoted baseline figures were checked against the
read-only database and cleaning reports. No blocking schema incompatibility was
found. In particular:

| Required check | Design result |
|---|---|
| Contracts map to actual Phase 3 tables/columns | PASS; public aliases mapped in §2; derived output keys are not claimed as stored fields |
| No nonexistent company or business relationship | PASS; separate accounting/sales contracts |
| No DR/CR revenue/expense inference | PASS; explicitly rejected |
| Currency unresolved; no cross-dataset monetary combination | PASS; UNKNOWN with mandatory disclosure |
| Exact arithmetic/serialization | PASS; Phase 3 trapped sums, explicit derived rounding and decimal strings |
| Missing/excluded disclosure | PASS; filter, dimension, per-measure and union accounting |
| Placeholders stay unresolved | PASS; Discounts 53 and Profit 5 handled separately |
| Unsupported financial interpretations catalogued | PASS; §12 |
| No tool/agent or other implementation added | Documentation-only deliverable |
| Database, raw and processed data unchanged | Verified by pre/post SHA-256 comparison for this documentation task |

### Implementation readiness

All **17 named contracts are READY within their stated descriptive scope**:
RG-01 through RG-08 and CF-01 through CF-09. Each has sufficient physical data
and explicit semantics for safe implementation. Sparse dimensions, unknown
currency and placeholders are handled by the contract, so they do not by
themselves block these narrowly defined questions. READY is not authorization;
implementation still requires the user's next explicit approval.

**DEFERRED named contracts: none.** Useful extensions deferred from 1.0 are
multi-dimensional grouping, independent fiscal-label groupings and source price
statistics. They are not necessary to implement the 17 requested interfaces and
need their own output/coverage or weighting decisions. Monetary shares, discount
rates, margins and growth ratios remain deferred pending comparable populations,
denomination evidence and precise denominator/sign semantics; their availability
is not implied by arithmetic feasibility.

**BLOCKED named contracts: none.** The unsupported business capabilities in §12
remain blocked: RG expense/revenue/cash/unique-event totals need verified event
and classification semantics; company-panel/balance-sheet analysis needs actual
company identity and facts; combined monetary analysis/FX needs a supported
relationship and denomination/rate evidence. No callable names are reserved for
these unsupported interpretations.

Recommended next step: review and explicitly approve implementation of the READY
contracts as read-only Financial Data Analysis tools, preserving the common
envelope and arithmetic/quality rules. Stop at contract design for Step 09.
