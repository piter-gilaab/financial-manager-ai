# Financial Manager AI V2.1 — Automated Data Preparation Contract

Status: **WP2 IMPLEMENTED — CONTRACT REMAINS AUTHORITATIVE FOR WP3–WP4**.

## Purpose

V2.1 adds a deterministic preparation step between the existing structural
profile and semantic approval. It automatically performs only transformations
that cannot change financial meaning, records what it did and refused to do,
and supplies quality evidence to the existing semantic and readiness authorities.

The invariant is:

> Raw source bytes and source tokens remain immutable. A prepared value is a
> traceable derived representation, not a replacement for its source and not an
> unrecorded financial interpretation.

## Existing contracts reused

The implementation must extend, not replace:

- `SafeFileIngestor` for bounded CSV/constrained-XLSX parsing and exact source
  preservation;
- `DeterministicProfiler` for structural observations and bounded examples;
- `SemanticMapper` for closed-ontology suggestions;
- `SemanticDecisionService` for explicit, append-oriented authority changes;
- `CanonicalMapper` for role-keyed canonical views and per-row lineage;
- `DatasetRegistry` for content-addressed artifacts and current projections;
- `CapabilityDiscovery` for current operation-specific readiness; and
- `OnboardingManager` as the small workflow interface used by Application/API.

No second registry, generic data platform, universal financial transaction or
parallel readiness engine is introduced.

## Terms

**Preparation run** is a deterministic derivation for one exact source
fingerprint and selected sheet under one preparation version. It produces a
preparation manifest and Data Quality Report. Its digest excludes clocks and
random run identifiers.

**Prepared structural value** is a source token plus zero or more explicitly
named structural representations, such as an exact Decimal parse or ISO date
parse. It carries no financial role by itself.

**Approved canonical value** is a prepared structural value associated with a
confirmed semantic role under a specific semantic mapping digest. It does not
erase the source token.

**Duplicate candidate** is a pair or group selected by a stated deterministic
comparison rule for review. It is not a finding that two rows represent the
same financial fact.

**Operation coverage** is the count of source rows eligible, excluded or failed
for one exact operation under current approved semantics. There is no universal
financially “usable row” count independent of an operation.

## Automation decision matrix

The class includes the stated precondition. Removing a precondition changes the
classification and is not permitted without changing this contract.

| Action | Class | Preconditions / required behavior | Why |
|---|---|---|---|
| Accept UTF-8 and remove a UTF-8 BOM for parser input | `SAFE_AUTOMATIC` | Exact bytes and encoding remain in the ingestion manifest | BOM handling changes representation, not content |
| Guess a non-UTF-8 encoding or decode with replacement | `PROHIBITED_AUTOMATION` | Reject with a controlled encoding error | A wrong guess can corrupt identifiers and values |
| Select CSV delimiter | `SAFE_AUTOMATIC` | Exactly one allowlisted delimiter passes full-width validation | Existing deterministic structural rule |
| Choose among ambiguous delimiters | `PROHIBITED_AUTOMATION` | Reject; no parser fallback | Choice can change table structure |
| Extract formula-free XLSX cell text | `SAFE_AUTOMATIC` | Existing ZIP/XML/sheet/formula/macro/link bounds pass | Data-only structural extraction |
| Select an XLSX sheet | `SUGGEST_ONLY` | One non-empty sheet may proceed automatically; multiple sheets require explicit selection | Sheet selection changes dataset identity |
| Create a normalized header comparison key | `SAFE_AUTOMATIC` | Preserve exact header; key is derived, versioned and collision-checked | Supports matching without renaming source |
| Rename or merge source columns | `PROHIBITED_AUTOMATION` | Canonical roles are separate references | Can erase distinctions or change meaning |
| Trim whitespace for a parsing attempt | `SAFE_AUTOMATIC` | Preserve raw token; record `TRIM_FOR_PARSE`; never trim canonical preserved text | Parsing view only |
| Rewrite descriptive/identifier text with trimmed/cased text | `PROHIBITED_AUTOMATION` | Source text is always preserved in V2.1 | May change identity or meaning |
| Treat an empty or whitespace-only cell as structurally blank | `SAFE_AUTOMATIC` | Preserve raw token and blank evidence | No financial value is invented |
| Treat `NA`, `N/A`, `NULL`, `NONE` or another token as missing | `SUGGEST_ONLY` | V2.1 may flag the interpretation but preserves the token; conversion is outside V2.1 | Tokens can be legitimate category values |
| Parse a full token exactly as `Decimal` | `SAFE_AUTOMATIC` | Versioned grammar; no binary float, rounding or scale loss; preserve raw token | Structural representation only |
| Parse a partial or locale-guessed number | `PROHIBITED_AUTOMATION` | Record parse failure | Thousands/decimal separators may be ambiguous |
| Parse allowlisted ISO `YYYY-MM-DD` dates | `SAFE_AUTOMATIC` | Calendar-valid full-token match; no machine locale | Unambiguous versioned rule |
| Choose `DD/MM/YYYY` vs `MM/DD/YYYY` | `SUGGEST_ONLY` | Explicit date-format decision required unless existing approved evidence already resolves it | `01/02/2026` is ambiguous |
| Apply an already approved date-format contract | `SAFE_AUTOMATIC` | Mapping digest and source column match; failures remain failures | Choice already has authority |
| Detect structural type and retain evidence counts | `SAFE_AUTOMATIC` | Deterministic rules and version recorded | Structural fact, not financial role |
| Measure missingness, cardinality and parse success/failure | `SAFE_AUTOMATIC` | Raw values preserved; sensitive examples suppressed | Observational diagnostics |
| Produce bounded examples/frequencies | `SAFE_AUTOMATIC` | First-observed deterministic order and existing privacy suppression | Reproducible evidence |
| Count exact duplicate-row candidates | `SAFE_AUTOMATIC` | Compare complete preserved source-token tuples; retain every row | Candidate detection only |
| Detect key-based duplicate candidates | `SAFE_AUTOMATIC` | Key roles and comparison normalization already explicitly approved; rule/version shown | Applies existing authority without deleting |
| Choose a deduplication key | `SUGGEST_ONLY` | User must approve the key/meaning if V2.1 exposes such a review | Key choice is semantic |
| Delete, collapse or merge duplicate candidates | `PROHIBITED_AUTOMATION` | Retain each source row | Repeated rows can be legitimate facts |
| Report numeric min/max or structural extremes | `SAFE_AUTOMATIC` | Descriptive only; no error/fraud label | Observation does not alter data |
| Remove, winsorize or replace outliers | `PROHIBITED_AUTOMATION` | Existing anomaly screens remain separate | Outlier does not mean bad data |
| Suggest a semantic column role | `SUGGEST_ONLY` | Closed ontology, evidence and alternatives; deterministic first, optional bounded local LLM second | Financial meaning requires authority |
| Confirm a semantic role from alias/confidence | `PROHIBITED_AUTOMATION` | Explicit decision still required | Even `HIGH` is not authority |
| Suggest a dataset domain | `SUGGEST_ONLY` | Closed domain list and evidence | Domain affects financial contracts |
| Confirm or change dataset domain | `PROHIBITED_AUTOMATION` | Explicit domain confirmation required | Domain is financial authority |
| Suggest status, debit/credit, cash-direction or actual/budget value meanings | `SUGGEST_ONLY` | Closed values and complete observed-value evidence | Value codes are source-specific |
| Decide cash direction from sign | `PROHIBITED_AUTOMATION` | Require confirmed direction semantics and amount convention | Sign alone is not cash direction |
| Change transaction signs | `PROHIBITED_AUTOMATION` | Preserve exact numeric value | Changes authoritative amount |
| Assign currency from a confirmed complete ISO value map | `SAFE_AUTOMATIC` | Apply the existing approved mapping; retain original token | Authority already exists |
| Infer currency from symbol, geography, language, filename, domain or LLM | `PROHIBITED_AUTOMATION` | State remains `UNKNOWN` | Evidence is insufficient |
| Perform FX conversion | `PROHIBITED_AUTOMATION` | No V2.1 conversion path | Outside scope |
| Suggest amount basis or cash amount convention | `SUGGEST_ONLY` | Closed qualifier choices and supporting evidence | Changes operation meaning |
| Guess outstanding balance | `PROHIBITED_AUTOMATION` | Require explicit `OUTSTANDING_BALANCE` evidence | Invoice amount is not necessarily open balance |
| Impute a financial amount, date, status, currency or dimension | `PROHIBITED_AUTOMATION` | Missing stays missing | Invents facts |
| Reconstruct Profit or another financial measure | `PROHIBITED_AUTOMATION` | Use only a confirmed supplied role or existing Core operation | Derived meaning is outside preparation |
| Interpret debit/credit as income/expense or cash in/out | `PROHIBITED_AUTOMATION` | Preserve confirmed debit/credit mapping only | Accounting direction is not business meaning |
| Create canonical role keys after semantic approval | `SAFE_AUTOMATIC` | Exact approved mapping digest; raw source remains attached | Applies recorded authority |
| Reuse a mapping on changed source/schema | `PROHIBITED_AUTOMATION` | Exact compatibility plus explicit versioned approval is required | Prevents silent semantic drift |

## Preparation interface

V2.1 introduces one deep in-process module inside `src/onboarding`, provisionally
named `PreparationEngine`. Its external interface is intentionally small:

```text
prepare(ingested_dataset, structural_profile) -> PreparationResult
assess(preparation_result, semantic_mapping?, readiness_report?) -> DataQualityReport
```

The exact Python type names may change during implementation, but the seam and
observable contract may not. Callers do not choose transformation functions,
null grammars, parsers, digests, sampling methods or lineage policies.

`PreparationResult` contains at least:

- `dataset_id`, source fingerprint, selected sheet and ingestion run reference;
- `preparation_version` and `preparation_digest`;
- profile version/digest used as input;
- ordered transformation definitions and versions;
- aggregate transformation outcomes by column;
- transformations performed and transformations refused;
- parse failures with counts and bounded source-row references;
- exact/key-based duplicate candidate summaries.

It contains data only. It cannot hold callables, SQL, expressions, import names,
filesystem paths, provider requests or executable adapter configuration.

## Transformation vocabulary

The preparation ledger uses closed identifiers. The initial set is:

```text
UTF8_DECODE
UTF8_BOM_REMOVE_FOR_PARSE
CSV_DELIMITER_SELECT
XLSX_DATA_CELL_EXTRACT
HEADER_COMPARISON_KEY
BLANK_CLASSIFY
TRIM_FOR_PARSE
PARSE_DECIMAL_EXACT
PARSE_ISO_DATE
PARSE_APPROVED_DATE_FORMAT
PRESERVE_TEXT
CANONICAL_ROLE_BIND
```

Each transformation definition records:

- identifier and implementation version;
- input representation and output representation;
- deterministic preconditions;
- failure status and whether failure is row/operation blocking;
- source-preservation statement; and
- automation class.

Adding a transformation identifier requires a contract and acceptance update.
Free-form transformation names are not accepted from users or providers.

## Canonical output

The canonical output is a deterministic logical view, materialized on demand by
the existing `CanonicalMapper`/execution adapters. V2.1 does not require a
second full persisted copy of every row. The artifact store persists the source,
preparation manifest, quality report, semantic decisions and canonical-view
manifest/digest; adapters may reconstruct the exact row view from those inputs.

Before semantic approval, the prepared structural representation has stable
source column IDs but no financial role keys. After approval, arbitrary source
names map to canonical role keys such as `AMOUNT`, `DUE_DATE` or `SALES` under
the exact mapping digest. The original header and raw token remain present in
lineage.

Each canonical field result has this conceptual shape:

```json
{
  "role": "AMOUNT",
  "source": {
    "dataset_id": "ds_...",
    "source_fingerprint": "sha256...",
    "sheet": null,
    "source_row_number": 14,
    "source_column_id": "col_...",
    "source_column": "Valor",
    "source_value": " 1,234.50 "
  },
  "transformations": [
    {"id": "TRIM_FOR_PARSE", "version": "1.0", "status": "APPLIED"},
    {"id": "PARSE_DECIMAL_EXACT", "version": "1.0", "status": "APPLIED"},
    {"id": "CANONICAL_ROLE_BIND", "version": "1.0", "status": "APPLIED"}
  ],
  "canonical_value": "1234.50",
  "value_status": "PARSED"
}
```

The actual projection may use more compact keys, but it must answer the same
lineage questions without consulting logs or model conversations.

## Source preservation and lineage

Accepted exact source bytes remain under the existing Git-ignored artifact root
and are never modified. Every canonical value must resolve this complete chain:

```text
dataset ID
  -> source SHA-256
  -> selected sheet (or CSV)
  -> preserved source row number
  -> stable source column ID and exact header
  -> exact source token
  -> ordered transformation IDs/versions/outcomes
  -> approved semantic mapping digest, when applicable
  -> canonical role and value/status
```

Public/API projections may redact raw values or examples under the existing
privacy policy. Redaction does not remove the local lineage link.

## Missing-value contract

`MISSING != ZERO` is mandatory.

- Empty and whitespace-only cells may be classified structurally blank while
  preserving their exact token.
- Zero, `0.00`, `false`, an empty string and a parse failure are distinct.
- Named null markers such as `NA` are candidates until source metadata or an
  explicit contract establishes their meaning for canonical use.
- No amount, date, status, currency, category or dimension is imputed.
- A missing required value excludes that row only from operations requiring the
  value, unless the existing operation contract blocks the whole operation.
- Coverage reports total, eligible, excluded and failed rows with reason counts.
- Existing V2.0.0 artifacts retain their versioned legacy behavior; V2.1 does
  not silently reclassify their tokens in place.

## Date contract

- The automatic date allowlist initially contains calendar-valid ISO
  `YYYY-MM-DD` only, matching the current unambiguous path.
- Date parsing never reads machine locale, timezone locale or browser locale.
- `01/02/2026` and all other day/month-order ambiguous forms remain unresolved
  until an explicit `DD/MM/YYYY` or `MM/DD/YYYY` contract is recorded.
- Once approved for the exact column/mapping, applying that format is automatic
  and reproducible; invalid values remain parse failures.
- Date min/max and operation ranges exclude unresolved or failed values and
  disclose that exclusion.
- The current dataset reference-date qualifier remains a separate financial
  decision. It is not inferred from file dates or the current clock.

## Currency contract

The only states are:

```text
UNKNOWN
CONFIRMED
CONFIRMED_MULTIPLE
```

Symbols and monetary formatting are structural observations only. No currency
is inferred from `$`, geography, language, filename, domain, local settings or
an LLM. A confirmed complete ISO value map may be applied automatically after
approval. V2.1 performs no FX conversion. `CONFIRMED_MULTIPLE` remains an
operation-specific aggregation blocker where the existing contract requires a
single comparable currency.

## Duplicate contract

### Exact duplicate candidate

Two or more accepted source rows whose complete ordered source-token tuples are
equal. Source row numbers are not part of the comparison and are retained for
each occurrence. No whitespace, case, sign, date or null-token reinterpretation
is used to declare exact equality.

### Key-based duplicate candidate

Two or more rows whose values match under an explicitly identified comparison
key and versioned normalization. Key-based detection is permitted only after
the relevant key semantics/normalization are approved. The report states the
key and never calls the rows duplicates without the word “candidate.”

### Legitimate repeated transaction

A repeated row or key can represent recurring charges, installments, separate
invoices, split postings, corrections or legitimately repeated events. V2.1
does not automatically distinguish or merge these cases.

### Review and readiness

Candidates remain in the prepared/canonical view. The UI groups bounded source
row references for review. Candidate presence is normally `WARNING` or
`INFORMATION` and does not block readiness unless an existing operation contract
explicitly requires uniqueness. No current V2 operation gains such a requirement
merely because V2.1 reports candidates.

## Data Quality Report

The report is versioned and content-addressed. It contains:

- dataset/source/sheet/preparation/profile/mapping identities;
- total accepted rows and structurally accepted rows;
- per-column missing/blank/null-candidate counts;
- exact parse successes and failures;
- ambiguous-date counts;
- exact and key-based duplicate candidate counts;
- structural type, evidence counts and confidence category;
- unresolved semantic fields and confirmation groups;
- currency state;
- transformations applied/refused;
- operation-specific coverage and exclusions; and
- explicit readiness impact.

### Finding levels

| Level | Meaning | Default readiness effect |
|---|---|---|
| `ERROR` | Integrity, safety or required canonicalization failed; the affected artifact/result cannot be trusted | Blocks the affected dataset or operation |
| `WARNING` | A real limitation or candidate condition may reduce coverage or require review, but is not proof of bad data | Limits coverage unless an existing contract says otherwise |
| `INFORMATION` | Descriptive structural evidence with no decision required | None |
| `REQUIRES_CONFIRMATION` | A financially meaningful or structurally ambiguous choice lacks authority | Blocks only dependent roles/operations |

Each finding records a stable code, level, scope, evidence summary, count,
bounded row references, readiness effect and remediation action when one exists.
A warning cannot silently become a blocker in presentation code.

### Row counts

The report avoids a misleading single “usable rows” number:

- `total_rows`: all accepted source data rows;
- `structurally_accepted_rows`: rows admitted by the safe tabular parser (normally
  equal to `total_rows` because malformed-width files are rejected);
- `operation_coverage[operation].eligible_rows`;
- `operation_coverage[operation].excluded_rows`; and
- `operation_coverage[operation].exclusions_by_reason`.

The UI may label `eligible_rows` as “usable for this analysis” only beside the
exact operation name.

## Readiness impact

The Data Quality Report provides evidence; `CapabilityDiscovery` decides
readiness. It consumes only typed findings/coverage and existing semantic,
policy and adapter facts. It does not import messages or UI severity colors.

Readiness effects are closed values:

```text
NONE
LIMITS_COVERAGE
BLOCKS_OPERATION
BLOCKS_DATASET
```

Missing optional dimension values usually limit or partition coverage. Missing
required measures/dates, parse failure leaving no eligible values, stale
artifacts, unresolved critical semantics and integrity errors can block only the
dependent operation or dataset according to existing contracts.

## Reproducibility and digests

The preparation digest is SHA-256 over canonical JSON containing only stable
inputs and results:

- source SHA-256 and selected sheet;
- ingestion contract/version and effective bounds;
- ordered exact headers and stable column IDs;
- profile version/digest;
- preparation version and closed transformation definitions;
- structural outcomes, counts and bounded deterministic references.

Timestamps, temporary paths, random ingestion run IDs and source basenames do
not influence the preparation digest.

The Data Quality Report has its own digest. It includes the preparation digest
and, when present, the current semantic mapping and readiness identities. A
mapping decision can therefore create a new quality report without changing the
immutable structural preparation digest.

The canonical-view digest additionally includes:

- preparation digest;
- canonical mapping version;
- semantic mapping digest, including approved value maps/qualifiers; and
- canonical transformation outcomes.

Therefore the same source bytes, sheet, effective versions/bounds and approved
decisions produce the same preparation and canonical-view digests. An optional
LLM conversation is never a reconstruction input.

## Failure model

Preparation fails closed. Representative stable codes include:

```text
preparation_artifact_mismatch
preparation_digest_mismatch
unsupported_transformation
canonical_parse_failure
ambiguous_date_contract_required
null_token_contract_required
quality_report_corrupt
quality_report_stale
confirmation_required
operation_coverage_unavailable
```

A failure never triggers a lossy parser, encoding guess, row deletion, value
repair, network provider, semantic confirmation or fallback transformation.

## Performance contract

Preparation remains local and synchronous within the current 10 MiB, 100,000
row, 64 column and cell/archive bounds. The implementation uses deterministic
linear passes and bounded summaries. Exact duplicate detection may use a hash
map/set bounded by accepted rows. It must not perform pairwise row comparison,
unbounded sampling, external calls or load a second independent data platform.

No Spark, queue, worker service, PostgreSQL or distributed system is justified.
If measured work at current bounds cannot meet the release budget in the
acceptance criteria, optimization must deepen the existing in-process module;
it does not authorize new infrastructure.

## Security and privacy

- All artifacts remain in the configured local Git-ignored onboarding root.
- No preparation data, sample or report is uploaded externally.
- No telemetry or analytics event is added.
- Raw values remain suppressed from public projections where the existing
  sensitive/high-cardinality policy applies.
- Transformation identifiers are code-owned allowlisted data, never executable
  user input.
- API callers cannot select parsers, filesystem paths, adapters, formulas, SQL,
  Python, shell, import targets or algorithms.
- Existing CSV/XLSX path, size, archive, XML, formula, macro, external-link and
  multipart protections remain mandatory.
