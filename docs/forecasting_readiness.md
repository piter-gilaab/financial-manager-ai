# Phase 5 — Step 15 Forecasting Readiness

## Status

**BLOCKED.** The current project data cannot support a financially meaningful
Cash Flow Forecast. No forecasting model or synthetic production history is
authorized or justified by this assessment.

The blocking condition is data-semantic, not a limitation of a particular
algorithm: neither current dataset identifies actual movements of cash. An
accounting amount is not automatically cash flow, a debit/credit code is not a
cash-flow direction, and a sales observation is not automatically a receipt.

## Evidence reviewed

This assessment reviewed:

- the approved processed run `20260928T190320706702Z_0a18cf5b`, its manifest,
  validation report, review flags, and both standardized CSV files;
- the loaded SQLite database, schema, and load-validation report;
- the dataset inventory and Receiver General and Company Financials EDA;
- the Phase 3 semantic model and schema documentation;
- the Phase 4 Financial Core, query contracts, and validation report;
- Phase 5 Steps 13 and 14 documentation and validation evidence; and
- the project glossary and current V1 direction.

The cleaning and database validation reports pass representation, lineage, and
round-trip checks. Those checks establish faithful storage, not cash semantics,
currency, economic comparability, or forecasting readiness.

## Readiness assessment

| Requirement | Result | Evidence and consequence |
|---|---|---|
| 1. Actual cash inflows/outflows | **No — blocker** | Receiver General has accounting records that can include voucher and accounting/control summary representations. Its `journal_voucher_item_amount` and `credit_debit_code` do not identify actual cash movements or their direction. Company Financials contains sales observations; `Sales`, `Gross Sales`, `COGS`, and `Profit` are not receipts, payments, or cash movements. Neither source has a verified cash account, settlement event, or bank movement. |
| 2. Clearly defined forecasting target | **No — blocker** | There is no observed `cash_in`, `cash_out`, net cash flow, or cash balance target. Forecast horizon, aggregation scope, account scope, and whether the intended output is flows, closing balance, or both also remain open in the V1 direction. Defining a target from current accounting or sales columns would reinterpret their meaning. |
| 3. Sufficient chronological history | **No** | Receiver General covers 2023-04-03 through 2024-01-03: 276 calendar days, 188 observed dates, and 10 source months, with January represented by only 3 days. Company Financials has 16 consecutive monthly labels from 2013-09 through 2014-12. Even if their semantics were suitable, neither source provides two complete annual cycles for a defensible annual-seasonality assessment. |
| 4. Defensible time frequency | **No** | Receiver General supplies accounting effective dates, not verified cash-value dates. Company Financials dates are first-of-month period labels, not proved sale or receipt dates. The operational forecast cadence and horizon are not defined. Daily, weekly, or monthly cash series cannot be selected from these sources without unsupported reinterpretation. |
| 5. Missing periods understood | **No** | Receiver General has no weekend dates and has 10 unobserved weekdays in its date range: 2023-04-07, 2023-05-22, 2023-07-03, 2023-09-04, 2023-10-02, 2023-10-09, 2023-11-13, 2023-12-25, 2023-12-26, and 2024-01-01. The data has no authoritative business calendar or completeness indicator proving whether an absent date means closure, zero activity, or missing extraction. Company Financials has all 16 dataset-level monthly labels, but monthly row counts vary between 35 and 70; only 2 of 150 segment/country/product combinations cover all 16 periods and the median combination history is 4 periods. An absent combination is not proved to be zero activity. |
| 6. Economic comparability over time | **No — blocker** | Receiver General's exact local row taxonomy and possible summary/detail overlap remain unresolved, as does fiscal/effective-date alignment. Company Financials has no company identity, has unresolved aggregation grain, and has compositionally uneven category histories. These conditions prevent a stable cash population and consistent measurement basis over time. |
| 7. Currency sufficiently known | **No — blocker** | All 9,282 Receiver General rows and all 700 Company Financials rows have `currency_status=UNKNOWN`, with null currency code and evidence. Symbols, country labels, publisher context, and the provisional V1 BRL direction do not establish source currency. Monetary observations cannot be assumed comparable or converted. |
| 8. Meaningful chronological train/test separation | **No** | Dates can be ordered mechanically, but there is no valid cash target to split. Receiver General provides less than one year and Company Financials only 16 months; reserving a meaningful holdout would leave inadequate training history and no supported seasonal comparison. Random splitting would leak future information and is prohibited for this use case. |

The database confirms the same boundary. It stores source/run/quality lineage plus
separate `receiver_general_accounting_record` and
`company_financial_sales_record` tables. It deliberately has no canonical
financial-fact join and no cash movement, cash account, balance, receivable,
payable, settlement, or forecast table. Phase 4 exposes deterministic descriptive
queries only and explicitly does not certify amounts as cash flows or economically
comparable totals. Step 13 rejects cash-flow and forecasting meanings; Step 14's
descriptive anomaly screen does not create cash semantics or temporal labels.

## Current data limitations

The exact blockers are:

1. No verified cash-event source or cash-account scope.
2. No observed forecasting target.
3. Unknown currency for every monetary row.
4. Insufficient history for annual seasonal behavior and a meaningful holdout.
5. No authoritative calendar/completeness contract for absent periods.
6. Unresolved and changing economic population/grain across time.
7. No confirmed link from sales to receipts or from accounting entries to cash
   settlements; no receivable/payable settlement linkage exists.

The current data must remain usable only within its already documented meanings.
It must not be relabeled, signed, aggregated, gap-filled, or duplicated to create
a cash history. In particular:

- do not map Receiver General `DR`/`CR` to `cash_out`/`cash_in`;
- do not map Company Financials `Sales` to `cash_in`;
- do not infer a currency from `$`, country, government provenance, or the
  provisional BRL project direction;
- do not treat an absent period as zero until source completeness and the
  applicable calendar establish that meaning; and
- do not create synthetic production observations to lengthen the history.

## Minimum future dataset requirements

A future readiness review requires an authoritative extract of actual cash
movements or authoritative period-level cash aggregates. It must meet all of the
following gates before model work begins:

- **Cash semantics:** documented evidence that inflows and outflows are settled
  movements in the in-scope financial account(s), not revenue, expense,
  obligation, invoice, order, journal direction, or sales proxies.
- **Target:** approve one primary target before extraction. The recommended
  primary target is period net cash flow, defined exactly as
  `cash_in - cash_out` for settled movements in the declared scope and currency.
  A closing-balance forecast may be a separate target only when authoritative
  opening/closing balances and reconciliation rules are available.
- **Scope and grain:** one consistent company/account perimeter, cutoff rule,
  timezone, settlement-date convention, sign convention, and aggregation rule.
  Transfers between in-scope accounts must be identified or excluded consistently
  so they do not create artificial company-level inflow and outflow.
- **Currency:** an authoritative ISO 4217 currency for every row. A series must
  be modeled per currency unless an approved, dated, fully traceable conversion
  policy creates a separate derived series.
- **Completeness:** a declared calendar and explicit distinction among zero
  activity, closed/non-applicable periods, and missing or partial extraction.
  Corrections, reversals, duplicates, late postings, and backfills need documented
  handling.
- **Comparability:** unchanged definitions and perimeter over the modeling window,
  or explicit break/version metadata that permits defensible segmentation.
- **History:** at least two complete annual cycles before the forecast origin:
  730 consecutive daily periods, 104 consecutive weekly periods, or 24 consecutive
  monthly periods, according to the approved cadence. These are minimum project
  gates, not proof that a model will be adequate. Longer history is required when
  the chosen horizon, sparsity, structural breaks, or seasonal pattern leaves too
  few independent training and evaluation periods.
- **Evaluation reserve:** after data-quality exclusions, retain an untouched
  chronological test window at least as long as the approved forecast horizon;
  the preceding training window must still satisfy the applicable history gate.
- **Lineage:** immutable source identity, extraction time, row or aggregate
  provenance, transformation version, validation result, and reproducible links
  from every modeled period to source evidence.

Receivables and payables are not substitutes for actual cash history. They may
be added later as known-future explanatory inputs only when their identity,
due dates, outstanding amounts, settlement links, currency, and as-of availability
are verified. Features must contain only information available at each historical
forecast origin.

## Proposed future input schema

This is a data-acquisition contract, not a change to either current dataset or
the database. The target grain is one complete period for the approved company/
account scope and one currency. If multiple currencies are present, produce
separate rows/series by currency rather than silently summing them.

| Field | Requirement | Definition and validation |
|---|---|---|
| `date` | Required | Period end (or period label) in an approved daily, weekly, or monthly calendar. Unique and strictly increasing within each scoped currency series; no future timestamp at a forecast origin. |
| `cash_in` | Required | Exact nonnegative sum of actual settled cash inflows during the period, supported by source movement lineage. Never derived from sales or credit journal totals. |
| `cash_out` | Required | Exact nonnegative sum of actual settled cash outflows during the period, supported by source movement lineage. Never derived from expenses, obligations, or debit journal totals. |
| `balance` | Conditionally required | Authoritative closing available-cash balance for the same perimeter, date, and currency. Required if the approved target includes future balance or if flow-to-balance reconciliation is a validation gate; otherwise omit rather than infer. |
| `receivables` | Optional, only if justified | Amount outstanding and eligible under an approved as-of definition at the period cutoff. Requires verified source, currency, due-date/settlement semantics, and point-in-time availability. Not counted as cash in. |
| `payables` | Optional, only if justified | Amount outstanding and eligible under an approved as-of definition at the period cutoff. Requires verified source, currency, due-date/settlement semantics, and point-in-time availability. Not counted as cash out. |
| `currency` | Required | Authoritatively evidenced ISO 4217 code applying to every monetary field in the row. No inferred default. |

Lineage and validation metadata must accompany the dataset in a separate manifest
rather than being discarded or encoded as monetary observations. The manifest
must identify source files/systems and hashes or immutable versions, extraction
cutoff, company/account perimeter, calendar, timezone, field definitions,
aggregation and transfer policy, transformation version, row counts, period
coverage, missing-period classifications, corrections, and validation outcomes.

For each row, validate `cash_in >= 0`, `cash_out >= 0`, finite exact decimal
representation, one confirmed currency, and no duplicate period within the same
scope. Define derived `net_cash_flow = cash_in - cash_out` in the modeling layer,
not as a fabricated source field. When `balance` is available, reconcile adjacent
balances to net cash flow plus explicitly documented non-flow adjustments; never
force a balance by editing source movements.

## Frequency and target decision gate

Frequency must follow both the source evidence and the operational decision:

- choose **daily** only when settlement dates, non-business-day treatment, and
  daily completeness are authoritative and the decision needs daily liquidity;
- choose **weekly** only with a fixed week boundary and consistent aggregation;
- choose **monthly** only when month-end cutoff and calendar are stable and the
  horizon is useful for the intended treasury decision.

Do not upsample monthly observations to daily or call accounting-effective dates
cash-value dates. If daily cash movements are authoritative, weekly or monthly
aggregates may be derived reproducibly; the reverse is not true.

Before modeling, approve and version:

1. primary target (`net_cash_flow` is recommended for first readiness);
2. scope and currency;
3. frequency and calendar;
4. forecast horizon and forecast-origin schedule;
5. treatment of transfers, reversals, missing periods, and structural breaks;
6. required decision tolerance and evaluation metric.

## Future modeling plan

Only after every readiness gate passes, progress in this order:

1. **Naive baseline:** use the smallest auditable baseline appropriate to the
   approved frequency, such as last observed period and a matching seasonal-naive
   baseline when at least two complete seasonal cycles exist.
2. **Moving average / exponential smoothing:** compare simple rolling and level,
   trend, or seasonal smoothing variants only where history supports their
   components.
3. **Statistical time-series method:** consider a documented statistical model
   only after diagnostics show that it addresses behavior the baselines miss.
4. **Machine learning:** consider ML only if materially more history, valid
   point-in-time explanatory variables, repeated backtests, and a demonstrable
   improvement over simpler models justify the added complexity.

Every stage must require:

- chronological train/validation/test separation or rolling-origin backtesting;
- no random split and no fitting of transformations, imputation, feature
  selection, or hyperparameters on future periods;
- prevention of target and as-of leakage, especially from later settlements,
  corrected balances, receivables, and payables;
- comparison against the approved naive baseline on identical forecast origins;
- an evaluation metric approved before test evaluation (recommended starting
  metrics: MAE in confirmed currency plus WAPE only when its aggregate denominator
  is nonzero; avoid MAPE when actual net flows can be zero or negative);
- an explicit forecast horizon and performance reported by horizon step;
- uncertainty intervals with empirical coverage checked by horizon, without
  presenting them as guarantees;
- lineage for the input snapshot, target build, features, split boundaries,
  model/configuration, code/version, forecast origin, and outputs; and
- documented abstention or fallback behavior for incomplete periods, unknown
  currency, broken reconciliation, or data outside the validated perimeter.

Model complexity does not repair missing cash semantics, unknown currency,
insufficient history, or inconsistent scope.

## Validation required before status can become READY

The next readiness review must produce evidence that:

1. source documentation and sampled lineage establish actual settled cash flows;
2. the approved target recomputes exactly from the validated period data;
3. every period in the declared interval is classified as observed zero,
   observed nonzero, closed/non-applicable, missing, or partial;
4. currency is confirmed and no unsupported cross-currency aggregation occurs;
5. balance reconciliation passes where balance is in scope, with every allowed
   adjustment separately evidenced;
6. duplicates, reversals, internal transfers, late postings, and corrections are
   handled by approved deterministic rules without losing lineage;
7. the economic perimeter and definitions are stable or breaks are explicitly
   versioned and excluded/segmented;
8. the minimum history remains after quality exclusions and the untouched test
   window is at least one forecast horizon; and
9. a reproducible chronological split can be frozen before any test-set scoring.

Failure of any cash semantics, target, currency, completeness, comparability,
history, or chronological-evaluation gate keeps the stage **BLOCKED**.

## Exact next step

Obtain and document an authoritative actual-cash source for the intended company
and account perimeter, using the proposed schema and manifest requirements. Then
run a new, separately authorized data-quality and forecasting-readiness review.
Do not implement even the naive baseline until that review changes this status
to **READY**.

## References

- [Project glossary](../CONTEXT.md)
- [V1 direction](planning/v1-direction.md)
- [Semantic data model](data_model.md)
- [Database schema](database_schema.md)
- [Financial Core](financial_core.md)
- [Phase 4 validation](phase4_validation.md)
- [Financial Analysis Agent](financial_analysis_agent.md)
- [Step 13 validation](step13_validation.md)
- [Anomaly detection](anomaly_detection.md)
- [Step 14 validation](step14_validation.md)
- [Dataset inventory](../notebooks/01_dataset_inventory.ipynb)
- [Receiver General EDA](../notebooks/02_eda_receiver_general.ipynb)
- [Company Financials EDA](../notebooks/03_eda_company_financials.ipynb)
