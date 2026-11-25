# Financial Manager AI V2.1 — Acceptance Criteria

Status: **FROZEN GATES — WP2 IMPLEMENTED; WP3–WP4 PENDING**.

Every mandatory criterion below requires automated evidence unless marked as a
review. V2.1 release requires all criteria to pass, no skipped mandatory test,
zero unresolved BLOCKER and zero unresolved HIGH correctness, authority,
security, privacy or integrity issue.

## A. Source and deterministic preparation

| ID | Criterion | Required evidence |
|---|---|---|
| A01 | Original source is immutable | Byte-for-byte SHA-256 before/after onboarding and replay is identical; source file is never written |
| A02 | Exact accepted bytes are locally preserved | Artifact digest matches upload bytes for CSV and XLSX; public projections contain no absolute path |
| A03 | Sheet is part of source identity | Same workbook/different selected sheet produces distinct deterministic identity/preparation; multiple non-empty sheets require explicit choice |
| A04 | Preparation is versioned | Projection/artifact contains preparation version, profile digest, source fingerprint and transformation versions |
| A05 | Preparation is deterministic | Repeated preparation of same stable inputs produces byte-equivalent canonical manifest and identical preparation/quality digests |
| A06 | Safe actions are closed | Every performed transformation is an allowlisted `SAFE_AUTOMATIC` identifier with preconditions and outcome |
| A07 | Refused actions are visible | Contract-relevant transformations not performed are represented with stable refusal/confirmation codes |
| A08 | No opaque chain exists | Every canonical field resolves source file/sheet/row/column/raw token, ordered transformations and canonical value/status |
| A09 | Existing V2.0.0 artifacts are not mutated | Before/after hashes and registry version files prove no in-place migration or relabeling |
| A10 | V2.0.0 compatibility is explicit | Legacy artifacts remain readable under legacy versions; explicit V2.1 reprocessing creates append-only artifacts |

## B. Safe automatic transformation

| ID | Criterion | Required evidence |
|---|---|---|
| B01 | UTF-8/BOM and unique delimiter handling are deterministic | UTF-8, BOM, comma/semicolon/tab/pipe fixtures pass; ambiguous delimiter and invalid encoding fail closed |
| B02 | Header handling preserves source | Derived comparison key is stable and collision checked; exact header remains in every lineage path |
| B03 | Whitespace is parse-view only | Numeric/date parse may trim under a recorded step; canonical preserved text and raw token remain unchanged |
| B04 | Exact numeric parsing uses Decimal | Accepted values preserve sign/scale information with no binary float, rounding or partial parse |
| B05 | Only allowlisted unambiguous dates parse automatically | Valid ISO dates pass; invalid/locale-dependent forms do not use machine/browser locale |
| B06 | Structural observations are non-semantic | Type/cardinality/missingness/range evidence does not create role/domain/currency/readiness authority |
| B07 | Bounded summaries are reproducible | Examples/frequencies use deterministic first-observed order and privacy suppression |
| B08 | Source values survive canonicalization | Tests cover numeric, date, text, missing and parse-failure cells with source and canonical representations side by side |

## C. Prohibited automation

| ID | Criterion | Required evidence |
|---|---|---|
| C01 | No financial imputation | Missing amount/date/status/currency/dimension remains missing; no default, mean, carry-forward or zero fill exists |
| C02 | No deletion | Missing, duplicate-candidate, parse-failure and extreme-value rows remain source-addressable |
| C03 | No automatic deduplication/merge | Exact and key-based candidates do not reduce source or canonical record count |
| C04 | No outlier modification | No removal, clipping, winsorization or replacement path; anomaly algorithms remain separate and unchanged |
| C05 | No sign reinterpretation | Numeric sign remains exact; cash direction never derives from sign |
| C06 | No currency inference or FX | Symbol/geography/language/filename/domain/LLM fixtures remain `UNKNOWN`; no converted amount is emitted |
| C07 | No DR/CR business reinterpretation | Confirmed debit/credit cannot become revenue/expense or cash direction automatically |
| C08 | No reconstructed measures | Profit/outstanding balance or another financial measure is never guessed or derived by preparation |
| C09 | No ambiguous date assumption | `01/02/2026` remains unresolved until explicit format contract; system locale variations produce identical unresolved result |
| C10 | No silent authority changes | Alias confidence, provider proposal, selector change and preparation completion produce no semantic/domain confirmation |

## D. Duplicates and missing values

| ID | Criterion | Required evidence |
|---|---|---|
| D01 | Exact duplicate candidates follow exact rule | Complete source-token tuple equality finds candidates and retains all source row numbers |
| D02 | Key-based candidates require approved key | Attempt before approved semantics is absent/`REQUIRES_CONFIRMATION`; after approval report states key/rule/version |
| D03 | Candidate is not fact | Backend/UI language always includes “candidate”; no error/fraud/invalid/duplicate-fact claim |
| D04 | Duplicate candidate does not silently block | Current operation readiness is unchanged unless an existing explicit uniqueness contract is identified |
| D05 | Missing is distinct from zero | Blank, zero, false, parse failure and source token are separately represented and counted |
| D06 | Null-like tokens are conservative | `NA/N/A/NULL/NONE` remain source values or parse failures; no generic V2.1 endpoint silently or explicitly converts them to missing |
| D07 | Coverage is operation-specific | Each ready/blocked operation reports total, eligible, excluded/failed and reason counts |
| D08 | No generic usable-row claim | API/UI labels usable rows only in exact operation context; structural accepted rows remain separately named |

## E. Dates, currency and financial semantics

| ID | Criterion | Required evidence |
|---|---|---|
| E01 | Ambiguous date contract is explicit | Both `DD/MM/YYYY` and `MM/DD/YYYY` decisions create versioned distinct canonical outputs/digests |
| E02 | Approved date format is reproducible | Replay applies exact approved format; invalid values are failures, not repaired |
| E03 | Dataset reference date remains separate | No source date/current clock auto-populates the qualifier; aging/overdue existing gates pass |
| E04 | Currency states are exact | `UNKNOWN`, one-code `CONFIRMED`, and multi-code `CONFIRMED_MULTIPLE` fixtures preserve current semantics |
| E05 | Currency approval requires evidence | Complete ISO map plus explicit decision is required; role confirmation alone leaves denomination unknown |
| E06 | Semantic roles remain explicit | Deterministic and local-LLM suggestions are never `CONFIRMED`; user/source authority record is required |
| E07 | Domain remains explicit | Domain suggestion/selector does not persist; only explicit confirmation changes mapping version |
| E08 | Critical value maps remain complete | Status, cash direction, debit/credit and actual/budget reject partial/unknown mappings |
| E09 | Outstanding balance remains explicit | Payable/receivable amount cannot satisfy open-balance operations without current approved amount basis/reference date |

## F. Data Quality Report

| ID | Criterion | Required evidence |
|---|---|---|
| F01 | Report is versioned/content-addressed | Same stable inputs produce same report digest; mutation or mismatch fails closed |
| F02 | Required summary exists | Total/structural rows, columns, missingness, parse failures, ambiguous dates, duplicate candidates, semantics, currency and readiness impact are present |
| F03 | Finding levels are distinct | `ERROR`, `WARNING`, `INFORMATION`, `REQUIRES_CONFIRMATION` serialize as closed enums with documented meaning |
| F04 | Readiness effect is explicit | Every finding has `NONE`, `LIMITS_COVERAGE`, `BLOCKS_OPERATION` or `BLOCKS_DATASET` and scope |
| F05 | Type evidence is inspectable | Per-column structural type includes success/failure/evidence counts, not an unexplained score |
| F06 | Parse failures are bounded and private | Count and bounded row references are present; sensitive/raw values follow suppression and never enter generic errors |
| F07 | Warnings are not verdicts | Duplicate/outlier/extreme findings do not claim bad data, fraud, error or risk |
| F08 | Report and readiness agree | Property/integration tests prove the same typed finding cannot be warning-only in report and silently dataset-blocking in readiness |

## G. Canonical dataset and readiness

| ID | Criterion | Required evidence |
|---|---|---|
| G01 | Source names are decoupled after approval | `Valor`, `amount`, `total_due` and `invoice_amount` fixtures can each bind to canonical `AMOUNT` only after their own explicit decision |
| G02 | Original representation is retained | Canonical records include exact source header/value references and stable row/column identity |
| G03 | Mapping compatibility is strict | Changed source/schema/profile/preparation digest blocks silent mapping/canonical reuse |
| G04 | Canonical digest includes decisions | Role/value/date/qualifier correction changes canonical-view digest and invalidates dependent readiness |
| G05 | Readiness remains current and operation-specific | Revocation/recovery, partial operation readiness and adapter revalidation pass with quality inputs |
| G06 | Preparation cannot activate capability | Prepared/profiled but unapproved datasets remain non-executable |
| G07 | Financial Core owns results | No preparation/application/API/web aggregate or authoritative financial result is introduced |
| G08 | Existing catalogs are unchanged | Exact 9/6/6/6 financial and two anomaly operation catalogs match `v2.0.0` |

## H. Application and HTTP

| ID | Criterion | Required evidence |
|---|---|---|
| H01 | Application remains transport-neutral | Preparation/quality commands and projections import no FastAPI/Pydantic/HTTP types and perform no semantic/financial/readiness logic |
| H02 | Preparation route is safe and typed | Exact dataset ID returns typed preparation projection without paths/raw private artifact |
| H03 | Quality route is safe and typed | Exact dataset ID returns typed report/coverage with suppression and stable errors |
| H04 | Upload response is one source of truth | Optional embedded preparation/quality equals subsequent GET projections byte-for-byte after JSON serialization |
| H05 | API cannot set authority fields | Unknown fields, authority source, transformation class/outcome, readiness effect, parser/adapter/path/SQL/formula/code are rejected |
| H06 | Decimal/missing encoding remains exact | Monetary/Decimal strings and JSON null/status contracts pass OpenAPI and runtime tests |
| H07 | Errors are bounded | No traceback, absolute path, raw sensitive token, artifact body or provider output is exposed |
| H08 | OpenAPI/generated client agree | Exported schema and generated TypeScript compile; new enums/routes are closed |

## I. Smart onboarding web

| ID | Criterion | Required evidence |
|---|---|---|
| I01 | Target workflow is implemented | Real-API E2E covers Upload → Processing → Preparation summary → Confirmations → Review → Readiness → Analysis |
| I02 | Automatic actions are explained | Summary shows what changed, why safe, what preserved/refused and technical details |
| I03 | No vague cleaning claim | Static copy test rejects “AI cleaned/fixed your data” and equivalent unqualified claims |
| I04 | Only ambiguity requests confirmation | Structural facts have no approval control; financially meaningful items do |
| I05 | Grouping does not create authority | Confirmation group navigation/selection sends no mutation; explicit commit sends exact existing command |
| I06 | Saved and pending are distinct | Component and request-count E2E prove selector changes remain local until commitment |
| I07 | Quality language is truthful | Duplicate candidates/outliers/missing/zero/date/currency copy follows backend state and neutral terminology |
| I08 | Readiness comes from backend | TypeScript contains no quality-to-readiness or confirmation-to-capability algorithm |
| I09 | Details are accessible | Keyboard, focus, status text, responsive 320–1440 widths and technical disclosures pass existing accessibility contract |
| I10 | Dataset detail is auditable | Preparation/quality/mapping versions, operation coverage and safe lineage identifiers are inspectable |

## J. Security, privacy and reproducibility

| ID | Criterion | Required evidence |
|---|---|---|
| J01 | Local-first remains true | Network-disabled regression completes; no external request, telemetry or analytics code path is required |
| J02 | Existing CSV/XLSX controls pass | Symlink/device/path, size/shape, ZIP expansion/traversal, XML, formula, macro, link, encryption and multipart tests pass |
| J03 | No arbitrary execution path | Malicious cells/headers/report fields remain inert; no eval/exec/shell/import/SQL/dynamic `getattr`/adapter selection |
| J04 | Optional LLM remains bounded/local | Full dataset is not sent; provider can only suggest; unavailable/malformed output leaves deterministic workflow usable |
| J05 | Replay descriptor is sufficient | Fresh process reconstructs identical preparation/canonical digests from source, sheet, versions/bounds and decisions only |
| J06 | Random/time metadata is non-authoritative | Different clocks/run IDs/source basenames do not change stable preparation/canonical results |

## K. Performance and release

| ID | Criterion | Required evidence |
|---|---|---|
| K01 | Current bounds remain enforced | 10 MiB, 100,000 row, 64 column and existing cell/archive boundaries pass at/over limit fixtures |
| K02 | Preparation complexity is bounded | Review plus benchmark shows linear passes and hash-based duplicate grouping; no pairwise row comparison or unbounded samples |
| K03 | Local performance budget passes | On a documented reference environment, each separate worst-permitted-shape fixture completes upload→quality projection within 30 seconds and peak process RSS stays below 512 MiB |
| K04 | No infrastructure creep | Dependency/inventory review finds no Spark, queue, worker service, PostgreSQL, cloud store or distributed execution |
| K05 | Full V1/V2 regression passes | All existing backend/frontend/E2E/security/offline tests pass with zero mandatory fail/error/skip |
| K06 | V2.0.0 behavior is unchanged | Golden catalog, financial result, readiness, lineage and web authority comparisons against `v2.0.0` pass |
| K07 | Documentation matches implementation | Scope, contract, architecture, UX, API/OpenAPI, technical guide and usage guidance are reconciled before release |
| K08 | Final authority/scope review passes | Explicit review finds no leakage, unsafe cleaning, hidden imputation/deletion, currency/sign/date inference, LLM authority, arbitrary query behavior or non-goal implementation |
| K09 | Release quality gate passes | Zero BLOCKER/HIGH; approved release evidence records exact tests/benchmarks/limitations before manual tag |

The K03 fixtures are separate because a 10 MiB file cannot necessarily
simultaneously reach every independent row/column maximum. The release record
must publish fixture shape, hardware, OS, Python version, wall time and peak RSS.

## Planning acceptance

The V2.1 specification is ready for implementation because each product promise
has an authority owner, deterministic contract and measurable gate. Passing this
document is required before a future manual V2.1 release; documentation alone
does not satisfy any implementation criterion.
