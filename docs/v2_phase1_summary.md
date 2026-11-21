# Financial Manager AI V2 — Phase 1 Summary

Status: **COMPLETE — FROZEN ARCHITECTURE; IMPLEMENTATION PENDING**.

## Frozen product

V2 is a local-first multi-domain financial analysis platform over explicit
semantics, current operation readiness and deterministic evidence. Mandatory
generic domains are exactly `SALES_RECORD`, `PAYABLE`, `RECEIVABLE` and
`CASH_TRANSACTION`; only the latter three are new implementation targets.

The roadmap is exactly Scope & Architecture, Multi-Domain Execution,
Application/API, Web Workspace, and Hardening & Release. Forecasting, RAG and the
other enumerated non-goals remain outside mandatory V2.

## Frozen execution contracts

- `PAYABLE`: six operations from count through explicit-date open-balance aging
  and overdue summary.
- `RECEIVABLE`: six corresponding operations with distinct `CUSTOMER` semantics.
- `CASH_TRANSACTION`: six operations using explicitly mapped direction and
  amount convention; Core computes inflow/outflow/net.
- `SALES_RECORD`: V1 nine-operation catalog and two anomaly screens unchanged.

The ontology reuses `AMOUNT` and adds only `CUSTOMER`. Aging uses explicit
`as_of_date` equal to an approved dataset reference date, five closed buckets,
complete settlement mapping and `OUTSTANDING_BALANCE` basis. Cash direction
never comes from sign. `CONFIRMED_MULTIPLE` blocks monetary operations; no FX
exists.

## Frozen application and web architecture

FastAPI/Pydantic v2 is the local `/api/v1` HTTP adapter over three small
application modules that delegate to the existing onboarding, Manager and
session interfaces. Decimal crosses JSON as a base-10 string and structured
evidence remains complete.

Next.js + TypeScript is the local workspace. Its six required areas cover
overview, datasets, onboarding, analysis, existing anomalies and chat. The UI
collects actions and renders evidence; it does not calculate financial facts,
decide readiness/semantics/currency or classify anomalies.

## Phase 2 authorized implementation boundary

Phase 2 may implement only:

1. shared multi-domain execution infrastructure strictly required by the frozen
   semantic/query contracts;
2. `PAYABLE` execution for the exact six-operation catalog;
3. `RECEIVABLE` execution for the exact six-operation catalog;
4. `CASH_TRANSACTION` execution for the exact six-operation catalog;
5. current operation-specific readiness for those operations;
6. `FinancialManagerAgent` integration through typed closed requests;
7. bounded conversational integration required to invoke those ready operations;
8. exact arithmetic, quality, currency, lineage and evidence validation; and
9. regression/security/privacy validation, including unchanged V1 behavior.

Phase 2 must not start API/application HTTP implementation, frontend/scaffolding,
Forecasting, RAG, payable/receivable/cash anomaly operations, authentication,
multitenancy, PostgreSQL, external providers or any generic query language.

## Integrated architecture review

| Review concern | Result |
|---|---|
| Scope creep/additional phases | None; five phases and three new execution targets only. |
| Unnecessary abstractions | No plugin/event/repository/ORM layer; three application seams match real authorities/callers. |
| V1 contradiction | Legacy paths/catalogs/CLI remain unchanged; V2 terms are targets. |
| LLM authority leakage | None; closed mediation and grounded explanation only. |
| Manager arithmetic | None authorized; Core/anomaly modules remain authorities. |
| API/frontend arithmetic | Explicitly forbidden; exact evidence transported/rendered. |
| Currency inference/FX | Forbidden; states and blockers preserved. |
| Implicit financial semantics | Status, amount basis, reference state and cash convention require confirmation. |
| Arbitrary query language | None; 18 new exact operations and closed parameters only. |
| Stale readiness | Current recomputation plus execution revalidation required. |
| False domain symmetry | Customer/supplier remain distinct; revenue/receipt/payment/cash are not inferred. |
| Unsafe overdue semantics | Due date alone insufficient; open balance/reference evidence required. |
| Unsafe cash-direction inference | Direction mapping is independent of signed convention. |
| Premature SaaS/auth/multitenancy | Explicitly outside local V2. |
| Forecast/RAG creep | Deferred and absent from routes/screens/Phase 2. |
| Catalog explosion | Six operations per new domain; no new anomaly catalog. |

The integrated review corrected one unsafe ambiguity: `as_of_date` is now
required to equal an explicitly approved `dataset_reference_date`. V2 does not
reconstruct historical open/settled state without settlement history. No other
cross-step contradiction remained after the correction.

## Phase 1 artifacts

- [V2 scope](v2_scope.md)
- [V2 roadmap](v2_roadmap.md)
- [Multi-domain semantic contract](v2_multi_domain_contract.md)
- [Closed query catalog](v2_query_catalog.md)
- [Application/API architecture](v2_application_api_architecture.md)
- [HTTP API contract](v2_api_contract.md)
- [Web architecture](v2_web_architecture.md)
- [Product flows](v2_product_flows.md)
- [Acceptance criteria](v2_acceptance_criteria.md)
- Step 01–04 validation records

The accepted Phase 1 architecture does not itself make any V2 capability
executable. The next permitted work is Phase 2 under the exact boundary above.
