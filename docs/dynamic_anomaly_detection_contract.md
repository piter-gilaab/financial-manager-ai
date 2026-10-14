# Phase 16 — Dynamic Anomaly Detection Contract

## Step 61 status and purpose

This document is the design authority for a future deterministic anomaly-
screening path over approved, dynamically onboarded `SALES_RECORD` datasets. Step
61 defines semantics, policy, evidence and integration seams only. It does not add
an operation enum, binder entry, adapter branch, readiness activation, Manager
route, conversational behavior or executable anomaly path.

Dynamic Anomaly Detection therefore remains `BLOCKED` for onboarded datasets at
this checkpoint. The existing legacy `ANOMALY_DETECTION` capability remains
`AVAILABLE` only for its already implemented Receiver General and Company
Financials paths.

The authority chain is:

```text
source data
  -> authenticated onboarding artifacts
  -> approved SALES_RECORD semantics
  -> closed dynamic anomaly operation
  -> approved deterministic anomaly policy
  -> statistical screening
  -> structured anomaly evidence
  -> Financial Manager
  -> optional LLM / presentation
```

Source values and approved semantics remain facts. A statistical assessment is a
derived observation under one named policy. Neither the Manager nor an LLM may
choose columns, define a policy, calculate a threshold, classify a record or
change the returned evidence.

## Domain semantics

The canonical terms are:

- `CANDIDATE`: the record was eligible, was assessed, and its measure value met
  the exact deterministic screening rule. This means only that it is a
  statistical screening candidate for possible investigation.
- `NOT_SELECTED`: the record was eligible, was assessed, and did not meet the
  exact screening rule. It does not mean normal, safe, correct, legitimate or
  certified.
- `NOT_ASSESSED`: the record could not validly participate in the stated
  assessment. It is an abstention, not a negative classification and not evidence
  that the record is free of anomalies.

`CANDIDATE` does not establish fraud, error, suspicious activity, manipulation,
misconduct, invalid accounting, illegality, business risk, probability of
wrongdoing or certainty of abnormal business activity. Presentation must not use
those claims or synonyms as interpretations of this capability.

The screening is observational. It never winsorizes, caps, deletes, replaces,
smooths, imputes, deduplicates or otherwise mutates a source or canonical value.

## Closed initial operation catalog

The complete initial dynamic anomaly catalog is:

| Operation | Approved domain | Screened semantic role | Scope | Policy |
|---|---|---|---|---|
| `SALES_ANOMALY_SCREEN` | `SALES_RECORD` | `SALES` | `GLOBAL` | `tukey_iqr` 1.0, both tails |
| `PROFIT_ANOMALY_SCREEN` | `SALES_RECORD` | `PROFIT` | `GLOBAL` | `tukey_iqr` 1.0, both tails |

These operation keys follow the existing uppercase, code-owned dynamic-operation
convention. They are contract names only until Step 62 implements them. An
operation fixes its measure and policy. It accepts no source-column name,
arbitrary measure, formula, statistical method, threshold, tail, minimum size,
filter, period, sort expression or grouping parameter.

In particular, this flow is prohibited:

```text
caller selects an arbitrary numeric-looking column
  -> anomaly detector executes
```

The only valid authority is an approved semantic role plus its allowlisted
policy. Numeric appearance, a header name, a model suggestion or an LLM
interpretation cannot authorize screening.

## Included and excluded measures

### Sales

`SALES_ANOMALY_SCREEN` screens only the uniquely confirmed supplied `SALES`
measure. It does not derive Sales, revenue, receipts, cash inflow or company
performance. It reuses the Company Financials precedent for two-sided Sales
screening because the legacy policy already treats supplied Sales as a signed
source measure under Tukey IQR 1.0.

Negative Sales values remain signed source facts. They are not converted to
positive values or automatically called errors. A negative Sales value is a
`CANDIDATE` only when it is strictly below the calculated lower fence (or,
independently of sign, strictly above the upper fence).

### Profit

`PROFIT_ANOMALY_SCREEN` screens only the uniquely confirmed supplied `PROFIT`
measure. Profit is never derived from Sales, COGS, Gross Sales, Discount or a
formula. It reuses the Company Financials precedent for two-sided signed Profit
screening under Tukey IQR 1.0.

Negative Profit values remain signed source facts. Sign alone is not a screening
rule, loss conclusion or error label. Only a strict fence comparison can select a
candidate.

### Excluded measures

`DISCOUNT` is excluded. Although Phase 15 established a monetary amount contract
for dynamic Discount analysis, the legacy anomaly review explicitly deferred
Discount and other measures pending measure-specific thresholds and evidence.
Numeric and monetary semantics alone do not establish an anomaly policy.

`UNITS_SOLD` is excluded. It is a quantity with unresolved unit comparability and
has no legacy anomaly-screening precedent. Its availability for deterministic
summary does not authorize anomaly screening.

`GROSS_SALES`, `COGS`, `SALE_PRICE`, `MANUFACTURING_PRICE`, arbitrary numeric
roles and all `ACCOUNTING_TRANSACTION`, `PAYABLE`, `RECEIVABLE`,
`CASH_TRANSACTION`, budget and balance measures are excluded. Adding any measure
requires a separately reviewed semantic and statistical policy; it is not an
automatic catalog extension.

## Deterministic statistical policy

The initial dynamic operations reuse, rather than replace, the existing Company
Financials Tukey IQR policy:

- method name: `tukey_iqr`;
- policy version: `1.0`;
- reference population: the complete current approved registered dataset cohort
  for the operation, including each assessed record itself;
- scope: `GLOBAL` only;
- tails: lower and upper for both Sales and Profit;
- minimum reference population: 30 usable exact numeric values;
- IQR requirement: strictly positive;
- multiplier: exact decimal `1.5`;
- comparison: strict; fence equality is not selected.

For ascending usable values `x[0] ... x[n-1]`, for `p` equal to `0.25` or
`0.75`:

```text
h = (n - 1) * p
i = floor(h)
Q(p) = x[i]                                      when h is an integer
Q(p) = x[i] + (x[i + 1] - x[i]) * (h - i)       otherwise

Q1 = Q(0.25)
Q3 = Q(0.75)
IQR = Q3 - Q1
lower_fence = Q1 - 1.5 * IQR
upper_fence = Q3 + 1.5 * IQR
```

A usable value is `CANDIDATE` with `tail=lower` only when
`value < lower_fence`, and with `tail=upper` only when
`value > upper_fence`. Otherwise it is `NOT_SELECTED`. Equality to either fence
is `NOT_SELECTED`.

The registered cohort is unfiltered in the initial catalog. “Global” therefore
means all current canonical records of that exact approved dataset, not a trained
population, rolling history or universal threshold. No filter or period input is
accepted. If filtered dynamic screening is proposed later, cohort construction
and threshold sensitivity require a new contract version.

## Minimum population and degenerate references

Thirty means 30 usable values of the selected measure, not 30 source rows. It is
the same exploratory guard used by the legacy anomaly contract, not a power
calculation, confidence guarantee, independence claim or proof of detection
quality.

- With fewer than 30 usable values, the global reference is ineligible with
  reason `insufficient_numeric_records`. No quartiles or fences are reported.
- With at least 30 usable values but `IQR == 0`, the reference is ineligible with
  reason `zero_iqr`. `Q1`, `Q3` and `IQR` are reported; fences are null.
- No alternative method, fallback threshold, global default, epsilon or division
  by zero is fabricated.

For a direct deterministic screening result, records with usable values receive
`NOT_ASSESSED` when their global reference is ineligible. Records with missing or
unparseable measures retain their more specific measure-unavailability reason.
Future Step 63 readiness must report an operation `BLOCKED` unless the current
cohort has at least 30 usable values and positive IQR, because otherwise no record
can receive a valid assessment. An abstention is not a data-corruption blocker.

## Dataset and operation eligibility

Each operation is evaluated independently against current persisted state. It is
eligible only when all of the following hold:

1. the exact `dataset_id` resolves to a current registered dataset through the
   authenticated workflow;
2. registry, workflow, ingestion, profile and mapping identities, versions and
   digests reconcile;
3. preserved source fingerprint, selected sheet, ordered schema and row count are
   current;
4. the mapping remains `SEMANTICALLY_APPROVED` for exactly `SALES_RECORD`;
5. the selected operation's measure role occurs exactly once as `CONFIRMED`, with
   its current stable column identity;
6. the canonical model/specification and dynamic anomaly policy/adapter versions
   are compatible;
7. operation-scoped canonicalization produces exact value/status pairs without a
   relevant integrity blocker;
8. the currency state is eligible under this contract;
9. at least 30 current usable measure values exist and their IQR is positive; and
10. a validated implementation of the exact operation and policy exists.

Semantic approval and numeric-looking data are necessary but not sufficient.
Step 61 supplies the missing policy contract but no implementation; condition 10
is false until Step 62 is separately implemented and validated. Dynamic anomaly
readiness therefore stays blocked now.

### SALES_RECORD domain requirements

The current `SALES_RECORD` domain contract independently requires its global
anchors `TRANSACTION_DATE` and `SALES` to remain approved. This domain validity is
a prerequisite for both anomaly operations; it is not a claim that transaction
date participates in the IQR calculation.

Operation-specific requirements are then narrow:

- `SALES_ANOMALY_SCREEN` requires approved domain validity plus confirmed
  `SALES`;
- `PROFIT_ANOMALY_SCREEN` requires approved domain validity plus confirmed
  `PROFIT`.

Missing or revoked Country, Segment, Product, Discount or Units Sold does not
block either operation. Missing Profit does not block Sales screening. Revoking
Sales or Transaction Date currently invalidates the approved domain and therefore
blocks both operations; revoking only Profit blocks only Profit screening.

## Missing, unparseable and invalid values

The Phase 15 status-preserving quality philosophy applies:

- an approved missing marker becomes an unavailable measure with its source
  status and `NOT_ASSESSED`;
- a non-missing value that cannot be parsed under the approved numeric contract
  becomes `parsing_failed` and `NOT_ASSESSED`;
- neither case enters quartile estimation or fence calculation;
- neither case becomes zero, a `NOT_SELECTED` record or a deleted source row;
- no imputation, placeholder expansion or value repair is permitted.

Representative assessment reasons are
`measure:sales:source_missing`, `measure:sales:parsing_failed`,
`measure:profit:source_missing` and `measure:profit:parsing_failed`. Reasons are
closed code-owned values, not raw exception messages.

A parsed non-finite value, a contradictory value/status pair, a malformed
canonical record, incompatible precision or another integrity failure is not an
ordinary per-record parse exclusion. It produces `DATA_QUALITY_BLOCKER` and no
partial classifications or thresholds. Duplicate-row candidates are retained as
distinct source observations and disclosed; they are neither deduplicated nor
automatically a blocker.

## Record and assessment accounting

Future evidence must preserve the existing distinction between selection
accounting and statistical candidate status. `records.candidates` means rows in
the selected cohort; uppercase `CANDIDATE` means a statistical assessment.

The initial unfiltered operations require:

```text
records.population = records.candidates
records.candidates = records.used + records.excluded

assessment_summary.assessed
  = assessment_summary.candidate + assessment_summary.not_selected

records.candidates
  = assessment_summary.candidate
  + assessment_summary.not_selected
  + assessment_summary.not_assessed
```

`records.used` is the number of usable numeric values supplied to reference
eligibility/estimation. `records.excluded` counts unavailable measure values, with
disjoint `exclusion_reasons`. `assessment_summary.not_assessed_reasons` separately
accounts for every abstention, including an ineligible global reference. Missing
and parsing-failed values are unavailable, not non-anomalous.

## Global and peer screening

The initial dynamic catalog is `GLOBAL` only. It does not expose `group_by`, peer
dimensions or a choice between global and peer methods.

The legacy Company Financials peer rule is `segment × sale_price`. Reusing it for
arbitrary onboarded data would require confirmed `SEGMENT` and `SALE_PRICE`,
numeric-equivalent price-label handling and evidence that the resulting groups
are meaningful and adequately populated. The current nine-operation dynamic
analysis contract does not require Sale Price. Conversely, Country, Segment or
Product alone would be a new peer policy, not reuse of the validated legacy rule.
They are therefore not silently substituted.

Peer screening is deferred. A later separately approved contract must define a
closed semantic grouping allowlist, minimum usable size per peer, missing-label
policy, deterministic labels/order, lineage, positive-IQR behavior and separate
global/peer assessments. It must also preserve the possibility that global and
peer results disagree. No future implementation may merge those meanings into
one unexplained status or accept an arbitrary source column. Existing legacy
global and peer behavior is unchanged.

## Exact arithmetic, ordering and ties

All authoritative values, quartiles, IQRs and fences use exact `Decimal`-
compatible canonical values under the existing isolated precision-60 context,
with `Inexact` and `Rounded` traps. No binary float, SQLite numeric aggregate,
Pandas/NumPy float reduction, two-decimal quantization or display rounding may
decide a classification.

Quarter interpolation and multiplier `1.5` are exact. Values and statistics are
serialized as fixed-point decimal strings; unavailable values/statistics are
null. Exact-arithmetic overflow or precision loss produces
`DATA_QUALITY_BLOCKER`, with no rounded threshold, fallback or partial candidate
set.

Items sort by ascending source row number, then canonical record ID. The single
global reference is first. Equal numeric values receive the same fence outcome;
there is no top-N truncation or tie-breaking rank. Source-row/canonical-ID order
only makes evidence reproduction deterministic. Every source record remains
distinct.

## Currency

Screening operates only on approved source-denomination values. It performs no FX
conversion and never infers denomination from Country, symbols, formatting,
headers, filenames or an LLM.

- `UNKNOWN`: screening may proceed in source denomination when every other gate
  passes, but evidence must state that denomination and cross-record economic
  comparability are not established.
- `CONFIRMED`: screening may proceed with the one approved ISO code/evidence;
  values remain in that source denomination.
- `CONFIRMED_MULTIPLE` or any incompatible state: both scalar global monetary
  screens are blocked. No mixed-currency scalar fence, implicit partition or FX
  conversion is permitted.

Currency state accompanies readiness and every screening result. Unknown currency
does not become known because a statistical method can operate numerically.

## Structured evidence contract

Step 64 must preserve complete, data-only authoritative evidence. At minimum a
successful, partial or all-abstained result contains:

- contract/service version, exact `dataset_id`, canonical domain, operation,
  semantic measure and `screening_scope=GLOBAL`;
- screening policy name/version, quantile convention, multiplier, minimum usable
  size, tails, strict comparison and in-sample reference-population basis;
- dataset capability state and the authenticated registry/profile/mapping/source/
  canonical/policy versions used;
- `records` population, selected cohort, usable/excluded counts and disjoint
  exclusion reasons;
- assessment counts for assessed, `CANDIDATE`, `NOT_SELECTED` and `NOT_ASSESSED`,
  plus disjoint abstention reasons;
- one global reference with numeric size, eligibility/reason, `Q1`, `Q3`, `IQR`,
  lower fence and upper fence;
- currency state/code/evidence basis and `conversion_applied=false`;
- relevant quality disclosures, including missing/unparseable values, duplicate-
  row candidates, unknown denomination and method limitations;
- every cohort record's operation-scoped measure value, raw source token or
  bounded source representation, status, one global assessment, reference link,
  applicable warning references and source lineage;
- candidate record references in authoritative source order; and
- explicit limitations: descriptive in-sample screening, no independence,
  detection-accuracy, fraud/error, probability or business-validity claim.

Evidence exposes only the selected measure and required metadata, not unrelated
columns or arbitrary dataset contents. It never exposes an absolute source or
artifact path, Python implementation name, registry payload, stack trace or raw
exception text.

Normal result statuses reuse `SUCCESS`, `PARTIAL`, `NO_DATA`, `INVALID_REQUEST`,
`UNSUPPORTED` and `DATA_QUALITY_BLOCKER`. Relevant unavailable values or an
ineligible reference make a nonempty returned cohort `PARTIAL`; a valid empty
population is `NO_DATA`. Integrity or exact-arithmetic failure returns
`DATA_QUALITY_BLOCKER` without partial classifications. Step 62 must fix precise
failure precedence while preserving the established binder/adapter precedence.

## Record references and lineage

Traceability is mandatory:

```text
dataset_id
  -> registry version/digest
  -> profile version/digest
  -> semantic mapping version/digest and confirmed role/column identity
  -> canonical model version/specification digest
  -> source fingerprint and source sheet
  -> canonical_record_id and source row number
  -> policy version and global reference
  -> record assessment
  -> candidate evidence/reference
```

Every item, not only candidates, retains its canonical record ID, source sheet/row
and assessment. Candidate evidence must be resolvable without treating a source
row as a business-event identifier.

The future Manager/presentation layer may issue bounded opaque local handles for
candidate records, following the existing `ANOMALY_RECORD` design where practical.
It must never accept a caller-supplied canonical record ID as authority, disclose
filesystem paths or cache detached classifications. Resolution must revalidate
current authoritative state and detect stale evidence. Step 61 does not extend
sessions, conversational follow-up or the existing legacy handle validator.

## Module interfaces and seams

The intended future flow is:

```text
Financial Manager
  -> validated typed dynamic anomaly request
  -> closed dynamic anomaly binder
  -> SALES_RECORD anomaly adapter
  -> deterministic anomaly engine
  -> structured evidence
```

The interfaces remain deliberately narrow:

- the binder resolves an exact `dataset_id` and one closed operation, validates
  operation-specific approved roles and records the versions bound; it neither
  loads arbitrary columns nor calculates thresholds;
- the `SALES_RECORD` anomaly adapter authenticates current onboarding artifacts,
  canonicalizes only the selected role with status/lineage, enforces currency and
  compatibility gates and delegates; it neither invents semantics nor owns the
  statistical algorithm;
- the anomaly engine owns Tukey IQR reference eligibility, exact thresholds,
  statuses, ordering and assessment accounting;
- Financial Core helpers may continue to own shared exact Decimal parsing,
  arithmetic and coverage primitives, but Financial Core analysis operations do
  not select anomaly policy;
- the Manager validates/wraps the returned envelope and performs no source
  mapping, arithmetic, threshold calculation, reclassification or evidence
  mutation.

Step 62 may reuse or deepen the existing pure anomaly baseline behind an interface
that accepts authenticated canonical records. It must not route dynamic data
through the legacy approved SQLite snapshot or alter legacy results. No second
statistical implementation with a subtly different quartile convention is
permitted.

## Future readiness model

Step 63 extends the existing dataset-scoped `CapabilityReadiness` projection; it
does not add a global availability switch. The dynamic anomaly candidate catalog
contains exactly the two operations above, each with existing operation states:

- `SUPPORTED`: semantic, policy, current-data, currency, adapter and deterministic
  reference validation all pass;
- `BLOCKED`: the operation is approved but current semantics, artifacts, source,
  schema, sample/IQR, currency, quality, policy compatibility or implementation
  prevents valid execution;
- `UNSUPPORTED`: the domain/operation is outside the closed catalog or was removed
  from the binder contract.

The dataset's `ANOMALY_DETECTION` state is
`AVAILABLE_WITH_LIMITATIONS` only when at least one operation is `SUPPORTED`.
Otherwise it remains `BLOCKED` or `BLOCKED_NOT_IMPLEMENTED` under the existing
semantic/policy/execution readiness vocabulary. Availability is derived from
current checks, never stored as an independent Boolean or supplied by an LLM.

The existing global Manager registry continues to describe legacy anomaly
availability. A dataset-scoped dynamic projection must be carried separately, as
dynamic Financial Analysis already does. `AVAILABLE_WITH_LIMITATIONS` means only
one or both fixed global screens can execute for that exact dataset; it does not
mean arbitrary anomaly detection, peer screening or parity with the legacy
service.

## Revocation and fresh validation

Readiness is recomputed from current authenticated artifacts. No stale anomaly
authorization survives:

- revoking or changing `SALES` or `TRANSACTION_DATE` invalidates the current
  `SALES_RECORD` domain and blocks both operations;
- revoking or changing `PROFIT` blocks only `PROFIT_ANOMALY_SCREEN` while domain
  validity remains;
- a source fingerprint, sheet, ordered schema, row population, profile, mapping,
  stable column identity, registry/workflow pointer, canonical model, adapter or
  policy-version change invalidates dependent readiness;
- a change that reduces usable records below 30, makes IQR zero, introduces an
  incompatible currency state or triggers relevant exact-arithmetic/quality
  failure blocks the affected operation;
- removing or making the policy/adapter incompatible blocks execution even if
  semantics remain approved.

Recovery requires fresh binder/adapter/policy validation over the restored current
state. Execution revalidates after readiness inspection, closing the interval
between discovery and use. It never falls back to an older mapping, cached fence
or nearby dataset.

## LLM and presentation authority

The LLM may interpret a user's words into an allowlisted request and explain
bounded returned facts only after the deterministic path exists and Step 64 is
authorized. It must not:

- decide whether a record is anomalous;
- calculate or restate invented quartiles, fences, z-scores or probabilities;
- choose a source column, measure, peer dimension, method, threshold, tail or
  minimum population;
- change policy or result status;
- infer missing values, financial meaning or currency;
- rerank, suppress or modify candidate evidence; or
- infer fraud, suspicion, error, manipulation, illegality, misconduct, risk or
  probability of wrongdoing.

Future deterministic and model-assisted presentation must say that a
`CANDIDATE` met one statistical screening rule and requires contextual review. It
must describe `NOT_SELECTED` as “not selected by this rule,” never “normal,” and
`NOT_ASSESSED` as an unavailable assessment, never a passed check.

## Security and privacy

Dataset identifiers, operation keys, headers, labels and values are inert data.
The dynamic anomaly path may contain no arbitrary source-column selection,
formula, statistical code, model-generated code, runtime code generation,
`eval`, `exec`, shell, subprocess, raw SQL, dynamic import, untrusted `getattr`,
request-selected adapter or plugin discovery. Dispatch remains a static,
code-owned allowlist with controlled path-free failures.

Screening is local-first, offline and deterministic. No external LLM, hosted
provider, telemetry, cloud storage or network call is required for classification.
No dataset or candidate record may be sent externally merely to decide a status.
A future explanation may receive only bounded mediated evidence under the existing
local/provider policy; deterministic structured evidence remains authoritative.

This is an application data-flow contract, not encryption, authentication, RBAC,
DLP, malware scanning, process sandboxing or host-level egress control.

## Legacy compatibility

Receiver General keeps its existing upper-tail accounting-amount policy and fixed
debit/credit × voucher-type peers. Company Financials keeps its existing two-sided
Sales/Profit policy and fixed segment × sale-price peers. Their request shapes,
minimum size, calculations, evidence, Manager routing, conversation references
and regression behavior are unchanged.

Dynamic `SALES_RECORD` sources are not relabeled as Company Financials and are not
migrated into its snapshot path. Policy reuse means the same documented global
Company Financials arithmetic and candidate semantics where valid; it does not
copy source identity, peer evidence or legacy dataset assumptions.

## Remaining Phase 16 steps

- **Step 62 — SALES_RECORD Dynamic Anomaly Adapter:** implement the two closed
  operations, authenticated operation-scoped canonical translation, exact global
  Tukey IQR screening and structured evidence. Do not activate dataset readiness.
- **Step 63 — Dynamic Anomaly Readiness:** add dataset/operation-specific
  `SUPPORTED | BLOCKED | UNSUPPORTED` projection, current sample/IQR/policy checks,
  revocation and `AVAILABLE_WITH_LIMITATIONS` derivation.
- **Step 64 — Manager / Evidence Integration:** add an explicit validated Manager
  execution surface and bounded presentation/evidence-reference integration. Do
  not give the Manager or LLM statistical authority.
- **Step 65 — End-to-End Validation:** validate the persisted onboarding-to-Manager
  flow, both measures, abstentions, arithmetic, currency, revocation, security,
  privacy, lineage, legacy compatibility and blocked Forecasting/RAG behavior.

Each step requires separate authorization. Step 61 implements none of them.

## Non-goals

Step 61 does not implement or activate anomaly execution, readiness, Manager
routing, conversation/session changes, peer screening, filters, arbitrary
measures, fraud detection/scoring, suspicion/risk/probability scoring, machine-
learning anomaly models, Isolation Forest, neural models, forecasting, RAG,
PAYABLE/RECEIVABLE logic, API, frontend, authentication, dependency changes,
schema migration, scaffolding or data mutation.

No ADR is added: the contract deliberately reuses an existing versioned policy
and chooses the smallest reversible dynamic scope. A future peer or measure policy
is an additive, separately reviewed contract decision rather than a hidden change
to this one.
