# Phase 10 — Step 32 validation

## Scope and implementation

Step 32 extends the local Python session with explicit `follow_up` and one
`ANOMALY_RECORD` reference type. It issues at most ten opaque handles for candidate
records from one current anomaly result. State retains only request identity,
logical snapshot/digest and lineage identifiers; resolution re-routes and
re-executes through the existing manager/service.

No Financial Analysis reference was added because the current result families do
not share one safely exposed record-reference contract. No CLI, persistence,
provider, capability, financial calculation, anomaly algorithm, dataset or
dependency changed. Step 33 was not started before this gate.

## Focused results

Step 32 command:

```sh
.venv/bin/python -B -m unittest tests.test_evidence_followups -v
```

After review fixes, **12 passed, 0 failed, 0 errors, 0 skipped** in **14.225
seconds**.

Steps 31+32 command:

```sh
.venv/bin/python -B -m unittest tests.test_conversation_session tests.test_evidence_followups -v
```

After review fixes, **29 passed, 0 failed, 0 errors, 0 skipped** in **17.941
seconds**.

## Covered behavior

Tests verify bounded opaque handle issuance, exact session membership, unknown and
modified handles, cross-session rejection, reset/expiry invalidation, unsupported
intent rejection, offline execution, blocked-capability context replacement,
logical snapshot comparison, acceptance of different SQLite bytes for an
equivalent logical rebuild, changed logical snapshot rejection, capability loss as
stale, fresh deterministic re-execution, prior-prose isolation, exact anomaly
status/value/fence/peer/lineage/warnings and screening-only terminology.

## Full regression

Command:

```sh
.venv/bin/python -B -m unittest discover -s tests
```

The pre-review run passed **343 tests** in **368.417 seconds**. After review
fixes, **345 passed, 0 failed, 0 errors, 0 skipped** in **369.281 seconds**.

## Focused code review

The initial two-axis review found three medium issues: inspection exposed opaque
handles, state accepted unbounded/non-digest provenance strings, and issuance did
not fully validate item/reference structure. TDD regressions reproduced each
boundary. The implementation now redacts handles from `status()`, validates exact
SHA-256/run/record forms and rejects malformed or unresolvable structured
evidence before it enters state. Both Standards and Spec re-reviews report zero
remaining findings.

## Files created or modified at this gate

- `src/manager/session.py`
- `tests/test_evidence_followups.py` (created)
- `docs/evidence_reference_followups.md` (created)
- `docs/step32_validation.md` (created)

Step 31 files remain part of the uncommitted Phase 10 working tree. Pre-existing
unrelated untracked files and data were not changed.

## Gate decision

**PASS.** Focused, combined and full regression gates are green; confirmed review
findings are fixed. Step 33 may begin.
