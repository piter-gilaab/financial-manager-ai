# Phase 7 — Step 21 validation

Baseline: `0944aa8c6782bd111afa8bf01e3f5ca8df8285f7` (Step 20), **272 passing
tests**. Tracked diff was empty; pre-existing untracked project files were retained.
Scope is acceptance validation only. Step 22 was not started.

## Scenarios and method

The `tdd` skill was applied at the real CLI/output and data-integrity seams specified
by the user. Scenarios were added and run incrementally against existing behavior;
no intentional production break was introduced to manufacture a red test. One
new assertion initially used “require investigation” instead of the existing
“requiring investigation”; it was corrected to match the documented neutral
terminology. This was a test-authoring mismatch, not an integration defect.

The 19 acceptance tests cover registry discovery, plan without query execution,
both record counts, sales/accounting summaries, country/month grouping, department
missingness, Discounts placeholders, extreme-record lineage, RG and Profit
screening, separate multi-capability results/repeatability, no-data, blocked
forecast/retrieval, both clarification layers, unsupported semantics, executable
payload rejection, malformed input and missing-data error sanitization.

All application components are real. Only process/network/database observation
is instrumented at external boundaries. Expected evidence comes from approved
public Core/service interfaces, not a second financial implementation. See
[V1 acceptance](v1_acceptance.md) for acceptance decisions and limitations.

## Test results

```sh
.venv/bin/python -B -m unittest discover -s tests -p test_acceptance.py -v
.venv/bin/python -B -m unittest discover -s tests -v
```

Acceptance: **19 passed, 0 failed, 0 errors, 0 skipped** in **86.990 seconds**.
Full regression: **291 passed, 0 failed, 0 errors, 0 skipped** in **290.719 seconds**.

| Tests | Passed | Failed | Errors | Skipped |
|---|---:|---:|---:|---:|
| Existing Phase 3–7 baseline | 272 | 0 | 0 | 0 |
| New Step 21 acceptance | 19 | 0 | 0 | 0 |
| **Full suite** | **291** | **0** | **0** | **0** |

All 272 previous tests pass unchanged. Counts are unittest methods; subcases are
not counted separately. Blocked capabilities are tested outcomes, not skipped tests.

## Defects and review

No integration defect was found; no application code or previous test was changed.
After both suites passed, the `code-review` skill ran parallel Standards and Spec
reviews against the pinned Step 20 baseline. Because the three new files were
untracked, the review used their complete working-tree diff and current contents,
with the user's Step 21 request as specification.

- **Standards: 0 findings.** Public interfaces, separated responsibilities and
  test-only boundary instrumentation conform to AGENTS.md, ADR 0001 and TDD guidance.
- **Spec: 0 findings.** No integration gap, layer bypass, duplicated business logic,
  evidence mutation, blocked-capability leak, privacy regression or scope creep found.

Final V1 acceptance: **PASS**, within the existing documented capability/data limits.
No follow-up production fix or test weakening was necessary.

## Data integrity and files

Acceptance cleanup compares hashes of all existing files under `data/` and
`notebooks/`, detecting modifications, additions or removals. A pre-Step-21 SHA-256
inventory also covers 96 existing source/test/documentation/data/notebook files.
All **96 baseline files remain byte-for-byte unchanged**, including the **19 files
under data/notebooks**. The production database SHA-256 remains
`8b9536867d7e1ee2e3fd8b0040d40f5806cf6ecb8afc38491cbc058de727c744`.
No raw/processed dataset, cleaning manifest/output, schema or prior test was changed.
Python syntax/whitespace checks pass. No new dependency or type checker was installed.

Created:

- `tests/test_acceptance.py`
- `docs/v1_acceptance.md`
- `docs/step21_validation.md`

No existing file modified. No production fixture, dependency, capability, network
transport or later-phase work added. Remaining limits are recorded in the
acceptance document rather than treated as skipped tests or fabricated capabilities.
