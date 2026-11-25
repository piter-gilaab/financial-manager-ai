# Financial Manager AI V2.1 — Architecture

Status: **WP2 IMPLEMENTED — WP3 APPLICATION/API/WEB INTEGRATION PENDING**.

## Baseline inventory

Repository inspection at `v2.0.0` found the following reusable implementation:

| Existing module | Current responsibility to preserve |
|---|---|
| `src/onboarding/ingestion.py` | Safe regular-file read, exact byte preservation, deterministic CSV delimiter handling and bounded formula-free XLSX extraction |
| `src/onboarding/profiling.py` | Deterministic missingness, parseability, cardinality, duplicate-row candidate and bounded-example observations |
| `src/onboarding/semantics.py` | Closed role ontology, deterministic aliases/conflicts and optional bounded local-provider suggestions |
| `src/onboarding/decisions.py` | Explicit role/domain/value-map/date-format/qualifier decisions and append-oriented mapping versions |
| `src/onboarding/canonical.py` | Approved role-keyed canonical specs, exact Decimal/date normalization and source-row lineage |
| `src/onboarding/registry.py` | Content-addressed profiles/mappings, workflow current pointer, append-oriented registry versions and integrity digests |
| `src/onboarding/readiness.py` | Sole semantic/policy/execution readiness authority with operation-specific states |
| `src/onboarding/manager.py` | Small workflow facade coordinating onboarding modules |
| `src/execution/` and `src/financial/` | Approved mapping translation, artifact revalidation and deterministic operation authority |
| `src/application/datasets.py` | Transport-neutral dataset commands and safe projections |
| `src/api/datasets.py`, `schemas.py`, `multipart.py` | Typed local HTTP adapter, streaming upload staging and safe error/projection transport |
| `web/app/datasets/new` and onboarding components | Explicit upload/profile/semantic/domain/qualifier/review/readiness flow |

The current tests already protect ingestion bounds, source preservation,
profiling, semantic suggestion, explicit confirmation, registry integrity,
canonical lineage, readiness, Application/API delegation, upload security, web
commitment boundaries and real-API onboarding. V2.1 extends these test surfaces.

## Architecture decision

V2.1 adds one deep in-process preparation module inside `src/onboarding` and
extends existing artifacts/projections. It does not add a service, database,
queue, generic adapter framework or second onboarding pipeline.

```text
Local CSV/XLSX
  -> SafeFileIngestor
  -> DeterministicProfiler
  -> PreparationEngine (new deep module)
  -> SemanticMapper -> SemanticDecisionService
  -> CanonicalMapper
  -> DatasetRegistry
  -> CapabilityDiscovery
  -> FinancialManagerAgent -> binder/adapter -> Financial Core
  -> DatasetApplication -> FastAPI /api/v1 -> Web Financial Workspace
```

Dependencies point downward along this flow. Web/API/Application do not import
preparation implementation rules. Preparation does not import FastAPI, React,
the Manager or financial calculation modules. Readiness consumes typed quality
evidence; quality does not decide readiness.

## New module

### PreparationEngine

Provisional location: `src/onboarding/preparation.py`.

It owns:

- the closed safe-transformation catalog and versions;
- source-preserving structural preparation;
- transformation outcomes and refusal records;
- parse-failure and duplicate-candidate evidence;
- Data Quality Report construction;
- preparation/report digests; and
- reconstruction metadata.

Its small interface is defined in
[the preparation contract](v2_1_data_preparation_contract.md#preparation-interface).
Internal helpers may be split for readability, but they remain private seams and
are not independently selected by callers.

The deletion test justifies this module: without it, transformation
classification, quality severity, lineage and digest logic would spread across
profiling, canonicalization, registry, readiness, API and UI.

No adapter interface is introduced for preparation. There is one deterministic
in-process implementation and no genuine variation. Tests call the same public
interface as `OnboardingManager`.

## Modified responsibilities

### SafeFileIngestor

Preserve current parsing/security behavior. Extend the ingestion manifest only
as needed to expose stable deterministic inputs to preparation. It does not
normalize financial values or produce quality/readiness decisions.

### DeterministicProfiler

Remain the structural observation authority. Extend typed evidence where needed
for:

- explicit parse failure counts;
- separation of blank cells from unapproved null-token candidates;
- structural-type evidence/confidence; and
- deterministic bounded source-row references.

Profiling does not own transformation lineage or Data Quality Report severity.

### SemanticMapper

May consume a bounded preparation summary in addition to the profile. It retains
the current closed ontology and `SUGGESTED|UNKNOWN` provider limit. It cannot
read raw prepared rows from an LLM path or auto-confirm any role/domain/value.

### SemanticDecisionService

Retains exclusive authority for mapping/domain/value-map/date-format/qualifier
decisions. V2.1 adds no generic null-token authority endpoint: nonblank
null-like tokens remain preserved source values or parse failures. Supporting a
new persisted null-token contract would require a future explicit scope change.

### CanonicalMapper

Extend the current spec/output with:

- preparation digest;
- source fingerprint and source column ID at field lineage;
- ordered transformation IDs/versions/outcomes;
- source value and canonical value status; and
- canonical-view digest.

It continues to create role keys only from confirmed semantic mappings and to
preserve source values. It is not replaced by a generic dataframe cleaning
layer.

### DatasetRegistry

Persist content-addressed preparation manifests, Data Quality Reports and
canonical-view manifests alongside current source/profile/mapping artifacts.
Registry entries gain their digests/versions and current quality summary. Old
versions remain immutable.

### CapabilityDiscovery

Remain the sole readiness authority. Extend evaluation inputs to include a
validated current Data Quality Report/preparation identity and use only closed
readiness effects. It continues to revalidate adapters and current artifacts.
No quality-report message string becomes executable readiness logic.

### OnboardingManager

Coordinate the revised workflow:

```text
ingest -> profile -> prepare/assess -> suggest -> persist workflow
decision -> reassess -> canonical manifest -> register -> readiness
```

The manager exposes preparation and quality read projections but does not
implement their rules. Existing role/domain/qualifier methods remain the
authority-changing interface.

### Execution adapters and Financial Core

Consume the extended canonical view and quality coverage. Their operation keys,
financial formulas and readiness requirements do not change. Financial Core
continues to own exact values, aggregation, coverage and exclusions returned by
an operation. Preparation never precomputes authoritative financial totals.

## Persistence model

The existing local Git-ignored JSON artifact store remains sufficient.
Provisional layout:

```text
data/onboarding/
  artifacts/<dataset_id>/
    source/source.csv|xlsx
    ingestions/<ingestion_run_id>.json
    profiles/<profile_digest>.json
    preparations/<preparation_digest>.json
    quality/<quality_report_digest>.json
    mappings/<version>-<mapping_digest>.json
    canonical/<canonical_view_digest>.json
  workflows/<dataset_id>/current.json
  registry/<dataset_id>/versions/<version>.json
  registry/<dataset_id>/current.json
```

The canonical manifest describes reconstruction and does not need to duplicate
all source rows. If implementation benchmarks prove that a materialized local
row artifact is required, it must be content-addressed, data-only, bounded and
derived from the same contract; that optimization does not alter authority.

Workflow/registry current pointers reference exact artifact digests. Atomic
replace remains appropriate for small manifests. The store remains explicitly
single-user/single-writer and is not promoted to a concurrent database.

### Backward compatibility

- V2.0.0 artifacts retain their original schema/version readers.
- V2.1 never edits a V2.0.0 profile, mapping or registry version.
- A missing V2.1 preparation artifact is not fabricated in a projection.
- Explicit V2.1 reprocessing creates new append-only artifacts from preserved
  source and records the new versions/digests.
- Readiness fails closed if a V2.1 registry entry references missing, stale or
  mismatched preparation/quality artifacts.

## Application interface

`DatasetApplication` gains transport-neutral projections provisionally named:

```text
preparation(dataset_id) -> PreparationProjection
quality(dataset_id) -> DataQualityProjection
```

Existing `upload`, `profile`, `mappings`, `readiness` and decision commands stay
intact. The upload result may include preparation/quality summaries to avoid
immediate duplicate reads, but those are the same application projections, not
API-owned calculations.

Application types are frozen data classes/enums. They contain no Pandas frame,
filesystem path, callable, parser object or internal artifact content.

## HTTP interface

Additive local `/api/v1` routes:

- `GET /datasets/{dataset_id}/preparation`
- `GET /datasets/{dataset_id}/quality`

`POST /onboarding` may add `preparation` and `quality` summary fields to its
typed response. Existing profile/mapping fields remain.

The preparation projection includes safe transformation summaries, versions,
digests, refusal codes and unresolved decision identifiers. The quality
projection includes findings and operation coverage, with raw values omitted or
suppressed under existing privacy policy.

Existing mutation endpoints remain:

- `POST /datasets/{dataset_id}/mappings/decisions`
- `POST /datasets/{dataset_id}/domain-confirmation`
- `POST /datasets/{dataset_id}/qualifiers`
- `POST /datasets/{dataset_id}/lifecycle`

No batch mutation is required for V2.1. Visual confirmation grouping does not
change backend authority. If later evidence justifies an atomic batch, it needs
a separate strict schema, expected current mapping digest, all-or-nothing
decision-service transaction and its own acceptance update.

Request schemas remain closed and reject unknown fields. Callers cannot supply
an automation class, transformation identifier, readiness impact, authority
source, source path, parser, adapter, column expression, SQL, code or algorithm.

OpenAPI and generated TypeScript types are regenerated from the actual FastAPI
factory. Decimal/currency/missing-value encoding remains unchanged.

## Web interface

The existing `/datasets/new` route is refactored in place to the workflow in
[Smart Onboarding](v2_1_smart_onboarding.md). Reuse:

- upload/sheet clarification;
- semantic mapping controls;
- `DomainConfirmation` pending-state behavior;
- qualifier controls;
- `ApprovalReview`;
- backend operation readiness; and
- the central generated-type API client.

Add presentation modules only where they reduce page complexity, for example:

- preparation summary;
- quality findings/coverage;
- confirmation-group navigation; and
- automatic-action technical details.

These are presentation modules, not financial or readiness modules. They render
typed backend facts and send only existing explicit commands.

The dataset detail page adds preparation version/digest, quality summary and
operation coverage. It remains a read projection.

## Authority ownership

| Decision/fact | Authority |
|---|---|
| Accepted bytes, format, sheet structure | `SafeFileIngestor` under explicit sheet selection rules |
| Structural profile | `DeterministicProfiler` |
| Safe transformation and quality finding | `PreparationEngine` |
| Semantic/domain/value/date/currency/qualifier approval | `SemanticDecisionService` plus recorded user/source authority |
| Canonical role binding/value representation | `CanonicalMapper` applying exact approved contracts |
| Artifact identity/current projection | `DatasetRegistry` |
| Capability/operation readiness | `CapabilityDiscovery` and adapter revalidation |
| Financial values, aggregation and operation coverage | Financial Core/domain modules |
| Workflow coordination | `OnboardingManager` and `FinancialManagerAgent` |
| Transport validation/projection | Application/FastAPI |
| Pending controls, explicit gestures and display | Web frontend |
| Optional semantic assistance | Local LLM proposal only |

## Security and privacy

The existing trust model remains unchanged:

```text
Browser -> loopback FastAPI -> Application -> local deterministic modules
```

V2.1 adds no external upload, telemetry, analytics, cloud store, external model,
URL ingestion, database connection, credential, dynamic provider or public
deployment assumption. The local model remains optional and receives only the
bounded proposal packet.

Preparation artifacts follow existing path validation, safe IDs, atomic local
writes, integrity digests and path-free public errors. Transformation text is
not executed. Raw source values and sensitive examples do not enter logs or
generic errors.

## Performance assessment

The current ingestion/profile implementation is synchronous and bounded by 10
MiB, 100,000 rows, 64 columns and archive/cell limits. Its dominant work is
linear parsing/profiling plus hash-based duplicate candidate counting. V2.1 adds
another bounded linear pass and artifact serialization, creating moderate CPU
and memory regression risk but no architectural need for background systems.

Implementation guidance:

- reuse parsed rows inside one manager call; do not reopen/reparse merely to
  build each projection;
- avoid retaining multiple full row/cell representations when aggregate
  transformation outcomes suffice;
- keep examples, row references and frequencies bounded;
- use hash-based exact duplicate grouping, never pairwise comparison;
- materialize canonical rows on demand as today; and
- benchmark worst permitted shapes before release.

The measurable release budget is defined in the acceptance criteria. Failure to
meet it authorizes profiling/optimization inside the module, not distributed
infrastructure.

## Rejected alternatives

### Parallel “clean data” pipeline

Rejected because it would duplicate source/profile/mapping/registry/readiness
authority and make execution choose between artifacts.

### Dataframe exposed through Application/API

Rejected because it leaks implementation and encourages transport/frontend
calculation. Only typed data projections cross those seams.

### Frontend cleaning and confirmation

Rejected because browser state is not authority, is not reproducible and cannot
revalidate source/mapping digests.

### LLM-led preparation

Rejected because deterministic parsing/quality evidence exists and an LLM cannot
establish financial meaning or reproducibility.

### New database or job infrastructure

Rejected because current local bounds need neither concurrency nor distribution.

## Architecture review result

The design keeps financial authority in deterministic modules, semantic
authority in explicit decisions, readiness in one existing module and UI/API as
adapters. It introduces no hidden imputation/deletion, sign or currency
reinterpretation, duplicate deletion, locale date assumption, arbitrary query
path, LLM authority or V2.0.0 mutation.

## Implementation risks and open questions

The remaining items are implementation risks with frozen expected outcomes, not
product/specification questions:

- **Legacy null-token behavior:** V2.0.0 profiling/canonical helpers recognize
  named null-like tokens. V2.1 must version the conservative behavior for new
  preparation artifacts without changing legacy artifact interpretation.
- **Memory amplification:** current ingestion retains bytes and parsed rows;
  preparation must avoid another full independent cell graph and pass K03.
- **Report/readiness drift:** typed readiness effects and integration/property
  tests must prevent UI copy or free-form messages from becoming gates.
- **UX density:** confirmation groups must reduce scanning while preserving one
  explicit commitment per stored decision.
- **Backward artifact replay:** upgrade tests must exercise a copy of real
  V2.0.0-shaped local state, not only new synthetic V2.1 artifacts.

No open question blocks implementation. Concrete type/file names may be refined
without changing the documented interfaces, dependency direction or authority.
