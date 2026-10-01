# Phase 6 — Step 19: security and privacy boundaries

The default Financial Manager remains a local, deterministic, read-only Python
application. This step strengthens existing message and error boundaries; it
does not add business capabilities, providers, network transports or a production
security framework. The Step 19 request authorizes these changes beyond the
historical planning-only guidance.

## Trust and data flow

| Boundary | Allowed | Not allowed |
|---|---|---|
| Caller → manager | Plain question text; explicit allowlisted capability plus data-only request | Executable objects, custom containers, dynamic imports/functions, shell/SQL instructions, runtime handler/provider registration |
| Router → execution | Locally created immutable plan; execution through manager.execute and its registry | Caller-supplied executable plans; explanation-driven execution; automatic fallback to another capability |
| Manager → specialized modules | Existing Step 13 ask / Step 14 analyze contracts, copied inputs | Direct manager database access, financial arithmetic, new algorithms or altered query semantics |
| Specialized modules → database | Approved snapshot, allowlisted fields/operations, bound values, read-only in-memory copy | User SQL, arbitrary tables/columns, connection handles in application responses, production writes |
| Agent → interpretation provider | Question, explicit dataset context and static metadata for 17 tools | Database connections, financial results/rows, structured supplemental filters, raw files, corpus, environment/credentials or application objects |
| Interpretation provider → agent | ToolIntent matching the deterministic grounded request after existing validation | New tools, changed scope, provider-generated financial evidence/explanations, provider exception text as public errors |
| Specialized evidence → manager/caller | Complete data-only response, original exact numbers/Decimal values, warnings, statuses and lineage | Live handles, arbitrary objects/copy hooks, silent warning removal, recalculation, currency inference or candidate relabeling |

Data stays in the local sensitive zone: database, processed/raw files, questions,
filters, summaries, quality disclosures and screening evidence. Question text may
itself contain sensitive data; being text does not make it public. Any future
approved document corpus and retrieved chunks also belong in this zone.

The caller is a local application consumer, not an authenticated remote principal.
Configured modules, project root and Python provider/adapter code are trusted
application configuration. Requests cannot select their implementations or paths.
The application does not sandbox malicious Python already running in its process.

## Capability execution

The existing registry remains the only top-level dispatcher. It contains exactly
FINANCIAL_ANALYSIS, ANOMALY_DETECTION, CASH_FLOW_FORECASTING and DOCUMENT_RETRIEVAL.
Only the first two have handlers. Unknown names remain INVALID_REQUEST and never
become imports or function references. Capability inputs must be plain strings or
the existing Capability enum, so custom string hash/copy hooks are not invoked.

Automatic execution still routes through manager.execute. Routing plans returned
to callers are previews, not executable inputs. Explicit execution remains
explicit. Natural-language refusal rules provide useful feedback, while static
dispatch and owned argument validation enforce the execution boundary even when
keyword recognition is insufficient. No eval, exec, shell, filesystem execution,
dynamic discovery or arbitrary SQL endpoint exists.

`src/manager/security.py` admits plain dict/list/tuple containers and finite plain
scalars. Dictionary keys must be plain strings. Cycles, nesting beyond 64 levels,
custom container/scalar subclasses and non-data objects are rejected before
serialization/deep-copy delegation. Request validation returns controlled
INVALID_REQUEST; existing domain validators still determine semantic validity.
This intentionally tightens Python input acceptance without changing JSON requests.

Delegated responses are checked before wrapping/copying. Finite Decimal objects
are additionally allowed in trusted response evidence, without float conversion.
Invalid adapter response objects raise a fixed-message ValueError, treated as a
development integration error. The check does not inspect string content as code,
sanitize financial values or strip fields from otherwise valid evidence.

## Database and immutable data

The manager has no connection object, SQL generator or data-path request option.
The Core and anomaly service retain their approved snapshot and query logic.
Source database bytes and schema are verified, then a process-local SQLite copy
is queried under query_only. Table/field choices are controlled and filter values
are bound parameters. SQL-shaped quoted categories remain literal data and cannot
change the SQL program. Raw connection objects cannot pass the response data check.

No production source, processed file, cleaning output, manifest or database is
written. Tests use temporary databases/files and test-only providers/adapters.
This is an application read-only rule, not filesystem permissions, encryption or
protection against another local process changing files.

## Provider and external processing policy

The existing ProviderLocation vocabulary remains authoritative:

| Location | Current policy |
|---|---|
| LOCAL | May interpret the minimal request after deterministic grounding; configured code is trusted and must operate offline |
| PRIVATE | Disabled; an on-prem transport is still a data crossing requiring separate configuration and approval |
| EXTERNAL | Disabled; no hosted provider/client, credential or transport exists |
| Missing/unrecognized location | Disabled before interpret is called |

There is no request flag that enables PRIVATE or EXTERNAL. Enabling a future
transport requires separately approved code/configuration and an explicit review
of the minimum data being transmitted; this step adds no enable switch. A provider's
LOCAL declaration is configuration, not proof that arbitrary injected Python is
network-free. OS/process egress restrictions remain a deployment responsibility.

The provider receives only InterpretationRequest(question, dataset, tools). The
agent never gives it evidence for explanation generation; explanations remain
deterministic. Supplemental structured parameters are merged and validated after
interpretation and are not provider context. Free-text questions can contain
caller-supplied paths/secrets; those words remain local and are not interpreted as
filesystem access. Static relative contract references are metadata, not file reads.

The existing FX abstraction accepts only public currency pair/date, never amounts
or transaction identity. It has no manager capability route, network implementation
or fallback. Its configured Python provider is trusted, and current UNKNOWN
currency is refused before provider invocation. No production conversion occurs.

No telemetry, analytics, logging of prompts/evidence, document upload, external
embedding, web search, credentials or external data flow was added.

The Phase 11 interactive CLI keeps one existing `FinancialManagerSession` in the
local process. It adds no transcript file, application-managed command history or
persistence. Its `/status` display omits session identity and uses only the public
redacted projection; complete evidence and handles are not exposed through
status. Host terminal, shell, redirected-output, swap and process-inspection
behavior remain outside the application boundary.

## Financial evidence and explanations

Specialized results remain authoritative, copied completely into existing manager
and orchestration envelopes. No numeric value, precision, count, currency state,
warning, exclusion, peer definition, threshold, candidate assessment or source
lineage is rewritten by this policy. Original exact decimal strings and trusted
Decimal objects stay exact. Original UNKNOWN currency and missing values persist.

Convenience warnings/explanations are separate copies. Changing them cannot mutate
nested evidence or the delegate's original response. Providers propose only
validated intents and never render or modify financial evidence. Multi-capability
results remain independent. Screening CANDIDATE is an investigation candidate;
NOT_SELECTED is not a validity finding and NOT_ASSESSED remains an abstention.

Returned dictionaries are caller-owned. Deep copying and the existing Step 13
digest are not signatures, an immutable audit log, or protection from deliberate
modification by trusted Python code. This layer does not certify the correctness
of an arbitrary injected service or automatically detect secrets in source values.

## Controlled errors

Expected request errors retain their existing status/code and controlled messages.
Provider invocation exceptions of any ordinary Exception subtype produce the fixed
PROVIDER_ERROR / interpretation_failed message, including provider-raised domain
errors. Provider text cannot masquerade as an approved application response.
The underlying chained exception remains available to developers, not serialized.

Snapshot read/verification errors produce DATA_QUALITY_BLOCKER / snapshot_mismatch
with a fixed message. Validation failures produce snapshot_validation_failed with
a fixed message. OSError/ValueError/SQLite validation bodies are not echoed:
they may contain absolute paths, artifact contents or database internals. These
messages are controlled at the source, so every downstream layer still preserves
the complete authoritative result unchanged. No post-hoc evidence redaction occurs.

Unexpected Core/service integration exceptions still propagate to developers,
as required by existing tests/contracts. They are not converted into successful
or normal application responses and are not automatically logged. Any future
CLI/API error presenter must avoid rendering raw tracebacks to an untrusted user;
the [Step 20 CLI](cli_workflow.md) now provides that controlled presenter, including
syntax, invocation and cancellation errors. No generic server handler exists.

Caller-supplied questions, invalid identifiers and legitimate lineage/quality
values may be echoed by existing contracts. This is not new internal disclosure;
the result itself remains sensitive. There is no blanket regex redactor or DLP
claim. Trusted adapters must return controlled error fields rather than raw
exception bodies, and callers must protect entire results before sharing them.

## Unavailable capabilities and non-goals

Forecasting stays BLOCKED: no verified actual-cash target/history and unresolved
denomination. Document retrieval stays BLOCKED: no approved production corpus;
architecture is documentation only. Both explicit and automatic paths return
readiness reasons without invoking a handler, model or retrieval placeholder.

Not implemented: authentication, accounts, RBAC/authorization infrastructure,
OAuth, secrets management, encryption-at-rest management, process sandboxing,
production egress controls, deployment security, an API/frontend or cloud services.
No forecasting, RAG, embeddings, vector store, external database, ML algorithm or
live FX was introduced. Existing financial/data readiness limits remain.

See [Step 19 validation](step19_validation.md) for tests, review and file integrity.
