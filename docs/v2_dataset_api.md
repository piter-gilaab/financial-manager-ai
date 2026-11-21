# V2 Phase 3 — Dataset and Onboarding API

Status: **IMPLEMENTED**.

Implemented routes:

- `GET /api/v1/datasets`
- `GET /api/v1/datasets/{dataset_id}`
- `GET /api/v1/datasets/{dataset_id}/profile`
- `GET /api/v1/datasets/{dataset_id}/mappings`
- `GET /api/v1/datasets/{dataset_id}/readiness`
- `POST /api/v1/onboarding`
- `POST /api/v1/datasets/{dataset_id}/mappings/decisions`
- `POST /api/v1/datasets/{dataset_id}/domain-confirmation`
- `POST /api/v1/datasets/{dataset_id}/qualifiers`
- `POST /api/v1/datasets/{dataset_id}/lifecycle`

IDs are exact `ds_` identifiers. Responses contain bounded workflow/profile/
mapping/readiness projections without absolute paths or raw rows. Domain and
semantic confirmation require an explicit closed action plus evidence. STATUS,
CASH_DIRECTION, currency and other value mappings remain governed by existing
onboarding validation. Qualifiers are limited to `OUTSTANDING_BALANCE`, strict
dataset reference date and the two approved cash amount conventions.

Multipart upload accepts one `.csv` or constrained `.xlsx`, optional sheet and
bounded provenance note. The multipart parser streams directly to a random
server-owned temporary file while enforcing the 10 MiB file bound and bounded
request overhead; no whole-file byte buffer or process-global parser setting is
used. Filename paths are never used as destinations. Multi-sheet workbooks
without an exact `sheet` return 409 `CLARIFICATION_REQUIRED` with safe sheet
names. Formula,
macro, external-link, malformed archive, ZIP traversal, fake extension, shape
and ingestion limits are enforced by the existing ingestion path.

