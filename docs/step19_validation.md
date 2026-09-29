# Phase 6 — Step 19 validation

Implemented only Security & Privacy Boundaries under the explicit Step 19
authorization. See [security/privacy policy](security_privacy_boundaries.md).
No later phase, authentication, production authorization or deployment work was
started. The pre-change baseline is commit
`d299da5c8079af6aab664e450e5d1bdc0b6b48cd`, with 229 passing tests and pre-existing
untracked project files retained.

## Changes and behavior

- Manager requests and delegated results now pass a small data-only check before
  serialization/copying. It rejects live handles, arbitrary objects/custom
  containers, cycles, nonfinite values and excessive nesting. Exact finite Decimal
  values remain supported in trusted result evidence without conversion.
- Capability lookup and natural-language inputs reject custom string objects
  before invoking hash/string/copy hooks. Only the existing registry selects
  implementations; explicit and automatic paths remain unchanged for plain data.
- Unlabelled providers now fail closed alongside PRIVATE/EXTERNAL/unknown
  locations. Provider invocation exceptions, including provider-raised domain
  errors, cannot inject private text into application errors or explanations.
- Snapshot read/verification and validation failures now emit controlled messages
  at their origin. The error codes and DATA_QUALITY_BLOCKER semantics are retained;
  the manager still preserves complete specialized evidence without redaction.
- Existing read-only query paths, local minimal provider request, copied evidence,
  UNKNOWN currency, blocked capabilities and no-network default remain intact.

No security framework, extra capability, external provider, credential, dependency,
financial algorithm, arbitrary execution interface or production write was added.

## Implementation method

Applied the locally available `implement` and `tdd` skills at the public manager
and provider interfaces specified in the task. New behavior was introduced in
vertical red→green slices. Recorded failures demonstrated snapshot path leakage,
provider-error injection, unlabelled provider failure, delegated object copy-hook
execution, custom request mapping execution and custom string execution before
their fixes. Additional tests cover existing protections and real integrations.

The initial currency assertion in a new integration test incorrectly assumed a
two-field envelope. It was corrected to inspect the actual approved currency
fields, including conversion_applied, while complete-envelope equality remained
required. No pre-existing tests or financial contracts were weakened.

Python syntax checks and `git diff --check` pass. No type checker is installed or
configured; none was installed, and syntax validation is not reported as static
type checking.

## Test results

Focused command:

```sh
.venv/bin/python -B -m unittest discover -s tests -p test_security_privacy.py -v
```

**18 passed, 0 failed, 0 errors, 0 skipped**, in **15.689 seconds**.

Full regression command:

```sh
.venv/bin/python -B -m unittest discover -s tests -v
```

| Suite | Passed | Failed | Errors | Skipped |
|---|---:|---:|---:|---:|
| Phase 3 database | 17 | 0 | 0 | 0 |
| Phase 4 financial tools | 37 | 0 | 0 | 0 |
| Phase 4 quality | 19 | 0 | 0 | 0 |
| Phase 4 currency/FX | 22 | 0 | 0 | 0 |
| Step 13 Financial Analysis Agent | 36 | 0 | 0 | 0 |
| Step 14 anomaly screening | 32 | 0 | 0 | 0 |
| Step 17 Main Financial Manager | 31 | 0 | 0 | 0 |
| Step 18 orchestration | 35 | 0 | 0 | 0 |
| Step 19 security/privacy | 18 | 0 | 0 | 0 |
| **Total** | **247** | **0** | **0** | **0** |

Full duration: **187.372 seconds**. All **229 previous tests remain unchanged
and pass**. Counts are unittest methods, not expanded subtests. No unavailable
business capability is represented by a skipped production test.

## Acceptance evidence

| Boundary | Verified outcome |
|---|---|
| Capability execution | Exactly the existing four entries; unknown names, module paths and executable strings do not become handlers |
| Automatic routing | Automatic output equals explicit facade output; existing Step 18 routing/delegation tests remain green |
| Arbitrary execution | Executable-shaped questions rejected; custom Python input/copy hooks rejected before invocation; default execution succeeds with shell entry points disabled |
| Database | SQL-shaped category is literal data and returns NO_DATA; production hashes unchanged; a live SQLite connection cannot leave a delegated response |
| Provider data | Request contains only question, dataset and 17 static metadata entries; no supplemental private filter, database handle or returned evidence is included |
| Provider location | PRIVATE, EXTERNAL, unlabelled and unrecognized providers cannot interpret a request |
| Provider authority | A changed tool proposal is rejected before Core execution; provider exception text cannot become an application explanation/error |
| Financial evidence | Actual partial Discounts retains all 53 unresolved placeholders, UNKNOWN currency and warnings; automatic and explicit responses are completely equal |
| Anomaly evidence | Actual Profit response and test-only exact Decimal/fence/lineage/candidate evidence survive unchanged |
| Explanation isolation | Mutating convenience explanations/warnings does not change nested evidence or original objects |
| Errors | Missing local snapshot yields controlled blocker without its temporary absolute path or OS exception details; unexpected development exceptions are not serialized |
| Malformed messages | Cycles, deep nesting, nonfinite values, invalid keys and live objects fail safely before delegation |
| Blocked capabilities | Forecast/RAG remain unavailable through explicit and automatic execution, without a handler/model/retrieval path |
| Offline default | Real analysis plus screening succeeds with socket creation disabled and without an external provider |
| Source integrity | No existing production data, manifest, cleaning artifact or database changes; fixtures remain test-only |

## Focused code review

The requested `code-review` skill is applied after passing focused/full tests,
with separate parallel Standards and Spec reviews focused on bypasses, arbitrary
execution, network/data paths, evidence mutation, sensitive disclosure and scope.
For these uncommitted changes the review uses the pinned baseline-to-working-tree
diff plus new files, rather than an empty baseline-to-HEAD comparison. The existing
untracked snapshot module is reviewed using its verified before/after error-handler
delta, not misrepresented as newly implemented query logic.

### Standards

**0 findings.** No documented-standard violation or actionable Fowler smell was
identified. The review confirmed one orchestrator, small concentrated validation,
source-level error control, public-interface tests and accurate descriptions of
trusted adapters versus sandboxing/egress enforcement.

### Spec

**0 confirmed findings.** Static execution, data-only request/result checks,
minimal provider context, disabled nonlocal providers, controlled error messages,
complete evidence preservation, blocked capabilities and scope limits conform to
Step 19. No boundary bypass, arbitrary execution path, accidental external data
flow, evidence mutation or new sensitive-error disclosure was found.

Both reviewers also inspected surrounding implementations; the Spec reviewer
independently reran the focused nested-provider-input test (1 passed). No review
fixes or additional affected-test reruns were required. Full-suite counts above
are from the completed regression run, not inferred from review or subtest counts.

## File and data preservation

The pre-edit inventory contains 85 existing files (Python cache files excluded).
77 remain unchanged; eight intentionally modified files are listed below. All
old tests, datasets, notebooks, historical manifests/cleaning outputs and production
database bytes remain unchanged. No file was added under data/.

Production database SHA-256 remains:
`8b9536867d7e1ee2e3fd8b0040d40f5806cf6ecb8afc38491cbc058de727c744`.

Created:

- `src/manager/security.py`
- `tests/test_security_privacy.py`
- `docs/security_privacy_boundaries.md`
- `docs/step19_validation.md`

Modified:

- `src/manager/agent.py`
- `src/manager/registry.py`
- `src/manager/routing.py`
- `src/agents/financial_analysis.py`
- `src/financial/snapshot.py` (pre-existing untracked module; only controlled-error handling changed)
- `docs/main_financial_manager_agent.md`
- `docs/orchestration.md`
- `README.md`

## Remaining limitations and next step

Trusted injected Python is not sandboxed; a LOCAL declaration cannot enforce OS
egress restrictions. Returned financial results remain sensitive caller-owned data,
not an authenticated/tamper-proof audit store. Caller-supplied secrets or legitimate
source values are not blanket-redacted. Unexpected development exceptions remain
available, and any future user interface needs controlled error presentation.

Authentication, accounts, RBAC, encryption-at-rest management, credential
infrastructure and production deployment security are outside this step. All
existing unknown-currency, missingness, placeholder, grain/provenance and screening
peer limitations persist. Forecasting and RAG remain BLOCKED and unimplemented.

The next recommended separately scoped work is the V1 CLI/reporting workflow and
end-to-end acceptance defined by the current planning direction. This report does
not invent a numbered next phase or authorize implementing that workflow. Step 19
is the stopping point.
