# Phase 6 — Step 18: capability routing and orchestration

`FinancialManagerAgent.ask(question)` adds local, deterministic top-level routing
to the existing manager. `plan(question)` previews the same decision without
executing services. Explicit `execute(capability=..., request=...)` remains
unchanged and never switches capabilities. This is one facade composing existing
modules, with no new LLM, financial calculation or autonomous agent framework.

```python
from src.manager import Capability, FinancialManagerAgent

manager = FinancialManagerAgent()
preview = manager.plan("What were total sales by country?")
answer = manager.ask("What were total sales by country?")
both = manager.ask(
    "Summarize sales by country and identify unusual sales records"
)
blocked = manager.ask("Forecast cash flow for next month")

# Existing explicit interface; no automatic routing or scope inference.
filtered_screen = manager.execute(
    capability=Capability.ANOMALY_DETECTION,
    request={"analysis_version": "1.0", "dataset": "company_financials",
             "measure": "sales", "period": {"year": 2014, "month": 5}},
)
```

## Boundaries and registry

```text
question → routing.py → immutable plan → orchestration.py
    → FinancialManagerAgent.execute → Step 17 registry
        → Step 13 FinancialAnalysisAgent.ask → approved Financial Core
        → Step 14 AnomalyService.analyze
    → separate complete manager responses + explanations
```

Routing performs no service execution, database access or arithmetic.
Orchestration executes only through the existing manager's public `execute`.
Every selected capability and its availability/reason come from the Step 17
allowlist. There is no dynamic registration, import/function discovery, SQL,
shell execution, filesystem access or caller-supplied executable plan.

| Capability | Current state | Automatic path |
|---|---|---|
| FINANCIAL_ANALYSIS | AVAILABLE | Pass the question to Step 13; it chooses among the 17 approved contracts |
| ANOMALY_DETECTION | AVAILABLE | Minimal request adapter for existing RG accounting amount / CF Sales / CF Profit screening |
| CASH_FLOW_FORECASTING | BLOCKED | Return registry blocker: no authoritative actual cash inflows/outflows and unresolved currency |
| DOCUMENT_RETRIEVAL | BLOCKED | Return registry blocker: no approved production financial-document corpus; implementation DEFERRED despite documented architecture |

Top-level routing does not select RG/CF contract IDs or infer the analysis dataset,
filters, grouping or aggregation. Step 13 retains responsibility for these and
for final Core validation. The only analysis language normalization is an anchored
`summarize/summarise` → `Show` or `What were/was` → `What are` prefix, retaining
all remaining words and source category values. Original clauses are also kept.

## Deterministic grammar and routing outcomes

The default grammar is bounded English, not unrestricted language understanding.
Nonempty strings up to 4,000 characters are accepted. Malformed types, blank/long
questions and unbalanced double quotes produce `INVALID_REQUEST`. Double-quoted
category values are masked during intent classification and splitting, then
passed intact to Step 13. They cannot introduce a capability or executable step.

| Intent / example | Decision |
|---|---|
| `Sales by country`, `Receiver General amount summary`, `Discount analysis`, `Show highest accounting amounts` | FINANCIAL_ANALYSIS; Step 13 owns the query decision |
| `Find outliers in Profit`, `Show unusually high accounting amounts`, `Screen sales`, `Compare Sales to supported peer groups` | ANOMALY_DETECTION, within the target grammar below |
| `Forecast cash flow for next month`, `Predict cash balance` | CASH_FLOW_FORECASTING / BLOCKED |
| `What does invoice 123 say?`, `Search financial reports`, `Read this PDF` | DOCUMENT_RETRIEVAL / BLOCKED |
| `Check this financial data`, unknown purpose, `Show extreme amounts` | CLARIFICATION_REQUIRED; ranked extremes and statistical screening are distinct |
| Fraud/error conclusions, investment advice, arbitrary execution, unsupported prediction targets | UNSUPPORTED, without execution |
| Balance-sheet amounts, best company, RG expenses/revenue, conversion, combined dataset totals | FINANCIAL_ANALYSIS when clearly descriptive; Step 13 retains its unsupported-semantic response |

Forecasting/document intent is never substituted with descriptive analysis.
Negation, exclusions and dependencies such as `then`, `those`, `same` or `based on`
require clarification. Overlapping forecasting/document/screening intent in one
clause also requires clarification. No probability or fabricated confidence score
is introduced. Keyword recognition may conservatively clarify unfamiliar wording;
it does not promise to understand every equivalent English request.

### Screening adapter scope

Automatic screening accepts a complete, unfiltered request for **accounting
amounts**, **Sales** or **Profit**, optionally prefixed with the matching dataset
name (`Receiver General`/`RG` or `Company Financials`/`CF`). It recognizes:

- `show/find/identify/detect/screen unusual TARGET` (also unusually high/low,
  anomalous, outlying; optional `values` suffix);
- `find/identify/detect/show/screen outliers/anomalies/anomaly candidates/unusual values in/for/among TARGET`;
- `are there [any] outliers/anomalies/anomaly candidates/unusual values in TARGET`;
- `screen [extreme] TARGET [for outliers/anomalies/anomaly candidates/unusual values]`;
- `compare TARGET to/with [their/supported] peers/peer groups`.

The entire clause must match. Optional `please`, terminal question mark/period,
and `records` after the target are accepted. Filters, dates, custom peer definitions,
algorithms, ranking limits and other unconsumed modifiers cause clarification;
they are never removed to create an unfiltered execution. Use the existing
explicit request API for approved filters/periods. Conflicting dataset/measure
labels are unsupported. The adapter uses Step 14's existing pure request validator.

There is no new anomaly configuration: RG retains upper-tail IQR with
debit/credit × voucher type peers; CF retains both-tail IQR with segment × sale
price peers, minimum 30 numeric records and the existing positive-IQR requirement.
Global and peer results are both returned completely. A high/low Sales/Profit
request carries a plan note that **both tails are returned without filtering**;
it does not change the baseline or trim evidence. Low-accounting screening is
explicitly unsupported because the current service screens only the upper tail.

## Routing plan version 1.0

Internal `RoutingPlan`/`PlanStep` records are frozen; normalized request objects
are stored as JSON text and materialized separately for execution. Public previews
are detached JSON-safe dictionaries. `ask` always builds a fresh plan from the
question; modifying a preview cannot inject an execution target or arguments.

The routing dictionary contains:

- `routing_version`, `original_request`, `status`, `reason_code`, `message`;
- `steps`: stable `step_id`, complete registry capability metadata, `original_clause`,
  `normalized_request`, step reason and scope `notes`;
- `clarification`: field, question and optional choices, or null;
- `blockers`: unavailable capability metadata with the registry's exact reasons.

Statuses are `ROUTED`, `MULTI_CAPABILITY`, `BLOCKED`, `CLARIFICATION_REQUIRED`,
`UNSUPPORTED`, `INVALID_REQUEST`. Only the first two are executable. A rejected
plan may preserve already identified steps for inspection, but none runs. Registry
DEFERRED, if introduced later, also produces a non-executable BLOCKED plan while
preserving DEFERRED in capability metadata. Availability is checked again by
`execute`, preserving the existing boundary.

## Bounded multi-capability policy

At most **one available Financial Analysis clause and one available Anomaly
Detection clause** may execute. Separate independent clauses with a semicolon,
or `and` followed by an explicit command such as `summarize`, `identify`, `screen`
or `show`. Separators inside quoted categories are ignored. Bare measure/filter
conjunctions stay with Step 13. More clauses, repeated capabilities, unavailable
combinations, interdependent scopes or unsupported screening modifiers require
clarification before any execution.

Execution order is always Financial Analysis, then Anomaly Detection, including
when the input states screening first. Each gets its own original clause-derived
request. Neither explanations, outputs, filters nor inferred scope flow from one
step to another. For example, `Sales by country; screen sales` screens the whole
Sales dataset, as explicitly recorded in the plan notes, not each country result.

SUCCESS, PARTIAL and NO_DATA allow the next independent step to execute. Any
clarification, expected rejection, quality blocker or provider failure stops
remaining steps and records them as `not_performed`. Completed results remain
intact. Unexpected implementation exceptions propagate; there is no retry,
fallback, rollback or synthesized successful response.

## Orchestration response version 1.0

| Field | Meaning |
|---|---|
| `orchestration_version`, `original_request`, `routing` | Original input and full inspectable routing decision |
| `execution_state` | NOT_PERFORMED, PERFORMED, or PARTIALLY_PERFORMED when a prior step halted remaining work |
| `execution_status` | Single delegate's effective status; for rejected plans the routing status (BLOCKED maps to CAPABILITY_UNAVAILABLE) |
| `results` | Ordered `{step_id, capability, response}` entries; response is the complete original Step 17 envelope |
| `not_performed` | Planned steps not called, with reason |
| `explanations` | Step-scoped original manager summaries, without new financial calculations |
| `warnings`, `errors` | Step-scoped copied lists; plan-level errors use null step ID |
| `limitations` | Step-scoped registry limitations; specialized limitations also remain in original evidence |
| `clarification`, `clarification_step_id` | Routing clarification or unchanged specialized clarification and its step |

For two completed steps, identical statuses remain that status; differing
SUCCESS/PARTIAL/NO_DATA statuses produce orchestration PARTIAL. This is a workflow
outcome, not a combined financial coverage measure. A halted delegated status is
preserved directly. Always inspect each separate response for its precise outcome.

Complete financial values, exact decimal strings (and trusted adapter Decimal
objects), counts, exclusions, quality coverage, flags, currency state, digests,
anomaly assessments, peers, fences, warning references and lineage are copied
without normalization. No numerical outputs are combined. Convenience warnings
and explanation text are independent copies and cannot mutate nested evidence.
Changing public dictionaries is possible; copying is object isolation, not a
tamper-proof audit store or a Step 19 security implementation.

Screening explanations retain Step 17's distinction: CANDIDATE means investigation
candidate; NOT_SELECTED establishes no validity finding; NOT_ASSESSED remains an
abstention. No fraud/error probability or confirmed-anomaly conclusion is produced.

## Local operation and remaining limits

No network, external model/provider, external FX, telemetry, credentials, document
upload, web search, dependency installation or database write was added. Tests use
local stubs and actual read-only services, including socket-disabled operation.
Injected services remain trusted application configuration, not user-controlled
plugins. No new provider abstraction or Step 19 framework is needed here.

The router is stateless: clarification replies must be resubmitted as complete
requests. Step 13's bounded grammar, unknown denomination, missing values and
unresolved placeholders remain unchanged. Screening remains exploratory in-sample
IQR with documented sparse/minimum-group limitations, not a validity judgment.
No entity identity, cash semantics or cross-dataset relationship is invented.
Forecasting and document retrieval remain blocked. [Step 19](security_privacy_boundaries.md)
adds data-only message and controlled error checks; API/frontend, authentication
and deployment remain unimplemented.

See [Step 18 validation](step18_validation.md) for focused/regression results and
protected-file checks. Routing/orchestration have their own version 1.0; Step 17,
Step 13, Step 14 and Core response contracts retain their existing versions.
