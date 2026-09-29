# Phase 6 — Step 18 validation

Completed only top-level capability routing and orchestration under the explicit
Step 18 authorization. [Orchestration architecture](orchestration.md) documents
the grammar, response contract, scope limits and examples. Historical planning-only
guidance was not treated as authorization for any additional phase.

## Architecture and capability paths

`FinancialManagerAgent.plan(question)` returns a detached preview without executing
services. `ask(question)` creates a fresh internal immutable plan and executes
only through the existing `execute` facade. Explicit execution is unchanged.
No externally supplied plan is executable. The Step 17 registry remains the
source of capability identifiers, availability, blockers and limitations.

| Capability | Availability | Validated path |
|---|---|---|
| FINANCIAL_ANALYSIS | AVAILABLE | Top-level decision → manager.execute → Step 13 agent → existing approved Core contract |
| ANOMALY_DETECTION | AVAILABLE | Complete target grammar → existing pure Step 14 request validator → manager.execute → Step 14 service |
| CASH_FLOW_FORECASTING | BLOCKED | Registry blocker returned; execute/delegate/model never called |
| DOCUMENT_RETRIEVAL | BLOCKED | Registry corpus blocker returned; no retrieval or engineering-document substitution |

The router does not select RG/CF contract IDs, access SQLite, call Financial Core
tools or calculate financial values. The screening adapter constructs only the
existing version/dataset/measure request, without changing methods, minimum peer
size, grouping, arithmetic, tails or thresholds. Financial Analysis receives its
question; lower-level routing and argument validation remain in Step 13.

One analysis clause plus one independent screening clause may run sequentially,
always analysis first. Neither a generated explanation nor a prior result is
passed downstream as evidence. Preflight ambiguity prevents all execution;
delegated clarification/rejection stops any remaining step. PARTIAL and NO_DATA
allow the next independent clause to run, retaining separate original results.

## Test results

Focused command:

```sh
.venv/bin/python -B -m unittest discover -s tests -p test_orchestration.py -v
```

**35 passed, 0 failed, 0 errors, 0 skipped**, in **19.386 seconds**.

Full regression command:

```sh
.venv/bin/python -B -m unittest discover -s tests -v
```

| Suite | Passed | Failed | Errors | Skipped |
|---|---:|---:|---:|---:|
| Phase 3 database | 17 | 0 | 0 | 0 |
| Phase 4 financial tools | 37 | 0 | 0 | 0 |
| Phase 4 quality | 19 | 0 | 0 | 0 |
| Phase 4 currency/FX | 22 | 0 | 0 | 0 |
| Step 13 Financial Analysis Agent | 36 | 0 | 0 | 0 |
| Step 14 anomaly screening | 32 | 0 | 0 | 0 |
| Step 17 Main Financial Manager | 31 | 0 | 0 | 0 |
| Step 18 routing/orchestration | 35 | 0 | 0 | 0 |
| **Total** | **229** | **0** | **0** | **0** |

Full duration: **176.278 seconds**. All **194 previous tests remain unchanged and
pass**. Counts refer to unittest methods; subtests are not counted as additional
tests. No discovery reorganization, skipped capability tests or dependency changes
were needed. `git diff --check` passes.

## Acceptance evidence

| Scenario | Verified outcome |
|---|---|
| Accounting, sales, counts, discounts, units and ranked amounts | Financial Analysis selected without an RG/CF contract ID or query parameters in the top-level decision |
| Actual country request | Step 13 selects `company_financials_sales_by_country`; complete automatic response equals explicit execution |
| Actual partial Discounts | All evidence retained, including 53 unresolved placeholders, UNKNOWN currency and ordered quality warnings |
| Actual count ambiguity / no data | Step 13 dataset clarification and NO_DATA propagate without fabricated values |
| Actual RG amount, CF Sales, CF Profit screening | Complete automatic responses equal explicit Step 14 responses, including references, observations, lineage and currency |
| Screening modifiers | Filter/period/algorithm/custom-peer modifiers clarify instead of silently becoming unfiltered screening |
| Tail and dataset mismatches | RG lower-tail requests and conflicting domain/measure labels reject; high/low CF scope notes disclose full both-tail evidence |
| Candidate terminology | CANDIDATE / NOT_SELECTED / NOT_ASSESSED remain unchanged; summaries contain investigation language, no fraud/error conclusions |
| Fraud, investment, mutation, unsupported prediction, executable input | Structured UNSUPPORTED without execution; unknown function names cannot select handlers |
| Unavailable capabilities | Forecasting/RAG blockers exactly match registry metadata; manager.execute is not called |
| Availability source | Test-only DEFERRED registry entry produces non-execution while preserving that availability |
| Ambiguity / malformed input | Unknown purpose, mixed/dependent intent, invalid type, empty/long input and unmatched quotes return structured outcomes |
| Quoted source values | Capability words and separators in quoted categories do not select capabilities or split clauses |
| Explicit override | Existing explicit API calls the selected service even when automatic routing would choose differently |
| Facade boundary | Automatic execution reaches public manager.execute; existing registry owns delegation |
| Evidence copying | Original complete objects, exact decimal strings and a test-only Decimal survive unchanged; convenience mutations do not change evidence |
| Status preservation | SUCCESS, PARTIAL, NO_DATA, invalid/unsupported, quality blockers, provider failures and clarification remain distinct |
| Determinism | Repeated plans/results are equal for fixed input/state; preview mutations cannot alter subsequent execution |
| Independent multi-request | Exactly two separate results, stable analysis→screening order even for reverse input, no numeric combination or explanation-as-input |
| Preflight and delegated stopping | Invalid second clause prevents first execution; delegated rejection stops remaining calls and retains completed evidence |
| Failure transparency | Unexpected exceptions propagate without fallback or retry |
| Offline operation | Default real two-capability execution succeeds with socket creation disabled and no external provider |

Fixtures are test-only. No synthetic record or invented document entered production.

## File and dataset preservation

The pre-edit SHA-256 inventory contained **110 existing files**. **106 remain
unchanged**; the four intentional modifications are README.md,
docs/main_financial_manager_agent.md, src/manager/agent.py and src/manager/models.py.

All existing tests, Step 13/14 source, Financial Core, database implementation,
query contracts, notebooks, schema/load pins, raw/processed source data and
historical cleaning/validation artifacts remain unchanged. No file was added
under data/. Existing database tests pass with their disposable fixture databases.

Production database SHA-256 remains:
`8b9536867d7e1ee2e3fd8b0040d40f5806cf6ecb8afc38491cbc058de727c744`.

Created:

- `src/manager/routing.py`
- `src/manager/orchestration.py`
- `tests/test_orchestration.py`
- `docs/orchestration.md`
- `docs/step18_validation.md`

Modified:

- `src/manager/agent.py`
- `src/manager/models.py`
- `docs/main_financial_manager_agent.md`
- `README.md`

Pre-existing unrelated/untracked files were retained. No old tests were edited.

## Privacy and remaining limitations

No network calls, external LLM/provider/FX requests, telemetry, credentials, web
search, document transmission, API/server, frontend, authentication, deployment
or new dependencies were added. Existing trusted local dependency injection is
preserved; it is not a plugin sandbox or comprehensive security framework.

Routing is bounded English and stateless. Clarifications require a complete new
request. Automatic screening is unfiltered and uses the existing fixed global/peer
baselines; filtered screening remains available through explicit execution. CF
high/low wording returns full both-tail evidence with scope notes. Unclear scopes
and multi-capability combinations beyond one independent analysis plus one
screening request require clarification.

Unknown denomination, unresolved placeholders, sparse dimensions, fiscal/grain
and provenance uncertainty, absent company identity and in-sample screening
limitations persist. No financial semantics were inferred or replaced. Forecasting
still lacks authoritative actual-cash data and sufficient denomination/history
readiness. Document retrieval still lacks an approved production corpus.

**Step 19 was not started.** The next recommended separately scoped task is
Phase 6 — Step 19: Security & Privacy Boundaries. Forecasting and RAG remain
unimplemented; no other phase or product work was started.
