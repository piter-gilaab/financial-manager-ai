# Financial Manager AI V2 — Final Technical Validation

Status: **INITIAL CANDIDATE TECHNICAL BASELINE — SUPERSEDED BY PHASE 5 REMEDIATION** (2026-11-22).

The deterministic authority findings below remain valid unless a remediation
test disproves them. This document no longer constitutes the final V2 release
gate by itself.

The Phase 5 remediation retained these boundaries and passed 773 backend tests,
42 frontend tests, 11 real-API browser tests, typecheck, lint and production
build. Its automated tasteskill gate was inconclusive; current release status is
recorded in [the remediation report](v2_phase5_release_remediation.md).

## Integrated architecture

```text
safe ingestion -> profile -> explicit semantic decisions -> current readiness
  -> FinancialManagerAgent -> binder/adapter -> Financial Core or Anomaly Engine
  -> Application Layer -> FastAPI -> Web / conversation presentation
```

The onboarding modules own artifacts and semantic decisions; readiness is a live
projection; the Manager orchestrates; binders/adapters authenticate lineage and
canonicalize closed requests; `src/financial` owns financial arithmetic and
`src/anomaly` owns quartiles, IQR, fences and classification. Application/API/Web
preserve and present evidence. This is a set of deep modules at explicit seams,
not a second financial implementation in each surface.

## Authority findings

- Totals, means, grouping, aging, overdue, outstanding balance and net cash are
  implemented in deterministic financial modules. Manager/Application/API do not
  recalculate them.
- Quartiles, IQR, fences, eligibility and `CANDIDATE` classification remain in
  anomaly modules. Web renders returned fences and converts exact strings only to
  non-authoritative chart coordinates.
- Mediation grounding counts/locates returned facts and may order groups using
  exact returned values for bounded explanation; it creates no financial value.
- API serialization rejects binary floats and non-finite Decimal, and serializes
  finite Decimal as base-10 strings. Frontend exact tables/tooltips retain those
  strings.

## Financial semantics

- Currency `UNKNOWN`, `CONFIRMED` and `CONFIRMED_MULTIPLE` remain distinct. No
  symbol, ISO, country or LLM inference and no hidden FX occur. Multiple confirmed
  currencies block scalar monetary aggregation.
- Cash direction comes only from confirmed `CASH_DIRECTION` mapping. Both
  `ABSOLUTE_WITH_DIRECTION` and `SIGNED_WITH_DIRECTION` conventions are checked;
  sign alone never establishes direction.
- Aging/overdue require confirmed `dataset_reference_date`; request
  `as_of_date` must equal it. Status mapping must be complete, open balance must
  represent outstanding balance, and machine today/historical reconstruction are
  not authorities. Equality with due date is `NOT_DUE`.
- Readiness is dataset- and operation-specific, recomputed from current profile,
  mapping, registry and source identities, revocable and repeated at execution.
- Anomaly remains Sales/Profit only, GLOBAL Tukey-IQR v1.0, minimum 30 usable
  values, positive IQR and candidate-only.

## Lineage and privacy

Source fingerprint, ingestion, profile, mapping, registry, adapter, catalog and
policy identities survive the Manager, Application and API evidence. Phase 5
corrected HTTP upload lineage so the safe original filename, not the server's
random temporary filename, is retained. Artifact paths remain internal; API/Web
projections do not disclose absolute paths.

## LLM boundary

Optional loopback mediation selects allowlisted intents, bounded parameters and
exact eligible dataset IDs, then explains grounded evidence. It receives no
authority to calculate, infer semantics/currency, classify anomalies, execute SQL
or select an adapter. Provider absence is controlled and deterministic operation
remains available.

## Review result

The Standards review found no hard repository-standard violation and one LOW
judgment call: explicit catalog representations across Core/Application/API/Web
create a synchronization risk. Generated OpenAPI plus exact catalog tests mitigate
it; refactoring a frozen catalog would add release risk without product benefit.
