# Step 03 Validation — Application / API Architecture

Status: **PASS — ARCHITECTURE ONLY**.

## Repository fit

- `FinancialManagerAgent` is the existing execution/orchestration facade and
  already delegates dynamic analysis/anomaly requests through static authorities.
- `OnboardingManager` is the existing safe onboarding facade; bypassing it for
  HTTP uploads would violate Phase 13.
- `FinancialManagerSession` owns process-local lifecycle, clarification,
  selection and evidence references; API/frontend intent logic would duplicate
  and weaken that authority.
- Existing results carry exact decimals, currency, quality, limitations and
  lineage; transport must preserve rather than reconstruct them.
- The repository baseline is CPython 3.14 with no third-party V1 runtime
  dependency and no installed FastAPI stack.

## Decisions frozen

1. Add transport-neutral Dataset, Analysis and Conversation application modules;
   do not add a second Financial Manager.
2. Select FastAPI + Pydantic v2 for the local HTTP adapter.
3. Use `/api/v1`; API version 1 is independent from product V2.
4. Keep the V1 CLI direct and compatible rather than routing it through HTTP.
5. Route uploads through the same safe ingestor with the existing 10 MiB and
   structural/archive limits; temporary transport files are always removed.
6. Use process-local, non-persistent single-user sessions with existing expiry;
   no identity/multitenancy system.
7. Serialize Decimal as base-10 JSON strings and preserve complete evidence.
8. Map known outcomes to stable non-500 responses while retaining precise body
   statuses/reasons.

## Compatibility evidence

- FastAPI official package metadata declares Python 3.14 support.
- FastAPI release notes record explicit Python 3.14 support.
- Exact dependency versions remain a Phase 3 lock/validation decision; none were
  installed in Phase 1.

## Authority review

| Risk | Result |
|---|---|
| API performs financial/anomaly arithmetic | Rejected; transport preserves Core/module evidence. |
| API decides semantics/readiness | Rejected; explicit onboarding and current readiness remain authoritative. |
| API accepts SQL/formula/adapter/path | Rejected by closed request schemas. |
| Upload bypasses ingestion | Rejected; same safe pipeline and limits are mandatory. |
| Decimal coerced to float | Rejected; exact decimal strings are frozen. |
| Session becomes SaaS identity | Rejected; opaque local process state only. |
| Every failure becomes HTTP 500 | Rejected; stable status mapping frozen. |

## Scope check

No dependency, route, server, application source, upload handler, frontend,
database, migration, auth system or production capability was implemented.
Step 03 is sufficient to define the web architecture in Step 04.
