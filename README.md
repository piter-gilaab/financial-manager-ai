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
application interfaces remain unimplemented.

Phase 6 Step 17 provides `src.manager.FinancialManagerAgent`, a single facade for
capability discovery and explicit delegation to the existing analysis agent or
screening service. Forecasting and document retrieval are reported as BLOCKED.
Automatic capability routing (Step 18) and broader security hardening (Step 19)
are not implemented.
