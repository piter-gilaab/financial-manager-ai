# Financial Manager AI V2 — Security and Privacy Validation

Status: **PASS** (application boundary review, not a compliance certification).

## Security review

- CSV is UTF-8, bounded and parsed as data. XLSX is treated as a constrained ZIP
  and rejects traversal, duplicate entries, excessive archive size/ratio,
  formulas, macros and external links.
- HTTP multipart is incrementally staged to a server-owned temporary regular
  file with a 10 MiB bound and guaranteed temporary-directory cleanup. Client
  filenames are validated as printable basenames; no path onboarding endpoint
  exists.
- Dataset/session IDs are opaque, shape-validated and exact. Semantic roles,
  value mappings, operations, parameters and adapters use closed catalogs.
- SQL-, shell-, Python/import-, formula- and prompt-shaped text stays inert or is
  rejected. There is no user `eval`, `exec`, shell or raw-SQL dispatch.
- JSON/date/Decimal validation rejects unknown fields, malformed values,
  binary floats and non-finite numbers. Known domain failures use controlled
  envelopes rather than stack traces.
- CORS is off by default and accepts only an explicit HTTP loopback allowlist,
  without credentials. The API binds to `127.0.0.1`; public exposure is not an
  approved deployment model.
- React escaping is intact; no `dangerouslySetInnerHTML`, arbitrary external URL
  fetching or browser secret exists. The only frontend fetch target is the
  configured local API base URL.

## Error privacy

Representative malformed upload, traversal, unknown operation/field, stale
artifact, invalid ID, provider failure and unexpected exception tests confirmed
that responses omit stack traces, absolute paths, source contents, registry
internals and exception representations. Phase 5 also restored safe original
filename lineage without exposing the transport temporary path.

## Session and data privacy

Conversation sessions are process-local memory, expire/reset/cancel independently
and are not authentication. No transcript is written to cookies, localStorage,
sessionStorage, IndexedDB or a database. Static dependency/source review found no
analytics SDK, telemetry or beacon. Browser state contains only current in-memory
workspace/session projections. Host access, disk encryption, backups, browser
history and shell history remain operator responsibilities.

## Secret and repository review

Tracked-file scans found no private key, provider credential, live API token or
password. Matches were documentation terms and explicit synthetic test canaries.
Private raw/processed/onboarding data, SQLite, `.env.local`, virtualenv, Node/Next,
Playwright and coverage artifacts are ignored.

## Residual boundaries

This is a local single-user application without authentication or tenant
isolation. Do not bind it publicly or treat session IDs as access control. XLSX
support is intentionally constrained, not a general spreadsheet runtime.
