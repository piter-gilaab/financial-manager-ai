# Phase 3 Validation — Completed

Approved cleaning run: `20260928T190320706702Z_0a18cf5b`.
Database: [financial_manager.db](../data/database/financial_manager.db).
Full read-only query results, all 57 database checks and artifact hashes:
[load_validation_report.json](../data/database/load_validation_report.json).

## Checkpoints and evidence

06 passed: separate accounting and sales domains; shared lineage and quality only;
no canonical transaction/company or business join; unknown currencies and unresolved
fiscal alignment retained. See [data_model.md](data_model.md).

07 passed: eight tables, composite lineage foreign keys, source/status constraints,
exact decimal TEXT, documented indexes and deferred concepts.
See [database_schema.md](database_schema.md). The Mermaid schema diagram names the
actual tables; conceptual monetary/period/dimension/currency concepts are embedded
attributes rather than additional unsupported master entities.

08 passed: 57 load checks, committed-file read-only reload, final published-file
read-only validation, SQLite integrity `ok`, foreign-key check empty.
Initialization refuses an existing destination and is rebuildable at another path.

| Requirement | Result |
|---|---|
| Approved run only; manifest/report/output hash pins | PASS |
| Raw files unchanged | PASS; both source hashes match approval |
| Approved processed artifacts unchanged | PASS; all five hashes match approval |
| Notebooks 01–05 unchanged | PASS; hashes match phase-start pins |
| Receiver General rows | 9,282 |
| Sales rows | 700 |
| Every standardized/raw/status/lineage value preserved | PASS, full row-by-row typed comparison |
| Candidate composite-key repetitions | 0 in both domains, matching cleaning report |
| Complete duplicate source-field rows | 0 in both domains |
| Company Financials five-field repetitions | Preserved, 12 (without Sale Price) |
| Exact numeric values, signs, scale and extrema | PASS |
| Negative Profit | 58 preserved |
| Receiver General zero amounts | 2 preserved |
| Null/status distinction | 29,876 source-missing RG cells; 58 CF unresolved placeholders; zero parser failures |
| Currency | UNKNOWN; all codes/original currency/evidence remain null |
| Lineage | 9,982 rows; every domain record resolves to raw + processed source and run |
| Quality flags | 29,944; original tokens/reasons/scopes preserved |
| Foreign-key violations | 0 |
| SQLite integrity | ok |
| Smoke queries | 7 groups of source-reconciled queries passed |
| Automated tests | 17 passed in 36.238 seconds; stdlib unittest |
| Rebuild from scratch | Same schema and stable record keys; full value validation passes |

Flag counts: source_missing 29,876; unresolved_placeholder 58; currency_unknown 2;
source_semantics_unresolved 7; fiscal_alignment_unresolved 1. Dataset conditions
remain dataset-scoped and were not duplicated over every record. No new issues
or meaning were inferred.

## Exact numeric smoke results

These are preservation checks in unverified source denominations; they are not
currency-comparable economic totals. SQL uses DECIMAL_SUM, not built-in SUM.

- Receiver General item amount: 3061288992129.16.
- Sales (700 available): 118726350.29.
- Profit (695 available): 16893702.29.
- Accounting effective-date range query: 2023-04-03 through 2024-01-03, 9,282 records.
- DR/CR grouped amounts, voucher counts, 16 monthly Profit groups and
  country/segment/product counts reconcile against the approved processed records.

## Automated coverage

Command: `.venv/bin/python -m unittest discover -s tests -v`.
Tests cover approved-run selection, every processed field, decimal precision/signs/
extremes, placeholders, literal None, identifiers, lineage, currency, flags,
integrity, smoke queries, FK/domain/status constraints, tampered input rejection,
existing-file preservation, schema+data rollback, precommit validation failure,
postcommit reload failure, reproducible rebuild and protected-source hashes.
Expected simulated failures publish no database; they are tests of the failure
policy, not failures of the approved data.

Database SHA-256:
`8b9536867d7e1ee2e3fd8b0040d40f5806cf6ecb8afc38491cbc058de727c744`

Schema SHA-256:
`7a815fe0ffbfa68849f5e3e1394d9e9e7fb117c771c7b318c0ab50fe75a83fe5`

Rebuild timestamps intentionally vary; binary database hashes need not be identical.
Source facts, record keys, flags and schema are reproducible.

## Remaining interpretation limits and next decision

Fiscal alignment, summary/item overlap, acquisition provenance, exact sales grain,
currency and dollar-dash meanings remain unresolved. Neither the database nor its
validation certifies cash movements, budget comparability, company histories or
currency-comparable totals.

Next: review and authorize the contracts for read-only Financial Data Analysis
queries, including allowable aggregations and required uncertainty disclosures.
No financial tools, agents, FX, ML, RAG, API, UI or deployment were implemented.
