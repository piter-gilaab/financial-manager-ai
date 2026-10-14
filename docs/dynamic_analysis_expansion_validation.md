# Dynamic analysis expansion end-to-end validation

## Acceptance scope

Phase 15 Step 60 validates the complete local path for the fixed nine-operation
dynamic `SALES_RECORD` catalog:

```text
synthetic source
  -> ingestion and deterministic profile
  -> explicit semantic decisions and domain approval
  -> versioned registry and operation readiness
  -> DynamicQueryBinder
  -> static SalesRecordExecutionAdapter
  -> Financial Core
  -> structured evidence
  -> FinancialManagerAgent
```

The validation uses public onboarding, capability, CLI and Manager interfaces.
It adds no operation, formula, arbitrary dimension/measure, execution CLI,
conversational dataset discovery or Phase 16 work.

## Primary all-nine flow

The primary synthetic CSV deliberately uses noncanonical headers: `TxnDate`,
`Nation`, `BusinessUnit`, `Item`, `Revenue`, `NetResult`, `RebateAmount` and
`Qty`. Explicit approved mappings establish the eight required semantic roles.
Capability discovery reports exactly nine operations, all `SUPPORTED`, and the
Manager executes every operation through binder, adapter and Financial Core.

The rows combine `0.1`, `0.2`, `0.3`, a negative Sale, positive/negative/zero
Profit, missing and placeholder-like values, a very large fractional quantity,
missing date/dimensions and SQL/import-shaped labels. All content remains data.

## Period and grouped analysis

`SALES_BY_PERIOD` defaults to calendar `MONTH` and was separately executed with
the bounded `YEAR` parameter. Groups are chronological; missing dates are an
explicit unavailable bucket. A non-missing unparsable date fails registration
with `canonical_parse_failure`; locale is not inferred and readiness is never
published for that invalid source.

Country and Segment were each exercised under BUCKET and EXCLUDE. Missing labels
are either retained as an unavailable group or explicitly counted under the
dimension exclusion reason. Product source labels—including case-sensitive and
SQL/import-shaped text—are preserved without hierarchy or semantic normalization.
Grouped evidence retains contributing canonical record identifiers.

## Profit, Discount and Units Sold

Profit uses only supplied `PROFIT`. Positive, negative and zero signs remain
distinct; a non-missing `-` is a `parsing_failed` exclusion, never derived or
converted to zero.

Discount remains the approved monetary `DISCOUNT` role. The acceptance result
contains count, exact sum, six-place mean, min, max, unavailable-value count and
coverage. `N/A` and `$-` remain separate source-missing and parse-failed reasons.
Rate-like fields without monetary role confirmation remain blocked.

Units Sold remains a quantity with `currency=null`. Integer, fractional, missing
and very large exact values retain Decimal precision and coverage. No rounding to
integer and no monetary conversion occurs.

## Currency, arithmetic and coverage

UNKNOWN currency allows otherwise valid source-denomination Sales, Profit and
Discount results while inferring no code or symbol. A second all-nine dataset
with explicit `USD -> USD` approval preserves `CONFIRMED`/`USD` through readiness,
binder, adapter, evidence and Manager. Units Sold remains currency-free.

The primary Sales sum is exactly `0.5`; the large fractional quantity sums to
`1000000000000000000000000000001.50`. Existing arithmetic-failure tests confirm
precision failure blocks readiness, returns a controlled execution blocker and
never returns a partial total. Every
summary/grouped result reconciles candidates, used/excluded records and unique
reason counts; no missing or placeholder value is imputed.

## Partial readiness, revocation and recovery

Datasets independently missing COUNTRY, PROFIT or UNITS_SOLD block only their
corresponding optional operation while unaffected operations remain supported.
Persisted revocation/recovery was exercised for COUNTRY, SEGMENT, PRODUCT,
PROFIT, DISCOUNT and UNITS_SOLD using newly constructed manager instances.
Only the associated operation changed, and restoration recomputed the current
projection. SALES revocation invalidated the existing global `SALES_RECORD`
domain contract and blocked all nine until the current mapping was restored.

Existing persisted integration tests also change source bytes/schema, corrupt
registry identity and exercise stale mapping/profile/workflow pointers. Every
case fails closed before calculation; restoring exact approved state permits a
fresh deterministic reevaluation.

## Security, privacy and reproducibility

Traversal-shaped IDs, import-shaped operations/headers/values, SQL-shaped
parameters/labels, shell-shaped labels and instruction-shaped strings are
rejected or preserved as inert data. The execution path introduces no `eval`,
`exec`, subprocess, shell, raw SQL, dynamic import, untrusted `getattr`, runtime
code generation or dynamic adapter loading.

Tests use only synthetic temporary local files. No internet, external LLM,
Ollama, cloud storage, telemetry or private user data participates. User-facing
evidence excludes filesystem paths while preserving dataset, registry, profile,
mapping, canonical record, source sheet/row and adapter/Core identities.

## Acceptance matrix

| ID | Scenario | Status | Observed result |
|---|---|---|---|
| A | All nine operations | PASS | One approved renamed-column dataset reports and executes exactly nine operations. |
| B | Renamed columns | PASS | Confirmed semantic roles, not literal headers, control execution. |
| C | MONTH | PASS | Default calendar-month groups are exact and chronologically ordered. |
| D | YEAR | PASS | The bounded YEAR parameter returns chronological calendar-year groups. |
| E | Missing dates | PASS | Approved missing dates use explicit unavailable coverage/BUCKET behavior. |
| F | Invalid dates | PASS | Non-missing unparsable dates fail registration; locale is not inferred. |
| G | Country BUCKET | PASS | Missing country remains an unavailable group. |
| H | Country EXCLUDE | PASS | Missing country is excluded with one explicit reason. |
| I | Segment BUCKET | PASS | Missing segment remains an unavailable group. |
| J | Segment EXCLUDE | PASS | Missing segment is excluded with one explicit reason. |
| K | Product handling | PASS | Source labels and malicious-looking values remain distinct inert data. |
| L | Profit positive/negative/zero | PASS | Supplied signs and exact total are preserved. |
| M | Profit missing/placeholders | PASS | Missing and parse-failed Profit values remain explicit exclusions, not zero. |
| N | Discount | PASS | Monetary CF-08 statistics and two distinct unavailable reasons reconcile. |
| O | Units Sold | PASS | Integer/fractional/large quantities aggregate exactly without currency. |
| P | UNKNOWN currency | PASS | Source-denomination monetary results execute with no inferred code. |
| Q | CONFIRMED currency | PASS | Explicit USD persists end to end; Units Sold remains non-monetary. |
| R | Partial readiness | PASS | Missing COUNTRY, PROFIT or UNITS_SOLD affects only its operation. |
| S | SALES revocation | PASS | Existing global domain contract blocks all nine; no stale authorization survives. |
| T | Dimension revocation | PASS | COUNTRY/SEGMENT/PRODUCT each revoke only their grouping operation. |
| U | Profit revocation | PASS | Only `PROFIT_SUMMARY` changes while domain approval remains valid. |
| V | Discount revocation | PASS | Only `DISCOUNT_ANALYSIS` changes. |
| W | Units revocation | PASS | Only `UNITS_SOLD_SUMMARY` changes. |
| X | Recovery | PASS | Fresh persisted reevaluation restores only currently valid operations. |
| Y | Source change | PASS | Fingerprint mismatch revokes readiness/execution; exact restoration recovers. |
| Z | Schema change | PASS | Old stable-column mapping cannot execute against changed schema. |
| AA | Stale mapping | PASS | Mapping/profile/workflow identity mismatch fails closed. |
| AB | Stale registry | PASS | Registry digest/version tampering returns controlled blocked readiness. |
| AC | Malicious data | PASS | Traversal, SQL, import, shell and instruction strings remain invalid or inert. |
| AD | Decimal precision | PASS | `0.1`/`0.2`/`0.3`, high-scale, large and negative values show no float drift. |
| AE | Coverage | PASS | Population/candidates/used/excluded/reasons reconcile without duplicate categories. |
| AF | Lineage | PASS | Dataset through canonical source row/sheet and grouped participation remains present. |
| AG | CLI human | PASS | All nine states and controlled unavailable reasons are shown. |
| AH | CLI JSON | PASS | Typed domain, currency, operations, reasons and blockers are serialized. |
| AI | Manager path | PASS | Every operation traverses Binder → Adapter → Core and preserves evidence. |
| AJ | Legacy Receiver General | PASS | Analysis, anomaly, UNKNOWN currency and fiscal limitations remain unchanged. |
| AK | Legacy Company Financials | PASS | CF-01–CF-09, placeholders, currency and anomaly behavior remain unchanged. |
| AL | Dynamic Anomaly blocked | PASS | No legacy anomaly policy is activated dynamically. |
| AM | Forecasting blocked | PASS | Sales/Profit/Units remain non-cash; all forecast gates remain blocked. |
| AN | RAG blocked | PASS | Tabular onboarding is not a governed document corpus; no retrieval path exists. |

## Result

All A–AN scenarios pass. Phase 15’s dynamic scope is the fixed nine-operation
`SALES_RECORD` catalog only. The limitations are explicit: global domain anchors
remain required, readiness is operation/data-quality specific, no arbitrary
analysis exists, and Dynamic Anomaly Detection, Forecasting and RAG remain
blocked.
