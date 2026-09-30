# Financial Manager AI

Financial analysis project with an offline, deterministic Python core and a
validated local SQLite database. The core implements 17 read-only accounting and
sales-record query contracts, exact decimal arithmetic, quality disclosures and
an offline FX lookup interface. Current dataset currencies remain UNKNOWN;
currency conversion is not implemented.

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

Run the tests from the project root with the existing environment:

```sh
.venv/bin/python -B -m unittest discover -s tests -v
```

Phase 5 Step 13 adds one Financial Analysis Agent over these 17 contracts, with
conservative local question routing, structured clarification and lossless tool
evidence. It requires no LLM or network service; model providers have a separate
interface. Step 14 adds a separate offline statistical screening service with
global/peer IQR rules and explicit investigation-candidate evidence; agent routing
remains limited to the original 17 tools. ML models, forecasting, RAG and
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
```

Omit `--json` for readable output. The CLI preserves exact evidence, UNKNOWN
currency and warnings; unavailable or ambiguous requests report the existing
blocker/clarification. See the workflow guide for syntax, exit codes and limits.
