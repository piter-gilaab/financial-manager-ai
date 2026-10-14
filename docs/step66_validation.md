# Step 66 validation — Conversational Dynamic Dataset Contract

## Status

**PASS.** The contract was reviewed against the implemented session, mediation,
Manager, onboarding registry, binder, adapter, Financial Core and grounding
seams before Step 67 implementation.

## Review result

The contract fixes all selection authority in code: an exact current registered
ID supplied by the user, a fresh current session selection, or an exact ID the
user supplies after a bounded choice prompt. It defines a 20-entry safe prompt
projection, rejects sole/first-entry/fuzzy/path/latest selection, and specifies
clarification whenever no explicit/current selection exists.

The session extension is limited to one dataset ID and one last closed operation,
in local memory only. Reset, expiry and cancel clear it; every execution
revalidates it. Stale or revoked state cannot remain implicit authority.

The operation catalog contains exactly the nine Phase 15 `SALES_RECORD`
operations. Parameters remain only `MONTH|YEAR` and `BUCKET|EXCLUDE` where the
existing binder already supports them. Readiness, currency and calculations stay
with the existing deterministic chain.

Grounding, security and privacy preserve the Phase 12 boundaries: the provider
sees bounded metadata/facts rather than datasets or registry artifacts, and its
output remains an enum proposal. Dynamic anomaly conversation is explicitly
deferred to Step 68; Forecasting and RAG remain blocked. Legacy conversation is
not made dependent on a dynamic selection.

## Implementation seams approved for Step 67 TDD

- public `FinancialManagerAgent` dataset catalog/resolution projection;
- public `FinancialManagerSession` selection and dynamic execution operations;
- `parse_intent` with a backward-compatible versioned closed schema;
- `ConversationMediator.handle` dispatch and deterministic ambiguity/fallback;
- existing grounding/presentation interfaces over unchanged Manager evidence.
