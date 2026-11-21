# Financial Manager AI V2 — Application and API Architecture

Status: **FROZEN ARCHITECTURE — IMPLEMENTED IN PHASE 3**.

## Purpose

V2 adds a stable transport-neutral application seam between user interfaces and
the existing financial modules. It does not replace the Financial Manager or
move domain logic into an HTTP server.

The architecture is:

```text
Existing CLI ------------------> Manager / Session / Onboarding interfaces

Web Workspace -> HTTP API -> Application modules
                              |-> DatasetApplication -> OnboardingManager
                              |-> AnalysisApplication -> FinancialManagerAgent
                              `-> ConversationApplication -> FinancialManagerSession
                                                               |
                                                               v
                                         binder/static adapters/Financial Core
                                         or deterministic anomaly modules
                                                               |
                                                               v
                                                   structured evidence
```

This refines the conceptual “Application Services → FinancialManagerAgent” flow
to match V1: onboarding and session lifecycle already have separate public
interfaces. The application layer coordinates those interfaces but does not
create a second financial orchestrator. The existing CLI may continue calling
them directly; moving it behind HTTP is not a V2 requirement and would add risk
without product value.

## Module interfaces

Phase 3 may implement three small application modules. Names are architectural,
not a required source layout.

### DatasetApplication

Owns transport-neutral use cases for:

- list and inspect safe dataset projections;
- initiate bounded CSV/XLSX onboarding;
- retrieve profile and semantic mapping projections;
- record explicit role/value/qualifier decisions;
- record explicit domain confirmation; and
- retrieve current dataset/capability/operation readiness.

It delegates ingestion, profiling, semantic decisions, artifact persistence and
readiness to `OnboardingManager` and its existing deterministic collaborators.

### AnalysisApplication

Owns transport-neutral use cases for:

- list global and dataset-scoped capabilities;
- execute one closed Financial Analysis request; and
- execute one existing closed anomaly request.

It constructs only typed, allowlisted requests and delegates through
`FinancialManagerAgent`. It does not call adapters or Financial Core directly.

### ConversationApplication

Owns transport-neutral use cases for:

- create one local in-memory session;
- submit a turn;
- inspect the safe redacted session projection;
- answer a pending clarification;
- resolve an issued bounded evidence follow-up;
- cancel or reset a session; and
- expire/remove process-local state.

It delegates intent, selection, freshness and evidence-reference rules to
`FinancialManagerSession`/mediation. It does not implement financial intent in
the API or frontend.

These modules earn their seam by centralizing transport-to-domain validation,
upload lifecycle, controlled error mapping and exact serialization for the web
and tests. They must not mirror every internal method or expose adapters as
request-selected dependencies.

## Authority matrix

| Concern | Authority | Application/API responsibility |
|---|---|---|
| Financial arithmetic/coverage | Financial Core | Preserve and serialize returned evidence. |
| Anomaly calculation/classification | Anomaly modules | Preserve existing result and terminology. |
| Domain/role/value confirmation | Explicit user decision through onboarding rules | Collect and validate a closed decision request; never auto-confirm. |
| Readiness | Current onboarding/binder/adapter checks | Request and transport fresh projection; never cache as authorization. |
| Currency | Confirmed semantic evidence | Preserve `UNKNOWN|CONFIRMED|CONFIRMED_MULTIPLE`; never infer/convert. |
| Orchestration | `FinancialManagerAgent` | Select one explicit application use case and delegate. |
| Conversation lifecycle | `FinancialManagerSession`/mediation | Hold only the process-local session registry and transport actions. |
| HTTP validation | FastAPI/Pydantic v2 schemas | Reject malformed/unknown transport fields and closed-enum violations. |

The API does not own financial/anomaly calculations, semantic inference,
currency inference, readiness logic, SQL generation, data repair or LLM prompt
authority.

## Technology decision

The V2 HTTP adapter is **FastAPI with Pydantic v2 models**, served locally over
ASGI. The framework was selected because V2 requires typed Python contracts,
request/response validation, multipart upload support, OpenAPI and straightforward
integration with a TypeScript frontend. It aligns with the Python implementation
and is smaller than introducing a separate-language backend.

Compatibility evidence checked on 2026-11-21:

- the repository baseline is CPython 3.14;
- the [FastAPI package metadata](https://pypi.org/project/fastapi/) declares
  Python 3.14 support; and
- the [FastAPI release notes](https://fastapi.tiangolo.com/release-notes/)
  record Python 3.14 support from 0.118.3.

No FastAPI dependency is installed in Phase 1. Phase 3 must select and lock a
then-supported FastAPI/Pydantic/ASGI-server set, run a CPython 3.14 compatibility
spike, and add only the dependencies needed by the implemented local API. The
framework decision is frozen; exact versions are an implementation-time
reproducibility decision.

## Dependency direction

```text
web -> HTTP adapter -> application modules -> existing public module interfaces
                                             -> deterministic implementations
```

The HTTP adapter depends inward on application contracts. Application modules
depend inward on public onboarding/Manager/session interfaces. Financial,
execution, onboarding, anomaly and mediation modules do not import FastAPI or
web types. OpenAPI schemas are transport adapters, not domain models.

No generic repository, plugin framework, event bus, ORM, background queue or
database abstraction is introduced without a concrete Phase 3 blocker.

## Upload architecture

Browser uploads must enter the exact safe onboarding pipeline; the API may not
parse financial rows or bypass Phase 13 controls.

1. Accept one multipart file named `file`, optional exact `sheet`, and optional
   bounded `provenance_note`.
2. Accept only `.csv` and `.xlsx` names and stream to a server-owned random
   temporary regular file.
3. Enforce the existing 10 MiB file limit while streaming, before unbounded
   memory use. Existing ingestion limits remain authoritative: 100,000 rows, 64
   columns, 4,096 characters per cell and the current XLSX archive bounds.
4. Invoke the same `SafeFileIngestor`/`OnboardingManager` flow used by CLI.
5. On acceptance, the onboarding store owns the immutable copied source and
   versioned artifacts under its configured local root.
6. Delete the transport temporary file in a guaranteed cleanup path after
   success or controlled failure. Never expose its path.

Multipart metadata does not confirm semantics. Formula/macro/external-link,
symlink/path, encoding, archive and shape restrictions remain unchanged. API
body limits may be stricter, never looser, than the ingestion contract.

## Local session architecture

Mandatory V2 remains local and single-user. The API process holds an in-memory
map from an opaque random session ID to one `FinancialManagerSession`.

- Session IDs are navigation/correlation capabilities, not user identity or
  authentication credentials.
- Sessions retain the existing 30-minute inactivity and four-hour absolute
  expiry semantics unless a later explicit contract changes them.
- Session state and transcripts are not persisted.
- Reset rotates identity and clears context; cancel/expiry removes usable context.
- Process restart loses all sessions and the web must create a new one.
- Every analysis/follow-up still revalidates current datasets/readiness/evidence.

The local server binds loopback by default. Development CORS, when frontend and
API use different local origins, is an exact allowlist; wildcard credentials or
public exposure are not part of mandatory V2. Enterprise auth, accounts, RBAC,
organizations and multitenancy are not designed here.

## Error and outcome model

Known outcomes are structured and never reduced to HTTP 500:

| Application outcome | Default HTTP status | Meaning |
|---|---:|---|
| `SUCCESS`, `PARTIAL` | 200 (201 for created resource/session) | Request completed; inspect limitations/coverage. |
| `NO_DATA` | 200 | Valid operation with no eligible result. |
| `CLARIFICATION_REQUIRED` | 200 | Normal conversational state with closed choices. |
| `INVALID_REQUEST` | 400 | Semantically invalid application request. |
| `UNSUPPORTED` | 400 | Closed domain/catalog does not support the request. |
| resource not found | 404 | Exact dataset/session/resource absent. |
| `BLOCKED`, stale state, data-quality blocker | 409 | Applicable request cannot execute under current state. |
| transport schema violation | 422 | JSON/multipart does not match typed HTTP contract. |
| provider unavailable/error | 503 | Optional mediation unavailable; no invented evidence. |
| unexpected integration defect | 500 | Fixed non-sensitive message; no traceback/internal path. |

The stable body retains the more precise application status and reason code.
HTTP status never substitutes for the deterministic result status.

## Structured evidence and Decimal transport

- All `Decimal` values cross JSON as canonical base-10 strings, never JSON
  numbers and never implicit binary floats.
- Dates use ISO `YYYY-MM-DD`; timestamps use UTC RFC 3339 strings.
- Currency remains an object containing state, optional code, basis/source and
  `conversion_applied=false`.
- Coverage, exclusions, limitations, lineage IDs/digests/versions, operation and
  policy versions remain present.
- API schemas must use strict string/enum types and explicit serializers; Pydantic
  coercion must not turn monetary strings into floats.
- The adapter may add transport metadata but may not rename, round, aggregate,
  sort, suppress or recalculate authoritative evidence.

## API versioning

All mandatory routes use `/api/v1`. This is **API contract version 1**, not
product V1. Financial Manager AI product V2 may correctly expose `/api/v1`.

Breaking transport changes require `/api/v2`; additive optional response fields
or new routes may remain within `/api/v1` only when existing clients remain
valid. Domain operation/catalog versions remain separately present in evidence.
No content-negotiation or per-endpoint version matrix is introduced.

## Security and privacy

Requests cannot supply SQL, formulas, Python/import paths, functions, adapter or
provider names, source filesystem destinations, arbitrary measures/dimensions,
statistical algorithms or runtime expressions. Exact enums and IDs are resolved
by code-owned registries.

The API returns safe dataset projections, not absolute filesystem paths or raw
registry artifacts. It adds no telemetry, persistent request log, external
provider, cloud upload or public deployment claim. Host/runtime hardening is a
Phase 5 validation concern within the local scope, not an enterprise security
certification.
