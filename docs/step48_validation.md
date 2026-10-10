# Phase 13 — Step 48 validation

## Status

**PASS.** A local versioned JSON registry admits only reconciled,
`SEMANTICALLY_APPROVED` artifacts and keeps the current projection separate from
immutable source/profile/mapping/version history.

## Storage decision

JSON manifests match the current offline single-user architecture, are
inspectable, need no dependency or migration service, and support atomic current
pointer replacement plus append-only numbered registry versions. The default
root is `data/onboarding/`, ignored by Git. This is intentionally not a
multi-process registry.

Entries record source fingerprint/type/run, contract versions, profile and
mapping digests, mapping statuses/unresolved semantics, quality and currency
state, approved canonical domain, date range, row count, lifecycle/readiness,
lineage and capability summary. Normal projections contain no absolute paths.

## Canonical mapping

`CanonicalMapper` builds a closed mapping specification from confirmed roles
only. Its permitted normalizations are exact `Decimal` parsing, unambiguous ISO
date parsing and text preservation. It cannot invert signs, assign currency,
perform FX, infer categories or turn sales/accounting values into cash.

Generated in-memory canonical records retain source value plus normalized value
and stable lineage from source fingerprint/sheet/actual CSV or worksheet row to
canonical record ID.
Full canonical records are not persisted by this phase. Accounting DR/CR remains
an approved indicator and is not rewritten as revenue, expense or cash.

Artifact digests must reconcile exactly. A changed schema/profile cannot reuse
an old mapping silently.

## Focused tests

`python -m unittest tests.test_onboarding_registry tests.test_onboarding_confirmation`

Result: **14 passed**. Tests cover registry fields, local-path privacy,
append-oriented versions, approval/reconciliation gates, canonical
normalization, row lineage, accounting semantics and incompatible-schema reuse.
