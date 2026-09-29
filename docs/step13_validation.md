# Phase 5 — Step 13 validation

Completed only the Financial Analysis Agent under the user's explicit Step 13
authorization. Readiness: **READY** over the unchanged 17 Phase 4 contracts.
There were no material contract/schema blockers or semantic redesigns.
Architecture, supported language, examples and privacy details are documented in
[Financial Analysis Agent](financial_analysis_agent.md).

## Test results

Focused command:

```sh
.venv/bin/python -B -m unittest discover -s tests -p test_financial_agent.py -v
```

Result: **36 passed, 0 failures, 0 errors, 0 skipped**, 25.362 seconds.

Full regression command:

```sh
.venv/bin/python -B -m unittest discover -s tests -v
```

Result: **131 passed, 0 failures, 0 errors, 0 skipped**, 120.460 seconds.

| Suite | Passed | Failed | Errors | Skipped |
|---|---:|---:|---:|---:|
| Phase 3 `test_database.py` | 17 | 0 | 0 | 0 |
| Phase 4 `test_financial_tools.py` | 37 | 0 | 0 | 0 |
| Phase 4 `test_quality.py` | 19 | 0 | 0 | 0 |
| Phase 4 `test_currency_fx.py` | 22 | 0 | 0 | 0 |
| Step 13 `test_financial_agent.py` | 36 | 0 | 0 | 0 |
| **Total** | **131** | **0** | **0** | **0** |

Counts are unittest methods, without inflating parameterized subtests. The
original 95 methods remain unchanged and pass. All 17 routed real-database
responses are compared for complete equality against direct Core queries,
including metadata, filters, exclusions, currency, quality and exact values.
Test fixtures and fake providers are confined to tests; no production observations
or source documents were created. No tests require live providers or credentials.

## Acceptance evidence

| Requirement | Evidence / outcome |
|---|---|
| Core remains the financial authority | All execution goes through `FinancialCore.query`; its normalizer is reused before final Core validation |
| One orchestrator, 17 approved tools | Static allowlist equals the current 17-contract registry; all eight RG and nine CF routes exercised |
| Provider independence | Protocol, immutable interpretation request and strict intent model; bundled local grammar and test-only fake provider |
| Grounded selection and parameters | A proposed intent must match the question's normalized intent; provider-invented tool/domain/filter choices are rejected |
| Clarification | Ambiguous domain, incomplete/relative dates, conflicting parameters and unconsumed clauses never execute a tool |
| Unsupported meanings | Tests reject RG expense/revenue, company/balance-sheet claims, currency conversion, combined totals and unavailable later capabilities |
| No SQL or arbitrary execution | Agent has no SQL, DB connection or dynamic function execution; invalid SQL properties/tool names rejected; SQL-shaped category passes as literal data to Core |
| Results unchanged | Complete evidence equality for every contract, defensive-copy test, evidence digest, preserved NO_DATA and DATA_QUALITY_BLOCKER statuses |
| No agent financial arithmetic | Agent only interprets request fields and renders supplied evidence; no Decimal/float arithmetic, totals or financial aggregation introduced |
| Quality and currency survive | Actual partial Discount/department results, full flags, UNKNOWN currency, null quantity/count currency and original snapshot lineage tested |
| Missingness preserved | 53 Discount and 5 Profit placeholders remain unavailable, all-placeholder sum remains null, department exclusions remain 26 |
| Negative Profit remains valid | 58 negative records survive with no anomaly/fraud relabelling |
| Offline privacy | Socket creation disabled during actual Core query with fake provider; private/external provider locations refused before invocation |
| Provider receives no result evidence | Immutable request has only question, dataset and static metadata; separate structured parameters and results are absent |
| Internal failures visible | Expected provider failures are structured/redacted; unexpected Core exceptions propagate |
| Regression and integrity | All original Phase 3/4 tests pass; protected hashes unchanged as below |
| Scope | No Step 14, forecasting, RAG, API/frontend, live LLM/FX, credentials, model training, dependency installation or deployment |

Provider injection is trusted local Python configuration, not a sandbox against
malicious plugin code. The supplied provider contains no network code. Natural
language is deliberately bounded; there is no claim of unrestricted LLM question
understanding or model-generated explanation.

## Protected-file verification

A pre-Step-13 SHA-256 inventory covered 61 existing files across data, source,
tests, documentation, notebooks, README, AGENTS and CONTEXT. After implementation
and the full test run, **60 files were unchanged**. The only changed existing file
was the intentional README update linking Step 13 and replacing the obsolete
statement that no agent existed. In particular:

- Raw data, both processed cleaning runs and all historical cleaning artifacts
  remained unchanged.
- Database, load-validation artifact, schema, approved-run metadata, Phase 3/4
  implementation/tests and Step 09 contracts remained unchanged.
- All five notebooks, data/schema documentation, Phase 4 validation, AGENTS,
  CONTEXT and historical planning documents remained unchanged.

Database SHA-256:
`8b9536867d7e1ee2e3fd8b0040d40f5806cf6ecb8afc38491cbc058de727c744`.

DDL SHA-256:
`7a815fe0ffbfa68849f5e3e1394d9e9e7fb117c771c7b318c0ab50fe75a83fe5`.

No migrations, database writes or metadata changes were introduced. Existing
database rebuild/failure tests continue using disposable temporary databases.

## Files in this step

Created:

- `src/agents/__init__.py`
- `src/agents/financial_analysis.py`
- `src/agents/routing.py`
- `src/agents/registry.py`
- `src/agents/provider.py`
- `src/agents/models.py`
- `src/agents/explanation.py`
- `tests/test_financial_agent.py`
- `docs/financial_analysis_agent.md`
- `docs/step13_validation.md`

Modified: `README.md`. Pre-existing unrelated/untracked work was retained.

## Remaining limits and stopping point

Unknown currencies, unresolved provenance/record grain/comparability,
accounting summary/detail overlap, fiscal alignment, sparse dimensions,
absent company identity, fractional quantity interpretation and unresolved
Discounts/Profit placeholders persist. No source is newly interpreted as verified
revenue, expense, cash flow or company financial statements.

The agent is a stateless, conservative English interpreter with lossless
deterministic rendering; it has no live/local LLM adapter or unrestricted prose
understanding. Nonlocal model transports remain disabled. Ratios, FX conversion
and other deferred contract operations remain unavailable.

The next recommended work is a separately authorized Step 14 readiness review
for investigation-candidate analysis. No anomaly detection or later Phase 5 stage
has been started or represented as operational.
