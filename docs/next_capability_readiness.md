# Next capability readiness

## Decision

**Recommended next capability: concise human presentation and reporting for the
existing local CLI. Status: READY_WITH_PREREQUISITES.**

The prerequisite is a small, explicit presentation contract that defines what a
concise view may select, how omitted detail is disclosed, how users reach complete
evidence, and how repeated warnings are referenced. Implementation must remain a
view over unchanged manager responses. This work should precede forecasting, RAG,
new financial domains, and conversational state because it addresses a measured
V1 user problem without requiring unavailable business data or new dependencies.

This is a readiness decision, not implementation approval. No capability, data,
dependency, financial calculation, or response schema changes in Step 26.
“Presentation capability” here means an application/CLI behavior over existing
responses, not a fifth entry in the manager capability registry.

## Current V1 baseline

The validated local V1 provides 17 deterministic read-only accounting and sales
contracts plus IQR investigation screening. One manager routes to Financial
Analysis or Anomaly Detection; Cash Flow Forecasting and Document Retrieval are
registered but blocked. Exact decimal values, UNKNOWN currency, quality warnings,
lineage, screening assessments, and specialized results survive orchestration and
JSON serialization.

Step 24 proved clean-clone reproducibility with Python 3.14 and seven explicitly
identified custodian-provided data files. Step 25 passed 299 tests and found that
results were correct and understandable at the top level. It also measured a
serious presentation problem: ordinary accounting answers can exceed 700 KB and
accounting screening can render about 12.7 MB / 468,000 terminal lines. Warnings
repeat across evidence and convenience envelopes, and internal identifiers remain
prominent. The application remains offline, local-first, and free of third-party
runtime dependencies.

The domain distinctions in `CONTEXT.md` remain authoritative. In particular, an
accounting record is not a payment or cash movement, a sales record is not a cash
receipt, an obligation is not its settlement, and a statistical candidate is not
proof of error or fraud. No new glossary term or ADR is needed for this reversible
prioritization decision.

## Candidate readiness summary

| Candidate | Status | Main evidence | Gate before implementation |
|---|---|---|---|
| Human Presentation / Reporting Layer | **READY_WITH_PREREQUISITES** | Step 25 measured unusably large human output; `src/cli/formatting.py` is already a presentation-only seam; complete JSON evidence exists | Approve concise/full display and evidence-reference rules |
| Cash Flow Forecasting | **BLOCKED** | No actual cash movement, balance target, confirmed currency, stable calendar, or sufficient comparable history | Acquire and validate authoritative settled-cash history |
| Financial Document RAG | **BLOCKED** | High-level architecture exists, but no approved real corpus, rights, access policy, evaluation set, or dependencies exist | Approve a representative corpus inventory and privacy assessment |
| Expanded Financial Analysis | **BLOCKED** | Current sources do not establish AP, AR, cash position, budgets, statements, company identity, or verified accounting meanings | Select one business concept and acquire an authoritative governed dataset |
| Conversational / UX Improvements | **DEFERRED** | Clarification is stateless and bounded phrasing has friction, but current manager has no session contract and presentation is the stronger measured problem | Complete presentation work, then define bounded in-memory session semantics |

## A. Human presentation and reporting

### Readiness dimensions

| Dimension | Assessment |
|---|---|
| Data readiness | **Ready.** The manager already returns complete structured evidence, summaries, warnings, limitations, statuses, record IDs, lineage, and anomaly reference IDs. No new data is needed. |
| Semantic readiness | **Ready with prerequisite.** Authoritative evidence and presentation must remain distinct. A displayed subset must never be described as the full result. Selection, omission, and warning-reference language need an approved contract. |
| Architecture readiness | **Ready.** Human rendering is isolated in `src/cli/formatting.py`; `--json` serializes the unchanged manager response. Financial Core, anomaly service, manager, and routing need no new responsibility. |
| Validation readiness | **Ready.** Existing CLI/acceptance fixtures can prove exact JSON equality, formatter non-mutation, visible status/currency/warnings, deterministic ordering, and disclosed omissions. Step 25 scenarios provide concrete size regressions. |
| Privacy/security readiness | **Ready.** A local formatter needs no network, provider, credential, telemetry, or persistence. Output remains sensitive local data and must not be logged or uploaded automatically. |
| User value | **High and observed.** Step 25 directly measured excessive volume, repeated warnings, and technical terminology in otherwise correct workflows. |
| Effort/dependencies | **Bounded.** Primarily presentation contracts, formatter code, tests, and documentation; the standard library is sufficient. Stateless pagination would require explicit offset/cursor semantics, so it should not be assumed. |

### Required presentation contract

Before implementation, approve these rules:

1. **Authority:** the manager/specialized structured result remains authoritative;
   the presentation layer performs no financial arithmetic or reclassification.
2. **Modes:** concise human output is clearly distinguished from complete detail;
   exact JSON remains a complete machine-readable path. If a full human mode is
   retained, its invocation and compatibility policy must be explicit.
3. **Collections:** a bounded preview uses existing deterministic ordering and
   shows total/returned/omitted counts plus stable record/reference identifiers.
   Omitted records are never silently discarded from the underlying response.
4. **Warnings:** human output may show one readable instance of a warning and
   references to affected evidence, while nested JSON warning fields remain intact.
5. **Terminology:** user-facing labels explain statuses, UNKNOWN currency,
   CANDIDATE, NOT_ASSESSED, coverage, and technical references without changing
   their meanings.
6. **Failures and limits:** blockers, clarification, exclusions, partial coverage,
   currency state, and access to complete evidence stay visible.

A top-N view is appropriate only where the specialized result already defines the
ordering and meaning. The formatter must not invent a “largest,” “most anomalous,”
or “highest risk” ranking. Stateful pagination is not yet ready; it needs stable
cursor/offset and snapshot-consistency semantics. The first scope should use a
deterministic disclosed preview plus complete JSON access.

### Minimal next implementation scope

The next separately scoped step should change only human CLI rendering and its
tests/documentation. It should provide a concise default for `ask`, preserve exact
`--json`, disclose every omitted collection count, show stable evidence references,
and avoid repeating identical warning content in the human view. It should use
existing result summaries and metadata rather than calculate replacements.

Interactive pagination, report files, web/API output, new response schemas,
conversation memory, and financial report generation should remain outside that
first scope. A deterministic preview is sufficient to address the measured problem
without creating session state.

## B. Cash Flow Forecasting

**Status: BLOCKED.** Nothing since the Step 15 readiness review changed the source
semantics. Receiver General rows remain accounting records with unresolved
detail/summary overlap; DR/CR does not establish cash direction. Company Financials
rows remain sales observations without receipt or company identity. All monetary
currency remains UNKNOWN. Later integration, security, provisioning, and user
evaluation work preserved these facts rather than resolving them.

| Dimension | Assessment |
|---|---|
| Data readiness | **Blocked.** No authoritative settled cash movements, balances, known currency, complete calendar, or adequate comparable history exist. |
| Semantic readiness | **Blocked.** Target, account/company perimeter, cash-value date, sign/transfer rules, frequency, horizon, and missing-period meaning remain unapproved. |
| Architecture readiness | **Deferred behind data.** The registry already protects the blocked capability and a future forecasting module can remain separate from the manager/LLM, but no model/data interface should be fixed before the target contract exists. |
| Validation readiness | **Blocked.** There is no authoritative target or chronological expected-result set. A future dataset must support frozen rolling/holdout evaluation and reconciliation. |
| Privacy/security readiness | **Ready with prerequisites.** Local execution can preserve current boundaries, but bank/account data will require explicit access, retention, storage, and export controls. |
| User value | **Plausible, not established.** Step 25 verified two understandable blocked user journeys; it did not provide real treasury users, decisions, horizons, or tolerances. |
| Effort/dependencies | **High and premature.** It requires governed acquisition/cleaning/loading, a target pipeline, baselines, chronological evaluation, and only then justified modeling dependencies. |

The minimum future input is an authoritative period-level cash series or settled
movement source with:

- actual settled `cash_in` and `cash_out`, never sales, revenue, expense,
  obligation, or journal-direction proxies;
- period date, approved frequency/calendar, timezone, cutoff, and complete
  classification of zero, closed, missing, and partial periods;
- one stable company/account perimeter, transfer/reversal/correction policy, and
  consistent settlement/sign semantics;
- confirmed ISO 4217 currency per series, with no silent cross-currency sum;
- at least two complete annual cycles after quality exclusions: 730 daily, 104
  weekly, or 24 monthly periods, plus an untouched chronological test window at
  least as long as the approved horizon;
- authoritative closing balance when cash-balance forecasting or reconciliation
  is in scope; and
- immutable source/version/extraction lineage and reproducible transformation and
  validation manifests.

Only after acquisition should a separately authorized review approve the target,
scope, cadence, horizon, reconciliation, and chronological evaluation split.
Model selection remains out of scope until those gates pass.

## C. Financial Document RAG

**Status: BLOCKED.** The documented flow is a useful architecture direction, but
architecture choices are still DEFERRED and the required production corpus is
absent. Project Markdown, notebooks, structured CSVs, and database rows are not a
production financial-document corpus.

| Dimension | Assessment |
|---|---|
| Data readiness | **Blocked.** No approved real financial-document corpus or representative sample exists. |
| Semantic readiness | **Blocked.** Source authority, version precedence, permitted claims, citation behavior, and answer/abstention expectations depend on the corpus. |
| Architecture readiness | **Deferred.** The high-level source→ingest→extract→chunk→retrieve→evidence flow is documented, while parser, chunk, embedding, index, access, and tool contracts intentionally remain unselected. |
| Validation readiness | **Blocked.** There are no production questions, expected passages, conflict/version cases, held-out retrieval set, or access-control fixtures. |
| Privacy/security readiness | **Blocked.** Rights, sensitivity, per-document access, retention/deletion, provider location, revocation, and authorization-safe citations are absent. |
| User value | **Plausible, not established.** Step 25 verified clear blocked responses for invoice/contract questions; it did not establish an approved corpus or prioritized document workflow. |
| Effort/dependencies | **Unknown until corpus inventory.** Formats and scale determine parsers, OCR, local models, indexes, access controls, and reproducible offline dependencies. |

A minimum corpus-readiness inventory must cover, for every proposed document:

- real source bytes and document type/format/language;
- owner, source authority, provenance, acquisition method, and content hash;
- version/effective date, supersession and duplicate policy;
- explicit rights and permitted purposes for extraction, indexing, retrieval,
  display, and any model processing;
- sensitivity classification, per-document access policy, and authorization-safe
  citation metadata;
- retention, deletion, backup, audit, and revocation requirements;
- allowed processing/storage locations and whether LOCAL or approved PRIVATE
  processing is permitted; and
- representative user questions, answerable/unanswerable evidence, conflicting
  versions, and expected citation spans.

Representative files must then determine parser/OCR needs, deterministic chunking,
retrieval and citation contracts, access enforcement, held-out evaluation, and
dependencies. No embedding model, vector technology, parser, or provider is
justified before that assessment.

## D. Expanded financial analysis

**Status: BLOCKED.** The Core and manager provide reusable contract/registry seams,
but architecture alone cannot supply business facts. Neither current dataset
establishes accounts payable, accounts receivable, cash position, budget versions,
financial statements, verified company identity, or revenue/expense/cash semantics.
There are therefore no authoritative expected answers with which to validate a
new domain contract.

| Dimension | Assessment |
|---|---|
| Data readiness | **Blocked.** None of the candidate AP, AR, budget, cash-position, statement, company, or additional-dimension facts is authoritatively available. |
| Semantic readiness | **Blocked.** Each option needs its own grain, dates, basis, scope, identity, status, currency, and reconciliation rules; current source labels cannot supply them. |
| Architecture readiness | **Ready with major prerequisites.** Existing deterministic contract/Core/registry patterns can host one approved domain, but it will need its own governed schema, loader, quality rules, and specialist contracts rather than a generic fact-table shortcut. |
| Validation readiness | **Blocked.** No approved source totals, reconciliations, edge cases, or expected answers exist for these domains. |
| Privacy/security readiness | **Unknown until source selection.** Counterparty, account, entity, and statement data may be more sensitive and require access/retention rules beyond the current local files. |
| User value | **Unprioritized.** Step 25 confirmed correct refusal of balance-sheet, company-ranking, expense, and cross-dataset requests; it did not identify which governed business workflow has highest real-user value. |
| Effort/dependencies | **High per selected domain.** One choice requires acquisition, EDA, semantic approval, cleaning, schema/load, queries, quality/lineage, routing, and acceptance evidence. Bundling choices would multiply risk. |

Choose one business problem before acquiring data. Minimum contracts would be:

| Business concept | Minimum authoritative fields and semantics | Coverage, currency, and provenance |
|---|---|---|
| Accounts payable / receivable | Stable obligation/receivable ID; counterparty; issue/recognition and due dates; original and outstanding amounts; as-of status; settlement IDs, dates, and amounts; cancellation/adjustment rules | Confirmed currency; complete as-of population and settlement linkage; source system/version, extraction cutoff, row lineage, validation manifest |
| Budget versus actual | Entity/perimeter; cash or accrual basis; period/calendar; approved budget version/scenario; stable dimension identifiers; budget and comparable actual amounts | Same basis, dimensions, currency, and period coverage; version approval and separate source lineage for budget and actual |
| Cash position | Financial account and owner/perimeter; as-of timestamp; explicitly defined ledger/available balance; reconciled movements and adjustments | Confirmed currency per account; complete account coverage; source statement/system, cutoff, reconciliation, and lineage |
| Financial statements | Verified entity; statement type; period/as-of date; line-item taxonomy; amount; accounting basis; consolidation scope; version/status | Confirmed presentation currency; complete statement and comparative periods where needed; authoritative filing/system provenance and version lineage |

Additional accounting dimensions are viable only when their labels, hierarchy,
coverage, and business meaning are authoritative. The current sparse source codes
must not be promoted into invented organizational or accounting hierarchies.

## E. Conversational and user-experience improvements

**Status: DEFERRED.** Step 25 shows value in clarification continuation and broader
natural phrasing, but the current router is deliberately stateless and conservative.
A bounded in-memory session could eventually carry a pending clarification and
explicit user selection; it must not alter financial evidence or infer unstated
dataset, period, measure, currency, or business semantics.

Prerequisites after presentation work are a versioned session contract, explicit
turn/expiry/cancellation rules, deterministic replay, limits on which structured
clarification fields may carry forward, and privacy rules for question/history
retention. Persistent memory, external LLMs, hidden state, and cross-user context
remain outside scope. Presentation comes first because it solves a measured problem
without adding sensitive history or another stateful boundary.

| Dimension | Assessment |
|---|---|
| Data readiness | **Ready.** No new financial dataset is needed; only caller questions, pending clarification fields, and explicit replies would be involved. |
| Semantic readiness | **Ready with prerequisites.** The project must define which clarification values may carry forward and prohibit inferred financial scope or meaning. |
| Architecture readiness | **Ready with prerequisites.** A bounded session wrapper can sit outside the stateless manager; manager plans must remain fresh, validated, and non-executable as caller-supplied objects. |
| Validation readiness | **Ready with prerequisites.** Versioned turn/expiry/cancellation/replay rules can be tested deterministically once the session contract exists. |
| Privacy/security readiness | **Ready with prerequisites.** Question history is sensitive; first scope must be in-memory, bounded, expiring, non-persistent, and free of external providers/telemetry. |
| User value | **Moderate and observed.** Step 25 found stateless clarification and bounded phrasing friction, but excessive output was the larger measured usability problem. |
| Effort/dependencies | **Moderate.** It needs session state/contracts and tests but no external dependency or LLM. It adds a new state boundary, so presentation should come first. |

## Priority and sequence

1. **Next:** specify and implement concise human presentation/reporting for the
   existing CLI, with exact JSON and authoritative evidence preserved.
2. **After that:** reassess a bounded, in-memory clarification continuation only
   if user evaluation still identifies routing friction as material.

Forecasting, RAG, and expanded financial analysis do not enter this sequence until
their external data/corpus gates are satisfied. Their next actions are acquisition
and readiness reviews, not implementation.

## Architecture constraints for the recommended scope

- Financial Core remains the owner of calculations, contracts, exact decimals,
  coverage, currency, and lineage.
- AnomalyService remains the owner of IQR rules, peer assessments, candidates,
  abstentions, thresholds, and references.
- Manager/orchestration continues to preserve complete delegated responses and
  separate multi-capability results.
- CLI formatting alone selects and labels human-visible detail; it never rewrites
  nested evidence or changes JSON.
- Blocked forecasting/RAG registry entries remain blocked and handler-free.
- No provider, network call, telemetry, persistence, arbitrary SQL, or data write
  is introduced.

These constraints make the presentation work fit the current deep-module seams:
authoritative modules keep domain decisions, while the CLI owns only display.

## Evidence references

- [Step 25 user evaluation](user_evaluation.md)
- [Cash Flow Forecasting readiness](forecasting_readiness.md)
- [Financial Document RAG readiness](rag_architecture.md)
- [Orchestration boundaries](orchestration.md)
- [Security and privacy boundaries](security_privacy_boundaries.md)
- [Environment/data provisioning](environment_and_data_provisioning.md)
- [Fresh-clone reproducibility](fresh_clone_reproducibility.md)
