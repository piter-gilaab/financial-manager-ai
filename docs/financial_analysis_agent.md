# Financial Analysis Agent — Step 13

## Readiness and scope

**READY and implemented for Step 13 only.** The approved Financial Core already
provides the 17 deterministic, read-only contracts, request validation, exact
decimal serialization, query-scoped quality disclosures and snapshot lineage
required for orchestration. No Phase 4 interface or semantic change was necessary.

Authority is [query contracts 1.0](query_contracts.md), the implemented
`src/financial/contracts.py` and `src/financial/filters.py`, and the
[Financial Core](financial_core.md). Prior evidence is in
[Phase 4 validation](phase4_validation.md). The explicit Step 13 implementation
request authorizes this work beyond the historical planning-only guidance.
Earlier provisional BRL/company assumptions in planning documents do not override
the actual data model: denominations remain UNKNOWN and company identity is absent.

This is one orchestrator, not a multiagent system. It ships a conservative local
English interpreter and deterministic explanations. No LLM model, credentials,
network adapter or new dependency is installed. Anomaly detection, forecasting,
RAG and application interfaces are not available capabilities.

## Interface and execution

```python
from src.agents import FinancialAnalysisAgent

agent = FinancialAnalysisAgent()
answer = agent.ask("Amounts by department in May 2023")
print(answer["explanation"]["text"])
evidence = answer["tool_result"]

# Explicit context resolves otherwise ambiguous questions.
count = agent.ask("How many records are there?", dataset="receiver_general")

# Typed options expose approved membership/null/quality policies without prose parsing.
sales = agent.ask(
    "Sales by product in 2014",
    parameters={
        "filters": {"country": {"in": ["Canada", "France"]}},
        "quality_detail": "full",
    },
)
```

`FinancialAnalysisAgent(core=None, provider=None)` accepts an existing
`FinancialCore` instance and an interpretation provider. Defaults use the
approved project database and `LocalQuestionProvider`. `ask(question, *,
dataset=None, parameters=None)` returns a JSON-safe dictionary. Calls are
stateless: clarify by submitting a complete question with explicit context.

Execution order:

1. Fully interpret the question through the closed grammar; reject unsupported
   meanings or ask for clarification before any provider/tool call.
2. Validate the grounded intent with Phase 4's existing normalizer.
3. Ask the local provider for a `ToolIntent`; validate that proposal and require
   normalized equivalence with the grounded question. Extra provider-invented
   filters, changed measures, datasets or tools cannot reach execution.
4. Merge explicit `parameters`. Conflicting textual and structured constraints
   require clarification; no constraint silently wins. Prefer supplying an option
   in one place, even for differently spelled equivalent predicates/periods.
5. Reuse Phase 4 normalization, then call only `FinancialCore.query`, which performs
   final validation and its existing read-only snapshot checks.
6. Copy the complete tool evidence and render an explanation without arithmetic
   or model rewriting. Unexpected internal errors propagate; expected request
   errors and declared provider failures are structured responses.

The agent contains no database connection, SQL execution, financial arithmetic,
FX conversion, dynamic tool discovery or arbitrary function dispatch. Integer
parsing is limited to request fields such as year, month and retrieval limit.

## Registry and supported questions

The explicit 17-name allowlist prevents future Core additions from becoming
automatically agent-accessible. Its metadata derives dataset, options, filters,
measure/group defaults and monetary classification from the existing Core
registry, with a reference to contract version 1.0 and interpretation limits.
`agent.registry.catalog()` returns a serializable metadata catalog.

| Contract | Example question | Core function suffix |
|---|---|---|
| RG-01 | Receiver General record count | `record_count` |
| RG-02 | Receiver General amount summary | `amount_summary` |
| RG-03 | Amounts by debit/credit | `amount_by_debit_credit` |
| RG-04 | Amounts by voucher type | `amount_by_voucher_type` |
| RG-05 | Amounts by department | `amount_by_department` |
| RG-06 | Receiver General amounts by month | `amount_by_period` |
| RG-07 | Amounts by general ledger account | `accounting_dimension_summary` |
| RG-08 | Receiver General highest 5 amounts | `extreme_amount_records` |
| CF-01 | Company Financials record count | `record_count` |
| CF-02 | Sales summary | `sales_summary` |
| CF-03 | Sales by month | `sales_by_period` |
| CF-04 | Sales by country | `sales_by_country` |
| CF-05 | Sales by segment | `sales_by_segment` |
| CF-06 | Sales by product | `sales_by_product` |
| CF-07 | Profit summary | `profit_summary` |
| CF-08 | Discount analysis | `discount_analysis` |
| CF-09 | Units sold summary | `units_sold_summary` |

Full function names prepend `receiver_general_` or `company_financials_`.
RG-07 also accepts subledger account, financial coding block and control data
type. RG-08 accepts lowest/smallest as well as highest/largest/top and a Core-
validated limit. Extreme records remain descriptive records, not anomalies.

The local grammar supports:

- Dataset names, `RG`/`CF` aliases or exact `dataset` context. Sales/profit/units
  and accounting-specific dimensions provide domain evidence; generic counts or
  amounts need a dataset. Conflicting contexts and both-dataset requests do not
  run a query.
- Polite prefixes such as `Show me` and `What is the`; trailing question marks.
- `total`, `sum`, `mean`/`average`, `median`, `min`/`minimum`, `max`/`maximum`
  where the selected contract permits them. Grouped contracts remain count/sum.
  Discount/profit contracts retain their documented fixed result fields.
- CF measures `gross sales`, `discounts`, `sales`, `COGS`/`cost of goods sold`,
  and `profit`, joined by commas or `and`. Units Sold uses its own quantity tool.
- One approved `by`/`per` grouping. Day/month/year apply to accounting chronology;
  Company Financials remains monthly or yearly. `daily`/`monthly`/`yearly` are
  equivalent period-group prefixes where the contract supports them.
- A trailing `in 2014`, `in May 2023`, or
  `from 2014-01-01 to 2014-12-31`, before any `where` clause. Bounds are inclusive;
  calendar validity and CF monthly boundaries use the Core validator. A month
  without a year, or a relative date such as `last month`, requires clarification.
- A final `where field="Exact source value"`, optionally joined with `and`.
  Public filter names accept spaces or underscores; `debit/credit` maps to
  `debit_credit`. Bare digits preserve identifier strings except `fiscal month`,
  which requires an integer. Quoted values retain original spelling and case.
  Example: `Amounts by department in May 2023 where fiscal month=12` keeps
  fiscal and chronological constraints independent.
- Other approved equality/membership/null policies, missing-dimension behavior,
  statistics and quality detail via the `parameters` object. Unknown keys,
  SQL fragments and contract-identity overrides are rejected by the existing
  validation rules. Quoted SQL-shaped category values stay literal filter values.

This is a deliberately bounded language interface, not general natural-language
understanding. An unconsumed clause triggers clarification; it is never discarded
while executing a partial interpretation. For example, `sales for Canada` asks
for a supported filter form instead of silently returning worldwide sales.

## Unsupported meanings

The guard and contract validation enforce the
[unsupported-query catalog](query_contracts.md#12-unsupported-questions-and-qualified-alternatives).
Examples include revenue/expenses from DR/CR, balance sheets, company rankings,
cash flow, unique business-event counts, combined dataset monetary totals,
currency conversion, monetary ratios/growth, and fraud/anomaly conclusions.
Later capabilities such as forecasting and document retrieval are unavailable.
Unrecognized wording receives clarification rather than an invented answer.

The guard is conservative: ambiguous business terms can require rephrasing with
the documented record/measure vocabulary. It does not certify arbitrary user
language as a valid business interpretation. It also rejects instructions to
suppress required warnings. Quoted source-category literals are data, not instructions.

## Evidence and response model

Agent envelope version: `agent_version: "1.0"`.

| Field | Meaning |
|---|---|
| `agent_status` | Orchestration outcome below; never overwrites Core status |
| `tool_request` | Exact controlled request submitted to the Core, or null |
| `tool_result` | Complete copied Core envelope, or null if no tool ran |
| `evidence_sha256` | SHA-256 of canonical JSON tool evidence, or null |
| `explanation` | `method: deterministic_template` and explanation text |
| `clarification` | Question, field, code and optional choices, or null |
| `errors` | Pre-execution agent/validation errors; Core errors stay in evidence |

| Agent status | Meaning |
|---|---|
| `ANSWERED` | Tool returned SUCCESS, PARTIAL or NO_DATA; read the preserved Core status |
| `TOOL_REJECTED` | Tool returned INVALID_REQUEST, UNSUPPORTED or DATA_QUALITY_BLOCKER |
| `CLARIFICATION_REQUIRED` | Missing, conflicting, ambiguous or unconsumed intent; no tool ran |
| `INVALID_REQUEST` | Invalid question/arguments, unknown tool or reserved identity; no tool ran |
| `UNSUPPORTED` | Unsupported meaning or operation found before execution |
| `PROVIDER_UNAVAILABLE` | Nonlocal provider transport is disabled in Step 13 |
| `PROVIDER_ERROR` | Declared provider failure or proposed intent disagrees with question |

Malformed provider intents use INVALID_REQUEST. Declared provider exceptions
produce a generic message without exposing private exception content. The agent
does not automatically retry or substitute another tool.

The explanation renders exact decimal strings without parsing, rounding or
currency symbols. Every result field, record accounting field, warning and
returned flag is retained in the rendering; large group/full-quality responses
can therefore be verbose. Metadata, lineage and diagnostics remain complete in
`tool_result`. The original Core object is not mutated or given to the provider.
Returned dictionaries are caller-owned copies; the digest detects changes when
compared with a trusted original but is not a signature or a tamper-proof store.

PARTIAL and NO_DATA are not recast as financial success. Missing values stay
null, negative Profit remains valid, the 53 Discounts and 5 Profit placeholders
remain unresolved, and sparse dimension coverage is visible. Monetary currency
is UNKNOWN/code null; counts and Units Sold have no monetary currency metadata.

## Provider and privacy interface

`IntentProvider.interpret(InterpretationRequest) -> ToolIntent` is independent of
any model vendor. The request is immutable and contains only question, explicit
dataset context and static approved tool metadata. The proposal carries a tool
name and strict JSON object arguments; duplicate keys and nonfinite values are
rejected. Providers do not receive database handles, tool results, records,
quality evidence, or the separate structured `parameters` object.

The bundled `LocalQuestionProvider` implements the supported grammar without an
LLM. Tests additionally exercise a deterministic fake provider. Custom local
providers must agree with the grounded interpretation; plugging in an LLM does
not automatically widen the supported language or capabilities. Widening that
grammar requires new intent-grounding tests and an explicit semantic review.

Location concepts distinguish LOCAL, PRIVATE and EXTERNAL. Only LOCAL executes
in this step. PRIVATE/on-prem and EXTERNAL transports are extension points, with
no concrete client, credentials or automatic fallback. Their invocation is
rejected before any provider method is called. A future approved adapter must
define its data permissions and minimize context; questions themselves may be
sensitive even though database evidence is excluded.

Database, processed data, question/filter values and returned evidence stay in
the local sensitive zone. The shipped code has no network operations or prompt
logging. Provider injection is trusted application configuration, not a user
argument; this interface is not an operating-system sandbox for arbitrary Python
provider code. Local model integrations must be audited to uphold the declared
location and avoid telemetry. Offline tests disable socket creation while
performing a real Financial Core query through a fake provider.

## Validation and remaining limits

See [Step 13 validation](step13_validation.md) for exact regression results and
protected-file checks. The existing dataset limitations documented in Phase 4
continue unchanged: unresolved denomination/provenance/grain and comparability,
fiscal alignment, summary/detail overlap, sparse dimensions, sales-record company
identity absence, fractional quantity semantics and unresolved placeholders.

There is no conversational memory, general date parser, trained/local model
runtime, hosted model client, or model-generated explanation. The callable Python
interface is ready for a separately scoped CLI or future Financial Manager;
this step adds no application interface. No Step 14 or later work is implemented.
