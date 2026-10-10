# Phase 13 — Step 43 validation

## Status

**PASS.** The Dynamic Data Onboarding contract is explicit before implementation.
No ingestion, profiling, mapping, registry, CLI or capability behavior was added
in Step 43.

## Decisions

- One deep `src/onboarding` module will hide file parsing, profiling, semantic
  proposal, decision/versioning, artifact persistence, registry projection and
  readiness rules.
- CSV and constrained formula-free XLSX are the initial local-file scope;
  SQLite, live databases, URLs, APIs and cloud sources are deferred.
- Versioned JSON manifests fit the current offline single-user system; the local
  onboarding root containing the artifact store and registry must be Git-ignored.
- `ACCOUNTING_TRANSACTION` and `SALES_RECORD` are current canonical mapping
  domains. Other named domains are recognized-only and non-executable.
- Semantic and execution readiness are separate. New datasets cannot become
  `READY` until an implemented deterministic capability adapter exists.
- The LLM may suggest only allowlisted roles from a bounded profile packet. It
  cannot approve critical meaning or capability availability.

## Domain-model checks

Concrete boundary cases are resolved explicitly:

- `VL_LIQ` may look decimal-like without being revenue, expense, cash or even a
  confirmed monetary amount;
- `TIPO` values `C`/`D` do not establish credit/debit meaning;
- `EMP` does not establish legal-entity scope;
- a `$`-formatted cell or country label does not establish currency;
- a sale is not a receipt, an obligation is not a payment, and accounting DR/CR
  is not cash direction;
- a payable-like schema can be recognized while its capability remains
  `BLOCKED_NOT_IMPLEMENTED`.

## Interfaces selected for behavior tests

Tests in Steps 44–50 will use the public `OnboardingManager`, the local
onboarding root supplied by the caller, the semantic-provider seam, and the CLI `dataset`
commands. Parser/profiler helpers are implementation details unless a safety
primitive has an independently meaningful public contract.

## Review

The required pre-Step-44 Standards/Spec review found one authority ambiguity:
the original status vocabulary did not explicitly prohibit a semantic provider
from returning `CONFIRMED`. The contract now limits provider output to
`SUGGESTED`/`UNKNOWN`; decisions and deterministic conflict detection own all
other statuses.

Three terminology/interface smells were also resolved before implementation:
provisional artifacts are now distinct from an admitted registry entry,
`Decisão semântica` is the umbrella over confirmation/correction/rejection, and
`OnboardingManager` is explicitly a thin facade over focused rule owners. The
review result after these corrections is **PASS**.
