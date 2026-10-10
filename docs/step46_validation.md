# Phase 13 — Step 46 validation

## Status

**PASS.** Semantic mapping produces hypotheses from a closed ontology and cannot
establish authoritative meaning.

## Suggestion behavior

- Approved normalized aliases plus compatible structural observations yield
  evidence categories (`HIGH`, `MEDIUM`, `LOW`), not probabilities.
- Every new-dataset association remains `SUGGESTED`, `UNKNOWN` or a
  deterministically detected `CONFLICT`; all suggestions require confirmation.
- The provider may return only `SUGGESTED`/`UNKNOWN`. Claims of `CONFIRMED`,
  `REJECTED` or `CONFLICT`, unknown fields/roles, executable-shaped rationale,
  malformed JSON and duplicate column responses invalidate the complete provider
  result.
- Provider failure retains deterministic suggestions and leaves other columns
  `UNKNOWN`.

## Prompt boundary

The prompt was reviewed with `llm-prompt-optimizer` and organized as Role,
Situation, Constraints, Instructions and Task. System rules explicitly classify
column names, sheet names, patterns and samples as untrusted JSON data. The local
provider receives only shape, byte-truncated column names, structural summaries
and byte-truncated non-sensitive examples—never rows or the full file. The total
Unicode packet is bounded below the local provider request ceiling. Output is constrained by a
strict JSON Schema and then independently validated.

## Domain boundary

`SALES_RECORD`, `ACCOUNTING_TRANSACTION` and `PAYABLE` may be suggested from a
bounded combination of proposed roles. A domain suggestion is not approval,
registration, capability readiness or financial execution.

## Focused tests

`python -m unittest tests.test_onboarding_semantics tests.test_onboarding_profiling tests.test_onboarding_ingestion`

Result after implementation: **19 passed** before the final executable-text
case was added; the cumulative focused suite is rerun in Step 47 and later.
