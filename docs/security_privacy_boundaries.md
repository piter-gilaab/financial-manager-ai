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

Dynamic anomaly Manager requests contain only an exact registered `dataset_id`
and one code-owned operation enum/string. Exact type checks reject objects and
string subclasses before Enum lookup, so caller-controlled Python protocols are
not invoked. Current operation readiness is recomputed, and the static adapter
then reauthenticates source/artifact identity before exact local screening.
Requests cannot select a column, measure, formula, algorithm, threshold,
grouping, adapter, SQL or executable path. No dataset is sent to an LLM,
external anomaly service, telemetry or network endpoint.

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

## Phase 12 LLM mediation boundary

The optional mediator (see the [contract](llm_mediation_contract.md)) adds two
crossings to the table above:

| Boundary | Allowed | Not allowed |
|---|---|---|
| Mediator → local model | Interpretation: the user's text, catalog IDs/descriptions, canonical pending choices, issued labels. Response: a bounded fact catalog (exact values, coverage, warnings) built by code | Database handles, raw envelopes, record IDs, hashes, paths, raw source tokens, session IDs, handles, prior turns, credentials |
| Local model → application | A closed-schema intent of enum values; a NaturalResponse whose numerals, currency, terminology and capability claims pass the grounding guard | Free text reaching routing/session/manager, tool or function names, SQL/shell/imports, unvalidated prose, provider error text |

Only `ProviderLocation.LOCAL` providers are called (identity check before
invocation). The HTTP adapter accepts loopback URLs only, ignores proxy
environment variables, refuses redirects, enforces per-operation and whole-call
deadlines and 64 KiB request/response caps, makes one attempt, sends no
credentials and replaces all errors with one fixed message. PRIVATE/EXTERNAL
remain disabled with no implementation. Prompts, responses and packets are not
logged or persisted; the only mediation state is an in-memory label map that is
invalidated by any session change. A loopback model server is trusted local
configuration: what that process does with the data is a host responsibility.

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

## Phase 13 onboarding boundary

Dynamic Data Onboarding introduces a local write boundary under the configured,
Git-ignored onboarding root. The user's original is read as a regular non-symlink
file and never modified. Accepted exact bytes, bounded structural profiles,
validated semantic proposals, explicit decisions and registry projections stay
local. Public status/CLI projections expose a basename and fingerprint, never an
absolute source path.

CSV and XLSX content is untrusted data. Ingestion enforces byte/row/column/cell
and archive bounds; rejects devices, symlinks, malformed tables, unsafe ZIP
paths/expansion, formulas, macros and external workbook links; and never executes
SQL, shell, imports or spreadsheet expressions. Missing values, duplicates,
outliers and ambiguous dates are findings—not silently removed, imputed or
reinterpreted.

An optional semantic provider must be `LOCAL` and receives only a bounded profile
packet. Likely-sensitive examples are suppressed. Dataset content is JSON data,
not prompt instructions. Strict output validation accepts only
`SUGGESTED`/`UNKNOWN` allowlisted roles; it cannot confirm meaning, choose
capabilities or emit executable plans. Raw provider output and chat history are
not persisted. User decisions, deterministic readiness and callable validated
adapters remain separate authorities.

Step 54 readiness is recalculated per dataset and operation through the closed
query binder and static adapter validation. `AVAILABLE_WITH_LIMITATIONS` is not a
global switch and cannot be supplied by registry, source or model text. The
explicit Manager entry accepts only the typed request with an exact `dataset_id`,
closed operation and bounded parameter; it adds no SQL, shell, dynamic import,
request-derived `getattr` or fuzzy dataset lookup. Current source/schema or
artifact integrity failure yields a path-free blocked report and execution still
revalidates through the adapter. UNKNOWN currency is disclosed, never inferred.

Step 55 validates this boundary through real persisted synthetic artifacts and
the typed Manager entry point. Traversal-shaped dataset IDs, import-shaped
operations, SQL-shaped parameters/values, shell-shaped cells and instruction-
shaped headers remain invalid or inert data. The acceptance run also verifies
revocation after source/schema changes, recovery only after restored approved
state, path-free controlled failures and the absence of network/provider
requirements. See [the Phase 14 acceptance matrix](dynamic_execution_validation.md).

The local store is not encryption, DLP, malware scanning, authentication or a
multi-user concurrency control. Host filesystem permissions, backups, disk/swap,
terminal history and the behavior of a configured local model process remain
deployment responsibilities.

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

## Phase 17 conversational dynamic dataset boundary

The Manager builds a maximum-20 interpretation catalog from authenticated
current registry IDs. Each entry contains only opaque ID, approved domain,
current Financial Analysis state and supported closed operation identifiers.
Source paths/filenames, rows, financial values, samples, profiles, mappings and
raw registry artifacts are excluded. An exact ID in user text receives a
reserved catalog slot; malformed, multiple, unknown, omitted and model-invented
IDs cannot become authority.

The session stores one ID and one last successful operation in process memory.
It is cleared by cancel/reset/expiry, never crosses sessions and is revalidated
before use. Execution constructs only `DynamicQueryRequest` and delegates to the
existing Manager/binder/static-adapter/Core chain. There is no new SQL, shell,
subprocess, dynamic import, runtime code generation, untrusted `getattr`,
caller-selected adapter, telemetry or persistence.

Provider text cannot redirect a dynamic target to a legacy dataset. Provider
failure with a dynamic target performs no financial execution; deterministic
legacy fallback remains unchanged when no dynamic target exists. Dynamic anomaly
requests return a code-owned Step-68 deferral and do not call the Phase 16 typed
anomaly execution seam.

## Phase 17 dynamic anomaly conversation boundary

Steps 68–69 replace only that anomaly deferral. The safe catalog adds anomaly
state and supported operation identifiers, never rows, samples, paths, columns,
values or raw readiness artifacts. The provider may propose only one of two
GLOBAL operation keys; code constructs the typed request and current readiness
still controls execution.

Candidate labels are opaque A1–A10 navigation aliases over session-local handles.
Handles bind the exact session, dataset, operation, canonical candidate record,
lineage digest and semantic result digest. Follow-up re-executes current evidence
and exposes a bounded relevant-measure projection only. Cross-session/dataset,
invented and stale references fail closed. Source/user prompt injection cannot
turn labels, headers or values into instructions. No new persistence, telemetry,
network, SQL, shell, subprocess, runtime import/code generation or arbitrary row
retrieval surface is introduced.
