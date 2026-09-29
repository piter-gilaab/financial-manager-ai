# Financial Manager AI

Financial analysis project with an offline, deterministic Python core and a
validated local SQLite database. The core implements 17 read-only accounting and
sales-record query contracts, exact decimal arithmetic, quality disclosures and
an offline FX lookup interface. Current dataset currencies remain UNKNOWN;
currency conversion is not implemented.

- [Financial Core usage and architecture](docs/financial_core.md)
- [Financial Analysis Agent — Step 13](docs/financial_analysis_agent.md)
- [Step 13 validation](docs/step13_validation.md)
- [Approved query contracts](docs/query_contracts.md)
- [Data model](docs/data_model.md) and [database schema](docs/database_schema.md)

Run the tests from the project root with the existing environment:

```sh
.venv/bin/python -B -m unittest discover -s tests -v
```

Phase 5 Step 13 adds one Financial Analysis Agent over these 17 contracts, with
conservative local question routing, structured clarification and lossless tool
evidence. It requires no LLM or network service; model providers have a separate
interface. ML, forecasting, anomaly detection, RAG and application interfaces
remain unimplemented.
