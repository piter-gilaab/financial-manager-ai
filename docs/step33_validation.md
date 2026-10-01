# Phase 10 — Step 33 validation

## Decision

**PASS_WITH_LIMITATIONS.** Steps 31 and 32 form a coherent bounded conversational
feature through the local Python session API. The narrow explicit surface improves
the validated Step 29 gaps while preserving deterministic routing, evidence
authority, local privacy and blocked capabilities.

## Repository evidence and scope

Validation covered `FinancialManagerSession`, `FinancialManagerAgent`, Step 18
routing/registry behavior, Financial Analysis record count, AnomalyService
candidate evidence, snapshot metadata and the existing security/presentation
contracts. No Financial Core calculation, anomaly rule, dataset, database,
dependency, provider or CLI implementation changed.

The CLI integration decision is **Python API only for Phase 10**. The current CLI
is intentionally one-shot. A conversational shell would expand lifecycle and
presentation scope without improving the safety proof for the approved session
contract.

## End-to-end scenarios

`tests/test_conversational_ux.py` validates:

- capability-choice clarification followed by fresh screening routing;
- record-count dataset clarification followed by the exact result;
- invalid capability/tool/SQL/shell-shaped answers without execution or activity
  extension;
- an unrelated `new_request` replacing clarification state;
- cancellation and reset;
- 30-minute inactivity and four-hour absolute expiry;
- anomaly handle issuance and fresh authoritative follow-up detail;
- logical snapshot mismatch as `STALE_REFERENCE`;
- cross-session references as `UNKNOWN_REFERENCE`;
- Forecasting and Document Retrieval remaining blocked;
- “Just use sales” not becoming cash-flow execution;
- bounded replacement without history/handle disclosure; and
- no persistence, network or provider dependency in the bounded state flow.

## Authority, privacy and security result

Conversation state remains contextual. Reconstructed requests route afresh;
follow-ups re-execute and validate authoritative structured evidence. Prior prose
is never input. Logical snapshot equality uses approved provenance/digests and not
SQLite byte equality.

State is process-local, in-memory, redacted on inspection and bounded to one
interaction plus at most ten current evidence handles. Expiry/reset delete the
context. No chat-state file/database, telemetry, network, external provider,
arbitrary SQL/function path or blocked-capability handler exists.

## Focused tests

Command:

```sh
.venv/bin/python -B -m unittest tests.test_conversational_ux -v
```

After final-review additions, **7 passed, 0 failed, 0 errors, 0 skipped** in
**10.931 seconds**.

Combined conversational command:

```sh
.venv/bin/python -B -m unittest tests.test_conversation_session \
  tests.test_evidence_followups tests.test_conversational_ux -v
```

After final-review additions, **40 passed, 0 failed, 0 errors, 0 skipped** in
**28.378 seconds**.

Full pre-review regression:

```sh
.venv/bin/python -B -m unittest discover -s tests
```

**351 passed, 0 failed, 0 errors, 0 skipped** in **375.108 seconds**.

Full post-review regression:

```sh
.venv/bin/python -B -m unittest discover -s tests
```

**356 passed, 0 failed, 0 errors, 0 skipped** in **378.337 seconds**.

## Usability findings and limitations

The operations have distinct meanings and statuses, and state inspection is
useful without exposing evidence. The explicit handle/intent model avoids fragile
pronoun guessing. The tradeoff is a deliberately small vocabulary and a Python
caller requirement. General chat memory, implicit references, arbitrary
measure/filter/period completion, financial-record references, persistence,
multi-user isolation services, CLI chat, Forecasting and RAG remain unsupported.

## Final review

The initial final Standards review found two medium fail-closed defects: a
malformed stored handle member could raise before state invalidation, and malformed
nested metadata/quality could escape controlled evidence rejection. The initial
Spec review also found incomplete item/assessment shape validation, and three
test-coverage gaps: absolute evidence-handle expiry, exact evidence fidelity and
the successful-sales-to-unrelated-accounting context transition.

Public red tests reproduced the runtime defects. The implementation now validates
container/member types before stored-state access and validates nested metadata,
quality, warning indices, item scope/lineage, closed assessments, candidate values
and structured references before issuance or detail construction. Malformed fresh
evidence returns `STALE_REFERENCE`. The added scenarios assert no execution after
absolute expiry, exact fresh evidence equality and no inherited scope.

Final Standards and Spec re-reviews each report **zero remaining actionable
findings**. The post-review focused and full results above are green.

## Files introduced or updated by Step 33

- `tests/test_conversational_ux.py` (created)
- `docs/conversational_ux_validation.md` (created)
- `docs/step33_validation.md` (created)
- `docs/financial_manager_ai_guide.md`
- `README.md`
