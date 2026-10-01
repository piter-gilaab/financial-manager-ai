# Phase 4 — Financial Core validation

Completed Steps 10, 11 and 12 under the user's explicit integrated implementation
authorization. Contract authority: [Step 09](query_contracts.md), unchanged.
Operation and architecture: [Financial Core](financial_core.md).

## Checkpoints

| Checkpoint | Evidence | Result |
|---|---|---|
| 10 — Financial Data Analysis tools | All 17 named contracts exercised; 37 financial-tool/arithmetic/filter tests and 17 existing database tests | PASS |
| 11 — Quality/uncertainty | Shared query-aware quality layer; 19 additional quality/accounting tests; prior suites unchanged | PASS |
| 12 — Currency/FX | Immutable currency/rate models, local rate provider, exact dated eligibility lookup; 22 currency/FX tests | PASS |
| Integrated regression | All four test files run together after currency integration | PASS |

One initial test incorrectly expected no records for May 2023 intersected with
fiscal year `2022/2023`. Read-only inspection found three records, with fiscal
month 12. The test was corrected to assert those source facts. Implementation
already preserved the independent fiscal/calendar fields; no contract or data
was changed to satisfy the test. There are no outstanding failures or blockers.

## Final test run

Command from the repository root:

```sh
.venv/bin/python -B -m unittest discover -s tests -v
```

| Suite | Passed | Failed / errors | Skipped |
|---|---:|---:|---:|
| `tests/test_database.py` | 17 | 0 | 0 |
| `tests/test_financial_tools.py` | 37 | 0 | 0 |
| `tests/test_quality.py` | 19 | 0 | 0 |
| `tests/test_currency_fx.py` | 22 | 0 | 0 |
| **Total** | **95** | **0** | **0** |

Elapsed time: 97.136 seconds. This is the count of unittest test methods;
parameterized subtests (including the 17 named-tool checks) are not inflated into
additional test counts. Existing rebuild/failure-injection tests use disposable
temporary databases. No live rate API tests or skipped network tests exist.
The offline test disables socket creation and executes both fixture FX lookup
and an actual analytical query successfully.

## Final scope and integrity checks

| Requirement | Verified outcome |
|---|---|
| All 17 READY contracts implemented | RG-01–RG-08 and CF-01–CF-09; no blockers or redesign |
| Read-only tools | Verified bytes queried in SQLite with query_only; attempted writes fail |
| Parameterized selection / no arbitrary SQL | Caller values are bound parameters; identifiers come from a closed registry; SQL-shaped values remain literal values |
| Exact arithmetic | Decimal TEXT authority; precision-60 sums/medians with traps; exact single-rounding means/coverage; fixed-point strings |
| Contract result structure | Six approved statuses, separate errors/warnings, metadata/hash lineage, per-measure/group coverage |
| Record accounting | Population/selection and candidate/participation equations reconcile; dimension-before-measure exclusion priority |
| Scope-aware quality | Unrelated missing dimensions do not make queries partial; all scoped flags remain available |
| No missing-to-zero conversion | Empty/all-null statistics stay null; real zero remains a numeric decimal string |
| Placeholders unresolved | Discounts 53 and Profit 5 preserved; counts recomputed per query |
| Negative Profit | 58 negative observations preserved; no anomaly label; 637 positive, 0 numeric zero, 5 unresolved |
| DR/CR unchanged | Source accounting codes retained; no expense/revenue mapping or signed netting |
| No company identity | Sales-record labels only; no new company columns/entities |
| Current currency | UNKNOWN for both datasets; monetary code/source null; quantity/count currency null |
| No production FX conversion | No conversion arithmetic implemented; eligibility has converted_amount null and conversion_applied false |
| No live FX API | Protocol and local repository only; no HTTP client, API keys or external calls |
| Offline operation | Standard library only; existing runtime; no dependency installation |
| Provider privacy | Request object contains only source code, target code and rate date; tests verify absence of amount/private evidence |
| Database/schema unchanged | Pre/post SHA-256 comparison passed; no migrations or metadata writes |
| Raw/processed/historical outputs unchanged | All data files and notebooks retained their pre-task hashes; approved bundle checks pass |
| Tests | 95 passed, 0 failures/errors, 0 skipped |
| Excluded application/model scope | No EDA/cleaning rerun, ML, anomaly detection, forecast, RAG, agent, API, frontend or deployment added |

The hash comparison covered 33 protected pre-existing files: data, notebooks,
Phase 3 source files, Step 09 contracts and existing database tests. Other
pre-existing files under the baseline source/test/documentation directories also
remained unchanged. Intentional documentation edits outside that baseline are
the README and domain-glossary additions to CONTEXT.md.

Database SHA-256 (unchanged):
`8b9536867d7e1ee2e3fd8b0040d40f5806cf6ecb8afc38491cbc058de727c744`.

DDL SHA-256 (unchanged):
`7a815fe0ffbfa68849f5e3e1394d9e9e7fb117c771c7b318c0ab50fe75a83fe5`.

## Remaining limits and next decision

Unresolved denomination/comparability, source provenance, accounting grain and
summary/detail overlap, fiscal alignment, sparse accounting dimensions, sales
grain and missing company identity, fractional quantity semantics, and the
Discounts/Profit placeholders remain visible. The approved Profit parenthesis
sign convention stays dataset-specific. No query certifies revenue, expenditure,
cash, company financial statements or currency-comparable economic totals.

MIXED-currency aggregation, FX conversion and external providers are future work
requiring explicit evidence and contracts. Monetary ratios/shares and other
deferred Step 09 features remain unavailable. No rates are populated in production.

Recommended next decision: approve a deterministic CLI/reporting workflow over
the existing Financial Core contracts. Phase 4 stops here; no next-phase work
has been implemented.
