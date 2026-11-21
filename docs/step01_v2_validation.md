# Step 01 Validation — V2 Product Scope & Non-Goals

Status: **PASS — CONTRACT ONLY**.

## Repository evidence reviewed

- `main` and tag `v1.0.0` point to `94be7b4`; no tracked baseline change was
  present before Phase 1 documentation.
- The final V1 baseline is 720 passed, 0 failed, 0 errors and 0 skipped.
- V1 has exactly one generic executable onboarding domain, `SALES_RECORD`, with
  nine Financial Analysis and two anomaly operations.
- The onboarding ontology already recognizes the eight frozen V1 domains, while
  code and V1 scope explicitly state that recognition is not execution.
- V1 is local, single-user and CLI-first; API/frontend/SaaS were deferred rather
  than partially implemented.

## Decisions frozen

1. V2 is a local-first multi-domain financial analysis platform; “platform” does
   not imply SaaS.
2. Mandatory generic executable domains are exactly `SALES_RECORD`, `PAYABLE`,
   `RECEIVABLE` and `CASH_TRANSACTION`.
3. `ACCOUNTING_TRANSACTION`, `BUDGET_RECORD`, `BALANCE_RECORD` and
   `DOCUMENT_METADATA` remain recognized and deferred.
4. The required surfaces are structured Manager/onboarding interfaces, compatible
   CLI, application/API, web workspace and bounded conversation.
5. Deterministic modules retain authority; LLM, Manager, API and frontend do not
   gain calculation or semantic authority.
6. The mandatory roadmap has exactly five phases.
7. Forecasting, RAG and the complete enumerated non-goal set remain outside V2.
8. PostgreSQL is not a roadmap assumption; it requires a reproduced blocker and
   separate approval.

## Contradictions resolved

- Historical V1 documents describe API, frontend and additional domains as
  future/unapproved. The user's explicit Phase 1 authorization supersedes that
  planning restriction only for architecture and contracts; no V2 production
  capability is implemented here.
- Earlier planning mentioned six broad capabilities. The final V1 repository and
  the new V2 five-phase scope take precedence; Forecasting and RAG are not made
  mandatory V2 work.
- Legacy Receiver General/Company Financials are not relabeled as onboarding
  domains, avoiding a false universal financial grain.

## Scope review

- No extra mandatory phase was added.
- No mandatory execution domain beyond the four approved targets was added.
- No new anomaly operation, Forecasting/RAG work or SaaS requirement was added.
- No source, test, dependency, migration, tag or release record was changed.

Step 01 is sufficient to proceed to the semantic and query contracts in Step 02.
