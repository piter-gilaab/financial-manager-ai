# Financial Manager AI V2 — Initial Candidate Acceptance Record

Record status: **HISTORICAL CANDIDATE BASELINE — SUPERSEDED**  
Current V2 status: **RELEASE CANDIDATE — REMEDIATION IMPLEMENTED, TASTESKILL GATE INCONCLUSIVE**  
Current release recommendation: **DO NOT RELEASE OR TAG YET**

This matrix records the Steps 23–29 candidate assessment. A later tasteskill
audit found release-blocking authority and substantial frontend issues. Preserve
the matrix for traceability, but use `v2_scope_freeze.md`, `v2_roadmap.md` and
[`v2_phase5_release_remediation.md`](v2_phase5_release_remediation.md) for current
authority and release status.

## Acceptance matrix A–BF

| ID | Gate | Status | Evidence/limitation |
|---|---|---|---|
| A | Frozen V2 scope | PASS | Final scope freeze matches implementation. |
| B | `SALES_RECORD` execution | PASS | Nine operations and regression/E2E pass. |
| C | `PAYABLE` execution | PASS | Six operations pass direct/persisted/API paths. |
| D | `RECEIVABLE` execution | PASS | Six operations pass. |
| E | `CASH_TRANSACTION` execution | PASS | Six operations pass; both conventions tested. |
| F | Exact financial catalogs | PASS | 9/6/6/6, 18 new asserted from code. |
| G | Exact anomaly catalog | PASS | Exactly Sales and Profit screens. |
| H | Decimal authority | PASS | Core Decimal; API/UI exact strings. |
| I | Currency boundaries | PASS | UNKNOWN/CONFIRMED/MULTIPLE distinct; no FX/inference. |
| J | Aging semantics | PASS | Explicit reference/as-of equality and open balance. |
| K | Overdue semantics | PASS | Due-date equality and settled/cancelled rules pass. |
| L | Cash direction | PASS | Never sign-inferred. |
| M | Readiness | PASS | Current, revocable, dataset/operation-specific. |
| N | Lineage | PASS | Full artifact/catalog lineage; filename defect fixed. |
| O | Safe CSV | PASS | Bounds/encoding/parser/malicious inputs tested. |
| P | Safe XLSX | PASS | ZIP/formula/macro/link/sheet controls pass. |
| Q | Application Layer | PASS | Transport-neutral delegation/evidence preservation. |
| R | FastAPI | PASS | Local `/api/v1` primary workflows pass. |
| S | OpenAPI | PASS | Closed generated schema validated. |
| T | Dataset API | PASS | Upload/profile/mapping/readiness pass. |
| U | Analysis API | PASS | All 18 new plus Sales paths pass. |
| V | Anomaly API | PASS | Sales/Profit and candidate follow-up pass. |
| W | Conversation API | PASS | Lifecycle/isolation/grounding/blocked states pass. |
| X | Safe sessions | PASS | Process-local, expiry/reset/cancel, no auth claim. |
| Y | Web Overview | PASS | Real API E2E. |
| Z | Datasets UI | PASS | List/detail real API E2E. |
| AA | Onboarding UI | PASS | CSV/XLSX real API E2E. |
| AB | Semantic confirmation | PASS | Explicit decisions and evidence pass. |
| AC | Readiness UI | PASS | Current backend projection displayed. |
| AD | Sales UI | PASS | Actual HTTP evidence E2E. |
| AE | Payable UI | PASS | Actual HTTP evidence E2E. |
| AF | Receivable UI | PASS | Actual HTTP evidence E2E. |
| AG | Cash UI | PASS | Actual HTTP evidence E2E. |
| AH | Anomaly UI | PASS | Sales/Profit candidate-only E2E. |
| AI | Chat UI | PASS | Session/clarification real API E2E. |
| AJ | Exact Decimal UI | PASS | Exact table/string tests; chart geometry only. |
| AK | Currency UI | PASS | State/code/limitations preserved. |
| AL | Responsive UI | PASS | Chromium at 1440/1024/768/390. |
| AM | Accessibility | PASS_WITH_LIMITATIONS | Semantic labels, keyboard-native controls, reduced motion and tests pass; no external formal WCAG certification. |
| AN | Frontend authority | PASS | No aggregation/classification; presentation only. |
| AO | Backend regression | PASS | 773/773, zero fail/error/skip. |
| AP | Frontend tests | PASS | 33/33 in 10 files. |
| AQ | Browser E2E | PASS | 11/11 Chromium twice, actual local API. |
| AR | Production build | PASS | Next.js optimized build and routes pass. |
| AS | Fresh Python install | PASS | New CPython 3.14.8 venv with pinned requirements. |
| AT | Fresh Node install | PASS | New tree, `npm ci`, 507 packages, zero audit findings. |
| AU | Documented startup | PASS | Two-terminal commands exercised by real E2E. |
| AV | Security | PASS | Closed dispatch/upload/CORS/error review. |
| AW | Privacy | PASS | No transcript persistence/telemetry/path leak. |
| AX | Offline-capable runtime | PASS_WITH_LIMITATIONS | No-route backend plus proxy-blocked real loopback E2E; installation may need Internet. |
| AY | Repository hygiene | PASS | Ignore/secret/generated/tracked review complete. |
| AZ | Documentation/demo | PASS | README, usage, demo and Steps 23–29 complete. |
| BA | Forecasting deferred | PASS | No executable capability. |
| BB | RAG deferred | PASS | No executable capability. |
| BC | No fraud claims | PASS | Candidate-only code/UI/docs/tests. |
| BD | No SaaS/auth scope creep | PASS | Local single-user; no auth/tenant/cloud capability. |
| BE | Zero BLOCKER/HIGH | PASS | None unresolved. |
| BF | V2 release recommendation | PASS_WITH_LIMITATIONS | Release v2.0.0 with documented non-blocking limits. |

## Historical completion rule

All mandatory capabilities, full regressions, clean installs, startup,
security/privacy, offline runtime, repository hygiene and documentation pass. The
three `PASS_WITH_LIMITATIONS` entries are explicit boundaries, not unfinished
mandatory capabilities. No BLOCKER/HIGH remains; V2 is complete.

## Manual release sequence

After reviewing actual changes, create approved logical commits, rerun the final
smoke gates, then manually:

```sh
git status --short
git diff --check
git diff --stat
# stage and commit only reviewed groups
git tag -a v2.0.0 -m "Financial Manager AI V2.0.0"
git push origin main
git push origin v2.0.0
# optional: gh release create v2.0.0 --generate-notes
```

These commands are instructions only. Phase 5 created no commit, tag, push or
GitHub Release.
