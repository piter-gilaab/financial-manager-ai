# Financial Manager AI V2 — Web Financial Workspace Architecture

Status: **FROZEN ARCHITECTURE — PHASE 4 IMPLEMENTATION PENDING**.

## Technology

The V2 Financial Workspace uses **Next.js with TypeScript**, App Router and the
versioned `/api/v1` HTTP contract. Server Components may load display data;
Client Components are limited to interaction, forms and visualizations that need
browser state. Neither kind owns financial authority.

Next.js was selected for typed React UI, routing, server/client composition and
a coherent local production build. Official Next.js documentation provides
[built-in TypeScript support](https://nextjs.org/docs/app/api-reference/config/typescript),
and the current Next.js 16 upgrade contract requires
[Node.js 20.9+ and TypeScript 5.1+](https://nextjs.org/docs/app/guides/upgrading/version-16).

The host currently has Node/npm, but the repository has no frontend manifest or
locked Node toolchain. Phase 4 must choose a then-supported Next.js release, pin a
compatible Node LTS/package-manager/dependency lock and validate the local build.
Phase 1 installs nothing and creates no frontend scaffold.

## Deployment shape

Mandatory V2 is a local single-user product:

```text
Browser -> local Next.js workspace -> loopback FastAPI /api/v1
                                      -> application modules
                                      -> existing deterministic authorities
```

The workspace may be served by one local Next.js process. It is not a SaaS
control plane and needs no CDN, edge runtime, cloud account, tenant database,
public ingress or enterprise identity. Same-origin deployment is preferred;
local split-origin development uses an exact CORS allowlist.

## Required routes and areas

The mandatory areas are exactly:

1. **Overview** (`/`)
2. **Datasets** (`/datasets` and dataset detail)
3. **Dataset Onboarding** (`/datasets/new`)
4. **Financial Analysis** (`/analysis`)
5. **Anomalies** (`/anomalies`)
6. **Chat / Ask Financial Manager** (`/chat`)

Settings is not a required seventh area. A minimal local configuration surface
may be added only if Phase 4 proves it necessary for loopback API/local-provider
configuration; it cannot contain billing, organizations, user administration,
enterprise settings, CRM or ERP workflows.

## Information and state flow

- The API is the only frontend data source for financial evidence, readiness,
  onboarding decisions and conversation state.
- URL state may contain safe opaque dataset IDs and closed operation keys, not
  raw evidence, paths or semantic authority.
- Client state holds form/display choices and one opaque process-local session
  ID. Reload/restart may require a new session.
- The frontend does not cache readiness as authorization. Execution responses
  and dataset views refresh current readiness from the API.
- No transcript, source dataset, semantic mapping or financial result is written
  to browser persistent storage in mandatory V2.

## Overview

Overview shows only evidence actually available from the API:

- dataset counts by approved domain/lifecycle state;
- selected dataset identity/domain/readiness/limitations;
- available operation identifiers for that selected dataset; and
- last in-memory UI result only when already returned in the current page state.

Domain cards are conditional. Sales, payables, receivables and cash are never
assumed to coexist or share a currency/entity/period. No generic “revenue,”
“expense,” “cash position,” “working capital” or consolidated KPI is invented.
Overview may link to analysis rather than execute hidden queries.

## Datasets

Dataset list/detail exposes safe metadata:

- opaque dataset ID;
- approved domain and lifecycle/readiness state;
- source type and safe basename when already part of the approved projection;
- row/column counts and profile version;
- currency state;
- approved roles/value mappings/qualifiers;
- operation-specific readiness and available operations;
- limitations, quality blockers and artifact versions/digests needed for lineage.

Absolute filesystem paths, raw registry files, hidden source samples, provider
packets and internal exception text are not displayed.

## Dataset onboarding

The UI is a visible, interruptible state machine:

```text
Upload CSV/XLSX
  -> safe ingestion
  -> deterministic profile
  -> semantic suggestions
  -> explicit user role/value/qualifier confirmation
  -> explicit domain approval
  -> current readiness
  -> available capabilities
  -> analyze
```

Suggestions are visually labeled non-authoritative. Confirm/correct/reject and
domain approval require an explicit user action plus evidence text. Critical
status/direction mappings and amount/sign qualifiers use closed controls. The UI
never sends confirmation merely because confidence is HIGH, a field name matches,
or a model proposed it. Blocked readiness remains visible with remediation
reasons; the flow does not skip directly from upload to analysis.

## Financial Analysis

The analysis area selects one exact ready dataset, then one operation from that
dataset's current supported catalog. It renders only the closed parameters for
that operation (`as_of_date`, granularity, missing-dimension policy).

Structured evidence is rendered as exact summary cards, tables, coverage,
currency, quality warnings, limitations and lineage. The browser does not sum
rows, compute net cash, assign aging buckets, derive overdue state, calculate
percentages or round authoritative amounts. It may sort/paginate a returned
display table only when that does not change the evidence order/meaning and is
clearly presentation state.

## Anomalies

The anomaly area exposes only currently ready
`SALES_ANOMALY_SCREEN | PROFIT_ANOMALY_SCREEN`. Required language is:

> Statistical candidates for review.

It never states “fraud detected,” “suspicious,” “error,” “risk” or probability of
wrongdoing. Candidate display may show observed value, lower/upper fences,
screening policy/version, assessment, currency/coverage and the bounded
evidence-linked record projection. Follow-up uses issued references and the API;
the UI does not reclassify candidates.

## Chat / Ask Financial Manager

Chat creates one API session and delegates every turn. The frontend implements
no financial intent parser, dataset inference, follow-up validation or evidence
grounding.

Conceptual supported prompts include:

- “Use dataset X.”
- “Show sales by country.”
- “Summarize payables.”
- “Show receivables aging as of 2026-11-01.”
- “Show net cash by month.”

They execute only when mediation resolves an exact closed operation and current
backend readiness permits it. Clarifications, blocked outcomes, provider
unavailability and issued anomaly references use their structured API states.
The rendered structured evidence remains authoritative over prose.

## Visualization policy

| Evidence shape | Permitted presentation |
|---|---|
| count/single summary | cards plus exact-value table |
| period groups | line or bar chart plus exact table |
| category/supplier/customer/account groups | bar chart plus exact table |
| aging buckets | ordered bar chart plus exact count/balance table |
| anomaly candidates/fences | candidate table and bounded value/fence plot |
| coverage/limitations | labeled disclosures, not hidden tooltips only |

Charts consume already-calculated values. Converting an exact decimal string to
a browser number solely for plotting is a non-authoritative visual approximation;
the exact string/table and backend evidence remain primary. The UI must label
that limitation where conversion can lose precision. It may not create shares,
growth rates, rankings, trends, totals, moving averages or other derived
financial measures solely to feed a chart.

## Frontend authority

Frontend owns:

- display, navigation and accessibility;
- input collection and explicit confirmation gestures;
- API/session interaction;
- safe local presentation state; and
- visualization of returned evidence.

Frontend does not own:

- financial or anomaly arithmetic;
- semantic/domain confirmation without user action;
- readiness or capability activation;
- currency inference/conversion;
- cash direction, settlement, aging or overdue classification;
- financial intent/operation invention; or
- anomaly classification/verdicts.

## Explicit blocked and error states

Known states have specific UI, code/reason, remediation when available and a
link back to dataset readiness/evidence:

- unsupported domain/operation;
- blocked operation;
- missing required role or value mapping;
- unknown currency limitation;
- multiple confirmed currency blocker;
- stale source/artifact/mapping;
- data-quality blocker;
- provider unavailable;
- empty/no-data result;
- clarification required;
- upload/ingestion rejection; and
- local session expired/restarted.

Generic “Something went wrong” is reserved for unexpected 500 responses and must
not expose a traceback or path. Known domain outcomes are not displayed as
crashes.

## Security/privacy and non-goals

The workspace never sends SQL, formulas, adapter names, Python paths/functions,
arbitrary measures/groupings or algorithms. User-provided labels/values are
rendered as inert text; no raw HTML execution is allowed. Files go only to the
bounded onboarding endpoint.

Mandatory V2 adds no auth, organizations, tenants, billing, cloud sync,
telemetry, persistent transcript, mobile application, banking action, ERP/CRM,
Forecasting or RAG UI.
