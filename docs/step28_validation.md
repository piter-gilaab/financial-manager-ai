# Phase 9 — Step 28 validation

## Scope

Step 28 validated the Step 27 presentation contract through real CLI subprocesses
and direct authoritative manager comparisons. It added no business capability,
response schema, dependency, provider, dataset, financial calculation, anomaly
algorithm or routing behavior.

## Defect found and fixed

Concise Financial Analysis output still repeated templated `Quality warning:` and
`Quality flags:` explanation lines before the dedicated warning section. A failing
CLI-boundary test demonstrated the duplication. `src/cli/formatting.py` now removes
only those deterministic explanation lines in concise mode. All warnings remain in
the dedicated section with their codes, messages, scope, affected counts and step
references. Expanded `--full` explanations and exact JSON are unchanged.

An initial warning validation assertion also counted a quality-flag reason as a
duplicate warning. That was a test interpretation error, not a product defect; the
test was corrected to inspect the dedicated warning section.

## Validation results

The representative set covers financial summaries, grouping, PARTIAL evidence,
screening, both blocked capabilities, clarification, unsupported intent and a
multi-capability result. It verifies bounded size, deterministic order, reconciled
omission counts, warning retention/deduplication, UNKNOWN currency, screening
terminology, exact JSON equality, no JSON floats, expanded human evidence and
mutually exclusive format flags. Detailed scenario and size evidence is recorded
in [presentation validation](presentation_validation.md).

- Focused Step 28 tests: **6 passed, 0 failed, 0 errors, 0 skipped** in 61.994 seconds.
- Full regression after the fix: **316 passed, 0 failed, 0 errors, 0 skipped** in 353.899 seconds.
- Previous validated baseline: **310 passed, 0 failed, 0 errors, 0 skipped**.

## Focused code review

The parallel Standards and Spec reviews passed. They found no evidence mutation,
hidden calculation, misleading omission accounting, warning loss, JSON regression,
unstable preview ordering, routing duplication or security/privacy expansion. They
also confirmed that the concise explanation filter removes only deterministic
warning/flag text that remains available from structured quality evidence. The only
required finding was to replace the pending review placeholder with this completed
result; no production or test correction followed from review.

## Files added or modified by Step 28

- `docs/presentation_validation.md` (created)
- `docs/step28_validation.md` (created)
- `src/cli/formatting.py`
- `tests/test_cli.py`
- `tests/test_presentation_validation.py` (created)

README links are updated with the completed validation documentation. Existing
Step 27 files remain part of the current uncommitted working tree.

## Remaining limitations

The concise CLI remains a fixed technical preview rather than pagination or a
candidate-only report. Full/JSON output remains intentionally complete, large and
sensitive. The CLI remains stateless and uses the existing bounded-English grammar.

Step 29 had not begun when this validation gate completed. No Phase 10 work began.
