# Phase 11 — Step 36 validation

## Decision

**PASS_WITH_LIMITATIONS.** The conversational CLI is a correct bounded local
workflow over `FinancialManagerSession` and the existing deterministic manager
architecture. No product defect was reproduced, no production implementation was
changed and no later phase was started.

## Baseline and scope

The actual pre-Step 36 baseline was measured from commit `52859da`:

```sh
.venv/bin/python -B -m unittest discover -s tests
```

**369 passed, 0 failed, 0 errors, 0 skipped** in **395.854 seconds**.

The only pre-existing uncommitted items were the user's `.gitignore` edit and
untracked `AGENTS.md`; Step 36 leaves both untouched. Validation added only tests
and documentation—no routing, session, manager, financial or anomaly production
code.

## End-to-end scenarios

`tests/test_conversational_cli_validation.py` adds five integration scenarios:

1. real-process startup/help, Financial Analysis, both approved clarification
   classes, invalid answer, new-request replacement, cancel, redacted status,
   reset and exit;
2. real-process Profit screening, bounded concise evidence, live follow-up,
   changed/reset/cross-process references and exact structured detail;
3. blocked Forecasting/RAG, unrelated request isolation, allowlisted commands and
   SQL/shell/import/tool/capability-shaped input under network/process audit hooks;
4. real `/exit`, EOF and Ctrl+C signal handling without traceback; and
5. four-hour absolute expiry despite successful activity every twenty minutes.

These tests deliberately reuse the existing Phase 10 session suites for exact
timestamp non-extension, session identity rotation, logical snapshot/digest
matching, stale/cross-session evidence, explanation poisoning, bounded state and
inactivity expiry. They validate behavior through public CLI/session seams rather
than private helpers or duplicated calculations.

## Security, privacy and integrity

The test process audit hook records and rejects socket, subprocess, shell and
OS-exec events; no prohibited event occurred. Status remains redacted and no
arbitrary identifier becomes authority. Application-file inventory and SHA-256
hashes of `data/` and `notebooks/` are unchanged after all new scenarios. No
application-controlled chat history, session file, telemetry or database appeared.

## Defects

No product defect was found or fixed, so the `diagnosing-bugs` skill was not used.
Validation-harness review found that two interactive subprocess paths could block
indefinitely and did not share the process/network audit guard. A common helper
now applies the guard, enforces bounded reads and communication, and centralizes
teardown. An earlier test-harness `ResourceWarning` was also removed by closing
subprocess streams. Neither issue affected application behavior.

## Tests

Focused Phase 11 command:

```sh
.venv/bin/python -B -m unittest tests.test_conversation_session \
  tests.test_evidence_followups tests.test_conversational_ux \
  tests.test_conversational_cli tests.test_conversational_cli_validation
```

**58 passed, 0 failed, 0 errors, 0 skipped** in **56.036 seconds**.

Complete post-validation regression:

```sh
.venv/bin/python -B -m unittest discover -s tests
```

**374 passed, 0 failed, 0 errors, 0 skipped** in **407.771 seconds**.

## Final review

The focused Phase 11 Spec review found no actionable gap in the requested
coverage or claims. The Standards review found the two validation-harness issues
described above; both were corrected before the final focused and complete test
runs. No actionable Standards or Spec finding remains.

The review explicitly checked duplicate routing, session bypass, stale
clarification/evidence, explanation-as-evidence, capability bypass,
blocked-capability leakage, execution paths, sensitive errors, persistence,
unbounded state, privacy, evidence mutation and scope expansion.

## Limitations

The bounded limitations in the Step 34 contract remain intentional: no general
memory, implicit continuation, arbitrary evidence IDs, persistent/cross-process
session, external provider, Forecasting, RAG, API or frontend. Consequently the
status is PASS_WITH_LIMITATIONS rather than a claim of unrestricted conversation.
