# Step 14 — Financial investigation screening

## Readiness gate

Step 14 is authorized as a separate deterministic statistical service. Evidence:
[Receiver General EDA](../notebooks/02_eda_receiver_general.ipynb) sections 12–14,
[Company Financials EDA](../notebooks/03_eda_company_financials.ipynb) sections
14–15 and conclusions, [data model](data_model.md), the implemented SQLite
schema, [Financial Core](financial_core.md), [Phase 4 validation](phase4_validation.md)
and [Step 13](financial_analysis_agent.md). Existing notebooks were reviewed,
not rerun or modified. No data was cleaned again.

| Dataset | Readiness | Implemented scope and evidence |
|---|---|---|
| Receiver General | **READY**, restricted descriptive screening | Accounting amount; global upper IQR fence and direction × voucher-type peers. EDA found 9,256 complete peer labels, 55 groups, 25 groups reaching 30 records and 9,107 eligible observations. Global and peer selection differed materially. |
| Company Financials | **READY**, restricted descriptive screening | Sales and signed Profit; global two-sided IQR fences and segment × sale-price peers. EDA found seven pricing groups of 100 rows; Profit has five unavailable observations. Sales global/peer candidates were 53/5 with no overlap. These are sales-record populations, not companies. |

READY means sufficient evidence to reproduce these transparent source-number
screening rules with explicit limitations. It does **not** establish a validated
business anomaly detector, independent observations, common denomination,
ground-truth labels, error detection or fraud probability. Unknown currency does
not prevent describing the supplied numbers, but it prevents claiming that their
cross-record economic magnitudes are comparable. That limitation accompanies
every result and every record through warning references.

Readiness was evaluated separately: RG uses only an upper tail because its
approved amounts are nonnegative; CF Sales/Profit use both tails, preserving
signed Profit. The two domains share computation, not business semantics.

## Peer decisions and deferred alternatives

| Dataset | Peer population | Decision |
|---|---|---|
| RG | `debit_credit × voucher_type` | Implemented; the EDA's first recommended comparison, with broad coverage and documented global/peer disagreement |
| RG | Add department | DEFERRED: 188 groups, median size 4, 60 singletons; 8,503 records in groups of at least 30. Requires separate assessment of additional context versus fragmentation. |
| RG | Direction × control type | DEFERRED: useful alternative, but the EDA found each populated voucher type mapped to one control type; avoid redundant initial screens |
| RG | Subledger, ledger, coding block | DEFERRED: selective coverage; subledger misses 2,186 rows, ledger misses 9,091. Only 90 ledger/direction records fall in groups of at least 30. No automatic sparse-account peers. |
| RG | Direction × voucher × calendar month | DEFERRED: 353 groups, 115 singletons, median size 8. Dates remain filter/context data, not a claim of independent temporal peers. |
| CF | `segment × sale_price` | Implemented for Sales/Profit; seven groups of 100 rows before measure-specific missingness |
| CF | Segment × country × product | DEFERRED: 150 groups of 2–18 rows; none reaches the exploratory guard |
| CF | Segment × sale price × month | DEFERRED: 112 groups of 5–10 rows; monthly screening is insufficiently supported |
| CF | Discount, quantity, other measures, ratio/identity checks | DEFERRED: distinct measure semantics and thresholds need their own review; the 53 Discounts placeholders remain unresolved |
| Either | Company peers, cash/revenue/expense meanings, supervised labels | BLOCKED by missing identity/semantics/reference evidence; not implemented |

Peer labels are exact supplied categories. Country is never a currency, and
segment is never a company. CF sale price is an existing physical decimal field
used only as a pricing-regime label, never summed. Numeric-equivalent price
tokens such as `10.0` and `10.00` share a peer. Original values/statuses are kept
on every item; the reference displays the first source-row representation.

No caller-supplied peer combinations, minimum sizes, thresholds, SQL or arbitrary
field expressions are accepted. There is no automatic fallback from an
ineligible peer to a global classification. The independent global assessment
can remain available while the peer assessment is NOT_ASSESSED.

## Method and minimum size policy

Implemented method: **Tukey IQR**, version 1.0. MAD and percentile screens were
evaluated as alternatives but deferred: IQR already has documented global/peer
evidence for both datasets. Additional rules would need justification and review
of disagreement, ties and degenerate populations. No ML dependency or model was
installed or trained.

For sorted available values `x[0] ... x[n-1]`, quartiles use the EDA's linear
interpolation convention: `h=(n-1)*p`, with `p=0.25` or `0.75`; interpolate between
the surrounding values. Define `IQR=Q3-Q1`, upper fence `Q3+1.5*IQR`, and, for
CF only, lower fence `Q1-1.5*IQR`. Strictly greater/less selects a candidate;
equality to a fence does not. Original amounts are not normalized, clipped,
imputed or overwritten. Summary-line counts do not expand or divide RG values.

Both global and peer populations require **at least 30 available target values
and positive IQR**. Thirty is carried forward from the EDA's exploratory
stability/coverage guard, not a power calculation, confidence guarantee or proof
of independent samples. The production coverage above supports using this
conservative starting policy. There are no user-tunable thresholds.

- Fewer than 30 numeric values: NOT_ASSESSED, `insufficient_numeric_records`;
  no quartiles or fences are reported for that population.
- Zero IQR: NOT_ASSESSED, `zero_iqr`, with observed quartiles/IQR and null fences.
  A single extreme among a flat majority does not trigger a fabricated fallback.
- Missing target: NOT_ASSESSED with its source status; never replaced by zero.
- Missing peer label: peer NOT_ASSESSED; no fictitious unavailable-category peer.
- Multiple missing dependencies are all disclosed, with disjoint abstention
  counts prioritizing peer fields in documented order, then missing measure.

These are in-sample descriptive fences: an assessed record is included in its
reference population. Filters/period restrict both assessment and fitting of
references. “Global” means the **selected cohort**, not an immutable threshold
from the entire extract. Narrowing filters can change fences and eligibility.
There is no rolling history, train/test evaluation, probability or predictive claim.

Quartiles/fences use Python Decimal with Phase 4's isolated precision-60 context
and Inexact/Rounded traps. Interpolation quarters and the multiplier `1.5` are
exact; there is no two-decimal quantization or binary-float authority. Precision
overflow produces DATA_QUALITY_BLOCKER with no partial assessments. Counts are
integers, amounts/statistics are fixed-point decimal strings and unavailable
statistics are null. Coverage percentages reuse the Core's six-place half-even
policy; they are not detection probabilities.

## Service interface

```python
from src.anomaly import AnomalyService

service = AnomalyService()
result = service.analyze({
    "analysis_version": "1.0",
    "dataset": "receiver_general",
    "measure": "accounting_amount",
})

profit = service.analyze({
    "analysis_version": "1.0",
    "dataset": "company_financials",
    "measure": "profit",
    "quality_detail": "full",
})
```

`AnomalyService(project_root=None)` uses the approved local snapshot; root is
trusted application configuration. The only request properties are
`analysis_version`, `dataset`, `measure`, and optional `filters`, `period`,
`quality_detail`. Version/dataset/measure are explicit and required. Approved
measures are RG `accounting_amount` and CF `sales`/`profit`.

Filters, inclusive period bounds, CF whole-month restrictions and quality detail
reuse Phase 4 normalization unchanged. In particular, sale-price peer use does
not introduce a sale-price filter into the Core. Unsupported measures return
UNSUPPORTED; invalid syntax, unknown keys or group/method/SQL options return
INVALID_REQUEST before database access. No natural-language parser exists here.

The service reuses `ApprovedSnapshot` and its verified bytes, `query_only`
connection, controlled parameterized predicates, approved bundle checks and
lineage validation. The existing 17 analytical contracts cannot export the full
paired record population needed here; this separate service uses the shared
read-only snapshot infrastructure rather than changing their semantics or
attempting to reconstruct rows from aggregates/extreme-record limits.

The pure internal baseline receives those verified records, computes references
and returns observations without writing files or changing rows. Synthetic
records enter only through test fixtures, never through a production request.

## Result and record accounting

The service envelope has `analysis_version`, `service`, `status`, `dataset`,
`measure`, `currency`, `records`, `filter_diagnostics`, `quality`, `errors`,
`metadata` and `result`. It is distinct from Step 09's analytical query envelope.

`metadata` preserves seven snapshot/artifact hashes, normalized filters/period,
observed date range, method/version, quantile convention, multiplier, minimum,
tail policy, exact-arithmetic policy and reference-population basis. No run clock
or random seed is needed: identical snapshots/requests reproduce identical output.

`result` contains:

- `references`: global and every complete observed peer, with reference ID,
  peer definition/values, numeric sample size, eligibility/reason, Q1/Q3/IQR and
  applicable fences. These are referenced rather than repeated on every item.
- `items`: every selected source record, never only the selected extremes;
  original value/raw token/status, dataset/measure, run/source/record ID and both
  source/processed row positions, original peer values/statuses, missing
  dependencies, two assessments and relevant `quality_warning_indices`.
- Each assessment has `status`, abstention `reason`, reference ID, numeric peer
  size and selected tail. Resolve its reference plus envelope method metadata
  when presenting/exporting it; never detach the item from its evidence.
- `summary`: separate global/peer counts for CANDIDATE, NOT_SELECTED and
  NOT_ASSESSED, with disjoint reasons for abstention.
- `comparison`: four global/peer selection combinations **only among records
  assessed by both**. Its denominator is explicit; abstentions are not negatives.
- `measure_coverage` and independent `dimension_coverage` by peer field.

Item statuses are **CANDIDATE**, **NOT_SELECTED**, **NOT_ASSESSED**. NOT_SELECTED
means only that the observation did not cross this particular eligible fence;
it is never NORMAL, verified, erroneous or fraudulent.

Phase 4 selection accounting is preserved:
`population = filtered_out + filter_unavailable + candidates` and
`candidates = used + excluded`. Here `records.candidates` means rows matching
filters, not statistical investigation candidates. `used` means numeric target
values available for reference estimation; `excluded` means unavailable target
values. Missing peer labels and small/flat groups are counted separately in
assessment abstentions; they need not remove an amount from the global reference.
Each mode's three assessment counts reconcile to `records.candidates`.

Source-row order and record ID break ordering ties. Global reference is first;
complete peers sort by source labels and numeric price where applicable. No
truncation, deduplication, inference of unique business events or synthetic rows.

Service statuses:

| Status | Meaning |
|---|---|
| SUCCESS | All selected rows assessed in both modes; informational uncertainties remain |
| PARTIAL | At least one abstention or relevant Core coverage limitation; includes all-unassessed cohorts so their lineage/reasons remain available |
| NO_DATA | No matching rows; selection accounting/diagnostics still returned |
| INVALID_REQUEST / UNSUPPORTED | Request rejected without assessment |
| DATA_QUALITY_BLOCKER | Snapshot/value-status/lineage or exact-arithmetic requirement failed; no assessments returned |

Unexpected implementation exceptions propagate. Warnings are not substituted for
hard failures, and a request never silently switches to another method.

## Quality, currency and privacy

Phase 4 `select_rows`, coverage helpers, `assess`, observed periods, monetary
metadata and original flags are reused. `assess` gains one optional keyword-only
`additional_fields` for trusted service dependencies. It makes both peer fields,
including physical CF `sale_price`, relevant without changing default behavior
or any Step 09 filter/group semantics. Previous Core tests remain unchanged.

Original scoped flags remain available; warnings are query-relevant. Missing RG
voucher type matters to this screen; unrelated missing department does not.
Unresolved Profit matters to Profit screening; unresolved Discounts does not
make Sales screening partial. Temporal/fiscal disclosures follow Core scope when
period/fiscal filters are used. No parser-failure or key-conflict flag is invented.

Additional `descriptive_screening` and counted `assessment_unavailable` warnings
explain method limits/abstentions. Per-item warning indices resolve against the
returned warning list: dataset limitations apply to all items; source-field
warnings only to affected records; abstention warnings only to matching
assessment reasons. Original flag row references remain traceable.

All monetary output has UNKNOWN currency, null code/evidence and
`conversion_applied=false`. Price-based peers do not establish denomination.
The five Profit and 53 Discounts placeholders remain unresolved. Negative Profit
is retained; sign alone is never a selection rule.

Database, observations, references and results stay local. The service has no
provider, credentials, network call, model client, telemetry or persistent result
store. No data is sent externally and no source/processed data is rewritten.

## Agent integration and stopping point

The Step 13 agent and its 17-tool registry remain unchanged. It still rejects
anomaly requests because its separate routing contract has not been extended.
The new service is independently callable and testable; a future explicitly
approved adapter may pass its intact structured evidence to the agent. No
statistical mathematics or candidate interpretation belongs in prompts.

See [Step 14 validation](step14_validation.md) for exact tests, observed counts
and protected-file checks. There are no ground-truth labels or measured detection
accuracy/recall. Currency, grain, summary overlap, independence and provenance
remain unresolved. The next decision is a separately scoped forecasting
readiness review; forecasting and RAG are not implemented here.
