# Financial Manager AI

## Overview

Financial Manager AI V1 is a local-first financial analysis system. It combines
deterministic financial calculations, safe local dataset onboarding, bounded
statistical anomaly screening, structured evidence and an optional local LLM for
language mediation. It runs from a Python CLI and keeps financial and statistical
authority outside the model.

The finished V1 supports two separate data paths:

- approved legacy Receiver General and Company Financials snapshots; and
- user-supplied CSV or constrained XLSX files approved as `SALES_RECORD`.

## Why this project exists

Financial data arrives with different columns, meanings, quality conditions and
provenance. Treating every spreadsheet as an immediately trustworthy financial
table creates avoidable calculation, currency and lineage errors. This project
therefore separates safe ingestion, deterministic profiling, explicit semantic
approval, current capability readiness, authoritative computation and human
explanation.

## Core principles

- **Local-first:** data, artifacts, execution and optional model mediation remain local.
- **Deterministic authority:** Financial Core and anomaly services own calculations.
- **LLM as mediator:** a model may select a closed intent and explain evidence; it
  cannot calculate totals, infer currency or classify anomalies.
- **Explicit semantics:** suggestions are not financial facts until a user confirms them.
- **Fail closed:** stale, ambiguous, malformed or unsupported requests do not execute.
- **Structured evidence:** human and model-written explanations remain subordinate to
  exact machine-readable results.
- **Lineage and reproducibility:** fingerprints, versions, source rows and policy
  identifiers accompany execution.
- **Anomaly is not fraud:** `CANDIDATE` means only a statistical candidate for review.

## Current V1 features

- Safe local CSV and constrained-XLSX onboarding
- Deterministic structural profiling and closed semantic mapping
- Explicit role/domain confirmation and versioned local registry
- Dataset- and operation-specific readiness
- 17 legacy Financial Core operations
- Nine dynamic `SALES_RECORD` Financial Analysis operations
- Legacy anomaly screening and two dynamic GLOBAL Tukey-IQR screens
- `FinancialManagerAgent` orchestration
- One-shot and conversational CLI workflows
- Optional loopback local-LLM mediation with grounded response validation
- Conversational dynamic dataset selection, analysis and anomaly screening
- Bounded `why_selected` and `record_detail` candidate follow-up
- Exact `Decimal` evidence, currency boundaries, lineage and reproducibility checks
- Security/privacy controls and 720-test regression coverage

## Architecture

```text
User
  -> CLI / Conversational CLI
  -> ConversationMediator (optional local LLM)
  -> FinancialManagerAgent
  -> current readiness / validated closed request
  -> Financial Core or Anomaly Engine
  -> authoritative structured evidence
  -> deterministic or grounded presentation
```

Dynamic onboarding is a separate preparatory path:

```text
CSV / constrained XLSX
  -> safe ingestion
  -> deterministic profiling
  -> semantic suggestions
  -> explicit role and domain confirmation
  -> versioned local registry
  -> operation-specific readiness
  -> deterministic execution
```

Readiness is a current projection, not a stored authorization. Execution repeats
artifact and source-integrity validation.

## Supported data

### Legacy datasets

- **Receiver General:** eight fixed accounting query contracts and legacy screening.
- **Company Financials:** nine fixed sales/profit query contracts and legacy screening.

These paths require the approved hash-pinned local data bundle and generated
SQLite snapshot. They are not automatically migrated into dynamic onboarding.

### Dynamic datasets

Only explicitly approved `SALES_RECORD` datasets have a generic V1 execution
adapter. The ontology recognizes other domains, but recognition does not make
them executable.

## Dynamic Financial Analysis operations

The catalog is exactly:

1. `SALES_RECORD_COUNT`
2. `SALES_SUMMARY`
3. `SALES_BY_COUNTRY`
4. `SALES_BY_PERIOD`
5. `SALES_BY_SEGMENT`
6. `SALES_BY_PRODUCT`
7. `PROFIT_SUMMARY`
8. `DISCOUNT_ANALYSIS`
9. `UNITS_SOLD_SUMMARY`

Availability is evaluated independently per dataset and operation. Optional
confirmed roles unlock only their corresponding operations.

## Anomaly detection

Dynamic anomaly screening supports exactly `SALES_ANOMALY_SCREEN` and
`PROFIT_ANOMALY_SCREEN`. Both use GLOBAL, two-sided Tukey-IQR v1.0, require at
least 30 usable values and a positive IQR, and preserve source signs and currency
state. Profit must be supplied and confirmed; it is never reconstructed.

`CANDIDATE` != `FRAUD` != `ERROR` != `SUSPICIOUS ACTIVITY`. A candidate is only
a statistical candidate for review. Dynamic peer screening and ML anomaly models
are not implemented.

## Conversational interface

Without a model, `chat` provides deterministic session commands and legacy
requests. With an optional loopback local provider, natural language may select
only allowlisted intents, exact eligible dataset IDs and closed operations. The
mediator receives bounded catalog metadata for interpretation and bounded facts
for explanation—not complete datasets or arbitrary executable text.

Sessions are process-local and non-persistent. `/cancel`, `/reset`, expiry and
selection changes clear the relevant context and candidate references.

## Installation

Validated environment: **CPython 3.14.7**. The V1 production runtime uses only
the Python standard library and repository source.

```sh
git clone https://github.com/piter-gilaab/financial-manager-ai.git
cd financial-manager-ai
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m src.provisioning
```

`requirements.txt` intentionally declares no third-party runtime dependency.
The provisioning validator performs no download and does not run the tests.

## Data provisioning

The legacy CLI requires the approved raw and processed bundle described in
[`data/README.md`](data/README.md). Those files are private/custodian-provided,
hash-pinned and intentionally absent from Git. The project has no supported
download or regeneration command for them.

After placing the approved files at their documented repository-relative paths:

```sh
python -m src.provisioning
python -m src.database.initialize
```

The database builder refuses to replace an existing database. Dynamic onboarding
accepts a user's own bounded local CSV/XLSX and stores immutable local artifacts
under the Git-ignored `data/onboarding/` path; it does not require adding that
source to Git.

## Quick start

Run from the repository root with the environment activated:

```sh
python -m src.cli capabilities
python -m src.cli plan "What were total sales by country?"
python -m src.cli ask "How many Company Financials records are there?"
python -m src.cli ask "What were total sales by country?" --json
python -m src.cli chat
```

The record-count command was validated against the approved legacy snapshot. A
bounded excerpt of its actual output is:

```text
Status: SUCCESS
Execution: PERFORMED
Step 1 — FINANCIAL_ANALYSIS: SUCCESS
The tool counted 700 source records.
```

Use `--full` for expanded human evidence or `--json` for the complete structured
response. An exit status of zero means a structured application response was
delivered; inspect its application status to distinguish success, blocked and
clarification outcomes.

## Dynamic dataset workflow

The following commands are real CLI syntax. The temporary synthetic file is
created by the [V1 usage guide](docs/v1_usage_guide.md); replace `ds_...` with the
opaque ID printed by `dataset add`.

```sh
python -m src.cli dataset add /tmp/financial_manager_ai_v1_demo.csv \
  --provenance-note "Synthetic V1 demo"
python -m src.cli dataset status ds_... --json
python -m src.cli dataset profile ds_... --json
python -m src.cli dataset mappings ds_... --json

python -m src.cli dataset confirm-domain ds_... SALES_RECORD \
  --evidence "Synthetic demo specification"
python -m src.cli dataset confirm ds_... date TRANSACTION_DATE \
  --date-format YYYY-MM-DD --evidence "Synthetic demo specification"
python -m src.cli dataset confirm ds_... sales SALES \
  --evidence "Synthetic demo specification"
python -m src.cli dataset confirm ds_... country COUNTRY \
  --evidence "Synthetic demo specification"
python -m src.cli dataset confirm ds_... segment SEGMENT \
  --evidence "Synthetic demo specification"
python -m src.cli dataset confirm ds_... product PRODUCT \
  --evidence "Synthetic demo specification"
python -m src.cli dataset confirm ds_... profit PROFIT \
  --evidence "Synthetic demo specification"
python -m src.cli dataset confirm ds_... discount DISCOUNT \
  --evidence "Synthetic demo specification"
python -m src.cli dataset confirm ds_... units UNITS_SOLD \
  --evidence "Synthetic demo specification"

python -m src.cli dataset capabilities ds_...
```

`dataset add` never makes suggested semantics authoritative. Confirm only roles
supported by real evidence for the supplied source.

## Conversational examples

With a confirmed dataset and optional local mediation enabled:

```text
User: Use dataset ds_<runtime-generated-id>.
User: Show sales by country.
User: Now by product.
User: Check Sales for anomalies.
User: Why was A1 selected?
```

The ID above is illustrative and does not exist until onboarding returns one.
`A1` is available only if the current authoritative screen issued that label.
The deterministic slash equivalent is `/follow A1 why_selected` after an issued
reference; use `/help` inside chat for the complete command list.

## Optional local LLM

The supported provider is a loopback-hosted OpenAI-compatible chat-completions
endpoint. Ollama may be used when already installed and configured; it is not a
V1 prerequisite and the project never downloads a model.

```sh
python -m src.cli chat --llm-model YOUR_LOCAL_MODEL
```

The default endpoint is `http://127.0.0.1:11434/v1/chat/completions`. A custom
`--llm-url` must remain loopback. Redirects, environment proxies and external
providers are refused. Provider failure cannot change deterministic evidence;
local-model latency depends on model and hardware.

## Testing

The final Step 73 acceptance baseline is **720 passed, 0 failed, 0 errors and 0
skipped**. Run the complete suite with:

```sh
python -B -m unittest discover -s tests
```

See [`docs/v1_technical_validation.md`](docs/v1_technical_validation.md) for
security, integrity, fresh-process and performance evidence.

## Security and privacy

- No telemetry or persistent chat transcript
- No external LLM requirement
- Loopback-only optional provider with bounded requests/responses
- No user-controlled `eval`, `exec`, shell, raw SQL or adapter dispatch
- Safe bounded CSV/XLSX ingestion with archive and workbook restrictions
- Local registry and source artifacts protected by Git-ignore rules
- Grounding rejects invented numbers, identifiers and unsafe verdict language

These are application boundaries, not a compliance certification. Host access,
disk encryption, backups and terminal/shell-history retention remain operator responsibilities.

## V1 limitations

- Local, single-user CLI; no server or public API
- Only `SALES_RECORD` has generic dynamic execution
- Readiness is dataset- and operation-specific
- Dynamic anomaly screening is GLOBAL-only Tukey-IQR v1.0
- Dynamic anomaly measures are Sales and supplied confirmed Profit only
- Candidate labels are bounded, session-local and evidence-specific
- Currency is never inferred and no FX conversion is performed
- Legacy data requires the approved private bundle
- Live local-model quality and speed depend on the selected model/hardware

## V2 / future work

Cash Flow Forecasting, Financial Document RAG, dynamic peer anomaly screening,
additional executable domains, arbitrary querying, ML/fraud models, SaaS,
frontend, API, authentication, multi-user/multitenant operation, cloud storage,
banking execution, ERP integrations, PostgreSQL migration, additional providers
and mobile applications are explicitly outside V1.

## Documentation

- [V1 usage guide](docs/v1_usage_guide.md)
- [5–10 minute demo walkthrough](docs/v1_demo_walkthrough.md)
- [Frozen V1 scope](docs/v1_scope_freeze.md)
- [Technical guide](docs/financial_manager_ai_guide.md)
- [Security/privacy boundaries](docs/security_privacy_boundaries.md)
- [Environment and data provisioning](docs/environment_and_data_provisioning.md)

## Project status

**Financial Manager AI V1 — COMPLETE.** Steps 1–73 are accepted, the scope is
frozen and deferred capabilities remain future/V2 work requiring new approval.
