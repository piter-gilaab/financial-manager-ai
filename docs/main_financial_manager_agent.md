# Phase 6 — Step 17: Main Financial Manager Agent

## Purpose and authority

`FinancialManagerAgent` is the single application-level facade for explicitly
selected financial capabilities. It composes the existing
[Step 13 Financial Analysis Agent](financial_analysis_agent.md) and
[Step 14 screening service](anomaly_detection.md). It performs no financial
calculations, dataset inference, statistical assessment, database access or
model interpretation of its own.

The explicit Step 17 request authorizes this implementation beyond the historical
planning-only guidance. Existing query contracts, financial semantics, IQR rules,
peer policies, statuses and privacy assumptions remain authoritative and unchanged.
This is one Financial Manager with specialized modules, not autonomous cooperating
agents. The existing class named FinancialAnalysisAgent remains a delegated module.

## Interface

```python
from src.manager import Capability, FinancialManagerAgent

manager = FinancialManagerAgent()
catalog = manager.list_capabilities()
forecast_status = manager.get_capability(Capability.CASH_FLOW_FORECASTING)

analysis = manager.execute(
    capability=Capability.FINANCIAL_ANALYSIS,
    request={"question": "Discount analysis", "parameters": {"quality_detail": "full"}},
)

screening = manager.execute(
    capability=Capability.ANOMALY_DETECTION,
    request={
        "analysis_version": "1.0",
        "dataset": "company_financials",
        "measure": "profit",
    },
)

unavailable = manager.execute(
    capability=Capability.DOCUMENT_RETRIEVAL,
    request={"question": "Find financial policies"},
)
```

Capability enum members and their exact uppercase string values are accepted.
There are no aliases, inferred defaults or keyword-based capability selection.
Omitting a capability returns INVALID_REQUEST. `get_capability` returns a fresh
metadata dictionary or null for unknown/malformed identifiers; listing has the
fixed order shown below. Discovery invokes neither queries nor model providers.

`FinancialManagerAgent(financial_analysis=..., anomaly_detection=...)` supports
trusted application dependency injection for existing configured instances and
test doubles. Callers cannot supply implementations, module names, providers or
registrations through an execution request. Default construction uses the existing
local implementations and performs no financial queries.

## Current capability registry

| Identifier | Name | Availability | Implementation / evidence |
|---|---|---|---|
| `FINANCIAL_ANALYSIS` | Financial Analysis | AVAILABLE | Existing Step 13 agent; 17 [approved contracts](query_contracts.md), RG-01–RG-08 and CF-01–CF-09 |
| `ANOMALY_DETECTION` | Anomaly Detection | AVAILABLE | Existing Step 14 service; RG accounting amount and CF Sales/Profit, global and fixed-peer IQR screening |
| `CASH_FLOW_FORECASTING` | Cash Flow Forecasting | BLOCKED | [Forecasting readiness](forecasting_readiness.md): no authoritative actual cash inflows/outflows, unknown currency and insufficient defensible target/history |
| `DOCUMENT_RETRIEVAL` | Document Retrieval | BLOCKED | [RAG readiness](rag_architecture.md): no approved real financial-document corpus; architecture is documented, implementation readiness remains DEFERRED |

Availability vocabulary is AVAILABLE, BLOCKED, DEFERRED. No current capability
uses DEFERRED as its top-level status: Document Retrieval uses the production
corpus BLOCKED status and explicitly preserves the separate architecture
DEFERRED condition in its reason/limitations. A design document is not an
operational retrieval implementation.

Metadata includes identifier, human-readable name, availability, unavailable
reason, documentation references and limitations. AVAILABLE means the delegated
implementation exists, not that every request or local data snapshot will succeed.
The registry is a static allowlist; it does not discover Python functions,
plugins, database queries or capabilities from arbitrary names. Blocked entries
have no execution handlers, forecasting models or retrieval placeholders.

## Delegation and request validation

1. Resolve the explicitly selected capability from the registry.
2. Check availability. Blocked/deferred entries return CAPABILITY_UNAVAILABLE
   before inspecting their payload: no speculative forecast/RAG request schema
   or operation is implemented.
3. Require a JSON-serializable object with string top-level property names for
   available capabilities. Nonfinite values, cycles and arbitrary objects are
   rejected. Serialization is a validation check, not a payload conversion.
4. For Financial Analysis, require `question` text and allow only optional
   `dataset` and `parameters`. Forward them unchanged to the existing `ask`.
   That agent owns question interpretation, normalization and the 17-tool routing.
5. For Anomaly Detection, pass the original object to `AnomalyService.analyze`.
   That service owns version, dataset/measure, period/filter and algorithm policy
   validation. The manager does not duplicate these rules.
6. Wrap the complete returned object and derive convenience status/warning fields.

Requests are copied before delegation so an adapter cannot mutate caller-owned
input. No retry, fallback, chained execution, batch planning, automatic capability
choice or reinterpretation follows a rejection. For example, explicitly selecting
Financial Analysis and asking for anomalies still returns its UNSUPPORTED
response; the manager does not redirect that question to Anomaly Detection.

The manager imports the two public module interfaces. It never calls the Core
directly, accesses SQLite, generates SQL, selects currencies or aggregates values.
The small adapter in the registry accommodates `ask(**payload)` versus
`analyze(payload)`; no existing implementation was rewritten.

## Unified response version 1.0

The response is a JSON-safe dictionary for the existing production delegates,
described by `ManagerResponse` TypedDict. Request shapes also have TypedDicts;
capability identifiers/availability use enums and registry entries are frozen
dataclasses. Public dictionaries are detached caller-owned values, not immutable
storage. Runtime validation remains explicit at the owning module interfaces.

| Field | Meaning |
|---|---|
| `manager_version` | Facade response contract version, `1.0` |
| `capability` | Selected identifier; unknown strings echoed, malformed/non-string selection null |
| `capability_status` | Registry availability; null if identifier is unknown |
| `execution_status` | Effective outcome mapped below |
| `delegated_status` | Original Step 13 `agent_status` or Step 14 `status`; null if no delegation |
| `delegated_result` | Complete copied original response, including its nested evidence and metadata |
| `summary` | Original Step 13 explanation text, or deterministic status/terminology text for screening/unavailability |
| `warnings` | Exact copied delegated quality warning list, preserving order; empty when no tool evidence exists |
| `limitations` | Registry-level scope limitations, separate from query-specific warnings |
| `errors` | Manager validation/unavailability error or copied delegated errors |
| `clarification` | Original Step 13 clarification object, otherwise null |

No correlation ID, request history, session store, clock, telemetry or additional
evidence-digest scheme is introduced. Step 13's existing evidence digest is
preserved inside its complete response.

### Status mapping

| Delegated/manager outcome | `execution_status` |
|---|---|
| Financial Analysis ANSWERED with tool SUCCESS / PARTIAL / NO_DATA | The unchanged tool status |
| Financial Analysis TOOL_REJECTED | Tool INVALID_REQUEST / UNSUPPORTED / DATA_QUALITY_BLOCKER |
| Financial Analysis CLARIFICATION_REQUIRED, INVALID_REQUEST, UNSUPPORTED, PROVIDER_UNAVAILABLE or PROVIDER_ERROR before tool execution | The unchanged agent status |
| Anomaly response | Its unchanged SUCCESS / PARTIAL / NO_DATA / INVALID_REQUEST / UNSUPPORTED / DATA_QUALITY_BLOCKER |
| Unknown/missing capability or malformed available-capability payload | INVALID_REQUEST, with `unknown_capability` or `malformed_request` code |
| Registry BLOCKED or DEFERRED | CAPABILITY_UNAVAILABLE with the documented reason; no delegated result |

The facade preserves AVAILABLE even when that capability's individual request
fails. PARTIAL is not promoted to success; NO_DATA is not converted to zero;
anomaly NOT_ASSESSED stays a record-level abstention inside the original result,
including the service's all-unassessed PARTIAL behavior.

For tool-backed Financial Analysis responses, top-level errors/warnings mirror
the nested Core envelope; for pre-tool outcomes they mirror the agent's errors
and clarification. Anomaly errors/warnings mirror the service envelope. The
complete original objects are always retained regardless of these convenience
fields. Unknown delegated statuses are integration failures and raise; unexpected
internal exceptions propagate without generic success responses or fallback.

## Evidence and explanation

`delegated_result` is authoritative. Deep copies preserve every original field,
decimal string, count, status, currency, peer definition, reference/fence, lineage,
flag, exclusion and warning index. No flattening or normalization occurs. The
manager never casts decimal values through floats or substitutes a derived amount.
Existing delegates already provide the approved exact JSON serialization; custom
trusted adapters remain responsible for their compatible result contracts.

Convenience warning/error/clarification fields are independent copies: modifying
them cannot mutate nested evidence or an implementation's original response.
Changing a returned summary likewise does not alter the structured facts. This
is object isolation, not a tamper-proof store or Step 19 security framework.

Financial Analysis explanations pass through verbatim; no query explanation is
reimplemented. The screening summary reports its returned status and states that
CANDIDATE records require investigation, NOT_SELECTED is not a validity finding,
and NOT_ASSESSED remains unassessed. It calculates no candidate counts or scores
and never converts candidates into accusations or confirmed findings. All global
and peer details remain in the original service response.

## Privacy, limitations and Step 18

There are no new provider interfaces, network operations, credentials, external
LLMs/FX calls, document uploads, telemetry, logging or data transmissions. Existing
local-first assumptions remain intact. Dependency injection is trusted local
configuration, not an execution channel for user-supplied Python. No new
authentication, authorization, sandbox or broader privacy framework is implemented.

Unknown denomination, unresolved placeholders, fiscal/grain/provenance limits,
company-identity absence and statistical peer limitations remain in the specialized
evidence. Forecasting needs verified cash data; production RAG needs an approved
real corpus and corpus-informed implementation decisions.

Step 17 offers explicit delegation only. Step 18 may later add approved automatic
intent/capability routing over this interface, but no such router exists here.
Step 19 hardening is also unstarted. There is no CLI application, server, API,
frontend, forecast, RAG implementation or deployment in this step.

See [Step 17 validation](step17_validation.md) for exact tests and protected-file
checks. Breaking changes to the facade's envelope or delegation semantics require
a new manager contract version; specialized contract versions remain unchanged.
