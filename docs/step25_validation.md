# Phase 8 — Step 25 validation

**User-evaluation status: PASS_WITH_LIMITATIONS.** The supported V1 scenarios
preserved authoritative evidence and limitations, while complete human output is
too large for comfortable interactive use.

## Evaluation performed

The fixed point was Step 24 commit `8952735`. Before evaluation, the requested
architecture, workflow, readiness, security, implementation, tests, Git status,
and Git diff were inspected. Pre-existing untracked governance and local data
artifacts were left untouched.

Twenty-seven realistic scenarios were run through real `python -m src.cli plan`
and `ask` subprocesses in human and JSON modes:

- 9 Financial Analysis requests;
- 4 anomaly-screening requests;
- 3 ambiguous requests;
- 6 unsupported requests;
- 2 forecasting requests;
- 2 document-retrieval requests;
- 1 multi-capability request.

An audit hook denied socket, shell, and child-process operations. JSON parsing
rejected floating point tokens. Executed results were compared with direct Core or
anomaly-service calls, and data hashes were unchanged. The full scenario record is
in [user evaluation](user_evaluation.md).

## Defects fixed

`src/manager/routing.py` received only bounded surface-language corrections:

- normalize leading `Analyze` like the existing `Summarize` alias;
- accept `unusual <measure> values` and `Are there outliers in <measure>?` for the
  three already approved screening targets;
- recognize a “what/how will ... cash flow/balance/inflow/outflow ...” request as
  the already registered, blocked cash-flow forecasting capability.

No financial contract, calculation, evidence, schema, service configuration, or
availability state changed. Five focused phrase cases were added across four
orchestration test methods, including a near-miss that keeps unrelated bare-cash
phrasing out of forecasting. Red failures were observed before implementation;
the focused tests passed after the changes.

## Results and limitations

All executed supported scenarios matched their specialized results exactly.
UNKNOWN currency, placeholder exclusions, coverage, warnings, screening
abstentions, thresholds, and lineage remained visible. Ambiguous requests did not
execute. Unsupported meanings did not fabricate answers. Forecasting and retrieval
remained BLOCKED. Multi-capability results remained ordered and separate.

The main non-blocking usability finding is terminal volume: representative human
responses ranged from about 15 KB for a sales summary to 12.7 MB for accounting
screening. The current full-evidence display also repeats warning material across
nested response levels and exposes technical identifiers. A concise human view was
not introduced because its evidence-selection contract needs separate design and
the complete current JSON/human evidence must not be weakened casually.

“Show unusually high accounting records” continues to request clarification
because “records” does not identify an approved numeric screening measure. The
clarification names the three supported targets and no guess is made.

## Tests

- Focused routing tests: 4 methods passed, including 5 new phrase cases.
- Full regression: **299 passed, 0 failed, 0 errors, 0 skipped** in 297.416 seconds.

## Code review

The required two-axis review compared `8952735...HEAD`. The Standards axis found
two issues: the technical guide still described an old clarification outcome, and
the new future-tense regex accepted bare `cash` too broadly. The Spec axis found
that this section still contained a placeholder instead of the review result.

The guide and orchestration grammar now match the implementation. The regex now
requires an approved cash forecast target, with a red/green near-miss test. This
section records the review outcome. The final follow-up found no remaining
standards or specification issue. Reviewers found no evidence alteration,
duplicated business logic, misleading anomaly language, warning suppression,
blocked-capability execution, security/privacy regression, or scope expansion.

## Files changed

- `README.md`
- `docs/financial_manager_ai_guide.md`
- `docs/orchestration.md`
- `docs/user_evaluation.md`
- `docs/step25_validation.md`
- `src/manager/routing.py`
- `tests/test_orchestration.py`

Step 26 was not started.
