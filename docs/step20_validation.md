# Phase 7 — Step 20 validation

Scope: V1 CLI / User Workflow only. The starting point was
`5bf017c16e6236fc8db0100784bb35c3b98d441c`, with 247 passing tests.
Existing partial CLI work was continued, not replaced. Pre-existing untracked
project files were retained. Steps 21 and 22 were not started.

## Implementation and boundaries

- Standard-library `argparse` entry point: `python -m src.cli`.
- `ask`, `plan` and `capabilities` call only the corresponding public manager
  methods. The CLI adds no capability registry, routing, query or financial logic.
- Human output retains evidence, warnings, UNKNOWN currency and screening terms;
  `--json` returns the complete application structure, with exact Decimal strings.
- Exit codes: 0 for delivered application outcomes/help, 2 for CLI syntax,
  1 for cancellation or unexpected invocation/serialization/output failure. Error text is fixed;
  no exception body, traceback or raw syntax argument is displayed.
- Step 19 data-only validation is reused for JSON serialization. Terminal controls
  are escaped for human display. Forecasting/RAG remain BLOCKED.
- No dependency installation, external provider, network/telemetry, new algorithm,
  schema change, source-data write, API/frontend or persistent chat was added.

See [CLI workflow](cli_workflow.md) for commands, exit policy and limitations.

## Test method and results

The requested `implement` and `tdd` skills were applied at the task's public CLI
and presentation seams. Vertical red→green checks introduced delegation, safe
parsing, exact JSON, controlled errors, terminal escaping and the module entry
point. A closed output pipe initially caused Python's shutdown traceback/exit 120;
the module now closes the output safely and returns 1. Help-output failure also
received a failing test before inclusion in the controlled exception boundary.

```sh
.venv/bin/python -B -m unittest discover -s tests -p test_cli.py -v
.venv/bin/python -B -m unittest discover -s tests -v
```

Focused: **25 passed, 0 failed, 0 errors, 0 skipped** (8.221 seconds).
Final full regression after the review fix: **272 passed, 0 failed, 0 errors,
0 skipped** (193.993 seconds). The initial full run also passed (271 tests),
before the additional cancellation regression test.

| Suite | Passed | Failed | Errors | Skipped |
|---|---:|---:|---:|---:|
| Phase 3 database | 17 | 0 | 0 | 0 |
| Phase 4 financial tools / quality / currency-FX | 78 | 0 | 0 | 0 |
| Step 13 analysis agent | 36 | 0 | 0 | 0 |
| Step 14 screening | 32 | 0 | 0 | 0 |
| Step 17 manager | 31 | 0 | 0 | 0 |
| Step 18 orchestration | 35 | 0 | 0 | 0 |
| Step 19 security/privacy | 18 | 0 | 0 | 0 |
| Step 20 CLI | 25 | 0 | 0 | 0 |
| **Total** | **272** | **0** | **0** | **0** |

All **247 previous tests pass unchanged**. Counts are unittest methods, not
expanded subtests. No blocked capability is represented by a skipped test.

Coverage includes registry-derived capability status, unchanged question
delegation, plan without financial execution, actual partial Discounts and Profit
screening, complete JSON equality, exact Decimal/lineage/fence/coverage retention,
human warnings, safe syntax/invocation/snapshot errors, blocked and clarification
outcomes, SQL rejection owned by the manager, offline operation, source-file
hashes, module help and closed-pipe behavior. Fixtures remain test-only.

## Final code review

The `implement` skill's required `code-review` ran Standards and Spec reviews
in parallel against the recorded Step 19 baseline, including the untracked new
files. The user-provided Step 20 specification was the review source.

### Standards

No confirmed violations or actionable code smells. Delegation, public-interface
tests and separation of calculations from presentation follow AGENTS.md, ADR 0001
and the Step 19 boundary documentation. **0 findings.**

### Spec

One confirmed finding: Ctrl-C raised KeyboardInterrupt beyond the ordinary
Exception handler, exposing a traceback and source path. A failing CLI test
reproduced it; an explicit cancellation handler now returns 1 with fixed text.
The reviewer rechecked the fix in human/JSON modes and the documented policy.
**1 finding fixed; 0 remaining findings.** No scope creep was identified.

## Integrity and files

SHA-256 comparison of the 89 pre-existing source/test/documentation/data/notebook
files captured before Step 20 shows only the intended README change. Existing
tests and Phase 3–6 implementation files remain unchanged. Production database
SHA-256 remains
`8b9536867d7e1ee2e3fd8b0040d40f5806cf6ecb8afc38491cbc058de727c744`.
Raw/processed data, historical cleaning outputs and manifests are unchanged.

Python AST syntax checks and `git diff --check` pass. No type checker is configured
or installed; none was added, and syntax validation is not static type checking.

Created:

- `src/cli/__init__.py`
- `src/cli/__main__.py`
- `src/cli/main.py`
- `src/cli/formatting.py`
- `tests/test_cli.py`
- `docs/cli_workflow.md`
- `docs/step20_validation.md`

Modified: `README.md` (launch examples and Step 20 links).

## Remaining limits

The inherited bounded English grammar, dataset semantics, unresolved currency,
missing values/placeholders and screening peer limits remain unchanged. Forecasting
and document retrieval have no executable implementation. The CLI is one command
per process, with no paging or installed console script; full screening output can
be large. Sensitive questions/results require local terminal, file and shell-history
care. No authentication, OS sandbox, deployment security or blanket content redactor
is claimed. Next: Step 21 End-to-End Acceptance Tests, under separate authorization.
