# Phase 12 — Step 41 validation

## Decision

**PASS_WITH_LIMITATIONS.** See the
[LLM mediation validation](llm_mediation_validation.md) for scenario coverage
and limitations.

## Tests

`tests/test_mediation_validation.py` adds 5 end-to-end tests:

1. scenarios A–N through `src.cli.main(["chat"])`, with network connect
   patched to fail;
2. O/P: provider unavailable, malformed response and ungrounded response;
3. Q/R: reset and expiry;
4. regression of `capabilities`/`plan`/`ask`/non-mediated `chat` without any
   LLM;
5. a real `python -m src.cli chat --llm-model …` subprocess under an audit hook:
   one loopback connect, no proxy, no retry, a clean fallback and no traceback.

The class teardown verifies that the `data/` and `notebooks/` SHA-256 hashes and
the application-file inventory are unchanged.

Focused Phase 12 command:

```sh
.venv/bin/python -B -m unittest tests.test_mediation_intent tests.test_mediation_input \
  tests.test_mediation_grounding tests.test_mediation_validation
```

**65 passed** (20 + 20 + 20 + 5).

Complete regression:

```sh
.venv/bin/python -B -m unittest discover -s tests
```

**439 passed, 0 failed, 0 errors, 0 skipped** in 480.1 seconds (Phase 11
baseline 374). `git diff --check` is clean.

## Final review

The final two-axis review subagents were cut off by an API rate limit, so the
final review was performed inline against the requested checklist. It covered:

- LLM → DB/shell/SQL/Python paths;
- capability and contract bypass;
- invented calculations and currency;
- stale state and hallucination exposure;
- prompt injection;
- network, secret and provider-error leakage;
- duplicated Core or anomaly logic;
- unbounded input and output;
- hidden persistence;
- the deterministic fallback.

One defect was reproduced: multiplicative comparisons written in words
(“o dobro”, “twice”, “3 vezes”) passed the guard. It was fixed with a
`derived_claim` rule and a test. Grep confirms that `src/mediation` has no
logging, file I/O, subprocess, sqlite, eval or dynamic import, and that its only
network I/O is the loopback POST.
