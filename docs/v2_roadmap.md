# Financial Manager AI V2 — Frozen Roadmap

Status: **PHASE 5 RELEASE REMEDIATION — FIVE PHASES, NO PHASE 6**.

The V1 baseline is complete at tag `v1.0.0`. This roadmap governs V2 and creates
no Phase 6. Each phase must preserve the authority, evidence and compatibility
rules in [the V2 scope](v2_scope.md).

## Phase 1 — V2 Scope & Architecture

Freeze, without production implementation:

- product scope, mandatory domains and non-goals;
- domain semantics and closed query catalogs;
- aging, overdue, cash-direction, currency and readiness contracts;
- application/API architecture and transport contracts;
- web architecture, product flows and authority rules;
- final V2 acceptance criteria; and
- the exact Phase 2 implementation boundary.

Exit gate: all Phase 1 documents are internally consistent with the V1
repository and clearly distinguish frozen targets from implemented behavior.

## Phase 2 — Multi-Domain Financial Execution

Implement only the shared execution infrastructure required by the frozen
contracts and deterministic execution for:

- `PAYABLE`;
- `RECEIVABLE`;
- `CASH_TRANSACTION`;
- operation-specific readiness;
- `FinancialManagerAgent` integration;
- bounded conversational integration for the new ready operations; and
- regression, security, integrity and lineage validation.

`SALES_RECORD` remains compatible. Phase 2 does not implement the HTTP API,
frontend, Forecasting, RAG or new anomaly catalogs.

## Phase 3 — Application / API Layer

Implement the transport-neutral application modules and the versioned local
FastAPI HTTP adapter frozen in Phase 1. Reuse safe onboarding, current readiness,
Manager execution and session authorities. Add typed request/response validation,
upload handoff, stable errors and JSON-safe evidence transport without financial
recalculation.

Phase 3 does not implement the web workspace, public SaaS deployment,
authentication, multitenancy, PostgreSQL, Forecasting or RAG.

## Phase 4 — Web Financial Workspace

Implement the local Next.js + TypeScript workspace against the Phase 3 API:

- Overview;
- Datasets;
- Dataset Onboarding;
- Financial Analysis;
- Anomalies; and
- Chat / Ask Financial Manager.

The frontend renders backend evidence and gathers explicit user decisions. It
does not reproduce financial, readiness, semantic or anomaly authority.

## Phase 5 — V2 Hardening & Release

Validate the complete product against the frozen acceptance criteria:

- V1 and V2 regression;
- security and privacy;
- data integrity, lineage and reproducibility;
- application/API and web end-to-end workflows;
- controlled blocked/error/no-data behavior;
- fresh setup and documented local operation;
- documentation and demo accuracy; and
- zero unresolved BLOCKER/HIGH release issues.

Phase 5 may fix defects inside the frozen scope. It may not add a mandatory
domain, operation, surface or sixth phase.

The initial Phase 5 candidate gate recorded **PASS_WITH_LIMITATIONS** on
2026-11-22. A subsequent frontend taste/accessibility audit reopened Phase 5 for
release remediation. No sixth phase was created; see
[the Phase 5 summary](v2_phase5_summary.md).

## Deferred work

Forecasting, Financial Document RAG, additional executable domains, multi-domain
anomaly operations, public/cloud deployment, enterprise identity, multitenancy,
PostgreSQL, external providers, banking/ERP integration, mobile and any generic
query/statistical language belong to V2.x, V3 or Future Work and require explicit
approval.
