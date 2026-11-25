# Financial Manager AI V2.1 — Smart Onboarding

Status: **PLANNED UX AND AUTHORITY CONTRACT — NOT YET IMPLEMENTED**.

## Goal

V2.1 reduces cognitive load without reducing financial control. The default
path shows what was safely resolved, then asks only for decisions that affect
financial meaning or deterministic execution.

The user-facing language must describe concrete actions. “AI cleaned your data”
is prohibited because it hides both transformation and authority.

## Existing workflow reused

The current `/datasets/new` flow already provides:

- bounded multipart CSV/XLSX upload;
- exact multi-sheet clarification;
- deterministic structural profile;
- explicit confirm/correct/reject semantic decisions;
- explicit domain confirmation separated from selector state;
- closed value maps and qualifiers;
- a read-only approval summary; and
- backend-provided operation-specific readiness.

V2.1 reorganizes and deepens this workflow. It does not introduce a second
onboarding page, client-side semantic engine or frontend readiness calculation.

## Target workflow

```text
1. Upload
2. Processing
3. Preparation summary
4. Confirm financial meaning
5. Review saved decisions
6. Readiness and analysis
```

The six labels are product language, not new backend lifecycle states.

### 1. Upload

The user selects one local `.csv` or constrained `.xlsx`, optionally provides a
bounded provenance note, and explicitly selects a sheet when more than one
non-empty safe sheet exists.

The screen states the effective file bound and supported constraints. It does
not imply support based only on extension.

### 2. Processing

The existing synchronous local request performs ingestion, profiling,
preparation, quality assessment and semantic suggestion. The UI may show named
steps such as “Checking file safety” and “Measuring data quality,” but it must not
claim progress percentages that the backend does not supply.

No background queue, job server or polling infrastructure is required at the
current bounds. A controlled failure identifies the stage and safe remediation.

### 3. Preparation summary

The first result view answers:

- What was accepted?
- What was automatically represented or normalized?
- Why was each automatic action safe?
- What source representation was preserved?
- What quality conditions were found?
- Which items still need financial confirmation?

The default summary contains:

- source basename, format and selected sheet;
- total accepted rows and columns;
- safe transformations applied, grouped by transformation identifier;
- parse failure and ambiguous-date counts;
- exact duplicate candidate count, explicitly labeled “candidates”;
- currency state;
- number of confirmation groups; and
- a short statement that no records were deleted or values imputed.

Technical details are progressively disclosed. A details view may expose
versions, digests, column evidence, bounded examples, row references and full
finding codes without requiring the user to understand backend class names.

Suggested primary copy:

> We preserved the original file and created traceable structural
> representations. No rows were deleted, no financial values were filled in,
> and no currency or cash direction was assumed.

### 4. Confirm financial meaning

Only `REQUIRES_CONFIRMATION` items and optional semantic suggestions are shown as
authority actions. The UI groups related decisions for comprehension, while
keeping every saved decision explicit.

Initial confirmation groups are:

1. **Dataset purpose** — canonical domain.
2. **Dates** — semantic role and ambiguous source format where applicable.
3. **Amounts and measures** — amount/measure role and supplied meaning.
4. **Status and direction** — complete closed value maps for status,
   debit/credit, cash direction or actual/budget.
5. **Currency** — complete ISO evidence when available; otherwise `UNKNOWN`
   remains visible without fabricated approval.
6. **Domain policy** — outstanding-balance basis, dataset reference date or cash
   amount convention where required.

A group is a presentation projection, not a new authority. V2.1 initially reuses
the existing role, domain and qualifier mutation endpoints. A later atomic batch
mutation would require a separate closed backend contract; the frontend must not
simulate atomicity by marking unsaved items approved.

For every decision:

- selector changes remain local pending state;
- the proposed meaning and evidence are visible;
- alternatives are closed and bounded;
- approval uses an explicit commitment verb such as **Confirm semantic role**,
  **Save value mapping** or **Confirm domain**;
- reject/correct remains available;
- required evidence is non-empty and saved with the authority record; and
- stale mapping/version responses cause a refresh and re-review, not blind retry.

### 5. Review saved decisions

The existing read-only review is extended to show:

- approved domain;
- current semantic roles and rejected suggestions;
- closed value mappings;
- date formats and domain qualifiers;
- currency state;
- preparation and mapping versions/digests in technical details;
- automatic actions applied under those decisions; and
- remaining unresolved decisions.

The review itself cannot save, infer or calculate authority.

### 6. Readiness and analysis

The final step displays the existing backend operation catalog and current state
for each operation. It adds operation coverage:

- total rows;
- rows eligible for that operation;
- excluded/failed rows by stable reason; and
- quality or semantic blockers.

“Analyze dataset” is enabled only when at least one current backend operation is
executable. The frontend never derives readiness from confirmation completion or
quality colors.

## Confirmation minimization rules

The system does not ask the user to approve:

- accepted UTF-8/BOM handling;
- uniquely detected delimiter;
- formula-free XLSX cell extraction;
- stable source row/column IDs;
- structural type observations;
- exact Decimal or ISO-date parsing as a structural representation;
- missingness/cardinality/parse counts;
- bounded examples/frequencies;
- source-preserving header comparison keys; or
- duplicate candidate detection.

The system always asks, unless exact approved evidence is already recorded and
version-compatible, for:

- semantic role;
- canonical domain;
- ambiguous date order;
- status/direction/actual-budget value meaning;
- cash amount convention;
- outstanding-balance meaning and reference date;
- currency.

V2.1 does not offer a generic confirmation that turns nonblank tokens such as
`NA` into missing values. It preserves them as source values or parse failures
and explains that the user may correct/re-export the source. This avoids making
a new cross-column null policy look like an ordinary semantic confirmation.

Applying an existing decision to the exact artifact it approved does not require
reconfirmation. Source, schema, profile, preparation or mapping incompatibility
invalidates dependent readiness and returns the affected decision to review.

## Semantic suggestions

The deterministic suggestion path remains first and authoritative only as a
proposal generator:

1. normalized source header comparison against the closed alias catalog;
2. structural compatibility evidence;
3. deterministic conflict detection; then
4. optional local-LLM assistance only for still-unknown proposals.

The optional local LLM continues to receive only a bounded profile/preparation
packet with sensitive examples suppressed. It may return only allowlisted roles,
`SUGGESTED|UNKNOWN`, bounded rationale and alternatives. It cannot:

- output a confirmation;
- change source/prepared values;
- choose a domain or operation;
- assign currency or value-map meaning;
- mark readiness;
- see the whole dataset; or
- become required for the manual workflow.

The UI labels deterministic and local-LLM proposals uniformly as suggestions,
while technical details may disclose the proposal source. Confidence remains an
evidence category, not a probability or approval threshold.

## Data-quality presentation

The UI uses the report levels consistently:

- `ERROR`: “Preparation could not be trusted” or exact operation blocker.
- `WARNING`: “Review recommended” with the limitation and coverage effect.
- `INFORMATION`: observed fact with no action required.
- `REQUIRES_CONFIRMATION`: explicit question and blocked dependent operation.

Colors/icons supplement the text; they do not carry meaning alone. Duplicate
candidates are never labeled duplicates, errors or fraud. Structural extremes
are never labeled bad data or risk.

## Explainability requirements

For each automatic action, the summary/details can answer:

- **What changed?** The exact derived representation, not a vague cleaning claim.
- **Why safe?** The deterministic precondition and automation class.
- **What was preserved?** Exact source bytes/token and lineage reference.
- **What failed?** Count, status and bounded source-row references.
- **What was refused?** The proposed/possible action and policy reason.
- **What needs confirmation?** The decision, evidence and dependent operations.
- **What blocks readiness?** Backend readiness reason and operation coverage.

Example:

> Parsed 982 values in `Invoice Amount` as exact decimals. The 18 values that
> did not match the approved numeric grammar remain unchanged and are excluded
> from amount-dependent operations. No value was replaced with zero.

## Resume and revision behavior

- A dataset can resume from its exact ID using current stored artifacts.
- Reopening shows saved decisions separately from pending choices.
- Revising a decision creates a new mapping version and invalidates dependent
  canonical/readiness projections.
- A source or sheet change creates a different source identity; it does not
  silently inherit decisions.
- Optional reuse on an exactly compatible schema remains outside automatic
  V2.1 behavior unless an explicit versioned approval is added later.
- Stop/reject remains explicit and does not delete preserved evidence.

## Accessibility and Institutional Workspace direction

V2.1 preserves the current Institutional Financial Workspace: restrained
hierarchy, equal gutters, business language first, technical evidence available
on demand, keyboard-native controls, visible focus, minimum touch targets and
textual status.

The preparation summary should be an open report, not a grid of decorative
cards. Confirmation groups should use responsive decision sections/cards rather
than a wide technical table on small screens. Exact values and decisions remain
available as text; no chart is required for onboarding quality.

## Frontend authority tests

The web implementation must prove that:

- changing any selector sends no mutation;
- upload sends no semantic/domain confirmation;
- automatic-action copy comes from typed backend projections;
- quality severity/readiness impact is not recomputed in TypeScript;
- every mutation has an explicit commitment action and required evidence;
- stale responses refresh instead of replaying a decision blindly;
- duplicate candidates remain retained and neutrally worded;
- unknown currency remains unknown; and
- analysis enablement uses current backend operation readiness only.
