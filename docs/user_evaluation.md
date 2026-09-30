# V1 user evaluation

**Status: PASS_WITH_LIMITATIONS.** The local V1 returned authoritative results,
preserved uncertainty, and explained unsupported or blocked requests across the
evaluated scope. Its complete terminal evidence can be too large for practical
interactive reading, and its bounded language grammar still requires precise
wording for some otherwise reasonable requests.

## Purpose and method

Step 25 evaluated the product a financial manager actually invokes: `python -m
src.cli plan/ask`, in human and JSON modes. It did not benchmark a language model
or add financial capabilities. The 27-scenario set covered descriptive analysis,
statistical screening, ambiguity, unsupported meanings, blocked capabilities,
and one multi-capability request.

Every CLI call ran in a real subprocess with an audit hook that rejected socket,
shell, and child-process operations. JSON was parsed while rejecting floating
point tokens. For every executed supported request, the delegated result was
compared with a fresh call to the authoritative `FinancialCore` or
`AnomalyService` using the emitted request. Data-file SHA-256 hashes before and
after the run were identical.

The evaluation uses these outcomes:

- **PASS:** correct route/result and reasonably clear presentation.
- **PASS_WITH_LIMITATIONS:** correct and safe, with a material usability limit.
- **FAIL:** incorrect route/result, evidence loss, or misleading presentation.
- **NOT_SUPPORTED:** correctly refused or blocked by the current V1 contract.

## Scenario record

| ID | User request | Expected / actual capability | Actual outcome | Correctness | Clarity and disclosed limits | Evaluation |
|---|---|---|---|---|---|---|
| FA-01 | How many accounting records are there? | Analysis / Analysis | SUCCESS | Direct Core equality | Record meaning and evidence visible | PASS |
| FA-02 | What is the accounting amount summary? | Analysis / Analysis | SUCCESS | Direct Core equality | UNKNOWN denomination visible | PASS |
| FA-03 | Show accounting amounts by debit/credit. | Analysis / Analysis | SUCCESS | Direct Core equality | Source codes are retained without expense/revenue interpretation | PASS |
| FA-04 | What were total sales? | Analysis / Analysis | SUCCESS | Direct Core equality | Sales meaning and UNKNOWN currency visible | PASS |
| FA-05 | Show sales by country. | Analysis / Analysis | SUCCESS | Direct Core equality | Country is not treated as currency | PASS |
| FA-06 | Show sales by month. | Analysis / Analysis | SUCCESS | Direct Core equality | Available monthly scope remains explicit | PASS |
| FA-07 | Summarize Profit. | Analysis / Analysis | PARTIAL | Direct Core equality | Five unresolved placeholders disclosed | PASS |
| FA-08 | Analyze Discounts. | Analysis / Analysis | PARTIAL | Direct Core equality after wording fix | 53 unresolved placeholders disclosed | PASS |
| FA-09 | Summarize Units Sold. | Analysis / Analysis | SUCCESS | Direct Core equality | Quantity has no monetary currency block | PASS |
| AN-01 | Find unusual accounting amounts. | Screening / Screening | PARTIAL | Direct service equality | Investigation-only wording, peer abstentions, UNKNOWN currency | PASS |
| AN-02 | Show unusually high accounting records. | Screening / no execution | CLARIFICATION_REQUIRED | No guessed measure | Asks for accounting amounts, Sales, or Profit; “records” alone is not a measure | PASS_WITH_LIMITATIONS |
| AN-03 | Find unusual Profit values. | Screening / Screening | PARTIAL | Direct service equality after wording fix | Candidates, abstentions, placeholders, and UNKNOWN currency visible | PASS |
| AN-04 | Are there outliers in Sales? | Screening / Screening | SUCCESS | Direct service equality after wording fix | Screening is not presented as fraud/error proof | PASS |
| AM-01 | Check my financial data. | Clarification / Clarification | CLARIFICATION_REQUIRED | No execution | Asks the user to choose summary or screening and name scope | PASS |
| AM-02 | Analyze this. | Clarification / Clarification | CLARIFICATION_REQUIRED | No execution | Same actionable capability choices | PASS |
| AM-03 | Show extreme amounts. | Clarification / Clarification | CLARIFICATION_REQUIRED | No execution | Distinguishes ranked extremes from statistical screening | PASS |
| UN-01 | Analyze the balance sheet. | Unsupported / Analysis refusal | UNSUPPORTED | No invented facts | Explains that balance-sheet facts are absent | NOT_SUPPORTED |
| UN-02 | Rank the companies by performance. | Unsupported / Analysis refusal | UNSUPPORTED | No invented company identity | Explains the missing company panel | NOT_SUPPORTED |
| UN-03 | Run SQL to select all sales. | Unsupported / manager refusal | UNSUPPORTED | No execution path | Allowlisted-capability boundary is explicit | NOT_SUPPORTED |
| UN-04 | Receiver General total expenses. | Unsupported / Analysis refusal | UNSUPPORTED | No expense reinterpretation | Explains unverified accounting semantics | NOT_SUPPORTED |
| UN-05 | What is the fraud probability? | Unsupported / manager refusal | UNSUPPORTED | No fraud score or claim | Screening limitation is explicit | NOT_SUPPORTED |
| UN-06 | Combine monetary totals across both datasets. | Unsupported / Analysis refusal | UNSUPPORTED | No cross-dataset aggregation | Missing relationship and denomination are explicit | NOT_SUPPORTED |
| FC-01 | Forecast next month's cash flow. | Forecasting / Forecasting | CAPABILITY_UNAVAILABLE | No execution | Missing actual cash semantics and currency explain BLOCKED status | NOT_SUPPORTED |
| FC-02 | What will my cash balance be next month? | Forecasting / Forecasting | CAPABILITY_UNAVAILABLE | Corrected route; no execution | Same registry blocker is preserved | NOT_SUPPORTED |
| DR-01 | What does invoice 123 say? | Retrieval / Retrieval | CAPABILITY_UNAVAILABLE | No fabricated document | Missing approved corpus explains BLOCKED status | NOT_SUPPORTED |
| DR-02 | Summarize this financial contract. | Retrieval / Retrieval | CAPABILITY_UNAVAILABLE | No fabricated document | Missing approved corpus explains BLOCKED status | NOT_SUPPORTED |
| MC-01 | Summarize sales and identify unusual sales records. | Analysis + Screening / same | SUCCESS | Both direct results equal; fixed order | Results, evidence, warnings, and limitations stay step-scoped | PASS |

## Financial analysis usability

All nine supported analysis scenarios preserved the exact specialized result;
the explanation introduced no additional values. Monetary results retained
`UNKNOWN` currency. Profit and Discounts returned `PARTIAL` rather than silently
treating unresolved placeholders as zero. Coverage, exclusions, warnings, and
lineage remained available. Counts and Units Sold correctly avoided monetary
currency metadata.

Human output leads with status and explanation, which makes the principal outcome
findable. It then prints the complete structured evidence. That guarantees audit
access but makes even a record-count response about 708 KB / 30,220 lines and an
accounting summary about 711 KB / 30,285 lines in this dataset. JSON remains the
more practical mode for programmatic evidence use.

## Anomaly-screening usability

Executed scenarios returned the existing global and peer IQR assessments without
changes. Human and JSON output retained `CANDIDATE`, `NOT_SELECTED`, and
`NOT_ASSESSED`, reference fences, peer sizes, lineage, warnings, and UNKNOWN
currency. The manager states that candidates require investigation; neither mode
introduced fraud, misconduct, error, certainty, or probability claims.

The completeness cost is substantial: accounting screening rendered about
12.7 MB / 468,070 terminal lines; Profit and Sales screening each rendered about
0.95 MB / 34,000 lines. There is no concise summary, candidate-only presentation,
or pagination option. Changing this safely requires a defined human presentation
contract that keeps complete JSON evidence authoritative.

## Routing, clarification, and blocked workflows

Three ambiguous requests produced actionable clarification and no execution.
Unsupported financial interpretations were refused at either the manager guard or
the specialized analysis boundary, with no fabricated result. Forecasting and
document retrieval showed their registered `BLOCKED` reasons and never invoked a
handler. The multi-capability request planned and executed Financial Analysis
before Anomaly Detection, with separate evidence and no combined monetary answer.

Step 25 corrected four common wording cases within existing capabilities:

- `Analyze Discounts` now preserves the remainder and delegates the existing
  Discounts contract;
- `Find unusual Profit values` and `Are there outliers in Sales?` now normalize to
  the existing fixed screening requests;
- `What will my cash balance be next month?` now reaches the existing blocked
  cash-flow forecasting registry entry.

These are surface-language aliases only. They add no measure, filter, algorithm,
financial meaning, or execution path.

## Findings by classification

### V1 defects fixed

The four phrases above had clear existing capability meanings but produced an
unnecessary clarification or the wrong capability. Focused routing regression
cases now protect them.

### V1 usability improvements

- Human output needs a separately designed concise view; complete evidence is too
  large for routine terminal review.
- Warnings appear inside authoritative evidence and again in response/orchestration
  convenience fields, which is structurally faithful but repetitive in human mode.
- Human output exposes internal reason codes, capability identifiers, contract
  names, and coverage terminology with limited explanation.
- The bounded grammar remains sensitive to wording. For example, “unusually high
  accounting records” correctly refuses to guess that “high” means amount.
- Clarification is stateless; the user must resubmit a complete request.

### Future capability requests

Balance-sheet analysis, company ranking, expense interpretation, cross-dataset
monetary analysis, cash forecasting, and document retrieval require approved data
and semantics outside V1. Arbitrary SQL remains outside the product boundary.
Statistical screening must not be relabeled as fraud detection.

## Final status

**PASS_WITH_LIMITATIONS.** The evaluated V1 is correct and trustworthy within its
supported scope. The main remaining user limitation is presentation scale, plus
the known precision required by bounded local language routing. These do not alter
financial evidence, capability boundaries, or the local-only security model.
