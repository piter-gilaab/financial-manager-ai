# Conversational Dynamic Anomaly Contract

Status: approved implementation contract for Phase 17 Step 68.

## Scope and authority

Conversational dynamic anomaly execution is a language-facing route to the existing Phase 16
capability. It supports exactly `SALES_ANOMALY_SCREEN` and `PROFIT_ANOMALY_SCREEN`, both with
`GLOBAL` scope and the code-owned `tukey_iqr` policy version `1.0`. The mediator cannot choose a
measure outside those operation keys, a peer group, threshold, algorithm, adapter, source column,
formula, filter, or classification rule.

The authority chain is user language → validated closed intent → deterministic dataset resolution
→ current anomaly readiness → `FinancialManagerAgent.execute_dataset_anomaly_request(...)` →
dynamic anomaly adapter → Tukey-IQR engine → authoritative evidence → grounded response. The LLM
classifies language and may verbalize approved facts; it never calculates, classifies records, or
executes request text.

Discount and Units Sold anomaly screening, peer screening, arbitrary measures and arbitrary
algorithms are unsupported. Forecasting and Document Retrieval/RAG remain blocked.

## Dataset resolution and catalog

Step 66 selection rules remain unchanged:

1. an exact eligible `dataset_id` found by code in the current user turn;
2. the one current session selection after fresh revalidation;
3. an exact user choice following bounded clarification.

No first-dataset or sole-dataset fallback exists. A missing selection always requires
clarification, even when the bounded catalog contains one dataset. Unknown, malformed, path-shaped,
multiple, fuzzy, provider-invented, revoked or stale targets are rejected.

The interpretation prompt receives at most 20 catalog entries. Each contains only the opaque
dataset ID, approved domain, Financial Analysis state and supported operations, anomaly state and
currently supported anomaly operations. It contains no rows, values, samples, paths, filenames,
source columns, registry artifacts or full metadata. Readiness is recomputed by deterministic code
before every execution; catalog metadata does not grant execution authority.

## Structured intent

Mediation schema `1.2` adds the closed `DYNAMIC_ANOMALY_SCREEN` action. Its only executable field is
one of the two anomaly operation keys and, when explicitly present, an exact dataset ID already in
the bounded context. Schema `1.0` legacy intents and schema `1.1` dynamic Financial Analysis intents
remain accepted. The historical `DYNAMIC_ANOMALY_DEFERRED` clarification is accepted only in an
exact schema-1.1 compatibility payload; it is not advertised or accepted by current schema 1.2.
The existing `EVIDENCE_FOLLOWUP` action and its `why_selected` / `record_detail`
allowlist are reused for candidate follow-up; no second language-facing reference action is needed.

Malformed, unsafe, invented or unavailable provider output fails closed. With a dynamic target, a
provider failure does not redirect to a legacy dataset and does not execute screening.

## Session evidence and candidate references

The session retains at most one active anomaly evidence context. It is process-local,
session-scoped, non-persistent and never shared. Dynamic candidate handles reuse the existing
opaque A1–A10 conversational label mechanism and the existing `follow_up(...)` entrypoint. The UI
bound stays 10 even though Phase 16 evidence may contain up to 20 candidate references.

Each handle is candidate-only and binds to:

- session identity;
- exact dataset ID;
- exact anomaly operation and measure;
- canonical record ID;
- authenticated lineage digest;
- complete semantic evidence digest.

Handles are inert navigation tokens, not record identifiers accepted from the model. Only labels
issued for the current evidence are supplied to mediation. A new anomaly result replaces the old
evidence context. New Financial Analysis, new legacy request, dataset selection change, cancel,
reset and expiry clear it. Source, mapping, registry or readiness invalidation makes re-resolution
stale. Cross-session and cross-dataset reuse is impossible.

## Follow-up semantics

`why_selected` re-executes the same typed Manager request, verifies the current dataset, operation,
lineage and semantic evidence digest, and locates the same candidate-only canonical record. It may
explain the observed value, lower/upper fence, tail relationship and policy name/version. It cannot
explain the business cause or infer fraud, error, suspicion, manipulation, misconduct, illegality
or probability of wrongdoing.

`record_detail` is supported through the same fresh-evidence check. Its bounded projection contains
only the source row reference, relevant observed measure/value/status, global assessment and
reference fences, policy, currency, applicable quality warnings and evidence binding. It is not an
arbitrary row lookup and exposes no unrelated source columns.

## Readiness, currency and presentation

Blocked readiness returns the exact controlled Manager limitation. Sales is never substituted for
Profit or vice versa. Missing confirmed Profit is not derived. Insufficient numeric records,
zero-IQR, stale artifacts, incompatible currency and deterministic arithmetic failure remain
blocking conditions owned by Phase 16.

`UNKNOWN` keeps the source-denomination qualification, `CONFIRMED` preserves the approved ISO code,
and `CONFIRMED_MULTIPLE` blocks where the anomaly contract requires. No inference or FX conversion
is permitted.

Candidate counts, observed values, fences, signs and policy facts come only from authoritative
evidence. Code renders tables/lists and mandatory disclosures. Natural prose is checked by the
existing grounding guard. `CANDIDATE` always means statistical candidate for review and never a
fraud, error, suspicious transaction, business-risk conclusion or probability.

## Security, privacy and compatibility

Dataset IDs, labels, headers, cell values and user text remain inert. There is no `eval`, `exec`,
shell/subprocess execution, raw SQL, dynamic import, runtime code generation, untrusted `getattr`,
caller-selected adapter, telemetry or transcript persistence. Interpretation receives catalog
metadata only. Response generation receives bounded grounded facts, never the full dataset or full
anomaly records.

Legacy Financial Analysis, legacy anomaly screening and legacy A1–A10 follow-up semantics remain
unchanged. Direct Phase 14–16 Manager APIs remain unchanged.
