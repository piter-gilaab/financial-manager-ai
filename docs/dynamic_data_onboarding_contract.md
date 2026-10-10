# Phase 13 — Dynamic Data Onboarding contract

## Purpose and invariant

Dynamic Data Onboarding accepts bounded local tabular files, preserves their
source bytes, profiles structural facts, proposes meanings from a closed
ontology, records explicit confirmation, and reports truthful capability
readiness. It does not make an arbitrary dataset executable by the Financial
Core.

> Source bytes and deterministic structural observations are facts. Semantic
> proposals are hypotheses. Critical meaning requires approved evidence or an
> explicit user decision. Capability availability additionally requires an
> implemented deterministic execution path.

The authority flow is:

```text
local user file
  -> safe ingestion and immutable source copy
  -> deterministic versioned profile
  -> bounded semantic suggestions
  -> explicit confirmation or unresolved meaning
  -> versioned domain-specific mapping
  -> local dataset registry
  -> deterministic semantic + execution readiness
  -> Financial Manager only when an executable adapter exists
```

## Module and interfaces

`src/onboarding` is one deep module. Its primary interface is a thin workflow
facade, `OnboardingManager`, that coordinates add, read-projection, semantic
decision and capability operations. It does not own parser, profiling, mapping,
persistence or readiness rules. Callers do not select parsers, storage paths
inside an entry, normalization functions, prompt text, or readiness rules.

The module concentrates rules behind narrower internal interfaces:

- safe tabular ingestion: local path + optional XLSX sheet -> data-only result;
- deterministic profiler: ingested table -> versioned structural profile;
- semantic provider: bounded profile packet -> strict proposal JSON;
- semantic decision service: proposal + explicit decision -> new mapping version;
- onboarding artifact store: append/version-oriented source, profile and mapping
  artifacts under one configured local root;
- dataset registry: validated current-entry projection over those artifacts;
- readiness evaluator: registered facts -> deterministic capability report.

The CLI is an adapter over `OnboardingManager`; it owns syntax and presentation
only. The existing manager, Financial Core, anomaly algorithms, query contracts,
session and mediation interfaces are unchanged in Phase 13.

## Lifecycle

The lifecycle vocabulary is:

| State | Meaning |
|---|---|
| `RECEIVED` | A bounded add operation has begun; no semantic claim exists. |
| `INGESTED` | Exact source bytes and an ingestion manifest were accepted in the local onboarding artifact store; this is not yet a registry entry. |
| `PROFILED` | A deterministic profile was produced for the exact source fingerprint. |
| `NEEDS_CONFIRMATION` | At least one required or critical meaning is unresolved. |
| `SEMANTICALLY_APPROVED` | The current mapping version has an explicitly approved canonical domain and all required meanings for that domain. |
| `REGISTERED` | A validated current-entry projection has been admitted to the dataset registry after its source, profile and mapping artifacts reconcile. |
| `READY` | Registration is valid and at least one current capability is actually executable against this dataset. |
| `BLOCKED` | Onboarding evidence is retained, but a stated semantic, quality, policy or implementation gate prevents readiness. |
| `REJECTED` | The source or onboarding decision is not eligible to proceed. |

Allowed forward transitions are:

```text
RECEIVED -> INGESTED | REJECTED
INGESTED -> PROFILED | BLOCKED | REJECTED
PROFILED -> NEEDS_CONFIRMATION | SEMANTICALLY_APPROVED | BLOCKED
NEEDS_CONFIRMATION -> SEMANTICALLY_APPROVED | BLOCKED | REJECTED
SEMANTICALLY_APPROVED -> REGISTERED | NEEDS_CONFIRMATION | BLOCKED
REGISTERED -> READY | BLOCKED | NEEDS_CONFIRMATION
READY -> NEEDS_CONFIRMATION | BLOCKED
BLOCKED -> NEEDS_CONFIRMATION | SEMANTICALLY_APPROVED | REJECTED
```

A correction never mutates an old mapping. It creates a new mapping version,
invalidates dependent readiness, and re-enters `NEEDS_CONFIRMATION` or
`SEMANTICALLY_APPROVED`. A changed source fingerprint is a new dataset/source
version and never silently reuses an incompatible mapping. `RECEIVED` and early
`REJECTED` may exist only in the returned operation result when path/file safety
prevents safe persistence.

`RECEIVED -> READY` is impossible. `READY` is not a synonym for “the model was
confident.” Phase 13 implements no generic Financial Core or anomaly adapter, so
newly onboarded datasets cannot reach `READY` in this phase; truthful terminal
outcomes are normally `NEEDS_CONFIRMATION`, `REGISTERED` followed by `BLOCKED`,
or `REJECTED`.

## Supported source types

Initial scope is local regular files only:

- CSV encoded as UTF-8 or UTF-8 with BOM;
- XLSX Open XML workbooks without macros, formulas, encryption or external links.

SQLite onboarding is deferred: accepting an arbitrary database would introduce
schema enumeration, query, extension and resource-control surfaces not needed for
local tabular onboarding. Also deferred are XLS/XLSM, live database connections,
credentials, cloud warehouses, Google Sheets, URLs, APIs and remote storage.

CSV delimiter selection is deterministic over an allowlist (comma, semicolon,
tab, pipe) and is followed by full-file width validation. Ambiguous delimiter,
duplicate/empty headers, inconsistent rows, invalid UTF-8, oversized fields and
malformed quoting are controlled rejections.

XLSX is parsed as bounded ZIP/XML data with the Python standard library. Archive
entry count, compressed/uncompressed bytes, expansion ratio, sheet count, rows,
columns and cell length are bounded. Macros and unsupported extensions are
rejected; formula cells are rejected rather than calculated or trusted as cached
facts. When multiple nonempty sheets exist, the caller must select one by its
exact workbook name. No workbook code or external relationship is executed.

## Source preservation and ingestion result

The user's original path is opened only after regular-file, symlink, extension,
size and content checks. It is never modified. Accepted exact bytes are copied
once under the ignored onboarding artifact-store root and named independently
of the user's path. Normal user output contains only the basename, never an
absolute path.

The ingestion manifest records at least:

- `dataset_id` and `ingestion_run_id`;
- source basename, detected format, optional sheet;
- SHA-256 and byte size;
- UTC ingestion timestamp supplied by a clock seam;
- ingestion contract version and applicable bounds;
- row/column counts and column names;
- locally available provenance: original basename and user-supplied provenance
  note when present.

Results and manifests contain plain JSON-compatible data only. No callable, SQL,
shell, import target or executable configuration can be stored.

## Profiling contract

Profiling precedes semantic interpretation and is deterministic for exact source
bytes plus profile version. It returns:

- row/column counts and ordered source column names;
- blank-cell counts and exact six-place percentages;
- distinct counts and exact duplicate-row candidate counts;
- primitive observations (`EMPTY`, `TEXT`, `INTEGER`, `DECIMAL`, `DATE`,
  `BOOLEAN`, `AMBIGUOUS_DATE`, `OTHER`);
- parse-success counts, unambiguous numeric/date ranges, decimal scale/sign and
  formatting observations;
- categorical cardinality and bounded frequent/example values;
- possible-identifier and likely-sensitive signals;
- explicit bounds, warnings, source fingerprint and profile version.

Source representation remains separate from structural type. A value such as
`$1,234.50` stays the original string while profiling may report a decimal-like,
monetary-formatted candidate. A symbol does not establish currency.

Numeric parsing uses `Decimal`, never binary float. Date ranges use only
unambiguous approved formats. A value such as `01/02/2026` is reported as
ambiguous and is not included in an authoritative date range until a user
approves a date-format contract.

Examples use first-observed deterministic order and bounded frequency summaries;
there is no random sampling. Likely identifiers, email-like values, long unique
numbers and other high-risk/high-cardinality columns suppress raw examples and
expose only pattern/count metadata. This is conservative screening, not a claim
of complete PII detection.

## Semantic mapping contract

The closed semantic-role ontology is:

```text
TRANSACTION_DATE, POSTING_DATE, DUE_DATE, AMOUNT, CURRENCY, DESCRIPTION,
ACCOUNT, CATEGORY, DEBIT_CREDIT_INDICATOR, VOUCHER_TYPE, DEPARTMENT, ENTITY,
COUNTRY, SEGMENT, PRODUCT, UNITS_SOLD, SALES, PROFIT, DISCOUNT, GROSS_SALES,
COGS, SALE_PRICE, MANUFACTURING_PRICE, INVOICE_ID, SUPPLIER, STATUS,
ACTUAL_BUDGET_INDICATOR, CASH_DIRECTION, BALANCE
```

Every stored mapping has `source_column`, stable column ID, proposed or approved
role (or null), one of `SUGGESTED | CONFIRMED | UNKNOWN | REJECTED | CONFLICT`,
`HIGH | MEDIUM | LOW | UNKNOWN` evidence category, bounded rationale,
`confirmation_required`, conflicts and bounded alternatives. Semantic-provider
output is narrower: it may emit only `SUGGESTED` or `UNKNOWN`. A provider output
that claims `CONFIRMED`, `REJECTED` or `CONFLICT` fails validation. Only the
semantic-decision service may assign `CONFIRMED`/`REJECTED`, and only the
deterministic proposal merger may assign `CONFLICT`.

Confidence is an evidence category, never an LLM probability:

- `HIGH`: exact approved alias plus structurally compatible values;
- `MEDIUM`: known alias or strong structural compatibility, but material context
  remains unresolved;
- `LOW`: plausible bounded alternative with weak/ambiguous evidence;
- `UNKNOWN`: no defensible proposal.

Even `HIGH` is a suggestion until its authority source is recorded. Conflicting
roles, duplicate exclusive roles and incompatible structural types remain
`CONFLICT`/`UNKNOWN`.

The optional local LLM receives only a bounded semantic packet: dataset-level
shape, source/sheet labels, column name/ID, structural observations, coverage,
cardinality, safe patterns and non-sensitive bounded examples. It never receives
the whole dataset. Column names, sheet names and values are untrusted JSON data,
not prompt instructions. Output is strict JSON over the closed ontology; unknown
keys/roles/types, code, SQL, shell, tool names or malformed output fail closed.
Provider failure leaves deterministic proposals or `UNKNOWN`; profiling and
manual confirmation remain usable.

## Confirmation contract

Only authoritative source metadata, an approved deterministic rule, explicit
user confirmation, or an existing approved project contract can establish
critical meaning. Phase 13 has no deterministic rule that silently establishes
financial meaning for arbitrary user columns.

Semantic-decision records are data-only and append/version-oriented. Each records the
decision (`CONFIRM`, `CORRECT`, `REJECT`), UTC timestamp, source column/ID,
previous proposal, approved role or null, bounded evidence note, optional closed
value mapping, authority source (`USER`, `SOURCE_METADATA`,
`EXISTING_CONTRACT`), and new mapping version/digest.

Explicit evidence is mandatory for currency, debit/credit or cash direction,
revenue/expense meaning, sale-versus-receipt, expense-versus-payment,
actual-versus-budget, invoice-versus-payment, settlement status, sign convention,
legal entity scope and fiscal-period meaning. In particular:

- `C`/`D` are not mapped to credit/debit without a confirmed closed value map;
- a currency column role does not confirm a denomination; a single ISO-like code
  becomes `CONFIRMED` only with explicit authority evidence;
- symbols, country and formatting never confirm currency;
- sales never become receipts, and accounting DR/CR never becomes cash direction.

Rejecting a proposal keeps that column unmapped. Correcting it names another
allowlisted role and records a new version. Cancelling/stopping onboarding moves
the dataset to `BLOCKED` or `REJECTED`; unresolved critical meaning never becomes
`READY`.

## Canonical financial domains

Phase 13 implements mapping/readiness descriptions for the two current domains:

- `ACCOUNTING_TRANSACTION`: an imported accounting record with approved posting
  date/amount semantics; it is not automatically expense, payment or cash;
- `SALES_RECORD`: an approved sales observation with its own measures and
  dimensions; it is not automatically revenue, receipt or company performance.

The registry may recognize but cannot execute `CASH_TRANSACTION`, `PAYABLE`,
`RECEIVABLE`, `BUDGET_RECORD`, `BALANCE_RECORD` and `DOCUMENT_METADATA`.
Recognition is a user-confirmed classification, not new business logic. No
universal transaction record is introduced.

## Registry and canonical mapping

The onboarding artifact store and dataset registry use versioned JSON manifests
under separate subdirectories of one ignored local root.
This fits the current single-user/offline architecture, keeps every artifact
inspectable, requires no schema migration or dependency, and supports atomic
replace of small current-pointer manifests. It is not a concurrent database and
must be revisited before multi-process or SaaS use.

Each entry records dataset/source IDs and versions, source type/fingerprint,
ingestion run, profile version/digest, mapping version/digest, mapping statuses,
unresolved semantics, quality/currency state, explicitly approved canonical
domain, observed date range, row count, lifecycle/readiness state, source-to-row
lineage policy and capability-readiness summary. Absolute source paths are never
part of user-facing projections.

Safe structural normalization is limited to validated UTF-8 decoding, XLSX cell
extraction without formula execution, explicit unambiguous date parsing,
validated Decimal observation and stable internal column/row IDs. Source values
remain unchanged. Sign inversion, DR/CR reinterpretation, currency assignment,
FX, sales-as-receipts, expense classification and financial imputation are
semantic transformations and are not implemented.

Lineage is:

```text
source SHA-256 + source basename + sheet
  -> source row number and stable column ID
  -> profile version/digest
  -> mapping version/digest and confirmation record
  -> domain-specific canonical role reference
  -> future capability result (not implemented in Phase 13)
```

## Capability readiness

Readiness is deterministic and separates:

1. semantic requirements satisfied;
2. policy/quality gates satisfied;
3. an implemented execution adapter exists.

For `FINANCIAL_ANALYSIS`, the semantic minimum is a confirmed supported domain
and the confirmed date/measure roles required by that domain. For
`ANOMALY_DETECTION`, a confirmed supported measure, at least 30 structurally
valid numeric values and an approved screening policy are additionally required.
No generic adapter or arbitrary-field screening policy is added in Phase 13, so
both capabilities remain execution-blocked for newly onboarded datasets.

`CASH_FLOW_FORECASTING` retains every existing gate: actual settled cash
semantics, target, entity/account perimeter, value date/calendar/completeness,
confirmed currency, comparable history (including the documented minimum cycles)
and chronological evaluation reserve. Sales, accounting direction, payables or
receivables do not satisfy actual-cash semantics.

`DOCUMENT_RETRIEVAL` retains the RAG gates. CSV/XLSX rows are structured tabular
data, not an approved document corpus. Onboarding them does not enable RAG.

Capability states are `AVAILABLE`, `BLOCKED`, or `BLOCKED_NOT_IMPLEMENTED`, with
separate `semantic_readiness` and `execution_readiness` fields and explicit
reasons. Only an actually callable, validated adapter may produce `AVAILABLE`.

## Privacy and security

All source bytes, profiles, mappings and registry artifacts stay local by
default. No telemetry, cloud storage, remote URL, external LLM or provider
fallback is added. The configured onboarding root is ignored by Git. Errors avoid absolute
paths and source contents.

Path traversal, directories/devices, symlinks, unsupported/mismatched formats,
oversize input, malformed CSV/XML/ZIP, formulas, macros, external workbook links,
archive expansion and excessive rows/columns/cells are controlled failures.
File/cell text cannot select imports, SQL, shell, tools or capabilities.

The semantic prompt has separate system rules and JSON data. Samples are bounded
and suppressed for likely-sensitive columns. Provider responses and hidden
reasoning are not persisted; only validated typed proposals and user decisions
are stored. This policy reduces exposure but is not filesystem encryption,
authentication, malware scanning or perfect PII detection.

## Versioning and reproducibility

Independent constants version ingestion, profiling, semantic ontology/prompt,
mapping and registry schemas. Reproduction requires exact source fingerprint,
selected sheet, ingestion contract/version and limits, profile version,
semantic mapping version/digest, confirmation records, normalization rules and
registry version. It never depends on “the LLM understood it once.”

A source change, sheet change, column order/name/type change, changed profile
algorithm, mapping correction or newly confirmed critical meaning produces a new
artifact/version and invalidates downstream readiness where relevant. A mapping
may be reused only after exact schema fingerprint compatibility and explicit
versioned approval; Phase 13 performs no automatic cross-source mapping reuse.

## Failure model

Expected failures return fixed, data-only codes and messages. Representative
codes include `unsafe_path`, `unsupported_format`, `source_too_large`,
`invalid_encoding`, `malformed_csv`, `malformed_xlsx`, `ambiguous_sheet`,
`limit_exceeded`, `profile_failed`, `semantic_provider_unavailable`,
`semantic_output_invalid`, `mapping_conflict`, `confirmation_required`,
`incompatible_schema`, `registry_corrupt` and `capability_blocked`.

No failure triggers another parser, network provider, lossy repair, row discard,
semantic guess, destructive cleanup or financial execution. Failed semantic
assistance preserves the deterministic profile and manual workflow. Corrupt or
inconsistent registry metadata blocks the dataset rather than selecting a nearby
version.

## Explicit non-goals

No Forecasting, RAG, AP/AR business logic, generated query contracts, generic
financial execution, arbitrary SQL/code, auto-cleaning, deduplication, imputation,
outlier modification, currency inference/conversion, API/frontend,
authentication, multi-user concurrency, remote ingestion or Phase 14 work is
authorized by this contract.
