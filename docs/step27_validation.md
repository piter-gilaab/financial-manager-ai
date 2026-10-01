# Phase 9 — Step 27 validation

## Scope and presentation contract

Step 27 changes only the CLI human presentation layer. The default `ask` view is
concise; `--full` provides expanded human evidence; `--json` preserves the complete
manager response and existing exact serialization. `--full` and `--json` are
mutually exclusive. Capabilities, routing, Financial Core, anomaly calculations,
manager response schemas, data, and dependencies are unchanged.

Ordinary lists over 10 entries show the first 10 in authoritative order, with
returned, total, and omitted counts. Anomaly reference previews include the
references actually named by those displayed assessments, in authoritative
reference order, so their exact fences and peer information remain interpretable.
Long duplicate explanation text is capped at 2,000 characters with the omitted
character count disclosed. Exact duplicate warnings are displayed once with all
applicable step IDs; distinct warnings remain visible. Large lists inside warning
entries use the same disclosed preview.

The formatter builds display-only values. It does not mutate evidence, calculate
money, infer currency, reroute requests, issue SQL, recompute anomaly thresholds,
or change assessment classifications. Exact values, UNKNOWN currency, status,
counts, coverage, exclusions, warnings, lineage, and stable references remain
available in the preview where applicable and completely through `--json`.

## Validation

Seven initial Step 27 tests plus four review-driven tests were added at the CLI
and real-subprocess acceptance seams. They cover bounded lists and explanations;
count reconciliation; deterministic ordering; non-mutation; exact decimals;
UNKNOWN currency and structured terminology; anomaly statuses, lineage, linked
fences and peer references; warning deduplication, distinct-warning retention and
multi-step applicability; complete JSON equality; expanded `--full`; mutual mode
exclusion; blockers; clarification; and offline/security boundaries.

- Focused CLI/orchestration/acceptance run: **91 passed** in 129.082 seconds.
- Full regression: **310 passed, 0 failed, 0 errors, 0 skipped** in 313.317 seconds.
- Prior baseline: **299 passed, 0 failed, 0 errors, 0 skipped**.
- `git diff --check`: clean before the focused review; repeated in final checks.

Representative default outputs measured after final review fixes were about 29.5
KB for Profit screening, 31.9 KB for Receiver General screening, and 14.3 KB for a
Receiver General amount summary, down from the Step 25 full-human measurements.
Exact sizes depend on the authoritative warnings and referenced preview evidence.

## Focused code review

The required two-axis review used `HEAD` (`1aa7f44`) as the fixed point and
reviewed the uncommitted Step 27 working-tree diff plus new documentation.

The initial Standards and Spec reviews found two confirmed presentation-integrity
issues: deduplicated warnings lost multi-step applicability, and independently
previewed anomaly reference lists could omit peer fences required by displayed
assessments. Both were fixed with step references and linked reference selection,
then protected by red/green tests. A low-risk terminology heuristic was also
replaced with structured evidence checks. A final edge-case review required count
disclosure when more than 10 linked references are all returned; the renderer now
reports returned, total, and zero omitted, with a focused regression test.
The final follow-up reported **zero remaining Standards findings and zero remaining
Spec findings**.

## Files created or modified

- `README.md`
- `docs/cli_workflow.md`
- `docs/concise_cli_presentation.md` (created)
- `docs/financial_manager_ai_guide.md`
- `docs/step27_validation.md` (created)
- `src/cli/formatting.py`
- `src/cli/main.py`
- `tests/test_acceptance.py`
- `tests/test_cli.py`

Pre-existing untracked governance and data artifacts were not changed.

## Remaining limitations

- Concise mode is a fixed deterministic preview, not pagination.
- It does not invent a candidate-only or financial-value ranking; therefore the
  first 10 assessment rows may not include every assessment status.
- `--full` and `--json` remain potentially large and contain sensitive local data.
- Explanation text is a bounded convenience view; complete structured evidence is
  authoritative, and expanded text remains available with `--full`.
- Request language remains the existing bounded, stateless English grammar.

Step 28 and Step 29 were not started. The next recommended step is Phase 9 — Step
28: Presentation / Reporting Validation.
