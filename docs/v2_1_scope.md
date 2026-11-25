# Financial Manager AI V2.1 — Automated Data Preparation & Smart Onboarding Scope

Status: **PLANNING BASELINE — READY_FOR_IMPLEMENTATION** (2026-11-24).

This document authorizes planning for the V2.1 minor release. It does not
implement production code, change the immutable `v2.0.0` tag, authorize a new
V2 phase, or expand the closed financial operation catalogs.

## Authority and baseline

The explicit V2.1 instruction and the repository state establish that V2.0.0 is
complete, committed, pushed and tagged. The annotated `v2.0.0` tag resolves to
commit `e838ec1`, which is also the inspected `main` and `origin/main` baseline.
Release-candidate wording retained inside documents at that tag is historical
release evidence; V2.1 does not rewrite those frozen V2.0.0 documents.

V2.1 inherits without reinterpretation:

- the four executable domains and their exact 9/6/6/6 operation catalogs;
- the two existing global Sales/Profit anomaly screens and candidate-only
  language;
- deterministic Financial Core and anomaly authority;
- operation-specific, current and revocable readiness;
- local CSV and constrained XLSX security limits;
- source, profile, mapping, registry and execution lineage;
- the Application Layer, local FastAPI `/api/v1` and Web Financial Workspace;
- exact Decimal transport, explicit currency state and explicit cash direction;
- the single Financial Manager as an orchestrator, not a multi-agent system; and
- the current local, single-user, no-telemetry operating model.

The V2.0.0 scope freeze remains authoritative for what that release contains.
This document authorizes only the incremental V2.1 work stated below.

## Product goal

V2.1 shall make onboarding feel like:

```text
Upload CSV/XLSX
  -> safe ingestion and immutable source preservation
  -> deterministic structural profile
  -> deterministic safe preparation
  -> data-quality report
  -> bounded semantic suggestions
  -> explicit confirmation only for financially meaningful ambiguity
  -> approved canonical dataset view
  -> operation-specific readiness
  -> analysis
```

The product promise is:

> The system handled everything it could prove safely and only asked me about
> decisions that required human financial meaning.

“Handled” means a named, versioned and reproducible transformation or finding.
It never means that an AI silently cleaned, repaired or interpreted the source.

## Scope

V2.1 includes:

1. A deterministic preparation contract over the existing accepted CSV/XLSX
   representation.
2. A versioned Data Quality Report with explicit severity and readiness impact.
3. Safe structural transformations that preserve raw source values and lineage.
4. Refined semantic suggestion and confirmation projections without weakening
   existing authority.
5. Canonical lineage from every prepared value to source file, sheet, row,
   column, raw value and transformation.
6. Exact and key-based duplicate candidate reporting without automatic deletion.
7. Explicit missing-value, date and currency policies.
8. A lower-cognitive-load onboarding workflow in the existing web workspace.
9. Additive Application/API projections for preparation, quality and unresolved
   confirmation groups.
10. Deterministic digests and replay rules for preparation and canonical views.
11. Regression, security, privacy, performance and release hardening for V2.1.

V2.1 applies to newly onboarded supported files. Existing V2.0.0 artifacts are
not mutated or relabeled in place. A V2.0.0 artifact may gain a new append-only
V2.1 preparation artifact only when the V2.1 pipeline explicitly processes it
from its preserved source; the legacy artifact remains readable under its own
versions.

## Automation classes

Every preparation behavior has exactly one class, including its preconditions:

- `SAFE_AUTOMATIC`: deterministic, source-preserving and incapable of changing
  financial meaning under its stated preconditions. It may execute without a
  new user decision.
- `SUGGEST_ONLY`: the system may present evidence and a bounded proposal, but
  persistence requires an explicit authority-changing user action.
- `PROHIBITED_AUTOMATION`: V2.1 must not execute the behavior automatically.
  Some items are entirely outside V2.1; others could only exist in a future,
  separately approved scope.

The normative matrix is in
[the preparation contract](v2_1_data_preparation_contract.md#automation-decision-matrix).

## Authority invariants

- Structural facts may be accepted automatically; financial meanings may not.
- A normalized selector, checked card or changed field is pending UI state, not
  approval.
- Semantic role, canonical domain, value meaning, amount convention, ambiguous
  date format, currency and outstanding-balance meaning require recorded
  authority.
- Applying a previously approved, version-matched contract is automatic;
  choosing that contract is not.
- The frontend collects decisions and displays backend evidence. It never
  calculates or confirms financial truth.
- FastAPI validates and transports typed commands/projections. It never derives
  financial or semantic truth.
- `OnboardingManager` coordinates the workflow. It does not absorb parsing,
  preparation, semantic, persistence or readiness rules.
- `CapabilityDiscovery` remains the sole onboarding readiness authority.
- Financial Core and deterministic domain modules remain the sole authorities
  for financial values, coverage and operation results.
- An optional local LLM can add only bounded `SUGGESTED`/`UNKNOWN` semantic
  proposals. It cannot prepare values, confirm meaning or affect readiness.

## Compatibility commitments

- No V2.0.0 source, profile, mapping, registry or execution artifact is rewritten.
- No existing operation key, meaning, qualifier or readiness gate changes.
- No existing API request is broadened to accept paths, arbitrary columns,
  formulas, SQL, adapters or algorithms.
- Existing V2.0.0 read projections remain available. V2.1 additions are typed
  and additive unless an explicitly versioned successor is required.
- Existing CLI-compatible behavior and all V1/V2 regression tests remain release
  gates.

## Non-goals

V2.1 does not authorize:

- Forecasting or cash-flow prediction;
- RAG, document ingestion or document retrieval;
- ML fraud detection, fraud/risk classification or new anomaly algorithms;
- bank, payment, ERP or external data-source integrations;
- authentication, RBAC, accounts, organizations or multitenancy;
- SaaS, public/cloud deployment architecture, telemetry or analytics;
- PostgreSQL, distributed processing, Spark or background queue infrastructure;
- arbitrary SQL, query DSLs, formulas, user-selected adapters or code execution;
- new financial domains, operations or anomaly screens;
- automatic imputation, record deletion, deduplication or outlier removal;
- currency inference, FX conversion or sign-based cash direction;
- a mobile application or external LLM provider requirement; or
- a “Phase 6” or another five-phase V2 roadmap.

## Deliverables

The V2.1 planning set is:

- this scope;
- [Automated Data Preparation Contract](v2_1_data_preparation_contract.md);
- [Smart Onboarding](v2_1_smart_onboarding.md);
- [Architecture](v2_1_architecture.md);
- [Acceptance Criteria](v2_1_acceptance_criteria.md); and
- [Roadmap](v2_1_roadmap.md).

These documents define implementation gates. They are not evidence that the
implementation already exists.

## Planning decision

**READY_FOR_IMPLEMENTATION.** The automation classes, authority owners,
preparation and quality contracts, persistence/versioning strategy, API/web
impact, release packages and measurable acceptance gates are specified. The
implementation must proceed only inside this V2.1 scope and must stop for a new
scope decision if repository evidence makes any prohibited automation necessary.
