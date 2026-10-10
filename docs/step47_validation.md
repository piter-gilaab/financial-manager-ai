# Phase 13 — Step 47 validation

## Status

**PASS.** Semantic suggestions can be confirmed, corrected, rejected or revised
through an explicit, append-oriented user-decision service. A manual correction
works when no semantic provider is available.

## Decision behavior

Each decision creates a new mapping version/digest and records UTC time, previous
proposal, approved role, evidence, optional closed value mapping and authority
source `USER`. Earlier mapping objects remain unchanged. Rejection removes the
current role; correction can select only an allowlisted role. Cancelling produces
`BLOCKED`; rejecting the dataset produces `REJECTED`.

Canonical-domain approval is separate from column approval. `SALES_RECORD`,
`ACCOUNTING_TRANSACTION` and `PAYABLE` reach `SEMANTICALLY_APPROVED` only after
their documented required roles are confirmed. A later rejection returns the
current version to `NEEDS_CONFIRMATION`.

## Critical semantics

- Debit/credit, cash direction and actual/budget indicators require an explicit
  closed source-value map covering every bounded observed value.
- Confirming that a column stores currency does not assign a denomination.
- Currency becomes `CONFIRMED` only when the user supplies a valid explicit ISO
- Ambiguous date roles require an explicit `DD/MM/YYYY` or `MM/DD/YYYY` format
  contract before confirmation and canonical parsing.
- Domain and all column decisions require bounded, printable evidence text.

No decision stores code, SQL, callable state or transformations.

## Focused tests

`python -m unittest tests.test_onboarding_confirmation tests.test_onboarding_semantics`

Result: **14 passed**. Cases cover confirmation, manual correction, rejection,
invalid roles/evidence, DR/CR value meanings, currency evidence, domain gates,
revision invalidation and stop/reject behavior.
