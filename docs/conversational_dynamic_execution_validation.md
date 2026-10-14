# Conversational Dynamic Execution Validation

Status: Phase 17 Step 69 acceptance record. Step 69 adds no capability.

## End-to-end evidence path

A synthetic local CSV is persisted through ingestion, profiling, explicit semantic confirmations,
domain approval and the registry. Conversation then selects the exact dataset, executes every
approved dynamic Financial Analysis operation, runs Sales and Profit anomaly screening, receives
bounded A1 labels and resolves `why_selected` against fresh authoritative evidence. Direct Manager
responses and session-wrapped responses are structure-equal.

The scripted local provider is sufficient for acceptance. Live Ollama is not required and no cloud
or external-network provider is used.

## Acceptance matrix

| ID | Scenario | Result | Evidence |
|---|---|---|---|
| A | Exact dataset selection | PASS | Exact registered ID becomes the one session selection. |
| B | Same-turn selection | PASS | Exact ID plus closed operation executes without prior selection. |
| C | Selection reuse | PASS | Each follow-on request freshly revalidates the same active ID. |
| D | Ambiguity clarification | PASS | Multiple eligible IDs are listed; none is selected. |
| E | No sole auto-selection | PASS | One eligible ID still requires explicit selection. |
| F | Stale dataset | PASS | Source/mapping invalidation clears selection and blocks execution. |
| G | Count | PASS | `SALES_RECORD_COUNT` uses Manager/binder evidence. |
| H | Sales summary | PASS | `SALES_SUMMARY` uses Manager/binder evidence. |
| I | Country | PASS | `SALES_BY_COUNTRY` uses closed grouping semantics. |
| J | Period month | PASS | `SALES_BY_PERIOD(MONTH)` produces month keys. |
| K | Period year | PASS | `SALES_BY_PERIOD(YEAR)` produces year keys. |
| L | Segment | PASS | `SALES_BY_SEGMENT` uses closed grouping semantics. |
| M | Product | PASS | `SALES_BY_PRODUCT` uses closed grouping semantics. |
| N | Profit summary | PASS | Supplied confirmed Profit only; no derivation. |
| O | Discount analysis | PASS | Existing deterministic operation only. |
| P | Units sold | PASS | Existing deterministic operation only. |
| Q | Financial follow-up | PASS | “Now by product” maps to the closed product operation. |
| R | Unsafe filter clarification | PASS | “And Canada?” creates no filter and asks for restatement. |
| S | Sales anomaly | PASS | GLOBAL Tukey-IQR through the typed Manager method. |
| T | Profit anomaly | PASS | GLOBAL Tukey-IQR on confirmed Profit only. |
| U | Blocked anomaly | PASS | Readiness reasons return without operation substitution. |
| V | Candidate references | PASS | Candidate-only A1–A10 session labels are issued. |
| W | `why_selected` | PASS | Fresh evidence supplies value, fence, tail and policy. |
| X | `record_detail` | PASS | Bounded relevant-measure projection is supported. |
| Y | Stale reference | PASS | Evidence/source mismatch returns `STALE_REFERENCE`. |
| Z | Cross-session reference | PASS | Another session has no matching evidence context. |
| AA | Cross-dataset reference | PASS | Dataset change clears incompatible references. |
| AB | Reset | PASS | Rotates session identity and clears selection/references. |
| AC | Cancel | PASS | Clears active dataset, operation and references. |
| AD | Expiry | PASS | Inactivity expiry clears all session context. |
| AE | UNKNOWN currency | PASS | Source-denomination qualification is preserved. |
| AF | CONFIRMED currency | PASS | Approved ISO code is copied without conversion. |
| AG | Multiple currency | PASS | `CONFIRMED_MULTIPLE` blocks anomaly execution. |
| AH | Provider invalid output | PASS | Validation rejects it; dynamic execution does not run. |
| AI | Provider unavailable | PASS | Safe deterministic/non-executing fallback; no legacy redirect. |
| AJ | Grounding numeric fabrication | PASS | Invented totals/signs/percentages/comparisons are rejected. |
| AK | Fraud-language guard | PASS | Verdict prose is rejected; code states candidate-only boundary. |
| AL | Malicious inputs | PASS | IDs, labels, headers, cells and prompt injection remain inert. |
| AM | Readiness revocation | PASS | Active authorization is rechecked and stale use is refused. |
| AN | Financial Analysis direct regression | PASS | Phase 14–15 Manager API remains structure-equal. |
| AO | Anomaly direct regression | PASS | Phase 16 Manager API remains structure-equal. |
| AP | Legacy conversation | PASS | Legacy datasets and anomaly references need no dynamic selection. |
| AQ | Security | PASS | Closed dispatch; no executable text/algorithm/adapter authority. |
| AR | Privacy | PASS | Catalog/fact bounds, no rows in interpretation, no persistence. |
| AS | Forecasting blocked | PASS | No forecast is fabricated or executed. |
| AT | RAG blocked | PASS | No document is retrieved or invented. |
| AU | Reproducibility | PASS | Same persisted artifacts/request reproduce semantic evidence. |
| AV | Lineage | PASS | Dataset, registry, profile, mapping, source and record lineage preserved. |

## Data integrity, lineage and reproducibility

Mediation performs no financial or statistical arithmetic. Exact decimal strings, signs, counts,
fences, candidate status and currency metadata are copied from delegated evidence. The dynamic
handle stores digests rather than rows; follow-up re-executes and compares the authenticated lineage
and semantic evidence. Direct and conversational results are structure-equal, while rendering is a
non-authoritative presentation over the same evidence.

## Scope gates

Forecasting remains `BLOCKED`. Document Retrieval/RAG remains `BLOCKED`. Dynamic anomaly remains
GLOBAL only. No peer grouping, additional anomaly measure, arbitrary filter/grouping/algorithm,
new domain, API, frontend, authentication, SaaS or Phase 18 work is included.
