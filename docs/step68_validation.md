# Step 68 validation — Dynamic Anomaly Mediation and Candidate Follow-up

## Status

**PASS.** The existing Phase 16 Sales/Profit GLOBAL screens are available through the bounded
conversation seam without transferring dataset, statistical, readiness or classification authority
to the LLM.

## Implemented path

Mediation schema `1.2` adds `DYNAMIC_ANOMALY_SCREEN` with exactly
`SALES_ANOMALY_SCREEN|PROFIT_ANOMALY_SCREEN`. The session resolves an exact/current dataset under
the Step 66 rules and delegates a typed `DynamicAnomalyRequest` only through
`FinancialManagerAgent.execute_dataset_anomaly_request(...)`. Phase 16 recomputes readiness and
performs all Tukey-IQR work.

The existing session evidence slot, opaque handle factory, A1–A10 label layer and `follow_up(...)`
entrypoint are reused. A typed dynamic binding was required because Phase 16 lineage differs from
legacy database snapshot lineage; both binding types use the same context, labels, lifecycle and
fresh-evidence resolution mechanism. Dynamic handles bind the session, dataset, operation, measure,
candidate record, lineage digest and result digest.

`why_selected` and `record_detail` re-run the same typed Manager request and fail if current evidence
does not reproduce exactly. The bounded dynamic detail includes only the relevant observed measure,
source row reference, GLOBAL assessment/fences, policy, currency and applicable warnings. It does
not expose arbitrary rows or unrelated columns.

## Validated behavior

- selected-dataset and exact same-turn Sales/Profit screening pass;
- one or multiple catalog datasets without a selection require clarification; no sole/first entry
  is selected;
- unknown/invented dataset IDs and operations fail closed;
- insufficient sample, zero-IQR, missing Profit, multiple currency and stale source state block
  without substitution;
- `UNKNOWN` and `CONFIRMED` currency are preserved without inference or conversion;
- candidate summaries and A1 labels come from exact authoritative evidence;
- `why_selected` preserves the observed value, upper/lower tail, fence and policy evidence;
- `record_detail` is a bounded projection, not arbitrary row retrieval;
- invented, cross-session, cross-dataset, reset, cancel, expiry, replaced-result and stale handles
  do not resolve;
- arbitrary algorithms, peer screening, Discount anomaly and Units Sold anomaly are not in the
  schema;
- malformed/unavailable provider output executes nothing and does not redirect to legacy anomaly;
- response-provider fraud claims and invented numbers are rejected by the grounding guard and
  replaced by deterministic presentation;
- legacy anomaly and dynamic Financial Analysis regression suites retain their existing paths;
- Forecasting and Document Retrieval/RAG remain blocked.

## Security and privacy

Interpretation receives at most 20 opaque catalog entries with safe readiness metadata. It receives
no rows, financial values, paths, source files, mappings or registry artifacts. Response generation
receives bounded fact packets only. Handles and user/source text remain inert. No transcript,
telemetry, external provider, SQL, shell, subprocess, runtime code generation, untrusted attribute
lookup or request-selected adapter was added.

## Focused test record

The Step 68 focused module contains **22 passing tests**. The combined conversational/dynamic slice
through Step 69 contains **153 passing tests**. Complete-regression and final review results are
recorded in [Step 69 validation](step69_validation.md).
