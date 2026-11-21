# Step 04 Validation — Web Architecture & V2 Acceptance

Status: **PASS — ARCHITECTURE ONLY**.

## Technology and repository fit

- The repository has no frontend files or locked Node toolchain; Phase 1 added
  none.
- Next.js + TypeScript is suitable for typed local UI/API integration and the
  required interactive onboarding, analysis, anomaly and chat flows.
- The host Node version is not treated as a project contract. Phase 4 must pin a
  compatible LTS/toolchain and dependency lock.
- The web remains an adapter over `/api/v1`, not a new financial module.

## Decisions frozen

1. Use Next.js + TypeScript with App Router.
2. Required areas are exactly Overview, Datasets, Dataset Onboarding, Financial
   Analysis, Anomalies and Chat / Ask Financial Manager.
3. Overview is dataset/domain-aware and cannot invent consolidated KPIs.
4. Onboarding always requires explicit semantic and domain actions.
5. Exact tables/evidence remain authoritative; charts are presentation and any
   numeric conversion for plotting is explicitly non-authoritative.
6. Anomaly wording is “Statistical candidates for review,” never fraud.
7. Chat delegates all intent/readiness/evidence rules to backend contracts.
8. Known blocked/error/no-data states have explicit UI states.
9. Acceptance criteria A–Z are all mandatory.

## Authority review

| Risk | Result |
|---|---|
| Frontend calculates totals/net/aging/overdue | Rejected; backend evidence only. |
| Frontend confirms semantics from suggestions | Rejected; explicit user decision/evidence required. |
| Chart invents KPI | Rejected; only approved returned evidence may be plotted. |
| Chat duplicates financial intent logic | Rejected; session/mediation/Manager remain authoritative. |
| Overview implies all domains/currencies coexist | Rejected; selected dataset/domain-aware only. |
| Anomaly becomes fraud verdict | Rejected by language and evidence policy. |
| Web implies SaaS/auth/tenants | Rejected; local single-user deployment. |

## Flow review

Upload-to-readiness, remediation, analysis, anomaly, conversation, currency,
stale-state and no-data flows are specified with controlled outcomes. No
mandatory screen depends on Forecasting, RAG, new anomaly operations or an
unapproved generic query.

## Integrated Phase 1 review

The cross-document review found and corrected one material ambiguity: an
explicit `as_of_date` was not initially bound to the date represented by source
status/balance. The final contract now requires an explicitly approved
`dataset_reference_date` and exact equality; it blocks historical reconstruction
with no settlement history.

Final documentation checks confirmed:

- all 14 required Step 01–04 files exist;
- new operation catalogs contain exactly 6/6/6 entries;
- acceptance identifiers are exactly A–Z;
- all local Markdown link targets exist;
- `git diff --check` passes; and
- no production source, test, dependency, frontend scaffold or migration changed.

## Scope check

No Node dependency, manifest, scaffold, route, component, API server, frontend
server, authentication, database or production capability was created.
Step 04 and the integrated Phase 1 architecture review pass.
