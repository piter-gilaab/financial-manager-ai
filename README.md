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
