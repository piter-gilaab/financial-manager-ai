# Phase 9 — Step 29 validation

## Scope and sources

Step 29 is a documentation-only readiness assessment. It reviewed the glossary,
technical guide, CLI workflow, Step 25 evaluation, Steps 26–28 readiness and
validation evidence, orchestration contract, security/privacy boundary, current
CLI/manager implementation, relevant orchestration/acceptance tests, and the
working-tree status/diff. It added no runtime state, capability, dependency,
provider, schema, dataset or test.

## Readiness result

**READY_WITH_PREREQUISITES.** Step 26 deferred conversational UX until the measured
presentation problem was addressed. Steps 27–28 completed and validated that work.
Clarification continuation and explicit evidence-reference follow-up now have a
plausible bounded design and moderate observed UX value, but no implementation is
authorized until the state, reference, lifecycle and privacy contracts listed in
[the readiness assessment](conversational_ux_readiness.md) are approved.

## Scenario and boundary findings

- A Canada follow-up may carry only validated request metadata and an explicit
  supported filter into a newly constructed request; it cannot filter a preview or
  bypass routing.
- `Why was this one selected?` is safe only with an explicit reference bound to the
  prior structured assessment and snapshot. The first scope must re-execute the
  validated request, verify the same snapshot identity/digest and resolve the
  reference; it stores no assessment rows. A pronoun alone requires clarification.
- A clarification reply may fill one pending validated field and then undergo fresh
  Step 18 routing. No stored plan or capability implementation is executable.
- Previous generated explanation text, arbitrary rows and full chat history are
  outside authoritative conversation state.
- Forecasting and Document Retrieval remain BLOCKED; conversation cannot grant new
  capability, infer currency or expand anomaly/Financial Core semantics.

The proposed first boundary is one local, in-memory, expiring interaction context
with allowlisted request/routing metadata, supported scope, snapshot-bound evidence
references and one pending clarification. Reset, cancellation, expiry and process
exit delete it. Persistence, external providers and cross-user state are excluded.

## Domain-modeling result

Scenario analysis preserved the glossary distinction between financial evidence,
documents, cash facts and statistical candidates. Conversation state and evidence
handles are application-interaction concepts, not newly resolved financial-domain
terms, so `CONTEXT.md` was not changed. This reversible readiness recommendation
does not fix a hard-to-reverse implementation decision, so no ADR was created.

## Validation and tests

No production or test code changed in Step 29, so no new runtime tests were added
or required. The latest completed regression remains the post-Step-28 result:
**316 passed, 0 failed, 0 errors, 0 skipped**. Final validation checks whitespace,
documentation paths, status/diff and consistency with the existing routing and
security contracts.

## Review

The parallel Standards and Spec reviews found no runtime implementation, evidence-
integrity, routing, blocked-capability, privacy or Phase 10 scope regression. Both
identified this section's pending review placeholder. The Spec review also found
that a digest/reference alone could not recover a prior assessment after the turn.
The readiness contract now explicitly requires deterministic re-execution against
the same authoritative snapshot, digest verification and fresh reference resolution;
otherwise the reference is stale and rejected. The Standards review's matching
design suggestion is therefore resolved. No production or test change followed.

## Files added or modified by Step 29

- `README.md`
- `docs/conversational_ux_readiness.md` (created)
- `docs/step29_validation.md` (created)

## Limitations

This assessment does not prove real-user demand, select exact expiry duration,
define a transport/authentication model, or authorize implementation. The current
CLI remains stateless. A future implementation needs its own approved contract,
TDD evidence, privacy/security review and regression run.
