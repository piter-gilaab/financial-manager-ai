# Financial Manager AI V1 Usage Guide

This guide is the operational companion to the repository README. Commands are
shown from the repository root and use the implemented V1 CLI. Replace every
placeholder such as `ds_...` or `YOUR_LOCAL_MODEL`; never paste a placeholder as
if it were a registered identifier.

## 1. Environment setup

V1 is validated on CPython **3.14.7**. Runtime code, database construction and
the test suite use only the Python standard library and repository source.

```sh
git clone https://github.com/piter-gilaab/financial-manager-ai.git
cd financial-manager-ai
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m src.provisioning
```

`requirements.txt` contains no installable third-party package. Upgrading pip is
optional and is the only common setup step that could contact a package index.

## 2. Data prerequisites

### Legacy path

Legacy Receiver General and Company Financials analysis requires the exact
approved raw and processed artifacts listed in [`data/README.md`](../data/README.md).
They are not distributed by Git because provenance/licensing and privacy do not
authorize redistribution. Obtain the hash-approved bundle from the authorized
project custodian and keep its repository-relative layout unchanged.

Validate it without changing files:

```sh
python -m src.provisioning
```

### Dynamic path

Dynamic onboarding accepts a bounded local UTF-8/UTF-8-SIG CSV or constrained
XLSX. The source may remain anywhere readable on the local filesystem; accepted
bytes and versioned artifacts are preserved under `data/onboarding/`, which is
Git-ignored. Do not onboard data you are not authorized to process.

## 3. Database initialization

When provisioning reports that the approved legacy inputs are valid and the
default database is absent, build it once:

```sh
python -m src.database.initialize
```

The builder refuses to overwrite `data/database/financial_manager.db`. To test a
rebuild without touching it, use a new destination:

```sh
python -m src.database.initialize --database /tmp/financial_manager.rebuilt.db
```

Run `python -m src.provisioning` again after initialization. Dynamic dataset
artifacts do not replace or modify this legacy SQLite snapshot.

## 4. Inspect global capabilities

```sh
python -m src.cli capabilities
python -m src.cli capabilities --json
```

The global catalog reports legacy Financial Analysis and Anomaly Detection as
available. Forecasting and Document Retrieval remain blocked. Dynamic readiness
is inspected separately for one exact dataset ID.

## 5. One-shot plan and ask

Preview routing without executing:

```sh
python -m src.cli plan "What were total sales by country?"
python -m src.cli plan "Find unusual Profit values" --json
```

Execute an approved legacy request:

```sh
python -m src.cli ask "How many Company Financials records are there?"
python -m src.cli ask "What were total sales by country?" --full
python -m src.cli ask "What were total sales by country?" --json
```

The first command was validated against the approved snapshot and reports 700
source records. `--full` expands human evidence; `--json` preserves the complete
Manager response. Do not combine those flags.

## 6. Interactive chat

Start deterministic process-local chat:

```sh
python -m src.cli chat
```

Inside chat:

```text
/help
/status
/answer <one displayed choice>
/follow <issued-reference> why_selected
/follow <issued-reference> record_detail
/cancel
/reset
/exit
```

Plain text starts a new request. `/answer` continues only an active approved
clarification. `/cancel` clears active request, selection and evidence context;
`/reset` additionally rotates session identity. Session state is never persisted.

## 7. Generate a synthetic onboarding file

The following standard-library command creates a temporary 31-row
`SALES_RECORD` file. Rows 0–29 provide varying values and the final row provides
a known upper-tail candidate for both Sales and Profit. It contains no private data.

```sh
python - <<'PY'
from csv import writer
from pathlib import Path

path = Path("/tmp/financial_manager_ai_v1_demo.csv")
with path.open("w", encoding="utf-8", newline="") as stream:
    output = writer(stream)
    output.writerow(("date", "sales", "country", "segment", "product", "profit", "discount", "units"))
    for value in range(30):
        output.writerow((f"2026-{value % 2 + 1:02d}-01", value, "Canada", "Government", "Widget", value, 1, 2))
    output.writerow(("2026-02-01", 100, "Brazil", "Enterprise", "Gadget", 200, 2, 4))
print(path)
PY
```

This temporary source is demo input, not a committed project artifact.

## 8. Add and inspect the dataset

```sh
python -m src.cli dataset add /tmp/financial_manager_ai_v1_demo.csv \
  --provenance-note "Synthetic V1 demo"
```

Copy the returned opaque ID and set it for the remaining shell examples:

```sh
DATASET_ID=ds_replace_with_the_returned_id
python -m src.cli dataset status "$DATASET_ID" --json
python -m src.cli dataset profile "$DATASET_ID" --json
python -m src.cli dataset mappings "$DATASET_ID" --json
```

Profile observations and mapping suggestions are not approved semantics. Review
column names, structural types, missing/parse counts and suggestions before deciding.

## 9. Confirm semantics

For this exact synthetic file, its generator is the evidence for the following
decisions. Real data requires its own authoritative evidence.

```sh
python -m src.cli dataset confirm-domain "$DATASET_ID" SALES_RECORD \
  --evidence "Synthetic demo specification"
python -m src.cli dataset confirm "$DATASET_ID" date TRANSACTION_DATE \
  --date-format YYYY-MM-DD --evidence "Synthetic demo specification"
python -m src.cli dataset confirm "$DATASET_ID" sales SALES \
  --evidence "Synthetic demo specification"
python -m src.cli dataset confirm "$DATASET_ID" country COUNTRY \
  --evidence "Synthetic demo specification"
python -m src.cli dataset confirm "$DATASET_ID" segment SEGMENT \
  --evidence "Synthetic demo specification"
python -m src.cli dataset confirm "$DATASET_ID" product PRODUCT \
  --evidence "Synthetic demo specification"
python -m src.cli dataset confirm "$DATASET_ID" profit PROFIT \
  --evidence "Synthetic demo specification"
python -m src.cli dataset confirm "$DATASET_ID" discount DISCOUNT \
  --evidence "Synthetic demo specification"
python -m src.cli dataset confirm "$DATASET_ID" units UNITS_SOLD \
  --evidence "Synthetic demo specification"
```

Each decision creates a new mapping version. `dataset reject` can reject an
incorrect column proposal, and `dataset stop` can stop or reject a dataset; use
their `--help` output before applying those state-changing decisions.

Currency remains `UNKNOWN` because the synthetic file intentionally contains no
currency evidence. Country and numeric formatting do not establish currency.

## 10. Inspect dynamic capability readiness

```sh
python -m src.cli dataset capabilities "$DATASET_ID"
python -m src.cli dataset capabilities "$DATASET_ID" --json
```

For the complete synthetic mapping, all nine Financial Analysis operations and
both anomaly operations are supported. Readiness is recomputed and may later be
revoked if the source or artifacts change.

There is no `dataset analyze` command. Dynamic execution uses the typed Manager
path, exposed conversationally only through optional local-LLM mediation.

## 11. Conversational dynamic Financial Analysis

If an OpenAI-compatible local service is already available on the default
loopback endpoint, start mediation with its local model name:

```sh
python -m src.cli chat --llm-model YOUR_LOCAL_MODEL
```

Then enter the runtime ID—not the illustrative value below:

```text
Use dataset ds_<runtime-generated-id>.
Show sales by country.
Now by product.
Show sales by year.
```

The mediator may select only an exact eligible ID, one of the nine operations,
`MONTH|YEAR` and `BUCKET|EXCLUDE` where applicable. It cannot create filters,
SQL, formulas or new groupings.

## 12. Conversational dynamic anomaly screening

Continue in the same mediated chat:

```text
Check Sales for anomalies.
Why was A1 selected?
Check Profit for anomalies.
```

The synthetic fixture deterministically produces an upper-tail Sales candidate
with observed value `100` and a Profit candidate with observed value `200`.
Those values and all fences come from authoritative screening evidence.

`A1` exists only after the current result issues that label. If it does, either
natural language or the deterministic slash command can request bounded follow-up:

```text
/follow A1 why_selected
/follow A1 record_detail
```

`CANDIDATE` != `FRAUD` != `ERROR` != `SUSPICIOUS ACTIVITY`. It means a
statistical candidate for review and does not explain business cause.

## 13. Deterministic no-model acceptance path

Live Ollama is optional. The repository's scripted-provider acceptance test runs
the persisted synthetic onboarding, all nine analyses, both anomaly screens and
candidate follow-up without network access:

```sh
python -B -m unittest \
  tests.test_conversational_dynamic_execution_end_to_end.ConversationalDynamicExecutionEndToEndTests.test_primary_persisted_flow_all_nine_financial_operations_and_anomalies
```

This is a reproducible validation command, not a substitute UI. Local-model
latency and wording vary by model and hardware; deterministic evidence does not.

## 14. Provider fallback

If the local provider is unavailable or returns malformed/ungrounded output,
validated deterministic behavior remains authoritative. Code-owned presentation
is used where a request was already deterministically executable. A dynamic
natural-language request that cannot be safely interpreted executes nothing; it
does not redirect to legacy data or guess an operation/dataset.

No model is needed for global capability inspection, onboarding, readiness,
legacy one-shot execution or deterministic session slash commands.

## 15. Controlled errors

Common outcomes include:

- `Invalid CLI syntax`: inspect `python -m src.cli --help` and the relevant subcommand help.
- `NEEDS_CONFIRMATION`: review mappings and explicitly approve the required roles/domain.
- blocked operation: inspect `dataset capabilities`; do not substitute another measure.
- unknown/stale dataset: use the exact current ID returned by `dataset add`.
- no evidence context: run a candidate-producing screen before `/follow`.
- unknown/stale reference: use only a label issued by the current session result.
- provider unavailable: retry with a valid local service or use deterministic surfaces.
- snapshot/setup failure: run `python -m src.provisioning` and restore approved inputs.

Normal CLI errors use controlled text and do not expose tracebacks, private
artifact payloads or filesystem paths.

## 16. JSON and automation

`--json` is supported by `capabilities`, `plan`, `ask` and every `dataset` leaf
command. Chat is human-oriented and does not accept `--json` or `--full`.

Application-level blocked/unsupported responses may still exit zero because a
structured response was delivered. Automation must inspect fields such as
`execution_status`, capability state and delegated evidence status.

## 17. V1 limitations

- Local, single-user, process-local conversation
- Approved legacy bundle required for legacy execution
- Only `SALES_RECORD` has generic dynamic execution
- Per-dataset, per-operation readiness
- GLOBAL-only Tukey-IQR v1.0 dynamic anomaly policy
- Sales and supplied confirmed Profit anomaly measures only
- At most A1–A10 conversational candidate labels
- No currency inference or FX conversion
- No arbitrary filters, measures, grouping, SQL or statistical algorithms
- Optional local-model performance depends on hardware
- Forecasting and Document Retrieval/RAG are blocked and deferred to V2

For architecture and validation details, see the
[`Financial Manager AI technical guide`](financial_manager_ai_guide.md),
[`V1 scope freeze`](v1_scope_freeze.md) and
[`V1 technical validation`](v1_technical_validation.md).
