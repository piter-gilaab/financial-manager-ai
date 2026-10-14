# Phase 16 — Step 61 validation

## Status

**PASS.** Step 61 is contract/design only. No anomaly operation,
adapter, binder, readiness activation, Manager route, conversation change,
dependency, migration or runtime code is added.

## Repository evidence inspected

The contract was checked against the current worktree and branch, the project
glossary/guide, query and security contracts, Phase 13–15 dynamic contracts and
validations, and the complete Step 14 anomaly design, implementation and focused
tests. The implementation inspection included:

- `src/anomaly/baseline.py` and `src/anomaly/service.py`;
- anomaly-related Financial Core arithmetic, quality, contract and currency
  helpers;
- the dynamic `SALES_RECORD` canonical adapter, binder and operation-readiness
  projection;
- Manager registry, routing, wrapping and anomaly evidence-reference behavior;
- legacy Company Financials Sales/Profit and Receiver General screening tests.

The repository baseline supplied for this step is 615 passed, with no failures,
errors or skips. The worktree was already non-clean with the authorized Phase
13–15 implementation and documentation; those pre-existing changes were
preserved.

## Resolved domain and policy decisions

The initial dynamic scope is exactly `SALES_ANOMALY_SCREEN` and
`PROFIT_ANOMALY_SCREEN` for approved `SALES_RECORD` datasets. Both reuse the
legacy Company Financials global Tukey IQR 1.0 policy: linear `(n-1)*p`
quartiles, exact multiplier 1.5, both tails, strict fence comparison, at least 30
usable values and positive IQR.

The new contract makes `CANDIDATE`, `NOT_SELECTED` and `NOT_ASSESSED` explicit in
the project glossary. A candidate met one identified statistical rule; it is not
fraud, error, suspicion, misconduct, manipulation, illegality, risk or a
probability claim. `NOT_SELECTED` is not “normal,” and `NOT_ASSESSED` is an
abstention rather than a passed check.

Discount and Units Sold are excluded because numeric/analysis readiness is not a
statistical policy. Other measures and domains are outside the closed catalog.
There is no arbitrary-column or arbitrary-method path.

## Global and peer decision

Initial dynamic screening is `GLOBAL` only. The existing Company Financials peer
definition is `segment × sale_price`; the dynamic nine-operation analysis contract
does not require Sale Price. Country, Segment or Product alone would be a new
policy without the legacy peer evidence. No peer definition is therefore copied,
substituted or exposed through an arbitrary `group_by` input.

Peer screening requires a later separately approved contract. Legacy Receiver
General and Company Financials global/peer behavior remains unchanged.

## Eligibility, quality and currency

The contract requires current authenticated registry/profile/mapping/source
identity, approved `SALES_RECORD`, one confirmed operation measure, compatible
canonical/policy/adapter versions, eligible currency, at least 30 current usable
values, positive IQR and no relevant blocker.

The current domain anchors `TRANSACTION_DATE` and `SALES` still govern domain
validity. Profit is an additional requirement only for Profit screening. Optional
Country, Segment, Product, Discount and Units Sold cannot block either screen.

Missing and parse-failed measures are `NOT_ASSESSED`, excluded from reference
estimation and never converted to zero. Inconsistent canonical state, non-finite
authoritative values or exact-arithmetic failure block without partial
classifications. Negative Sales/Profit values stay signed and are selected only
by strict fence comparison.

`UNKNOWN` currency permits qualified source-denomination screening;
`CONFIRMED` preserves its one approved code; `CONFIRMED_MULTIPLE` or an
incompatible state blocks scalar screening. There is no currency inference,
partition fabrication or FX.

## Evidence and integration

Future evidence must reconcile population, usable/excluded records, assessed and
all three statuses; expose the exact policy/reference/fences, currency, quality,
limitations and candidate references; and preserve dataset → registry/profile/
mapping → canonical specification/record → source sheet/row → assessment
lineage without filesystem paths.

The designed seam is Manager → typed dynamic anomaly binder → one
`SALES_RECORD` anomaly adapter → deterministic anomaly engine → structured
evidence. The Manager and LLM have no threshold/classification authority.
Conversational follow-up is not implemented in this step.

## Readiness and revocation

Step 63 must project both operations independently as
`SUPPORTED | BLOCKED | UNSUPPORTED`. Dataset-scoped `ANOMALY_DETECTION` may become
`AVAILABLE_WITH_LIMITATIONS` only when at least one operation is genuinely
executable. This does not change the existing global legacy capability registry.

Mapping/source/schema/profile/registry/canonical/policy/adapter changes, domain-
anchor or measure revocation, insufficient current values, zero IQR, incompatible
currency and relevant quality failure revoke the affected readiness. Execution
must revalidate and no cached fence or authorization may survive.

## Acceptance matrix

| Requirement | Contract result |
|---|---|
| Sales / Profit only | PASS — exact two-operation catalog |
| Discount / Units Sold excluded | PASS — no policy inferred from numeric roles |
| Legacy policy reuse | PASS — exact Tukey IQR 1.0 global arithmetic |
| Minimum sample / zero IQR | PASS — 30 usable values and positive IQR required |
| Exact arithmetic | PASS — precision-60 Decimal, trapped loss, strict fences |
| Missing / parse failure | PASS — `NOT_ASSESSED`, never zero or `NOT_SELECTED` |
| Negative values | PASS — preserved; sign alone is not selection |
| Currency | PASS — UNKNOWN/CONFIRMED allowed with disclosure; multiple blocked |
| Arbitrary numeric columns | PASS — prohibited by semantic-role/policy catalog |
| Arbitrary peer grouping | PASS — peers deferred; no `group_by` |
| Structured evidence | PASS — counts, references, statuses, quality and limits required |
| Lineage / record references | PASS — complete path-free source trace required |
| Readiness / revocation | PASS — operation-specific current-state derivation |
| LLM authority | PASS — no column, method, threshold or classification authority |
| Fraud/suspicion language | PASS — explicit prohibition |
| Source mutation | PASS — observational screening only |
| Security/privacy | PASS — static local deterministic data-only path |
| Legacy compatibility | PASS — no migration or behavior change |
| Forecasting/RAG scope | PASS — remain blocked and out of scope |
| Steps 62–65 boundary | PASS — responsibilities documented, none implemented |

## Verification

- Documentation/source inspection: complete.
- Runtime code changed: no.
- Full implementation regression: not required for this contract-only step and
  not run.
- `git diff --check`: PASS.
- Required two-axis code review: PASS. Standards found no hard or heuristic
  violations. Spec found one low-severity completion-state bookkeeping issue in
  this validation report; its pending markers were replaced with these final
  results. No substantive contract gap, scope creep or architecture conflict
  was found.

## Files in Step 61

Created:

- `docs/dynamic_anomaly_detection_contract.md`
- `docs/step61_validation.md`

Modified:

- `CONTEXT.md` (glossary terms only)

No ADR or implementation file is created. No Git commit is made.

## Remaining limitations and stop

The contract does not establish independent observations, comparable economic
magnitudes under unknown currency, detection accuracy, ground-truth labels,
fraud/error identification or meaningful dynamic peers. A minimum of 30 and
positive IQR is an exploratory eligibility guard, not proof of statistical
sufficiency.

Dynamic Anomaly Detection remains blocked until separately authorized Steps
62–64 implement and activate the defined path, followed by Step 65 end-to-end
validation. Phase 16 is incomplete. The next recommended step after Step 61 is
Step 62 only.
