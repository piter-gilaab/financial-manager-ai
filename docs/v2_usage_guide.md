# Financial Manager AI V2 — Usage Guide

## 1. Installation

Prerequisites: CPython 3.14, Node.js/npm, Git and a Chromium installation usable
by Playwright only when running browser tests.

```sh
git clone https://github.com/piter-gilaab/financial-manager-ai.git
cd financial-manager-ai
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m src.provisioning
cd web && npm ci && cd ..
```

The legacy snapshot workflows additionally need the custodian-provided,
hash-approved bundle described in [environment provisioning](environment_and_data_provisioning.md).
Generic onboarding uses your own bounded CSV/XLSX and does not need that bundle.

## 2. Startup

Terminal 1, repository root:

```sh
FINANCIAL_API_CORS_ORIGINS=http://127.0.0.1:3000 .venv/bin/python -m src.api
```

Terminal 2:

```sh
cd web
cp .env.example .env.local
npm run dev
```

Open `http://127.0.0.1:3000`. Health is
`http://127.0.0.1:8000/api/v1/health`; local OpenAPI is available from the
FastAPI application. Do not expose either server publicly.

## 3. Web Overview

Overview shows registered datasets, approved domain, lifecycle/readiness,
currency state and closed operation availability. It deliberately does not invent
cross-dataset KPIs.

## 4. Add CSV/XLSX

Choose **Add dataset**, select one UTF-8 CSV or constrained `.xlsx`, optionally
choose an exact sheet and provide a provenance note. XLSX formulas, macros,
external links and unsafe archives are rejected. The upload does not approve any
financial meaning.

## 5. Profiling

Inspect row/column counts, structural types, missingness, parse coverage, bounded
examples and sensitivity hints. A profile describes structure, not authority.

## 6. Semantic confirmation

For each relevant column, confirm, correct or reject the proposed canonical role
and provide evidence. Dates require an explicit format; status/direction values
require a complete closed value mapping. Suggestions never approve themselves.

## 7. Domain confirmation

Approve exactly one supported domain only when the source evidence supports it:
`SALES_RECORD`, `PAYABLE`, `RECEIVABLE` or `CASH_TRANSACTION`. Supplier and
customer are distinct; an obligation is not a cash movement.

## 8. Qualifiers

Payable/receivable aging needs `OUTSTANDING_BALANCE` plus an explicit
`dataset_reference_date`. Cash needs a confirmed amount convention:
`ABSOLUTE_WITH_DIRECTION` or `SIGNED_WITH_DIRECTION`. Currency may remain
`UNKNOWN`; never guess it. `CONFIRMED_MULTIPLE` blocks scalar monetary totals.

## 9. Readiness

Readiness is per dataset and operation. Resolve only evidence-backed blockers.
Changing source/profile/mapping/qualifiers revokes stale readiness; execution
checks current artifacts again.

## 10. Analysis

Open **Financial analysis**, select the exact dataset, one returned ready operation
and only its bounded parameters. Aging/overdue `as_of_date` must equal the approved
reference date. Exact values, coverage, currency, exclusions, limitations and
lineage come from the backend; charts are presentation geometry only.

The complete catalogs are in [the scope freeze](v2_scope_freeze.md).

## 11. Anomalies

Use **Anomalies** only for eligible `SALES_RECORD` Sales or supplied Profit. The
GLOBAL Tukey-IQR screen requires at least 30 usable values and positive IQR.
`CANDIDATE` means statistical candidate for review—not fraud, error, suspicion,
risk or proof. Candidate follow-up is bounded to labels issued by current evidence.

## 12. Chat

**Ask Financial Manager** creates a process-local session. Deterministic commands
and controlled provider-unavailable behavior work without a model. An optional
already-installed loopback OpenAI-compatible model may interpret closed intents
and explain evidence; it cannot calculate truth. Reset/cancel/expiry clears
session context, and transcripts are not persisted.

## 13. CLI alternative

```sh
python -m src.cli capabilities
python -m src.cli dataset add /path/to/source.csv --provenance-note "Owner export"
python -m src.cli dataset profile ds_... --json
python -m src.cli dataset mappings ds_... --json
python -m src.cli dataset confirm-domain ds_... SALES_RECORD --evidence "Owner specification"
python -m src.cli dataset confirm ds_... Sales SALES --evidence "Owner specification"
python -m src.cli dataset capabilities ds_... --json
python -m src.cli chat
```

The CLI preserves the V1 commands and supports generic onboarding/inspection.
V2 qualifier confirmation for payable/receivable/cash is performed through Web or
the local API; this is an intentional surface limitation, not implicit approval.
With an optional local model, use `chat --llm-model NAME`; non-loopback URLs fail.

## 14. API concept

`/api/v1` exposes health/capabilities, datasets/onboarding, mapping/domain/qualifier
decisions, readiness, analysis, anomalies and process-local conversations. Request
models reject unknown fields and arbitrary operations. Decimal evidence is JSON
string data. Prefer generated OpenAPI/types over hand-built request shapes.

Example read-only checks:

```sh
curl http://127.0.0.1:8000/api/v1/health
curl http://127.0.0.1:8000/api/v1/capabilities
curl http://127.0.0.1:8000/api/v1/datasets
```

## 15. Troubleshooting

- `unsupported_format`/upload errors: use a bounded UTF-8 CSV or constrained XLSX.
- `CLARIFICATION_REQUIRED`: choose the exact XLSX sheet or provide the requested
  semantic/parameter decision.
- blocked readiness: inspect the operation's reasons; never bypass them.
- aging blocked: confirm outstanding-balance semantics, complete statuses and the
  exact dataset reference date.
- provider unavailable: continue through Web/API/closed CLI; the model is optional.
- CORS failure: start the API with the exact loopback Web origin.
- stale artifact: re-onboard/reconfirm from the current source; do not edit registry
  JSON or preserved artifacts.

## 16. Offline behavior

After dependencies, build and data are provisioned, mandatory deterministic runtime
works without Internet. Localhost networking remains required for Web -> FastAPI.
Installation, updates and obtaining legacy custodian data may require network or
authorized transfer. The product is offline-capable, not offline-only.

## 17. Limitations

Local single-user runtime; no authentication, tenant isolation or public-hosting
contract. No Forecasting, RAG, fraud/ML, arbitrary querying, ERP/banking, cloud,
PostgreSQL or mobile. Currency is not inferred and no FX is applied. Anomalies are
Sales/Profit GLOBAL IQR only. Optional LLM behavior/latency depends on the local
model; deterministic operation does not.
