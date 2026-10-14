# Financial Manager AI V1 Scope Freeze

Status: **FROZEN** at Phase 18 Step 70 on 2026-10-14.

This document defines the implemented V1 release scope. Historical planning and
phase contracts remain useful evidence, but they do not expand this freeze. Code,
validated contracts and current deterministic behavior take precedence over an
older roadmap statement.

## V1 product definition

Financial Manager AI V1 is a local-first financial analysis system that:

- ingests bounded local CSV and constrained XLSX financial datasets;
- profiles their structure deterministically and proposes only closed semantic roles;
- requires explicit evidence-bearing confirmation before financial semantics become authoritative;
- registers approved datasets with versioned artifacts, fingerprints, lineage and integrity metadata;
- derives current, dataset- and operation-specific readiness;
- executes allowlisted deterministic Financial Analysis operations;
- performs bounded deterministic statistical anomaly screening;
- orchestrates execution through one `FinancialManagerAgent`;
- supports a structured CLI and a bounded process-local conversation;
- may use an optional loopback-hosted local LLM for closed language mediation and grounded explanation; and
- keeps authoritative financial and statistical calculations outside the LLM.

V1 is descriptive and screening-oriented. It is not an accounting ledger, cash
management system, forecasting product, document-retrieval product, fraud system,
general query engine, SaaS application or multi-user service.

## Capability matrix

| Capability surface | Frozen V1 state | Exact qualification |
|---|---|---|
| Financial Analysis | `AVAILABLE` | Legacy Receiver General and Company Financials through 17 fixed Core contracts. Availability does not guarantee every request succeeds. |
| Dynamic `SALES_RECORD` Financial Analysis | `AVAILABLE` | Per exact registered dataset and per operation. Only currently `SUPPORTED` operations execute; readiness is freshly derived. |
| Legacy Anomaly Detection | `AVAILABLE` | Receiver General accounting amount and Company Financials Sales/Profit under the existing global and fixed-peer policies. |
| Dynamic Anomaly Detection | `AVAILABLE_WITH_LIMITATIONS` | Per exact eligible `SALES_RECORD`; exactly two GLOBAL operations under `tukey_iqr` v1.0. |
| Conversational Financial Analysis | `AVAILABLE` | Bounded legacy conversation, clarification and candidate follow-up. |
| Conversational Dynamic Financial Analysis | `AVAILABLE` | Optional local-LLM mediation may select an exact eligible dataset and one of the fixed nine operations. |
| Conversational Dynamic Anomaly | `AVAILABLE_WITH_LIMITATIONS` | Exactly the two current GLOBAL screens; A1–A10 candidate navigation and bounded fresh-evidence follow-up. |
| Cash Flow Forecasting | `BLOCKED` / future V2 | No authoritative actual-cash target/history, confirmed comparable scope/currency or implementation. |
| Document Retrieval / RAG | `BLOCKED` / future V2 | No approved production document corpus or operational retrieval implementation. Architecture notes are not a capability. |
| Additional financial domains | `DEFERRED` / future V2 | Recognition or semantic approval does not imply an executable adapter or operation catalog. |

Global Manager availability and dataset readiness are intentionally different.
The global `FINANCIAL_ANALYSIS` and `ANOMALY_DETECTION` entries describe the
legacy implementations. Dynamic availability is a separate current projection
for one exact dataset and one closed operation.

## Frozen operation catalogs

### Legacy Financial Core — 17 contracts

Receiver General has exactly eight operations: RG-01 record count, RG-02 amount
summary, RG-03 amount by debit/credit, RG-04 amount by voucher type, RG-05 amount
by department, RG-06 amount by accounting period, RG-07 accounting dimension
summary and RG-08 extreme-value retrieval.

Company Financials has exactly nine operations: CF-01 record count, CF-02 Sales
summary, CF-03 Sales by period, CF-04 Sales by country, CF-05 Sales by segment,
CF-06 Sales by product, CF-07 Profit summary, CF-08 Discount analysis and CF-09
Units Sold summary.

### Dynamic `SALES_RECORD` Financial Analysis — exactly nine

1. `SALES_RECORD_COUNT`
2. `SALES_SUMMARY`
3. `SALES_BY_COUNTRY`
4. `SALES_BY_PERIOD`
5. `SALES_BY_SEGMENT`
6. `SALES_BY_PRODUCT`
7. `PROFIT_SUMMARY`
8. `DISCOUNT_ANALYSIS`
9. `UNITS_SOLD_SUMMARY`

Only `MONTH|YEAR` period granularity and `BUCKET|EXCLUDE` missing-dimension
policy are accepted where the operation contract permits them. There is no
arbitrary measure, dimension, grouping, filter, formula, SQL or source-column selector.

### Dynamic anomaly — exactly two

1. `SALES_ANOMALY_SCREEN`
2. `PROFIT_ANOMALY_SCREEN`

Both are GLOBAL, two-sided, deterministic Tukey-IQR v1.0 screens. Each requires
at least 30 usable exact values, a positive IQR and exact threshold arithmetic.
Fence equality is `NOT_SELECTED`; unavailable measure values are
`NOT_ASSESSED`; negative values retain their sign. Profit means supplied,
confirmed Profit and is never reconstructed. A `CANDIDATE` is a statistical
candidate for contextual review, never a fraud, error, suspicion, risk or
probability conclusion.

Legacy anomaly policies remain distinct: Receiver General retains its upper-tail
global/fixed-peer policy; Company Financials retains its two-sided Sales/Profit
global/fixed-peer policy. Dynamic sources do not gain peer screening.

## Recognized and executable domains

The closed onboarding domain vocabulary recognizes
`ACCOUNTING_TRANSACTION`, `SALES_RECORD`, `CASH_TRANSACTION`, `PAYABLE`,
`RECEIVABLE`, `BUDGET_RECORD`, `BALANCE_RECORD` and `DOCUMENT_METADATA`.
Recognition means that a user can approve a semantic classification; it is not
execution readiness.

Only approved `SALES_RECORD` datasets have a dynamic execution adapter in V1.
They may execute the nine Financial Analysis operations and two anomaly
operations only when their operation-specific current gates pass.
`ACCOUNTING_TRANSACTION` can be semantically modeled but has no validated
dynamic adapter. The remaining recognized domains likewise have no V1 execution
path. Legacy Receiver General and Company Financials remain executable through
their separate approved snapshot path and are not onboarding domain aliases.

## Authority architecture

The frozen authority chain is:

```text
user language
  -> optional LLM interpretation of a closed intent
  -> Financial Manager orchestration
  -> current dataset/operation readiness where applicable
  -> binder and authenticated static adapter where applicable
  -> Financial Core or deterministic anomaly engine
  -> authoritative structured evidence
  -> deterministic presentation and optional grounded LLM explanation
```

The LLM may interpret and explain. It cannot calculate authoritative totals,
choose an arbitrary operation/column/algorithm, assign currency, override
readiness, classify anomalies or replace structured evidence. The Manager owns
orchestration and result wrapping, not financial or statistical algorithms.
Readiness is a current projection, not a cached authorization. Dynamic adapters
repeat source/artifact authentication at execution.

## Architecture review result

| Review question | Result |
|---|---|
| Does an LLM perform authoritative arithmetic or classification? | No. Intent and prose are closed/validated; facts originate in deterministic evidence. |
| Does mediation duplicate Financial Core or anomaly math? | No. It builds bounded fact catalogs and validates prose; it does not produce financial/statistical evidence. |
| Does the Manager perform financial calculations? | No. It delegates and preserves evidence. Candidate-count wording reads an authoritative returned count and does not reclassify records. |
| Does the Manager perform anomaly calculations? | No. Quartiles, IQR, fences and classifications remain in the anomaly modules. |
| Is readiness used as stale authorization? | No. Manager/session resolve current readiness and binder/adapter reauthenticate artifacts at execution. |
| Do adapters infer semantics? | No. They resolve exact confirmed roles and preserve value/status/lineage. |
| Can onboarding create approved financial facts without confirmation? | No. Profiling observations and semantic suggestions remain non-authoritative until an explicit decision. |
| Does presentation mutate evidence? | No confirmed mutation. Human/LLM presentation is derived from copied authoritative evidence. |
| Is session state a hidden source of financial truth? | No. It stores typed selection/reference context and digests; execution and follow-up obtain fresh evidence. |
| Can dynamic execution bypass integrity checks? | No. Workflow, registry, profile, mapping, stable columns, source fingerprint/schema and adapter compatibility are checked. |

Dependency direction is acceptable for V1: CLI depends on session/manager and
onboarding; mediation depends on closed vocabularies and manager models; manager
coordinates onboarding/execution/anomaly modules; execution depends on onboarding
artifacts and Financial Core; anomaly owns statistical policy; Financial Core owns
financial arithmetic. Local imports in the Manager keep fresh-process imports acyclic.

`FinancialManagerSession` now contains substantial evidence-shape validation for
legacy and dynamic candidate handles. This lowers module depth and is a
maintenance observation, but it is located at the lifecycle/reference seam,
passes fresh-evidence/stale-reference tests and creates no current correctness,
security, import-cycle or testability blocker. Phase 18 does not authorize a broad extraction.

## Legacy and dynamic coexistence

The two paths intentionally coexist:

- Receiver General and Company Financials use the approved processed bundle,
  SQLite snapshot and 17 legacy query contracts plus legacy screening policies.
- Phase 13+ datasets use immutable onboarding artifacts, semantic decisions,
  registry/readiness, a static `SALES_RECORD` adapter and the closed dynamic catalogs.

V1 does not migrate legacy sources into onboarding, relabel dynamic sources as
Company Financials or unify them under an invented universal transaction grain.

## Data authority rules

- Raw source bytes are preserved; accepted onboarding bytes are immutable local
  artifacts and legacy raw/processed assets retain hashes.
- Processed/canonical values are deterministic and traceable through versions,
  digests, stable columns, source rows and record identifiers.
- Currency is `UNKNOWN` unless approved evidence explicitly confirms one ISO
  denomination. Country, symbols, formatting, headers and the LLM cannot assign it.
- Missing and unparseable values remain unavailable and are never silently zero.
- Dynamic Profit operations use only supplied, confirmed `PROFIT`; no accounting identity reconstructs it.
- Receiver General DR/CR codes remain source accounting directions and are never
  silently converted to revenue, expense, receipt or payment.
- Anomaly results are statistical screening observations, not fraud findings.

## Local-first and LLM boundary

Every authoritative V1 workflow can operate without an LLM. The default legacy
CLI, Financial Core, anomaly services, onboarding/profile/mapping decisions,
readiness and typed dynamic execution are local deterministic code. An optional
loopback local model may improve conversational interpretation and explanation.
Provider failure, malformed output, prompt injection, invented identifiers or
ungrounded prose fails closed or falls back to code-owned behavior; it cannot
corrupt deterministic results. No external LLM is required for financial truth.

## V1 non-goals and deferred work

The following are not V1 capabilities and must not be inferred from the
recognized vocabulary or historical roadmap:

- Cash Flow Forecasting;
- Financial Document RAG or document retrieval;
- dynamic peer anomaly screening;
- additional executable financial domains;
- arbitrary SQL, filters, grouping, measures or statistical algorithms;
- ML anomaly models;
- fraud detection or fraud scoring;
- SaaS, frontend, API or mobile application;
- authentication, multi-user operation or multitenancy;
- cloud storage;
- banking or payment execution;
- ERP integrations;
- PostgreSQL migration; and
- additional LLM providers.

These items are future/V2 work and require separate evidence, contracts and
explicit authorization.

## Scope-freeze rule

After Step 70, no feature may be added before the V1 release unless it fixes a
confirmed correctness, data-integrity, security/privacy, reproducibility,
release-blocking UX or release-blocking performance defect. All other proposals
go to V2. The catalogs above may not be extended during V1 finalization.
