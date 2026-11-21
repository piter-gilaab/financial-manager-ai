# Financial Manager AI V2 — HTTP API Contract

Status: **FROZEN API V1 CONTRACT — IMPLEMENTED IN PHASE 3**.

Base path: `/api/v1`. JSON is UTF-8. Requests reject unknown fields unless this
contract explicitly says otherwise. Execution request enums come from the frozen
domain catalogs; callers never send adapter, module, class or function names.

## Common response envelopes

Projection response:

```json
{
  "api_version": "1",
  "status": "SUCCESS",
  "data": {},
  "limitations": [],
  "errors": []
}
```

Execution response:

```json
{
  "api_version": "1",
  "status": "SUCCESS",
  "evidence": {},
  "limitations": [],
  "errors": []
}
```

`evidence` is the complete authoritative Manager/domain result. The API does not
duplicate selected totals into a second transport field. Errors contain stable
`code`, optional `field` and safe `message`. `limitations` is never omitted.

## Health and capabilities

### `GET /health`

Returns process liveness and API version only. It does not read financial data,
call a model, disclose paths or claim readiness for every dataset.

### `GET /capabilities`

Returns global Manager capability metadata plus catalog identifiers. Optional
`dataset_id` requests a freshly computed exact dataset projection; an unknown ID
is 404. Global availability never substitutes for dataset/operation readiness.

## Dataset resources

### `GET /datasets`

Returns bounded safe projections sorted by exact dataset ID. Query parameters
are limited to cursor/page-size pagination added in Phase 3 if needed; no fuzzy
path/filename search is mandatory. Each item contains dataset ID, approved
domain, lifecycle/readiness state, currency state, supported operations and
limitations, without absolute paths.

### `GET /datasets/{dataset_id}`

Returns the safe current registry/workflow projection for one exact ID.

### `GET /datasets/{dataset_id}/profile`

Returns the existing bounded deterministic profile projection. Likely-sensitive
sample suppression remains enforced.

### `GET /datasets/{dataset_id}/mappings`

Returns current semantic suggestions/decisions, approved domain, role/value
mappings, semantic qualifiers, versions and unresolved requirements.

### `POST /datasets/{dataset_id}/mappings/decisions`

Records exactly one explicit semantic decision. Body fields are closed:

```text
column, decision=CONFIRM|CORRECT|REJECT, role?, evidence,
value_mapping?, date_format?, semantic_qualifiers?
```

The endpoint does not accept `authority_source` from the caller and never turns
a suggestion into confirmation without the explicit decision/evidence.

### `POST /datasets/{dataset_id}/domain-confirmation`

Body: exact `domain` enum and bounded non-empty `evidence`. Records a new mapping
version; does not make execution ready by itself.

### `GET /datasets/{dataset_id}/readiness`

Recomputes and returns current capability and operation readiness, required
roles/mappings/qualifiers, currency/date gates, reasons and limitations. It is a
projection, not an authorization token.

## Onboarding

### `POST /onboarding`

Multipart fields:

- `file`: one required CSV/XLSX file;
- `sheet`: optional exact XLSX sheet name;
- `provenance_note`: optional bounded plain text.

Maximum accepted file bytes are 10 MiB, matching the existing safe ingestion
contract. The endpoint returns 201 with the safe onboarding projection, profile
and semantic suggestions when successful. A multi-sheet XLSX requiring selection
returns a controlled 409/clarification-shaped error with safe sheet names, not a
parser fallback. Upload never approves semantics or domain.

## Financial analysis

### `POST /analysis`

Body:

```json
{
  "dataset_id": "ds_...",
  "operation": "PAYABLE_AGING",
  "parameters": {"as_of_date": "2026-11-01"}
}
```

`operation` is the union of the closed executable domain catalogs. Parameters
are a discriminated schema for that operation: only `as_of_date`, `granularity`
and/or `missing_dimension` where the catalog permits them. No question text,
source column, filter, measure, grouping, formula, SQL or adapter selector is
accepted by this structured endpoint.

The application delegates through `FinancialManagerAgent`; the response carries
complete current readiness and evidence.

## Anomalies

### `POST /anomalies`

Body contains exact `dataset_id` and one of the existing
`SALES_ANOMALY_SCREEN | PROFIT_ANOMALY_SCREEN` operation keys. V2 adds no other
dynamic anomaly key. Algorithm, threshold, tail, peer, measure, source column and
adapter are not request fields.

Returned evidence preserves candidate/assessment/policy/coverage/currency/lineage
fields and the limitation that a candidate is only statistical evidence for
review.

## Sessions and conversation

### `POST /sessions`

Creates one process-local session and returns 201 with opaque `session_id`, safe
lifecycle state and expiry timestamps. It creates no user account.

### `GET /sessions/{session_id}`

Returns the existing redacted session status. It omits internal evidence handles,
lineage payloads and private state.

### `POST /sessions/{session_id}/turns`

Body: one bounded text `message`. The application uses the existing
session/mediator authority and returns execution evidence, clarification or a
controlled provider outcome. Text never becomes SQL/formula/tool code.

### `POST /sessions/{session_id}/answers`

Body: one exact pending clarification `value`. The session revalidates it.

### `POST /sessions/{session_id}/follow-ups`

Body: current issued `reference` plus `intent=why_selected|record_detail`.
References remain session/evidence-bound and freshly re-executed.

### `POST /sessions/{session_id}/reset`

Clears context and rotates session identity. Returns the new safe projection.

### `DELETE /sessions/{session_id}`

Cancels/removes the local session. This is session cleanup, not deletion of
financial datasets or artifacts.

## Status and HTTP mapping

| Body status/code family | HTTP |
|---|---:|
| `SUCCESS`, `PARTIAL`, `NO_DATA`, `CLARIFICATION_REQUIRED` | 200 |
| resource/session/onboarding creation | 201 |
| `INVALID_REQUEST`, `UNSUPPORTED` | 400 |
| exact resource absent | 404 |
| `BLOCKED`, stale, semantic/readiness/data-quality blocker | 409 |
| transport schema validation | 422 |
| optional provider unavailable/error | 503 |
| unexpected defect | 500 |

An application error preserves the internal controlled status/reason. A 500
contains a fixed safe message and no traceback, raw exception or path.

## Decimal and evidence encoding

- Every monetary amount, statistic, quartile, fence and other exact Decimal is a
  JSON string such as `"123.4500"`.
- Integer counts remain JSON integers.
- Non-finite values are rejected; JSON `NaN`/`Infinity` are never emitted.
- Currency is never represented only by a symbol/string; its full state object
  is retained.
- Missing values are JSON `null` only where the evidence contract defines them,
  accompanied by status/coverage rather than coerced zero.
- The complete lineage projection remains nested under evidence metadata.

## OpenAPI and client generation

FastAPI may publish OpenAPI for `/api/v1`. It is documentation/client-contract
output, not an operation discovery mechanism that permits arbitrary execution.
Generated TypeScript types must preserve decimal strings and closed enums. Phase
3 acceptance must compare OpenAPI schemas with these frozen request/response
rules.

## Non-goals

No public internet deployment, auth/RBAC, tenant/organization resource, billing,
webhook, background job, arbitrary file path, bulk delete, SQL endpoint, generic
query endpoint, Forecasting endpoint or RAG endpoint is part of API v1.
