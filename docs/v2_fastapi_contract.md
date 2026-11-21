# V2 Phase 3 — FastAPI Contract

Status: **IMPLEMENTED**. Base path: `/api/v1`.

API v1 is the transport contract version; the product is Financial Manager AI
V2. `create_app(...)` creates isolated application modules and accepts injected
modules/provider factories for tests. The safe runtime entry point is
`python -m src.api`, bound by default to `127.0.0.1:8000`.

Core dependencies are pinned in `requirements.txt`: FastAPI 0.165.0, Pydantic
2.14.4, Uvicorn 0.54.0, python-multipart 0.0.34 and ASGI test transport httpx
0.28.1. They were validated on CPython 3.14.8; project metadata remains pinned
to the supported Python 3.14 line.

Transport models reject extra fields. Operations, anomaly operations, domains,
semantic roles, periods, missing-dimension policies, qualifiers and follow-up
intents are closed enums. Dates use exact `YYYY-MM-DD`. Authoritative Decimal is
recursively serialized with `format(value, "f")`; non-finite Decimal/float values
are rejected and counts remain integers.

Known results retain their application/domain status. Schema failures use 422,
unknown exact resources 404, invalid/unsupported requests 400, blockers 409,
provider failures 503 and unexpected defects a fixed private 500 envelope.
Every route publishes the bounded `ErrorEnvelope`; accidental programming
`KeyError` remains a private 500 rather than being masked as a missing resource.
Generated OpenAPI exposes typed dataset/session/profile/mapping/readiness
projections and the complete closed catalogs; it exposes no Forecasting, RAG,
auth or frontend route.

