# Financial Manager AI V2 — Frozen Product Scope

Status: **FROZEN CONTRACT — IMPLEMENTATION PENDING**.

This document defines the mandatory product scope of Financial Manager AI V2.
It authorizes only the five phases in [the V2 roadmap](v2_roadmap.md). The V1
release at tag `v1.0.0` remains complete, historical and behaviorally frozen.

## Product definition

Financial Manager AI V2 is a local-first, multi-domain financial analysis
platform that safely onboards approved structured financial datasets, requires
explicit confirmation of their canonical domain and financial semantics,
executes closed domain-specific capabilities through deterministic modules, and
exposes the same authoritative evidence through the existing structured Manager
interfaces, compatible CLI workflows, an application/HTTP API and a web
Financial Workspace.

The optional LLM remains a language mediator and evidence explanation layer. It
does not own financial arithmetic, semantic confirmation, currency assignment,
readiness, anomaly classification or execution policy.

“Platform” means a coherent set of local interfaces over the same approved
capabilities. It does not imply cloud deployment, multi-tenancy or SaaS.

## Mandatory generic executable domains

V2 freezes exactly four mandatory generic execution domains:

1. `SALES_RECORD` — existing V1 behavior remains compatible.
2. `PAYABLE` — new V2 implementation target.
3. `RECEIVABLE` — new V2 implementation target.
4. `CASH_TRANSACTION` — new V2 implementation target.

The recognized domains `ACCOUNTING_TRANSACTION`, `BUDGET_RECORD`,
`BALANCE_RECORD` and `DOCUMENT_METADATA` remain non-mandatory and non-executable
unless a later, separately approved V2.x or V3 contract changes that status.
Recognition or semantic approval never implies execution readiness.

Legacy Receiver General and Company Financials remain separate V1 snapshot
paths. They are not aliases for an onboarding domain and are not migrated or
redesigned by V2.

## Required product surfaces

By V2 completion, approved capabilities must be reachable through:

- the existing structured `FinancialManagerAgent` and onboarding interfaces;
- CLI-compatible workflows, without breaking the frozen V1 commands;
- a versioned application/HTTP API;
- the local web Financial Workspace; and
- the existing bounded conversational path, extended only for ready closed V2
  operations.

Every surface delegates to the same current readiness and deterministic
execution authorities. A surface cannot create an operation, infer a semantic
role, or reinterpret evidence.

## Preserved authority and data rules

- The Financial Core owns financial arithmetic and result coverage.
- The anomaly modules own statistical calculations and classifications.
- The Financial Manager owns orchestration and response wrapping, not arithmetic.
- Semantic suggestions remain hypotheses until explicit evidence-bearing
  confirmation.
- Readiness remains current, dataset-specific and operation-specific.
- Monetary values use exact `Decimal`; missing and unparseable values are never
  silently replaced with zero.
- Currency is never inferred from symbols, formatting, geography, headers or an
  LLM. V2 performs no mandatory FX conversion.
- Source signs, values, source rows, fingerprints and semantic versions remain
  in lineage.
- Each executable domain has a closed operation catalog. No interface exposes a
  generic financial query language.

## Mandatory V2 outcomes

V2 must deliver:

- generic deterministic execution for `PAYABLE`, `RECEIVABLE` and
  `CASH_TRANSACTION` under [the multi-domain contract](v2_multi_domain_contract.md);
- stable compatibility for the nine V1 `SALES_RECORD` Financial Analysis
  operations and two existing Sales/Profit anomaly screens;
- a transport-neutral application seam and versioned local HTTP API;
- a web workspace for overview, dataset onboarding, financial analysis,
  existing anomaly screening and bounded conversation;
- security, privacy, integrity, lineage, fresh-setup and full-regression gates;
  and
- final V2 documentation, demo and release acceptance.

## Non-goals

The following are outside mandatory V2 scope:

1. Cash Flow Forecasting.
2. Financial Document RAG.
3. Arbitrary SQL.
4. Arbitrary formula execution.
5. Arbitrary group-by.
6. Arbitrary statistical algorithms.
7. ML anomaly models.
8. Fraud detection or scoring.
9. Banking or payment execution.
10. ERP integration.
11. Mobile application.
12. Multi-tenant SaaS.
13. Enterprise identity or authentication.
14. Distributed or cloud data platform.
15. PostgreSQL migration, unless a reproduced mandatory V2 blocker proves it
    necessary and the user separately approves the change.
16. Additional external LLM providers.
17. Autonomous financial decision-making.

The API and frontend do not authorize public hosting, accounts, organizations,
billing, RBAC, cloud storage, background financial automation or multi-user
concurrency. These items require separate evidence and approval.

## Change policy

The roadmap contains exactly five mandatory phases. A capability not required
to complete one of them is recorded as Future Work, V2.x backlog or V3. It does
not become a sixth mandatory phase and does not enter an implementation phase by
association.

Architecture documents may identify a future-compatible interface only when it
is required by a current V2 caller. They must not add speculative adapters,
providers, databases, deployment tiers or generic extension frameworks.

## V2 completion definition

Financial Manager AI V2 is complete only when all of the following hold:

1. `PAYABLE` is generically executable.
2. `RECEIVABLE` is generically executable.
3. `CASH_TRANSACTION` is generically executable.
4. Existing `SALES_RECORD` behavior remains stable.
5. Readiness remains operation-specific and freshly recomputed.
6. Multi-domain execution works through `FinancialManagerAgent`.
7. The application/API seam is stable and validated.
8. The web workspace supports the mandatory primary workflows.
9. Security, privacy and data-integrity gates pass.
10. Complete regression passes without modifying the frozen V1 meaning.
11. V2 documentation, demo and release acceptance pass.
12. No mandatory V2 blocker or unresolved BLOCKER/HIGH release issue remains.

Detailed release criteria are frozen in
[the V2 acceptance criteria](v2_acceptance_criteria.md).

## Phase 1 status

Phase 1 freezes contracts and architecture only. It implements no new adapter,
route, server, frontend, dependency, migration, anomaly algorithm, Forecasting
or RAG capability. Terms such as “supports” in V2 target documents describe the
accepted completion target unless explicitly marked as implemented V1 behavior.
