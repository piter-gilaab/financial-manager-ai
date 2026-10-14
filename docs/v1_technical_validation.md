# Financial Manager AI V1 Technical Validation

Status: **PASS** for Phase 18 Step 71 on 2026-10-14.

This validation answers: the frozen V1 is technically safe and stable enough to
proceed to the documentation/release-candidate phase, with the explicitly listed
non-blocking product and environment limitations.

## Validation environment

- Python: CPython 3.14.7; repository contract: Python 3.14.
- Runtime dependencies: standard library and repository code only;
  `requirements.txt` declares no third-party runtime package.
- Persistence: approved local SQLite snapshot plus versioned local onboarding artifacts.
- Network: not required. One existing audit test intentionally attempts and
  blocks a loopback connection; live Ollama was not used or required.
- Test data: approved local assets and bounded synthetic temporary data.

## Regression strategy and result

Existing validation reports and test categories were inspected before execution.
Focused slices ran first: onboarding (51 tests), legacy Core/agent/anomaly/Manager
(172), dynamic execution/anomaly/conversation (117), and security/mediation (96).
The loopback audit case requires an unrestricted local-socket environment; it
passes there and is denied before `socket.connect` by the managed sandbox.

The final complete unrestricted suite result and duration are recorded in
[`step71_validation.md`](step71_validation.md): 720 tests passed in 528.891
seconds with 0 failures, 0 errors and 0 skips. No test was removed, skipped or weakened.

## Security validation

The static and behavioral review found no user/LLM-controlled path through
`eval`, `exec`, shell, subprocess, dynamic imports, runtime code generation,
untrusted `getattr`, raw SQL or request-selected adapters. Relevant occurrences
were classified rather than rejected by keyword alone:

- SQLite execution is internal, uses static statements/allowlisted fields and
  bound values over validated snapshots; no user/LLM SQL interface exists.
- `getattr(..., "location", ...)` checks trusted provider configuration and is not dispatch.
- `importlib` in provisioning validates fresh imports; it is not request-driven.
- subprocess usage is confined to tests that exercise/audit fresh CLI processes.
- malicious strings in tests are inert values used to prove rejection or preservation.

The 18-test dedicated security/privacy suite passes. Manager payloads remain
data-only, capability and operation dispatch is static, unexpected CLI exceptions
produce a fixed diagnostic and blocked capabilities have no handlers.

## Prompt and LLM security

Closed schemas and current context validation reject malformed/oversized output,
unknown operations, provider-invented datasets/references, fake SQL/shell/tool
proposals and version-incompatible intents. Prompt data and rules are separated.
Interpretation receives at most 20 safe dataset entries and no dataset rows,
paths, filenames, profiles or mappings. Response generation receives bounded
facts, and ungrounded numbers, currency, fraud/certainty language, internal IDs
and unsafe markup fall back to code-owned presentation.

Provider failures cannot alter deterministic evidence. Only loopback-hosted LOCAL
mediation is implemented; proxy use and redirects are disabled. Slash commands never reach the model.

## Dataset ingestion security

Focused onboarding tests validate regular-file/no-symlink requirements, path and
dataset-ID containment, bounded file/row/column/cell sizes, strict UTF-8 CSV,
consistent widths, constrained XLSX ZIP/XML parsing, safe archive paths and
expansion limits, and rejection of formulas, macros, external links and encrypted
workbooks. Unsupported formats and malformed CSV/XLSX fail with controlled codes.
No format was added.

## Data integrity

Validated behavior includes exact `Decimal` arithmetic, source fingerprint and
schema checks, workflow/registry/profile/mapping version and digest consistency,
stable-column identity, missing-versus-zero preservation, parse-failure
accounting, sign preservation, explicit currency state with no unintended FX,
complete lineage, stale-artifact rejection and fresh revocation/recovery.

Raw source bytes are preserved. Dynamic Profit remains supplied Profit only.
DR/CR remains accounting direction. Adapter execution reauthenticates current
artifacts after readiness evaluation.

## Financial and anomaly regression

Legacy Financial Analysis retains all 8 Receiver General and 9 Company
Financials contracts. Dynamic `SALES_RECORD` regression covers all nine operations,
direct Manager and conversational execution, readiness, exact evidence, dimension
policies, MONTH/YEAR grouping, currency, renamed columns and stale state.

Legacy anomaly policies and evidence remain unchanged. Dynamic Sales and Profit
screens validate minimum 30 usable values, positive IQR, strict fence comparison,
fence equality as `NOT_SELECTED`, missing/parse failures as `NOT_ASSESSED`, signed
negative values, source-denomination currency rules and candidate-only semantics.
No peer screen or fraud interpretation was introduced.

## Conversational regression

Session isolation, reset, cancel, inactivity/absolute expiry, approved
clarifications, exact dynamic dataset selection, stale selection, closed
follow-ups, candidate references, `why_selected`, bounded `record_detail`, local
provider fallback, grounding and legacy conversation pass. Selection/reference
state is process-local and never substitutes for fresh readiness/evidence.

## Privacy

The application persists no transcript and emits no telemetry. No external
provider is required. Interpretation prompts contain bounded catalog metadata,
not full datasets; response prompts contain bounded facts. Artifacts remain local,
`data/raw`, `data/processed`, `data/database/*.db` and `data/onboarding` are
Git-ignored as appropriate, and tests use approved local or synthetic temporary
data. Terminal/shell/host retention and filesystem encryption remain outside the
application boundary.

## Reproducibility and fresh processes

`.python-version`, `requirements.txt`, approved-run metadata, raw/processed
hashes, schema hash, SQLite validation, registry/profile/mapping/source digests
and deterministic policy versions define the baseline. `python -m src.provisioning`
returned PASS with 720 tests discovered, zero import errors, a valid approved
bundle/database and `network_required=false`. A temporary fresh SQLite
build produced schema version 1, passed disk reload validation and created a
28,590,080-byte artifact without replacing the approved database.

Fresh processes successfully imported CLI, database initialization, onboarding,
Manager/session and mediation modules. CLI startup/help, human and JSON
capabilities, plan and ask, deterministic chat startup, temporary dataset add and
dataset capability discovery all completed without prior import ordering.

## CLI and controlled errors

Human and JSON modes were exercised on currently supported syntax. Forecasting
and Document Retrieval requests returned `CAPABILITY_UNAVAILABLE` / `BLOCKED`
with `NOT_PERFORMED`. Traversal-shaped dataset IDs, Python/SQL/shell-shaped text,
unsupported operations and fake candidate references were rejected or inert.
Representative errors exposed no traceback, filesystem internals, private
artifact payload, raw exception or Python implementation detail.

## Performance characterization

These are bounded observations, not thresholds. Measurements used one warm local
CPython 3.14.7 process on the validation host. Dynamic measurements used a
56,003-byte synthetic CSV with 1,000 rows and 8 columns; the conversational case
used `ScriptedProvider` and included deterministic execution and grounding.

| Operation | Representative input | Wall-clock |
|---|---|---:|
| Onboarding ingestion + deterministic profile | 1,000 × 8 CSV | 0.044425 s |
| Dynamic dataset catalog/readiness | one approved 1,000-row dataset, 9 + 2 operation probes | 0.618340 s |
| Dynamic Financial Analysis | `SALES_BY_PRODUCT`, 1,000 rows | 0.407547 s |
| Dynamic anomaly screening | `SALES_ANOMALY_SCREEN`, 1,000 rows | 0.404786 s |
| Conversational dynamic request | `SALES_BY_PRODUCT`, scripted local provider, 1,000 rows | 1.547275 s |
| Representative legacy Financial Analysis | Company Financials Sales by country, 700 rows | 3.374484 s |

No intended V1 workflow was practically unusable and no existing performance
contract was violated. Full-suite duration is recorded separately because it is
validation cost, not interactive latency. Live local-model latency remains
hardware/model dependent and was not measured.

## Release-blocker classification

| Severity | Confirmed finding | Disposition |
|---|---|---|
| BLOCKER | None | — |
| HIGH | None | — |
| MEDIUM | None | — |
| LOW | The security test fixture opened an in-memory SQLite connection without explicitly closing it; Python's connection context manager does not close the resource. | Fixed with `contextlib.closing`; the warning-sensitive test and security suite pass without a `ResourceWarning`. |
| OBSERVATION | The managed sandbox denies socket creation before the loopback audit hook can observe `socket.connect`. | Environment-only; exact test passes unrestricted as required. |
| OBSERVATION | `FinancialManagerSession` carries substantial evidence-shape validation. | Maintenance seam retained; no release defect or cycle. |

No confirmed product defect required a code fix. One test-fixture resource leak
was reproduced and fixed without changing product behavior. Forecasting and Document
Retrieval/RAG remain blocked. Step 71 therefore passes with zero BLOCKER and zero
unresolved HIGH correctness, security or privacy findings.
