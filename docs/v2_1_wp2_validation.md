# Financial Manager AI V2.1 — Work Package 2 Validation

Status: **IMPLEMENTED AND VALIDATED — READY FOR WP3 REVIEW** (2026-11-25).

This record covers only Work Package 2, Deterministic Preparation & Data
Quality. It does not authorize or implement the Work Package 3 API/Web UX.
`v2.0.0` remains the immutable baseline at `e838ec1626ab`.

## Implemented module and contracts

`src/onboarding/preparation.py` adds the in-process `PreparationEngine` behind
the approved `prepare` and `assess` seam. The module owns structural preparation
evidence, bounded duplicate candidates, quality findings and deterministic
digests. It does not own semantic decisions, currency, readiness, financial
calculation or anomaly classification.

The versioned artifacts are:

- preparation manifest `1.0`, stored by preparation digest;
- Data Quality Report `1.0`, stored by report digest;
- prepared canonical mapping manifest `1.1`, stored by canonical-view digest;
- additive optional references from existing workflow/registry projections.

Existing registry and workflow schema versions remain `1.0`. Missing V2.1
references retain the V2.0.0 reader path and are not fabricated or rewritten.

## Automatic structural behavior

The implementation records the closed, versioned transformations appropriate
to the accepted source format:

- UTF-8 decode and UTF-8 BOM removal for the parse view;
- deterministic allowlisted CSV delimiter selection;
- constrained, formula-free XLSX data-cell extraction;
- derived collision-aware header comparison keys;
- structural blank classification and whitespace-only parse views;
- exact base-10 Decimal parse attempts;
- allowlisted ISO `YYYY-MM-DD` parse attempts;
- preserved text, structural type/confidence, missingness and cardinality;
- bounded parse-failure row references and repeated-value summaries; and
- hash-based exact source-row duplicate candidate detection.

Every source token remains in the immutable ingested artifact. Preparation
metadata contains counts and bounded references, not a second raw dataset.
Canonical field results expose the stable source column ID, raw source token,
ordered transformation IDs/versions/outcomes, canonical value/status, source
fingerprint, selected sheet and actual source row number.

## Explicit non-transformations

The manifest records refusals for financial imputation, row deletion,
duplicate merge, outlier modification, sign mutation, currency inference, FX,
cash-direction inference, debit/credit reinterpretation, profit
reconstruction, outstanding-balance inference, semantic confirmation and
domain confirmation. Ambiguous date order and null-like-token interpretation
are `SUGGEST_ONLY` refusals.

No missing or malformed amount becomes zero. No duplicate candidate is deleted,
merged, invalidated or classified as a duplicate fact. No machine locale,
timezone, filename, language, LLM state or clock participates in date authority
or preparation identity.

## Reproducibility and integrity

Preparation identity is SHA-256 over canonical JSON containing stable source,
sheet, ingestion/profile/preparation versions, effective bounds, structural
configuration and bounded outcomes. It excludes timestamps, source basenames,
temporary paths, ingestion run IDs, random values and provider conversation.
The quality digest additionally binds the current preparation/profile/mapping
identities. The prepared canonical-view digest binds preparation and approved
semantic mapping identities.

Preparation, quality and canonical artifacts fail closed on content-digest or
identity mismatch. Authorized semantic changes create a new quality/canonical
artifact without changing the immutable preparation digest.

## Quality and readiness boundary

The report supports the closed levels `ERROR`, `WARNING`, `INFORMATION` and
`REQUIRES_CONFIRMATION`, with closed readiness-effect references. It contains
row/column counts, structural type/confidence, blank/null-like evidence, parse
results, ambiguous dates, exact/key-based duplicate candidates, unresolved
decisions, currency state and bounded remediation evidence.

`CapabilityDiscovery` remains the sole readiness authority. It authenticates a
supplied current quality report but does not derive readiness from warning text
or severity. Tests prove the same readiness result with and without a valid
warning-bearing quality report and failure on a stale mapping identity. The
optional `assess(..., readiness_report=...)` input authenticates and records
bounded capability references; it does not calculate or override those states.

## Compatibility and integration boundary

The existing `CanonicalMapper` accepts an authenticated preparation manifest
and produces the additive `1.1` lineage/digest contract. The registry persists
that canonical manifest during V2.1 registration. Existing execution adapters
continue using their V2.0 `1.0` canonical execution contract in WP2 so existing
operation output and legacy null-marker behavior remain unchanged. Switching
Application/API/Web and execution projections to the prepared contract is an
explicit integration concern for WP3, not a silent WP2 behavior change.

A checked-in workflow/registry fixture was produced by running the tagged
`v2.0.0` source from `git archive` at the fixed baseline commit, then copied as
data-only test evidence. It has no preparation/quality fields, remains readable,
and is byte-identical after V2.1 read operations. V2.1 reads do not silently
migrate or rewrite it.

## Performance evidence

Reference environment: Linux 6.18.58-1-lts x86_64, Python 3.14.8, Intel Core
i5-7300HQ at 2.50 GHz, four logical CPUs. Peak RSS is Python
`resource.getrusage(RUSAGE_SELF).ru_maxrss` on Linux. Each figure covers a fresh
process performing local source generation followed by
`OnboardingManager.add`, through persisted quality projection.

| Fixture | Shape / source bytes | Wall time | Peak RSS |
|---|---:|---:|---:|
| Row limit | 100,000 × 4 / 3,027,811 bytes | 3.173 s | 119,972 KiB |
| Column limit | 15,000 × 64 / 4,662,783 bytes | 9.382 s | 115,856 KiB |
| Near byte + row limit | 100,000 × 4 / 9,477,934 bytes | 3.370 s | 152,872 KiB |

All are below the approved 30-second and 512-MiB budgets. Preparation uses
linear column/row passes and hash maps; duplicate evidence and row references
are bounded, and no pairwise row comparison is used.

## Validation gates

- focused V2.1 preparation tests: deterministic replay, source preservation,
  manifest/report integrity, Decimal exactness, ambiguous dates, missing-not-zero,
  header collisions, duplicates, refusals, canonical lineage and bounded evidence;
- onboarding regression, including V2.0.0-shaped artifact compatibility;
- API security and privacy regression, including inert hostile cell content;
- complete backend regression;
- Python compile check and `git diff --check`;
- focused standards, specification and architecture review.

Final validation results:

- focused V2.1 preparation/quality: **10 passed, 0 failed**;
- complete onboarding regression: **73 passed, 0 failed**;
- security/privacy regression: **23 passed, 0 failed**;
- canonical/readiness/binding/adapter compatibility: **62 passed, 0 failed**;
- complete backend regression: **788 passed, 0 failed** in 648.936 seconds;
- Python `compileall`: **PASS**;
- `git diff --check`: **PASS**.

The focused groups overlap the complete backend count and are not additive.
Final Standards review found no hard breach. Final Spec review found no
remaining defect; it accepted operation-specific row coverage ownership as the
documented non-blocking limitation below. The architecture review found no
financial/semantic/readiness authority leakage, hidden cleaning, external
runtime expansion or V2.0.0 mutation.

## Known limitations

- WP3 typed Application/API projections and Web preparation/quality screens are
  intentionally absent.
- Operation-specific eligible/excluded row coverage remains owned by the
  existing deterministic operation adapters; the quality report references
  structural impacts and does not invent coverage or readiness.
- Key-based duplicate detection is initially limited to the explicitly
  confirmed `INVOICE_ID` key contract.
- No FX conversion, financial imputation, automatic deduplication or external
  provider behavior exists.
