# Phase 10 — Step 31 validation

## Scope

Step 31 adds only the local Python `FinancialManagerSession` clarification seam,
its public export, behavior tests and documentation. Financial Core, anomaly
algorithms, Step 18 routing, the capability registry, CLI, data, dependencies and
provider policy remain unchanged. Step 32 was not started before this gate.

## Implemented behavior

- One versioned, bounded in-memory session with injected clock and identifier
  factory for deterministic tests.
- Frozen typed state with stored schema version and exact validation before reads
  and replacements; expired records are deleted rather than marked in-state.
- Explicit `new_request`, `answer`, `cancel`, `reset` and `status` operations.
- Thirty-minute inactivity expiry and four-hour absolute expiry.
- Closed `CAPABILITY_CHOICE` and `FINANCIAL_RECORD_COUNT` descriptors only.
- Fresh `FinancialManagerAgent.ask` routing for every accepted reconstruction.
- Invalid answers preserve state, execute nothing and do not update activity.
- Expiry, cancellation, reset, new-request replacement, defensive inspection and
  session-instance isolation.
- Monotonic clock enforcement and rejection of non-string request objects without
  invoking custom string hooks.
- No raw question, history, result, explanation, database object or executable
  capability reference in state.

An accepted capability choice may correctly lead to another unretained
clarification because the session does not invent a dataset or measure. A record
count dataset answer produces a complete canonical request and the ordinary
Financial Analysis/Core result.

## Test results

Focused command:

```sh
.venv/bin/python -B -m unittest tests.test_conversation_session -v
```

**17 passed, 0 failed, 0 errors, 0 skipped** in **3.347 seconds** after review
fixes. The pre-review focused run passed 15 tests in 3.317 seconds.

Full regression command:

```sh
.venv/bin/python -B -m unittest discover -s tests -v
```

The pre-review run passed **331 tests, 0 failed, 0 errors, 0 skipped** in **358.213
seconds**. After the two review-driven regression tests and fixes, the required
post-review run passed **333 tests, 0 failed, 0 errors, 0 skipped** in **352.489
seconds**. All 316 pre-Step-31 tests remain passing. Production data was not
modified.

## Security/privacy evidence

Tests cover invalid and arbitrary-object answers/requests, exact allowlisted choices,
fresh manager calls, blocked Forecasting/RAG, unsupported clarification types,
defensive status copies, invalid identity/clock configuration, session isolation,
offline socket denial, expiry, clock rollback, atomic failure behavior and absence
of chat-history accumulation.

## Focused code review

The initial Standards review found four confirmed issues: a non-string request
could reach a custom `strip` method during state capture; state was not a stored,
validated typed/versioned record; expiry retained a second `_expired` source of
truth; and clock rollback was unchecked. The Spec review independently confirmed
the state-version/read-validation and monotonic-clock gaps.

Public red tests reproduced the custom-hook and clock defects. The implementation
now uses frozen/slotted typed records, stores and checks schema version `1.0`,
validates the exact closed clarification/lifecycle shape before reads and
replacements, deletes expired/invalid state, and rejects backward time. The final
Standards and Spec re-reviews each reported **zero remaining findings**. The
post-fix focused and full results above are green.

## Files created or modified at this gate

- `src/manager/session.py` (created)
- `src/manager/__init__.py`
- `tests/test_conversation_session.py` (created)
- `docs/clarification_continuation.md` (created)
- `docs/step31_validation.md` (created)

Pre-existing unrelated untracked files and data were not changed.

## Gate decision

**PASS.** Step 31 is implemented, reviewed and fully green. Step 32 may begin.
