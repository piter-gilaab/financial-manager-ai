# Dynamic execution end-to-end validation

## Acceptance scope

Phase 14 Step 55 validates the complete, local path from a synthetic user file
to authoritative Manager evidence:

```text
CSV/XLSX source
  -> safe ingestion and deterministic profile
  -> explicit semantic decisions and domain approval
  -> versioned registry and operation readiness
  -> DynamicQueryBinder
  -> static SALES_RECORD adapter
  -> Financial Core
  -> Manager response 1.1
```

The validation uses the public `OnboardingManager`,
`FinancialManagerAgent.execute_dataset_request(DynamicQueryRequest)` and
`python -m src.cli dataset ...` seams. Synthetic files and their real persisted
artifacts live only in temporary directories. The main acceptance scenarios use
no mock of onboarding, registry, binding, adapter, Core or Manager.

This is a validation step. It adds no operation, route, adapter, capability,
dataset selector, filter or execution CLI.

## Authority and result criteria

The observed path retains these authorities:

- source bytes establish source facts;
- the deterministic profile establishes structural facts;
- explicit decisions establish critical semantics and canonical domain;
- current readiness code establishes dataset and operation availability;
- the binder accepts only an exact dataset ID, closed operation and bounded
  missing-dimension policy;
- the static adapter translates approved roles and revalidates current artifacts;
- `src.financial.sales_records` and shared exact arithmetic establish totals,
  coverage, ordering and result status;
- the Manager preserves evidence and adds no financial calculation;
- no LLM participates in readiness or execution.

A scenario passes only when its current persisted state, controlled status,
financial evidence, currency disclosure, coverage and lineage agree. A stale
in-memory result is never treated as authorization.

## Observed primary flow

A six-row `Date,Country,Sales` CSV was added, profiled, explicitly mapped and
approved as `SALES_RECORD`. The persisted capability report returned
`AVAILABLE_WITH_LIMITATIONS`, with all three bounded operations `SUPPORTED`.
The Manager then executed:

- `SALES_RECORD_COUNT`: six source observations;
- `SALES_SUMMARY`: five usable values, one explicit missing-value exclusion and
  exact sum `1000000000002.173456`;
- `SALES_BY_COUNTRY`: deterministic source-label groups under both `BUCKET` and
  `EXCLUDE` policies.

The data include `0.1`, `0.2`, a large high-scale value, a negative value, a
missing sale and a missing country. Results contain exact decimal strings rather
than floats, preserve the negative source value, disclose UNKNOWN denomination,
and trace every canonical record to its source row. Neither Manager nor evidence
contains the temporary source path.

## Semantic and currency variants

An independently onboarded `SaleDate,Nation/renamed-country,Revenue,CurrencyCode`
shape executes through the same three operation keys after explicit mapping.
The actual acceptance header is instruction-shaped and its country values include
SQL- and shell-shaped text; all are inert source data. This proves execution uses
confirmed roles rather than literal development headers or content as instructions.

Without approved currency metadata, monetary results remain valid source-
denomination summaries with `status=UNKNOWN` and `code=null`. With an explicitly
approved `USD -> USD` value mapping, readiness and evidence preserve
`status=CONFIRMED`, `code=USD`; country, symbols and formatting infer nothing.

## Partial readiness, revocation and recovery

Readiness remains operation-scoped:

- approved SALES with rejected/unresolved COUNTRY keeps count and summary
  supported while country grouping is blocked;
- an approved SALES role with no parseable values keeps record count supported
  while both monetary operations are blocked by adapter quality validation;
- rejecting required SALES removes semantic approval for `SALES_RECORD`, so all
  operations—including count—are blocked until SALES authority is restored.

The last rule is intentional: record count has no additional measure role, but it
still requires a coherently approved `SALES_RECORD` domain. The system does not
use the count operation to bypass the domain's minimum semantic approval.

COUNTRY and SALES revisions were persisted, then read through newly constructed
manager instances. Mapping and registry versions increased; no in-memory state
was needed. Restoring valid confirmed mappings produced a fresh readiness
projection and restored only the operations whose current requirements passed.

Changing the preserved source bytes and schema after approval persisted a
blocked readiness projection and made Manager execution fail closed. Restoring
the exact approved bytes allowed deterministic reevaluation and recovery.
Separate adapter/registry tests authenticate mapping, profile, workflow and
registry digests and reject stable-column schema mismatch before calculation.

## Manager and response contract

Valid execution traverses:

```text
FinancialManagerAgent.execute_dataset_request
  -> DynamicQueryBinder
  -> statically registered SalesRecordExecutionAdapter
  -> Financial Core sales-record primitive
  -> unchanged structured evidence
```

The response is Manager contract `1.1`. The legacy global
`capability_status=AVAILABLE` remains the built-in Manager registry state;
`dataset_capability.state=AVAILABLE_WITH_LIMITATIONS` is the distinct typed
projection for the exact onboarded dataset. Controlled binding/adapter errors
use the same envelope without stack traces, Python types, artifact payloads or
local paths.

## Capability discovery and CLI

The real Phase 13 CLI workflow was exercised through `dataset add`, `status`,
`profile`, `mappings`, `confirm`, `confirm-domain` and `capabilities`. Human
capability output was checked for a fully supported SALES_RECORD, a partial
SALES_RECORD and an unsupported accounting domain. `capabilities --json` was
also checked for the exact structured state, operations and non-analysis
blockers.

No `dataset analyze` command was added. Dynamic execution remains the explicit
typed Python Manager entry point.

## Security, privacy and bounds

Exact target validation distinguishes malformed IDs, valid-shaped unknown IDs
and registered IDs. Import-shaped operation text, SQL-shaped parameters,
instruction-shaped headers, SQL-shaped country values and shell-shaped cells
are rejected or returned as inert data. Recognized non-sales domains are never
coerced into `SALES_RECORD`.

Static scans and execution tests verify no request path through `eval`, `exec`,
subprocess, shell, raw SQL, dynamic imports, untrusted `getattr` or dynamic
adapter loading. The acceptance run needs no network, provider, Ollama, GPU,
external API or private user dataset. Binding inspects authenticated metadata;
source loading and the one-pass bounded aggregation remain adapter/Core work.

The configured onboarding root remains local and Git-ignored. Public results
carry dataset/artifact identities and source-row lineage but no absolute source
path. This is not encryption, DLP, authentication or a multi-user storage model;
host filesystem protection remains an operator responsibility.

## Acceptance matrix

| ID | Scenario | Status | Observed result |
|---|---|---|---|
| A | Clean SALES_RECORD | PASS | Persisted onboarding reaches all three Manager operations. |
| B | Renamed columns | PASS | Confirmed roles, not literal headers, control execution. |
| C | UNKNOWN currency | PASS | Count and source-denomination summaries execute; no code is inferred. |
| D | Confirmed currency | PASS | Explicit approved USD is preserved in readiness and evidence. |
| E | Partial capability | PASS | Missing COUNTRY blocks only country grouping. |
| F | Record-count-only readiness | PASS | Confirmed domain with unparseable SALES supports count only; unresolved required SALES blocks domain approval. |
| G | Missing SALES | PASS | Required semantic loss blocks the dataset; no count-based approval bypass. |
| H | Missing COUNTRY | PASS | Count and summary remain supported; country grouping is blocked. |
| I | BUCKET | PASS | Missing dimension is retained as the unavailable group. |
| J | EXCLUDE | PASS | Missing dimension is explicitly excluded and accounted for. |
| K | Decimal precision | PASS | `0.1`, `0.2`, large/high-scale and negative values sum exactly. |
| L | Negative SALES | PASS | Source sign is preserved without refund/error reinterpretation. |
| M | Revocation | PASS | Persisted COUNTRY/SALES revisions immediately remove affected readiness. |
| N | Recovery | PASS | Corrected persisted mappings restore only valid operations with new versions. |
| O | Changed source | PASS | Fingerprint mismatch persists blocked readiness and blocks Manager execution. |
| P | Changed schema | PASS | Changed source/schema and stable-column mismatch cannot reuse approval. |
| Q | Stale mapping | PASS | Pointer/digest/profile identity mismatches fail closed before calculation. |
| R | Stale registry | PASS | Registry digest tampering produces controlled blocked state. |
| S | Unsupported domain | PASS | ACCOUNTING_TRANSACTION remains `BLOCKED_NOT_IMPLEMENTED`; no coercion. |
| T | Unsupported operation | PASS | Product/profit/forecast/import-shaped keys return controlled unsupported results. |
| U | Valid Manager execution | PASS | Manager 1.1 delegates binder -> adapter -> Core and preserves evidence. |
| V | Unknown dataset | PASS | Valid-shaped unknown ID returns `DATASET_NOT_FOUND`. |
| W | Malformed dataset ID | PASS | Traversal-shaped ID returns `INVALID_REQUEST` before path access. |
| X | Malicious operation/data | PASS | All content remains rejected or inert data; no execution channel appears. |
| Y | Legacy Receiver General | PASS | Existing Financial Analysis/anomaly acceptance and UNKNOWN currency remain unchanged. |
| Z | Legacy Company Financials | PASS | Existing contracts, placeholders, anomaly and UNKNOWN currency remain unchanged. |
| AA | Dynamic Anomaly blocked | PASS | Dataset report remains BLOCKED; no legacy policy is reused. |
| AB | Forecasting blocked | PASS | Sales never satisfy actual-cash/history/model readiness. |
| AC | RAG blocked | PASS | Tabular onboarding never becomes a governed document corpus. |
| AD | CLI capability discovery | PASS | Full, partial and unsupported human reports plus full JSON are truthful. |
| AE | Reproducibility | PASS | Source/profile/mapping/registry/canonical/adapter identities reconstruct authority. |
| AF | Lineage | PASS | Dataset -> artifacts -> canonical record -> sheet/row remains present. |

## Reproducibility and lineage

Evidence records the current dataset ID, source fingerprint, ingestion identity,
profile version/digest, mapping version/digest, registry version/digest,
canonical model/specification and adapter version. Canonical record IDs retain
source sheet and row number; grouped evidence retains contributing canonical
record IDs. Execution depends on those authenticated artifacts and current code
contracts, never on a prior model interpretation.

## Defects and final status

One capability-presentation defect was reproduced. Unsupported-domain reports
correctly carried a controlled Financial Analysis reason, but the human CLI
printed only the separate `limitations` list. Because that list is intentionally
empty outside the SALES_RECORD operation catalog, the blocked report omitted a
`Limitations:` section. A failing acceptance assertion captured the behavior;
the renderer now displays explicit limitations when present and otherwise falls
back to the capability reasons. Structured readiness, execution and financial
logic were unchanged.

Phase 14 is complete. Its implemented dynamic scope is deliberately limited to
approved onboarded `SALES_RECORD` datasets and these operations:
`SALES_RECORD_COUNT`, `SALES_SUMMARY` and `SALES_BY_COUNTRY`.
