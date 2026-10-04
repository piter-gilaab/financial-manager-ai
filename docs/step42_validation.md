# Phase 12B — Step 42 validation

## Scope and result

Step 42 hardens local-model response language and conversational quality without
changing financial authority, routing, query contracts, anomaly methods, session
semantics or capability availability. The implementation adds no dependency,
translation service or financial feature.

The response prompt now explicitly requires every sentence to use the grounded
packet language: Brazilian Portuguese for `pt-BR`, English for `en`. It describes
the model as a communication mediator and asks for a direct answer, relevant
evidence, material coverage/exclusions, and only relevant warnings or supported
next actions. It also discourages internal terminology and duplicated tables/lists.

## Deterministic enforcement

`validate_natural_response` retains the existing schema, numeric, currency,
anomaly-safety, capability and internal-metadata guards. In addition to checking
the declared `language` field, it now rejects prose dominated by common lexical
markers of the other supported language. The deliberately small heuristic targets
obvious mismatches only; it is not a general language classifier and does not
translate or repair model output.

Any mismatch follows the existing fail-closed path: no model text is displayed,
and the same authoritative outcome is rendered by the deterministic fallback.
Tables, lists, exact values, counts, warnings and evidence references continue to
come from code and structured evidence.

## Covered behavior

Deterministic tests cover:

- natural pt-BR and English responses;
- obvious English prose for `pt-BR` and Portuguese prose for `en`;
- fallback without leaking rejected model text;
- the real Profit screening request with 102 global candidates, 695/700 coverage
  and 5 exclusions, retaining statistical-candidate semantics;
- UNKNOWN currency without denomination inference;
- grounded sales-by-country prose plus evidence-rendered tables;
- provider failure, malformed/unsafe response fallback and deterministic
  `ScriptedProvider` behavior.

## Validation

- Focused grounding tests: `26 passed`.
- All `78` mediation test methods, including the added short-prose bypass
  regression, are included in the final full run.
- Full regression: `452 passed, 0 failed, 0 errors, 0 skipped` in 461.729 seconds.
  It ran outside the managed socket sandbox so the existing subprocess audit-hook
  test could create and immediately block its one loopback connection as designed.
- `git diff --check`: passed.

## Live Ollama smoke test

**NOT RUN.** The Ollama executable is installed, but no running Ollama process was
visible. This managed environment also blocks socket creation before the existing
real-process audit hook can observe a loopback connection. No live-model claim is
made by this validation record.

## Limitations

- The lexical guard intentionally accepts language-neutral prose when an obvious
  mismatch cannot be established; focused review added coverage for short, clearly
  English and clearly Portuguese financial prose.
- Correct-language prose can still contain a wrong non-numeric attribution; the
  authoritative evidence-rendered table/list remains the reference.
- Prompt compliance with `qwen2.5:7b-instruct` was not measured in this run.
