# Financial Manager AI V2.1 — Minor Release Roadmap

Status: **PLANNED — FOUR WORK PACKAGES, NO PHASE 6**.

V2.1 is a compact minor release over immutable `v2.0.0`. These are work
packages, not a new five-phase product roadmap and not “Phase 6.” A package may
fix defects discovered inside the V2.1 scope, but cannot add a new domain,
operation, surface or deferred capability.

## Work Package 1 — Scope and preparation contracts

### Outcomes

- Freeze V2.1 scope, automation matrix and non-goals.
- Freeze preparation, transformation lineage, Data Quality Report, duplicate,
  missing-value, date, currency and reproducibility contracts.
- Freeze the smallest architecture extension and authority ownership.
- Freeze measurable acceptance criteria and compatibility policy.

### Deliverables

- `docs/v2_1_scope.md`
- `docs/v2_1_data_preparation_contract.md`
- `docs/v2_1_smart_onboarding.md`
- `docs/v2_1_architecture.md`
- `docs/v2_1_acceptance_criteria.md`
- this roadmap

### Exit gate

Architecture/spec review finds no contradiction or unresolved decision that
would change production interfaces, authority or scope. Planning status is
`READY_FOR_IMPLEMENTATION`.

Current planning result: **COMPLETE**. This is not production implementation.

## Work Package 2 — Deterministic preparation and data quality

### Outcomes

- Implement the deep in-process preparation module behind its small interface.
- Extend structural evidence conservatively without changing V2.0.0 artifacts.
- Persist versioned preparation/quality/canonical manifests and digests.
- Extend canonical lineage to source column/value and transformation chain.
- Integrate typed quality evidence into current operation-specific readiness.

### Required test-first slices

1. Stable preparation/quality model and digest fixtures.
2. Safe transformation/refusal behavior.
3. Blank/null-like token and missing-not-zero behavior.
4. Unambiguous/ambiguous date behavior independent of machine locale.
5. Exact/key-based duplicate candidate behavior with no deletion.
6. Currency/sign/DR-CR/outstanding-balance prohibited behavior.
7. Canonical per-value lineage and replay.
8. Registry/readiness integrity, revocation and legacy artifact compatibility.
9. Performance benchmarks at existing bounds.

### Exit gate

Acceptance sections A–G, J05–J06 and K01–K04 pass through onboarding module
interfaces. No Application/API/Web change is needed to prove deterministic
authority.

Current result: **COMPLETE**. Implementation and validation evidence is recorded
in `docs/v2_1_wp2_validation.md`. Work Package 3 has not started.

## Work Package 3 — Smart onboarding Application/API/Web integration

### Outcomes

- Add transport-neutral preparation/quality projections.
- Add the two additive read routes and update onboarding response/OpenAPI.
- Regenerate typed web contracts.
- Refactor `/datasets/new` to the smart workflow in place.
- Extend dataset detail with quality, coverage and safe lineage.
- Preserve explicit commitment boundaries and Institutional Workspace direction.

### Required test-first slices

1. Application delegation/projection safety.
2. API schema, exact-ID, privacy and error behavior.
3. Frontend pending-versus-saved authority tests.
4. Preparation/quality explainability and neutral language tests.
5. Responsive/accessibility component tests.
6. Real-API CSV, multi-sheet XLSX, ambiguous-date, duplicate-candidate,
   currency-unknown and partial-coverage E2E.

### Exit gate

Acceptance sections H–I and J01–J04 pass. Web request-count evidence proves that
viewing, selecting and grouping never persist authority.

## Work Package 4 — Hardening and V2.1 release

### Outcomes

- Run full V1/V2/V2.1 regression, security, offline, performance and real-browser
  gates.
- Reconcile implementation, OpenAPI, generated types, usage guidance and the
  technical guide.
- Audit artifact migration/compatibility from a copy of V2.0.0 local state.
- Complete final authority/scope review and risk record.
- Produce release evidence and a manual release checklist.

### Exit gate

- Every V2.1 acceptance criterion passes.
- Existing exact operation/anomaly catalogs are unchanged.
- Zero unresolved BLOCKER/HIGH correctness, authority, security, privacy or
  integrity finding remains.
- A human explicitly authorizes commit/tag/push/release actions.

No commit, tag, push or release is automatic under this roadmap.

## Dependency order

```text
WP1 contracts
  -> WP2 deterministic preparation/quality
  -> WP3 Application/API/Web integration
  -> WP4 hardening/release
```

WP3 may begin typed projection scaffolding after WP2 models are stable, but it
cannot invent or duplicate transformation/readiness rules. WP4 runs only against
the integrated implementation.

## Scope-change rule

Stop and obtain an explicit V2.1 scope decision if implementation appears to
require:

- automatic financial imputation, deletion, merge or sign change;
- a new financial operation/domain/anomaly algorithm;
- currency inference or FX conversion;
- arbitrary query/formula/adapter selection;
- external processing, telemetry, cloud services or new persistence
  infrastructure;
- authentication/multitenancy/SaaS;
- a required external LLM; or
- mutation of the `v2.0.0` tag or its frozen artifacts.

Recognizing a possible future improvement does not authorize it.

## Suggested implementation commit sequence

After each package is implemented, reviewed and green, suggested logical commits
are:

1. `docs(v2.1): freeze automated preparation and smart onboarding contracts`
2. `feat(onboarding): add deterministic preparation and quality artifacts`
3. `feat(api): expose typed preparation and data quality projections`
4. `feat(web): streamline smart onboarding confirmations and readiness`
5. `test(v2.1): harden preparation security reproducibility and regressions`
6. `docs(v2.1): reconcile release evidence and operating guidance`

These are suggestions only. Staging, committing, tagging and pushing require
explicit user action after reviewing actual changes.
