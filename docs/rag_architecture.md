# Phase 5 — Step 16 Financial Document RAG Readiness

## Readiness classification

| Area | Status | Decision |
|---|---|---|
| Architecture readiness | **DEFERRED** | The project has compatible foundations and this document defines a local-first target architecture, but no RAG interface, document model, parser, chunking policy, embedding provider, index, retrieval evaluation, or agent integration has been approved or implemented. Corpus-dependent choices must wait for representative real documents. |
| Production corpus readiness | **BLOCKED** | The repository contains no suitable real financial document corpus. Structured CSV files and their SQLite representation are not a RAG corpus, and project documentation/notebooks are not production financial evidence. |

No document, chunk, embedding, index, credential, production fixture, or RAG
implementation is created by this assessment.

## Evidence reviewed

The review covered the repository inventory, project documentation, current
SQLite/data architecture, the V1 direction and architecture decision, Phase 5
agent/provider design, privacy statements, tests, and current imports and
dependency declarations.

Relevant findings:

- The repository has no PDF, DOC/DOCX, ODT, RTF, TXT, HTML, XML, PPT/PPTX,
  XLS/XLSX, scanned-image, email, or other source-document files outside the
  project's code and technical artifacts.
- The only source data files are the Receiver General and Company Financials
  CSVs. They are structured datasets and cannot be relabeled as a document corpus.
- The Markdown files and notebooks describe the project, its data processing,
  EDA, architecture, and validation. They are engineering evidence about the
  project, not contracts, invoices, policies, statements, procedures, or reports
  belonging to a production financial-document collection.
- The EDA links to external publisher documentation, but those pages are not a
  locally acquired, approved, versioned, and access-controlled production corpus.
- SQLite schema version 1 stores dataset/run/source-row lineage, accounting
  records, sales records, and quality flags. It has no document, document version,
  page, extracted text, chunk, embedding, index, retrieval, or citation entities.
- Step 13 has one Financial Manager with a closed tool allowlist, complete tool
  evidence, an evidence digest, and `LOCAL`, `PRIVATE`, and `EXTERNAL` provider
  location concepts. Document retrieval remains explicitly unavailable.
- There is no project dependency manifest. Production source imports use the
  Python standard library and project modules. The existing virtual environment
  does not constitute approval of a RAG dependency stack.

The glossary already distinguishes a **financial document**—a contract, report,
policy, or other relevant document with identifiable origin and version—from
**documentary evidence**, which is a retrieved passage with a source reference
and is not automatically a structured financial fact. This architecture retains
that distinction.

## Current available sources

| Source | Current role | Production RAG corpus? |
|---|---|---|
| Receiver General raw/processed CSV and database rows | Structured accounting records with source-row lineage | **No.** Structured records are queried by deterministic tools; they are not source documents. |
| Company Financials raw/processed CSV and database rows | Structured sales observations with source-row lineage | **No.** Structured records are not financial-document passages. |
| Project Markdown documentation | Planning, glossary, architecture, contracts, and validation evidence | **No.** These files document the software project rather than the company's production financial affairs. |
| EDA/cleaning notebooks | Analysis, transformations, outputs, and validation history | **No.** They are analytical artifacts, not authoritative production source documents. |
| External links mentioned by EDA | Supporting public source references | **No, currently.** They have not been approved, acquired, hashed, versioned, licensed for this use, or scoped as a corpus. |
| Synthetic documents | None currently present | **Never production evidence.** Future synthetic documents may be test fixtures only and must be visibly marked and isolated from production indexes. |

No current file may be presented to users as a production financial-document
corpus merely to demonstrate retrieval.

## Intended architecture

The required information flow is:

```text
Document source
    ↓
ingestion
    ↓
text extraction
    ↓
chunking
    ↓
embedding
    ↓
index
    ↓
retrieval
    ↓
source evidence
    ↓
agent explanation
```

The Financial Manager remains the single orchestrator. RAG is one specialized
tool module, not another agent. Its external interface should remain small: an
authorized retrieval request enters and a bounded evidence packet returns. The
module hides source reading, extraction, chunking, embedding, indexing, ranking,
and lineage resolution from the agent. The agent must not receive arbitrary
filesystem or index access.

### 1. Document source

Accept only sources registered in an approved corpus inventory. Each source must
have an owner, authority/provenance, document type, version or effective date,
access classification, retention rule, acquisition method, and permitted use.
Contracts, reports, policies, invoices, procedures, and statements are only valid
when those facts are established; a filename alone is insufficient.

The original bytes remain immutable. Replacement content is a new document
version, not a silent overwrite. Duplicate and superseded versions remain
distinguishable. Unsupported or encrypted formats must fail explicitly rather
than yielding partial text presented as complete evidence.

### 2. Ingestion

Ingestion validates source authorization, file type, byte size, content hash,
duplicate/version status, sensitivity, and extraction eligibility. It records an
immutable ingestion manifest before extraction. Failed or quarantined files do
not enter the searchable corpus. Ingestion must be repeatable and must never
alter the original document.

Source access controls must propagate to every derived artifact. Authorization
is checked before retrieval, not left for the LLM to enforce. Future deletion or
retention requests must remove or make inaccessible all corresponding chunks,
embeddings, index entries, caches, and generated previews while preserving the
required audit record.

### 3. Text extraction

Use format-specific extraction only after representative source formats are
known. Preserve page numbers, headings/sections, table locations, and reading
order where the format supports them. Store extraction status and quality
warnings. OCR is conditional on approved scanned documents and must retain page
anchors and confidence/quality diagnostics; OCR text is not silently treated as
perfect transcription.

Do not ask an LLM to reconstruct unreadable pages or invent missing text. Tables,
signatures, footnotes, headers, and repeated boilerplate require explicit tested
handling based on the corpus. Extraction output remains linked to exact source
bytes and extraction version.

### 4. Chunking

Chunk deterministically with a versioned policy. Prefer document structure such
as section, clause, heading, paragraph, page, or table boundaries where reliable;
use bounded overlap only when evaluation shows it is needed. Never combine text
from different documents or versions into one chunk.

Every chunk retains its verbatim extracted text and source span. Derived summaries
may be separate artifacts but cannot replace the source text used for citation.
A changed chunking policy produces a new ingestion/index version rather than
silently changing existing identifiers.

### 5. Embedding

Embedding is deterministic for a recorded model/version and preprocessing policy.
The default architecture must support a local adapter that keeps document text,
queries, and vectors on the approved host. A private/on-prem adapter may use an
approved private endpoint. An external adapter is optional, disabled by default,
and cannot be required for system operation.

The provider location, model identity/version, vector dimension, preprocessing,
and embedding run belong in lineage. Embeddings are sensitive derived data and
receive the same or stricter access classification as their source chunks.

This is a future provider seam; concrete adapters should be created only when an
approved provider actually exists. The current Step 13 `IntentProvider` should
not be overloaded as an embedding interface because interpretation and embedding
have different inputs, permissions, failure modes, and privacy exposure.

### 6. Index

The index stores searchable representations and the minimum metadata needed to
resolve a result back to an authorized source chunk. It must support atomic,
versioned publication: incomplete ingestion runs do not become searchable.
Document/version revocation, rebuilds, and index-to-manifest reconciliation must
be testable.

No vector database is assumed. Corpus size, update rate, retrieval method,
metadata filters, access-control needs, backup policy, and measured retrieval
quality must justify the eventual local or private index. A small approved corpus
may support a simpler local index; scale evidence may later justify a dedicated
vector store. External hosted storage is optional and requires separate approval.

### 7. Retrieval

Retrieval accepts a normalized question plus an authorized corpus/filter scope
and returns ranked source chunks, not an answer. It must enforce access before
search, apply approved document/version/effective-date filters, use deterministic
tie-breaking, cap results, and expose empty or insufficient evidence explicitly.

The initial evaluation should compare the smallest useful retrieval baselines,
including lexical retrieval where suitable, before adding semantic or hybrid
complexity. Embedding similarity is not proof of relevance or factual truth.
Retrieval score interpretation is method-specific and must not be rendered as a
confidence percentage unless separately calibrated and validated.

### 8. Source evidence

The retrieval module resolves each result into a self-contained evidence item:
verbatim source text, document/version identity, source reference, page/section
anchor where available, chunk identity, rank, retrieval score/method, ingestion
version, and authorization-safe display metadata. Evidence ordering and truncation
must be visible. A caller must be able to resolve every citation back to the
approved source bytes and extraction span.

### 9. Agent explanation

The Financial Manager may select the future RAG tool and explain its returned
evidence. It must preserve the complete evidence packet, as the current agent
preserves deterministic tool evidence. Explanations may summarize but cannot
promote unsupported claims into cited facts, invent citations, cite a chunk that
does not support the associated claim, or conceal conflicting/superseded sources.

Document text is untrusted data, including text that resembles instructions.
Neither ingestion nor retrieval may allow document content to override system,
tool, access-control, or citation rules. The explanation stage must abstain or
state that evidence is insufficient when the retrieved passages do not support
an answer.

## Privacy and provider model

Financial documents, extracted text, chunks, embeddings, queries, retrieval
results, and explanations are sensitive unless an approved classification says
otherwise. Local/private operation is a core requirement, not an optional later
enhancement.

| Mode | Permitted design | Requirements |
|---|---|---|
| `LOCAL` | Source bytes, extraction, embeddings, index, retrieval, and optionally explanation remain on the approved local host. | Default path. No network requirement, telemetry, implicit model download, or external fallback. Local model/runtime licenses and storage protections still require review. |
| `PRIVATE` | Approved organization-controlled/on-prem infrastructure may provide embedding, indexing, or explanation adapters. | Explicit endpoint and data-flow approval, authenticated encrypted transport, least data sent, retention/training policy, access controls, auditability, and no fallback outside the private environment. |
| `EXTERNAL` | Optional adapter for a specifically approved hosted provider. | Disabled by default. Requires explicit authorization for provider, document classes, fields/snippets, jurisdiction, retention, training use, cost, and credentials. Local/private use must not depend on it. |

Embedding and explanation locations are independent decisions. Approval to send a
query does not imply approval to send documents or retrieved passages. Approval
for embeddings does not imply approval for LLM explanation. Every adapter must
declare what leaves the sensitive zone before invocation.

Credentials must never be committed to the repository, stored in documents or
chunks, included in prompts, or written to retrieval logs. No credentials are
created in this step. Logging defaults should contain identifiers, versions,
timings, counts, and redacted errors—not document bodies, questions, passages,
vectors, secrets, or generated answers. Any content logging requires a separate,
explicit retention and access policy.

## Document lineage model

Future chunks must preserve at least:

| Field | Meaning |
|---|---|
| `document_id` | Stable identity of the logical document; never inferred from text alone. |
| `file_source_reference` | Authorized resolvable file/system reference without embedding credentials. |
| `content_hash` | Cryptographic hash of the exact source bytes for the document version. |
| `page_section` | Page, section, clause, table, or equivalent source span when available; explicitly unavailable otherwise. |
| `chunk_id` | Deterministic identifier unique to document version, source span, and chunking version. |
| `ingestion_version` | Version/run linking source inventory, extractor, chunking policy, embedding run, and index publication. |
| `retrieval_score` | Query-time score paired with retrieval method/version and rank; not a permanent property of the chunk or a truth probability. |

The model should also retain document version/effective date, source owner,
document type, access classification, extraction status/version, chunk ordinal,
embedding model/version, index version, retrieval request/run ID, and supersession
state when the approved corpus demonstrates those needs.

Lineage is append/version oriented. A new source file, correction, extractor,
chunking policy, or embedding model produces new versioned artifacts. Derived
artifacts never overwrite source evidence. The existing structured-data tables
may inspire run/hash validation, but document entities must remain a separate
domain; no relationship to accounting or sales rows is invented.

## Citation model

Every returned evidence item receives an evidence identifier scoped to the
retrieval response. Each factual claim in an explanation that depends on a
document must cite one or more of those evidence identifiers. The rendered
citation must expose an authorized document label/version and page/section when
available, while the structured result retains full lineage.

Required behavior:

- citations resolve only to chunks actually returned by the retrieval tool;
- quoted text remains verbatim and visibly distinguished from paraphrase;
- paraphrases stay within what the cited passage supports;
- different versions, effective dates, and conflicting passages remain visible;
- lack of evidence, inaccessible evidence, extraction failure, and retrieval
  failure are not rewritten as negative factual conclusions;
- citation presence is not proof that the source is authoritative, current, or
  correct; provenance/version status must accompany that judgment; and
- the structured evidence packet survives explanation unchanged, with a digest
  or equivalent integrity check when integrated into the agent.

An explanation that cannot map a material claim to supporting evidence must omit
the claim or state that the corpus does not provide sufficient support. The LLM
must not turn a plausible inference, retrieval score, filename, or user premise
into a cited fact.

## Corpus acceptance and evaluation requirements

Before architecture status can become READY, an explicitly approved,
representative sample must establish:

1. real source documents and authoritative provenance;
2. rights and permitted purposes for ingestion, indexing, retrieval, and model
   processing;
3. document owner, versions/effective dates, duplicates/supersession, languages,
   formats, page/scanning quality, expected tables, and corpus size/update rate;
4. sensitivity classification, per-document access policy, retention/deletion,
   backup, audit, and allowed provider locations;
5. representative user questions, answerable and unanswerable cases, expected
   evidence passages, and conflict/version scenarios;
6. extraction acceptance checks for text completeness, reading order, pages,
   sections, tables, and OCR quality where applicable;
7. deterministic chunk coverage and source-span resolution without cross-document
   contamination;
8. retrieval evaluation using fixed fixtures and a held-out set, reporting at
   minimum relevance/recall at the selected result limit, citation support, empty
   result behavior, latency, and access-control failures; and
9. end-to-end tests proving that unsupported claims are rejected, prompt-like
   document text is treated as data, unauthorized chunks cannot be returned, and
   external network use is absent in local mode.

Synthetic documents may later exercise extraction, chunking, permissions,
conflicts, prompt injection, and citations in automated tests. They must live in
a clearly marked test-fixture location, use fictional identities/content, never
enter a production index, and never be described as actual project evidence.

## Dependencies and implementation decisions

No project dependency manifest currently declares a vector database, embedding
package, document parser, OCR runtime, tokenizer, reranker, orchestration library,
or hosted provider SDK. None was installed or selected in this step.

Future implementation may require, subject to explicit approval and corpus
evidence:

- format-specific document parsing libraries;
- an OCR engine only for approved scanned/image documents;
- a local embedding model/runtime and its tokenizer/model artifacts;
- a local/private vector or hybrid index, or a dedicated vector database only if
  measured corpus scale and operational requirements justify it;
- optional reranking only if retrieval evaluation shows a material need;
- storage/encryption/access-control support appropriate to the approved threat
  model; and
- a hosted-service SDK only if an optional external adapter is separately
  approved. It is not required by this architecture.

Dependency selection must record license, model/data provenance, artifact hashes,
offline behavior, transitive dependencies, security maintenance, resource use,
supported formats, and data egress. Packages or models must not download content
or contact telemetry endpoints implicitly. A checked-in, reproducible dependency
manifest and offline/privacy tests are prerequisites for implementation approval.

Do not install a vector database, embedding package, document parsing stack, OCR
stack, hosted service SDK, or model simply to demonstrate the pipeline.

## Blockers and deferred decisions

### Production corpus blockers

- No real financial documents are present.
- No corpus inventory, owner, provenance, version/effective-date policy, or source
  authority has been approved.
- No ingestion/indexing rights, sensitivity classifications, document access
  policies, retention/deletion rules, or provider-location permissions exist.
- No representative format/language/scan/table sample exists for extraction and
  chunking decisions.
- No production questions, expected evidence passages, or retrieval/citation
  evaluation set exists.

### Architecture decisions deferred until a corpus sample exists

- supported formats and whether OCR is needed;
- extractor and table/reading-order policy;
- chunk boundaries, size, overlap, and versioning details;
- embedding model/runtime and local resource requirements;
- lexical, vector, or hybrid retrieval and whether reranking is justified;
- index technology, metadata filters, backup/update/deletion behavior, and scale;
- exact access-control model and authorized citation rendering;
- retrieval limits, score handling, abstention threshold, and evaluation targets;
- agent RAG tool contract and explanation provider; and
- any private/on-prem or optional external adapter and its data permissions.

The high-level flow is suitable for planning, but choosing implementations before
these facts are known would create speculative adapters and potentially unsafe
data flows. That is why architecture readiness is **DEFERRED**, while absence of
a real corpus makes production corpus readiness **BLOCKED**.

## Exact next step

Obtain explicit approval to inventory a small, representative set of real
financial documents without committing them to the repository. For each proposed
document, record source/owner, type, version/effective date, provenance, permitted
use, sensitivity, access policy, retention, format/language, and allowed processing
locations. Then perform a corpus/privacy assessment and use those findings to
specify extraction, chunking, retrieval, citation, evaluation, and dependency
contracts.

Do not implement RAG or install dependencies until that inventory is reviewed and
the architecture receives explicit implementation approval.

## References

- [Project glossary](../CONTEXT.md)
- [V1 direction](planning/v1-direction.md)
- [Financial Manager architecture decision](adr/0001-financial-manager-com-ferramentas-especializadas.md)
- [Semantic data model](data_model.md)
- [Database schema](database_schema.md)
- [Financial Analysis Agent](financial_analysis_agent.md)
- [Step 13 validation](step13_validation.md)
- [Anomaly detection](anomaly_detection.md)
- [Step 14 validation](step14_validation.md)
- [Forecasting readiness](forecasting_readiness.md)
