# Financial Manager AI

Financial analysis project with an offline, deterministic Python core and a
validated local SQLite database. The core implements 17 read-only accounting and
sales-record query contracts, exact decimal arithmetic, quality disclosures and
an offline FX lookup interface. Current dataset currencies remain UNKNOWN;
currency conversion is not implemented.

- **[Start here: Financial Manager AI — Technical Guide](docs/financial_manager_ai_guide.md)**
- [Environment and data provisioning — Step 23](docs/environment_and_data_provisioning.md)
- [Fresh-clone reproducibility — Step 24](docs/fresh_clone_reproducibility.md)
- [V1 user evaluation — Step 25](docs/user_evaluation.md)
- [Next capability readiness — Step 26](docs/next_capability_readiness.md)
- [Concise CLI presentation — Step 27](docs/concise_cli_presentation.md) and
  [validation](docs/step27_validation.md)
- [Presentation validation — Step 28](docs/presentation_validation.md) and
  [validation record](docs/step28_validation.md)
- [Conversational UX readiness — Step 29](docs/conversational_ux_readiness.md) and
  [validation record](docs/step29_validation.md)
- [Conversation state contract — Step 30](docs/conversation_state_contract.md) and
  [validation record](docs/step30_validation.md)
- [Clarification continuation — Step 31](docs/clarification_continuation.md) and
  [validation record](docs/step31_validation.md)
- [Evidence-reference follow-ups — Step 32](docs/evidence_reference_followups.md)
  and [validation record](docs/step32_validation.md)
- [Bounded conversational UX — Step 33](docs/conversational_ux_validation.md) and
  [validation record](docs/step33_validation.md)
- [Conversational CLI contract — Step 34](docs/conversational_cli_contract.md) and
  [validation record](docs/step34_validation.md)
- [Interactive CLI implementation — Step 35 validation](docs/step35_validation.md)
- [Conversational CLI validation — Step 36](docs/conversational_cli_validation.md)
  and [validation record](docs/step36_validation.md)
- [LLM mediation contract — Step 37](docs/llm_mediation_contract.md),
  [validation](docs/llm_mediation_validation.md) and records for
  [Step 37](docs/step37_validation.md), [Step 38](docs/step38_validation.md),
  [Step 39](docs/step39_validation.md), [Step 40](docs/step40_validation.md) and
  [Step 41](docs/step41_validation.md), plus
  [Step 42 language and response-quality hardening](docs/step42_validation.md)
- [Dynamic Data Onboarding — Phase 13](docs/dynamic_data_onboarding_contract.md)
  and [end-to-end validation](docs/dynamic_data_onboarding_validation.md)
- [Execution Adapter contract — Phase 14 Step 51](docs/execution_adapter_contract.md)
  and [SALES_RECORD adapter validation — Step 52](docs/step52_validation.md), plus
  [Dynamic Query Binding — Step 53](docs/dynamic_query_binding_contract.md) and
  its [validation record](docs/step53_validation.md), and
  [Dynamic Capability Activation — Step 54](docs/dynamic_capability_activation_contract.md)
  with its [validation record](docs/step54_validation.md), completed by the
  [Phase 14 end-to-end execution validation — Step 55](docs/dynamic_execution_validation.md)
- [Dynamic Analysis Expansion — Phase 15 Step 56](docs/dynamic_analysis_expansion_contract.md),
  with [Step 57](docs/step57_validation.md) and [Step 58](docs/step58_validation.md)
  implementation validation, the [Step 59 capability expansion contract](docs/dynamic_capability_expansion_contract.md)
  and [Step 60 end-to-end validation](docs/dynamic_analysis_expansion_validation.md)
  with its [validation record](docs/step60_validation.md)
- [V1 acceptance](docs/v1_acceptance.md) and [Step 21 validation](docs/step21_validation.md)
- [Documentation / architecture review — Step 22](docs/step22_validation.md)
- [Financial Core usage and architecture](docs/financial_core.md)
- [Financial Analysis Agent — Step 13](docs/financial_analysis_agent.md)
- [Step 13 validation](docs/step13_validation.md)
- [Investigation screening — Step 14](docs/anomaly_detection.md)
- [Step 14 validation](docs/step14_validation.md)
- [Main Financial Manager — Step 17](docs/main_financial_manager_agent.md)
- [Step 17 validation](docs/step17_validation.md)
- [Capability routing and orchestration — Step 18](docs/orchestration.md)
- [Step 18 validation](docs/step18_validation.md)
- [Security and privacy boundaries — Step 19](docs/security_privacy_boundaries.md)
- [Step 19 validation](docs/step19_validation.md)
- [Local CLI workflow — Step 20](docs/cli_workflow.md)
- [Step 20 validation](docs/step20_validation.md)
- [Approved query contracts](docs/query_contracts.md)
- [Data model](docs/data_model.md) and [database schema](docs/database_schema.md)

Provision the Python 3.14 environment and approved local data before running the
CLI. The V1 runtime and tests have no third-party dependencies:

```sh
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m src.provisioning
```

See the [Step 23 provisioning guide](docs/environment_and_data_provisioning.md)
for the exact data layout and SQLite reconstruction procedure. Run the tests from
the project root with the activated environment:

```sh
.venv/bin/python -B -m unittest discover -s tests -v
```

Phase 5 Step 13 adds one Financial Analysis Agent over these 17 contracts, with
conservative local question routing, structured clarification and lossless tool
evidence. It requires no LLM or network service; model providers have a separate
interface. Step 14 adds a separate offline statistical screening service with
global/peer IQR rules and explicit investigation-candidate evidence; the Step 13
agent's internal routing remains limited to the original 17 tools. ML models, forecasting, RAG and
web/API interfaces remain unimplemented.

Phase 6 Step 17 provides `src.manager.FinancialManagerAgent`, a single facade for
capability discovery and explicit delegation to the existing analysis agent or
screening service. Forecasting and document retrieval are reported as BLOCKED.
Step 18 adds deterministic `manager.plan(question)` and `manager.ask(question)`
for top-level capability routing. Explicit `manager.execute(...)` is unchanged.
Independent analysis and screening requests can run sequentially with separate
results; ambiguous scopes require clarification. Step 19 enforces data-only manager
messages, controlled snapshot/provider errors and the existing local-only provider
policy. It adds no authentication, network transport or deployment security.

Phase 7 Step 20 adds a thin local CLI over that manager. From the repository root:

```sh
.venv/bin/python -m src.cli capabilities
.venv/bin/python -m src.cli plan "Find outliers in Profit"
.venv/bin/python -m src.cli ask "What were total sales by country?" --json
.venv/bin/python -m src.cli ask "Find unusual Profit values" --full
```

Omit both format flags for concise human output. Use `--full` for expanded human
evidence or `--json` for the complete exact structured response. The CLI preserves
UNKNOWN currency and warnings; unavailable or ambiguous requests report the
existing blocker/clarification. See the workflow guide for syntax and limits.

Phase 10 adds `src.manager.FinancialManagerSession`, a local in-memory Python API
for explicit `new_request`, `answer`, `follow_up`, `cancel`, `reset` and `status`
operations. It continues only the two approved clarification types and can
re-resolve session-issued anomaly-candidate references through fresh authoritative
execution. State expires after 30 minutes of inactivity or four hours absolute,
is never persisted, and cannot unlock Forecasting or Document Retrieval.

Phase 11 exposes that same bounded session through an additive local interactive
adapter:

```sh
.venv/bin/python -m src.cli chat
```

Plain text always starts a new request. Use `/answer` for an approved pending
clarification and `/follow` for a session-issued anomaly reference; `/help` lists
the small command vocabulary. Chat is concise-only, process-memory-only and adds
no provider, network, persistence, transcript or unrestricted conversation memory.

Phase 12 adds optional natural-language mediation to that chat through a locally
hosted OpenAI-compatible model:

```sh
.venv/bin/python -m src.cli chat --llm-model qwen2.5:7b-instruct \
  --llm-url http://127.0.0.1:11434/v1/chat/completions
```

The model understands English and Portuguese and explains results. It is not the
financial authority: it only selects approved requests, and its prose is shown
only when a deterministic guard verifies it against the authoritative evidence.
Tables come straight from that evidence. Only loopback endpoints are accepted, and
any model failure falls back to the deterministic Phase 11 behavior. Without
`--llm-model`, nothing changes.

Phase 13 adds safe local onboarding for bounded CSV and constrained formula-free
XLSX files. It preserves source bytes under the Git-ignored `data/onboarding/`
root, profiles structure deterministically, proposes only closed semantic roles,
requires explicit user decisions, versions mappings/lineage, and reports
capability readiness:

```sh
.venv/bin/python -m src.cli dataset add company.csv
.venv/bin/python -m src.cli dataset mappings ds_...
.venv/bin/python -m src.cli dataset confirm-domain ds_... SALES_RECORD --evidence "Data owner confirmation"
.venv/bin/python -m src.cli dataset capabilities ds_...
```

Phase 13 itself did not make newly onboarded datasets executable by the existing
Financial Core: it added no generic analysis/anomaly adapter, forecasting, RAG
or AP logic, so confirmed datasets remained `BLOCKED` or
`BLOCKED_NOT_IMPLEMENTED` pending separately authorized execution work.

Phase 14 Steps 51–53 add a directly testable, static `SALES_RECORD` execution
adapter and a deterministic query binder for record count, sales summary and
sales by confirmed country. They use approved Phase 13 registry/mapping artifacts
and existing exact Core arithmetic. Step 54 now reports those operations as
dataset-specific `AVAILABLE_WITH_LIMITATIONS` when current binder and adapter
validation pass, and exposes an explicit typed Manager execution method. It adds
no fuzzy/conversational dataset selection, new operation, Anomaly, Forecasting or
RAG activation. Step 55 validates this complete persisted path, including
revocation/recovery, exact evidence, capability discovery, security boundaries
and unchanged legacy behavior; Phase 14 is complete.

Phase 15 Steps 56–58 add direct typed execution for Sales by period, Segment and
Product, Profit summary, monetary Discount analysis and Units Sold summary. The
new operations use the same static adapter and deterministic Core. Step 59 now
advertises all nine fixed operations through dataset-specific deterministic
readiness and the existing capability CLI; it does not add conversational
routing. Step 60 validates the complete persisted onboarding-to-Manager path,
renamed semantics, partial readiness, revocation/recovery, security, lineage and
unchanged legacy behavior. Phase 15 is complete; its scope remains the fixed
nine-operation `SALES_RECORD` catalog.

Phase 16 is complete. Approved dynamic `SALES_RECORD` datasets support exactly
`SALES_ANOMALY_SCREEN` and `PROFIT_ANOMALY_SCREEN` through explicit typed
`FinancialManagerAgent` execution. Both are global, deterministic `tukey_iqr`
v1.0 screens over approved supplied Sales/Profit values. Current dataset
readiness is operation-specific, the adapter reauthenticates persisted artifacts
at execution, and complete exact evidence/lineage is preserved. `CANDIDATE` is
only a statistical selection, never fraud or suspicion. There is no peer screen,
conversational dynamic execution or anomaly execution CLI; Forecasting and
Document Retrieval/RAG remain blocked.
