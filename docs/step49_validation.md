# Phase 13 — Step 49 validation

## Status

**PASS.** Capability discovery is deterministic and keeps semantic, policy and
execution readiness separate. It never calls an LLM.

## Rules

- Financial Analysis can be semantically ready for approved
  `SALES_RECORD`/`ACCOUNTING_TRANSACTION` date and measure roles. It remains
  `BLOCKED_NOT_IMPLEMENTED` without a validated generic execution adapter.
- Anomaly Detection additionally requires at least 30 valid values for a
  confirmed supported measure and an approved domain/measure screening policy.
  Existing fixed policies are not generalized to arbitrary onboarded fields.
- Cash Flow Forecasting retains actual-settled-cash, target, perimeter,
  calendar/completeness, currency, history and evaluation gates. Sales,
  accounting DR/CR and payables do not meet them; no model exists.
- Document Retrieval remains blocked because a tabular file is not an approved
  financial-document corpus and no retrieval execution path exists.
- Recognized `PAYABLE` does not create an Accounts Payable capability.

No adapter or policy injection seam exists in Phase 13. `AVAILABLE` would require
future separately authorized integration with a validated deterministic execution
path; it is impossible for newly onboarded datasets in the current implementation.
A recorded all-blocked report advances a registered entry to truthful
lifecycle/readiness state `BLOCKED`, not `READY`.

The existing Financial Manager catalog is unchanged: Financial Analysis and
Anomaly Detection remain available for the two development datasets, while
Forecasting and Document Retrieval remain blocked.

## Focused tests

`python -m unittest tests.test_onboarding_readiness tests.test_onboarding_registry tests.test_onboarding_confirmation tests.test_onboarding_semantics tests.test_onboarding_profiling tests.test_onboarding_ingestion`

Result: **39 passed**. Tests cover semantic-versus-execution readiness,
screening policy isolation, sales/cash and tabular/RAG boundaries, recognized
payables, registry readiness versioning and the unchanged manager catalog.
