# V2 Phase 3 — Application Layer Execution

Status: **IMPLEMENTED**.

The transport-neutral seam is `src/application/` and contains three modules:

- `DatasetApplication` delegates safe ingestion, profiles, semantic decisions,
  registry state and current readiness to `OnboardingManager`.
- `AnalysisApplication` builds only closed typed requests and delegates financial
  and anomaly execution to `FinancialManagerAgent`.
- `ConversationApplication` owns the process-local session map and delegates all
  lifecycle, mediation, clarification and evidence-reference behavior to
  `FinancialManagerSession` and `ConversationMediator`.

Commands and projections are explicit frozen dataclasses/enums in
`src/application/models.py`. Application modules import no FastAPI/Pydantic or
HTTP types. They contain no financial arithmetic, semantic inference, currency
inference, readiness rules, SQL generation or anomaly calculation.

Upload accepts bounded bytes for direct callers or a server-owned staged file
for streaming transports. It rejects path-shaped names, invokes the existing
onboarding pipeline and removes the transport file in a guaranteed cleanup
path. Accepted source bytes are copied into existing onboarding ownership before
cleanup; no client-supplied filesystem path enters this seam.

Direct application tests verify delegation, exact Decimal preservation,
blocked/unsupported outcomes, safe projections and isolated session lifecycle.

