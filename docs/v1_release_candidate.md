# Financial Manager AI V1 Release Candidate

Status: **ACCEPTED RELEASE CANDIDATE** for Phase 18 Step 73.

This inventory identifies the frozen candidate that is being evaluated for V1
final acceptance. It does not create a commit, tag, package, GitHub release or
published artifact. The candidate is the reviewed local worktree based on branch
`main` at `1a5bc12545548e30f4170064f0e2605c944c51b4`, including the uncommitted
Phase 17–18 changes that must later be staged intentionally.

## Product definition

Financial Manager AI V1 is a local-first CLI system for deterministic financial
analysis and bounded statistical anomaly screening over approved legacy data and
explicitly onboarded `SALES_RECORD` data. It supports structured and
conversational use while keeping financial/statistical authority outside the LLM.

## Frozen capabilities

| Capability | V1 state |
|---|---|
| Financial Analysis | `AVAILABLE` |
| Dynamic `SALES_RECORD` Financial Analysis | `AVAILABLE`, subject to current dataset/operation readiness |
| Legacy Anomaly Detection | `AVAILABLE` |
| Dynamic Anomaly Detection | `AVAILABLE_WITH_LIMITATIONS` |
| Conversational Financial Analysis | `AVAILABLE` |
| Conversational Dynamic Financial Analysis | `AVAILABLE` |
| Conversational Dynamic Anomaly | `AVAILABLE_WITH_LIMITATIONS` |
| Cash Flow Forecasting | `BLOCKED` / V2 |
| Document Retrieval / RAG | `BLOCKED` / V2 |
| Additional executable domains | `DEFERRED` / V2 |

## Operation inventory

Legacy Financial Core remains exactly 17 contracts: eight Receiver General and
nine Company Financials operations.

Dynamic Financial Analysis remains exactly:

1. `SALES_RECORD_COUNT`
2. `SALES_SUMMARY`
3. `SALES_BY_COUNTRY`
4. `SALES_BY_PERIOD`
5. `SALES_BY_SEGMENT`
6. `SALES_BY_PRODUCT`
7. `PROFIT_SUMMARY`
8. `DISCOUNT_ANALYSIS`
9. `UNITS_SOLD_SUMMARY`

Dynamic anomaly remains exactly:

- `SALES_ANOMALY_SCREEN`
- `PROFIT_ANOMALY_SCREEN`

Both dynamic screens are GLOBAL, two-sided Tukey-IQR v1.0, require at least 30
usable values and positive IQR, and use Sales or supplied confirmed Profit only.
Candidate status is statistical screening evidence, not fraud/error/suspicion.

## Executable domain boundary

Only approved `SALES_RECORD` has a generic dynamic V1 adapter. Recognized
`ACCOUNTING_TRANSACTION`, `CASH_TRANSACTION`, `PAYABLE`, `RECEIVABLE`,
`BUDGET_RECORD`, `BALANCE_RECORD` and `DOCUMENT_METADATA` do not gain generic
execution from recognition. Receiver General and Company Financials remain
separate executable legacy paths.

## Runtime and setup

- Validated Python: CPython 3.14.7; supported repository contract: Python 3.14.
- Runtime dependencies: Python standard library plus repository source.
- CLI entry point: `python -m src.cli` from the repository root.
- Legacy persistence: local validated SQLite built from one approved data run.
- Dynamic persistence: versioned local artifacts under `data/onboarding/`.
- Network: not required for authoritative execution or acceptance.
- Optional mediation: loopback OpenAI-compatible local provider only.

Setup, provisioning and copy-pasteable commands are documented in
[`v1_usage_guide.md`](v1_usage_guide.md).

## Data prerequisites

Legacy execution requires two raw CSVs and the five artifacts of approved run
`20260928T190320706702Z_0a18cf5b`, obtained from an authorized custodian and
verified against pinned hashes. Git does not distribute those bytes and the
project performs no automatic download.

Dynamic users supply their own bounded local CSV/constrained XLSX, review its
profile and explicitly confirm domain/roles. Source bytes and registry artifacts
remain local and Git-ignored.

## Authority and security assumptions

- Financial Core owns financial arithmetic.
- The anomaly engine owns quartiles, fences and classification.
- Readiness is recomputed for the exact dataset/operation.
- Adapters authenticate current source/artifact lineage at execution.
- The LLM proposes only a closed intent and grounded prose.
- Currency is unknown unless explicitly confirmed by approved evidence.
- Missing/parse failures are never silently converted to zero.
- No user-controlled executable code, SQL, shell or adapter selection exists.
- No telemetry or persistent transcript exists.
- Host access control, disk encryption, backups and shell history are operator responsibilities.

These boundaries are engineered and tested but are not a production/compliance certification.

## Deferred capabilities

Forecasting, Financial Document RAG, peer dynamic anomaly screening, additional
executable domains, arbitrary query/statistical languages, ML/fraud models,
SaaS/frontend/API/authentication, multi-user/multitenant operation, cloud
storage, banking execution, ERP integration, PostgreSQL, additional providers
and mobile applications remain outside V1.

## Known non-blocking limitations

- Local, single-user CLI and process-local conversation
- Private approved bundle required for legacy execution
- Dynamic readiness varies by exact dataset and operation
- GLOBAL-only fixed anomaly policy and only two measures
- A1–A10 bounded, session/evidence-specific candidate labels
- No currency inference or FX conversion
- Local-model wording and latency vary with hardware/model
- `FinancialManagerSession` remains a relatively large maintenance seam

## Validation baseline

Step 71 established 720 passing tests with no failure, error or skip, plus passing
security/privacy, compilation, diff, prohibited-execution, unfinished-marker,
temporary/secret and catalog checks. Step 72 added documentation only and passed
116 focused CLI/onboarding/conversation tests. Step 73 records the final complete
720-test pass after documentation and the single final review.

## Repository and release form

The project does not need a new package/version mechanism for this local CLI.
There is no existing Git tag convention. If final acceptance passes and the
changes are intentionally committed, the recommended initial release tag is
`v1.0.0`. This record does not create it.
