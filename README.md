# Financial Manager AI V2

**Release status: V2 release candidate — remediation implemented; final
tasteskill gate inconclusive.** The product is implemented, but it is not a final
release and `v2.0.0` must not be tagged until the audit gate passes. Current scope authority:
[`docs/v2_scope_freeze.md`](docs/v2_scope_freeze.md).

Financial Manager AI V2 is a local-first, multi-domain financial analysis
platform. It safely onboards approved CSV/XLSX datasets, requires explicit
financial-semantic confirmation, recomputes operation-specific readiness and
executes closed deterministic capabilities. CLI-compatible workflows, an
Application Layer, local FastAPI and the Web Financial Workspace expose the same
authoritative evidence. An optional local LLM may interpret bounded intents and
explain evidence; it never owns financial or statistical truth.

V2 is **local-first and offline-capable after installation and provisioning**.
It is not offline-only: cloning, dependency installation, updates and obtaining
the private legacy bundle may require authorized network/custodian access.
Mandatory deterministic runtime analysis requires no external Internet service;
Web-to-API and optional model traffic stay on loopback.

## Principles and architecture

- Financial Core owns totals, averages, grouping, aging, overdue and net cash.
- Anomaly modules own quartiles, IQR, fences, eligibility and classification.
- Semantic suggestions are hypotheses until explicit evidence-bearing approval.
- Readiness is current, dataset-specific, operation-specific and revocable.
- Exact monetary authority uses `Decimal`; JSON/UI evidence uses base-10 strings.
- Currency and cash direction are never inferred; no hidden FX is performed.
- Closed catalogs reject arbitrary SQL, formulas, groupings, columns or adapters.
- `CANDIDATE` means statistical candidate for review, never fraud/error/risk.

```text
CSV / constrained XLSX
  -> safe ingestion -> deterministic profile -> explicit semantics/qualifiers
  -> current readiness -> FinancialManagerAgent -> binder/adapter
  -> Financial Core or Anomaly Engine -> authoritative evidence
  -> Application Layer -> FastAPI /api/v1 -> Web / optional conversation
```

Legacy Receiver General and Company Financials remain frozen V1 snapshot paths.
They are separate from generic V2 onboarding domains.

## Supported domains and exact catalogs

### `SALES_RECORD` — 9

1. `SALES_RECORD_COUNT`
2. `SALES_SUMMARY`
3. `SALES_BY_COUNTRY`
4. `SALES_BY_PERIOD`
5. `SALES_BY_SEGMENT`
6. `SALES_BY_PRODUCT`
7. `PROFIT_SUMMARY`
8. `DISCOUNT_ANALYSIS`
9. `UNITS_SOLD_SUMMARY`

### `PAYABLE` — 6

`PAYABLE_COUNT`, `PAYABLE_SUMMARY`, `PAYABLE_BY_SUPPLIER`,
`PAYABLE_BY_DUE_PERIOD`, `PAYABLE_AGING`, `OVERDUE_PAYABLE_SUMMARY`.

### `RECEIVABLE` — 6

`RECEIVABLE_COUNT`, `RECEIVABLE_SUMMARY`, `RECEIVABLE_BY_CUSTOMER`,
`RECEIVABLE_BY_DUE_PERIOD`, `RECEIVABLE_AGING`,
`OVERDUE_RECEIVABLE_SUMMARY`.

### `CASH_TRANSACTION` — 6

`CASH_TRANSACTION_COUNT`, `CASH_INFLOW_SUMMARY`, `CASH_OUTFLOW_SUMMARY`,
`NET_CASH_BY_PERIOD`, `CASH_BY_CATEGORY`, `CASH_BY_ACCOUNT`.

V2 adds exactly 18 multi-domain operations while preserving the nine Sales
operations. The frozen details are in [the final scope](docs/v2_scope_freeze.md).

## Anomaly scope

Exactly `SALES_ANOMALY_SCREEN` and `PROFIT_ANOMALY_SCREEN`: GLOBAL, two-sided
Tukey-IQR v1.0, minimum 30 usable values and positive IQR. Profit must be supplied
and confirmed; it is never reconstructed. Peer screens, additional domains, ML
and fraud scoring are not implemented.

## Installation

Validated release environment: CPython **3.14.8**, Node **26.13.0** and npm
**11.20.0**. Python and Node dependencies are pinned by `requirements.txt` and
`web/package-lock.json`.

```sh
git clone https://github.com/piter-gilaab/financial-manager-ai.git
cd financial-manager-ai
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m src.provisioning
cd web
npm ci
cp .env.example .env.local
cd ..
```

Generic onboarding uses your own bounded CSV/XLSX. Legacy snapshot execution
requires the private hash-approved bundle described in
[environment and data provisioning](docs/environment_and_data_provisioning.md).

## Start locally

Terminal 1, repository root:

```sh
FINANCIAL_API_CORS_ORIGINS=http://127.0.0.1:3000 .venv/bin/python -m src.api
```

Terminal 2:

```sh
cd web
npm run dev
```

Open `http://127.0.0.1:3000`. Health is
`http://127.0.0.1:8000/api/v1/health`. These are local development servers; public
exposure is outside the security model.

## Web workflow

1. Open **Datasets → Add dataset** and upload one bounded UTF-8 CSV or constrained
   XLSX (formulas/macros/external links are rejected).
2. Inspect deterministic profile and suggestions.
3. Confirm/correct/reject semantic roles with evidence.
4. Confirm the exact domain and required qualifiers: outstanding balance/reference
   date for aging, or cash amount convention for cash.
5. Inspect current per-operation readiness.
6. Run a closed analysis and inspect exact evidence, currency, coverage,
   limitations and lineage.
7. For eligible Sales data, run Sales/Profit anomaly screening.
8. Optionally use process-local chat for bounded selection/explanation.

See the complete [V2 usage guide](docs/v2_usage_guide.md) and
[5–10 minute synthetic demo](docs/v2_demo_walkthrough.md).

## CLI

```sh
python -m src.cli capabilities
python -m src.cli dataset add /path/to/source.csv --provenance-note "Owner export"
python -m src.cli dataset profile ds_... --json
python -m src.cli dataset mappings ds_... --json
python -m src.cli dataset confirm-domain ds_... SALES_RECORD --evidence "Owner spec"
python -m src.cli dataset confirm ds_... Sales SALES --evidence "Owner spec"
python -m src.cli dataset capabilities ds_... --json
python -m src.cli chat
```

The frozen V1 CLI remains compatible. V2 qualifier confirmation for
payable/receivable/cash is available through Web/API; it is never inferred by CLI.

## Local API

FastAPI `/api/v1` provides health/capabilities, dataset onboarding/profile/mapping,
domain/qualifier confirmation, readiness, analysis, anomalies and process-local
conversation. Request schemas are closed and reject unknown operations/fields;
authoritative Decimal is serialized as JSON string data.

```sh
curl http://127.0.0.1:8000/api/v1/health
curl http://127.0.0.1:8000/api/v1/capabilities
curl http://127.0.0.1:8000/api/v1/datasets
```

The checked-in `web/openapi.json` and generated TypeScript schema represent the
closed transport contract.

## Optional local LLM

An already-installed OpenAI-compatible loopback provider may be used from CLI
chat or the conversation adapter. The default endpoint is
`http://127.0.0.1:11434/v1/chat/completions`. Redirects, environment proxies and
non-loopback endpoints are refused; no model is downloaded automatically.
Provider failure does not affect deterministic operation or evidence.

```sh
python -m src.cli chat --llm-model YOUR_LOCAL_MODEL
```

## Security and privacy

- Local loopback binding and explicit loopback-only CORS allowlist
- Bounded safe CSV/constrained-XLSX ingestion and temporary upload cleanup
- Exact dataset/session IDs and allowlisted operations/parameters/adapters
- No telemetry, analytics, persistent transcript or browser transcript storage
- No user-controlled shell, `eval`, `exec`, raw SQL or arbitrary URL fetch
- Safe error envelopes without stack traces, source contents or absolute paths
- Private data, databases, `.env.local`, environments and build/test artifacts
  are Git-ignored

These are application boundaries, not a compliance certification. Host access,
disk encryption, backups, browser/shell history and public network controls remain
operator responsibilities. Session IDs are not authentication.

## Testing

Initial V2 release-candidate evidence before the current remediation:

- Backend: **773 passed**, 0 failed/errors/skipped
- Frontend Vitest: **33 passed** in 10 files
- Chromium real FastAPI E2E: **11/11 passed**
- Offline-simulated real FastAPI E2E: **11/11 passed**
- Type generation/typecheck, ESLint, Python compilation, OpenAPI and production
  Next.js build: PASS
- Clean Python venv and clean `npm ci`/build: PASS

```sh
.venv/bin/python -B -m unittest discover -s tests
cd web
npm run typecheck
npm run lint
npm test
npm run build
npm run test:e2e:real
```

## Limitations and deferred work

- Local single-user application; no authentication, users/organizations,
  multitenancy, SaaS or approved public deployment
- No Cash Flow Forecasting, Financial Document RAG, ML/fraud, new anomaly domains,
  arbitrary SQL/formulas/group-by/query DSL, ERP, banking/payment execution,
  PostgreSQL migration, cloud storage, additional external LLM providers or mobile
- Currency is not inferred; no FX; multiple confirmed currencies block scalar sums
- Aging is snapshot-only at the confirmed reference date; no historical-state
  reconstruction and no machine-today authority
- Anomaly is GLOBAL Sales/Profit IQR only and makes no wrongdoing claim
- Live local-model quality and latency depend on model/hardware

## Releases

V2 Phase 5 remediation is implemented and functionally validated; see the
[remediation record](docs/v2_phase5_release_remediation.md),
[release candidate](docs/v2_release_candidate.md) and
[initial candidate acceptance](docs/v2_final_acceptance.md). Do not create the
tag until a fresh authorized tasteskill gate returns PASS/OPEN without a blocker.

The historical V1 release remains frozen at tag `v1.0.0` with its 720-test final
baseline and CLI/snapshot behavior. V1 history is preserved; V2 is the current
product.
