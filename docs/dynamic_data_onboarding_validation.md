# Dynamic Data Onboarding — Phase 13 validation

## Result

**PASS_WITH_LIMITATIONS.** The local onboarding pipeline is safe, reproducible
and truthful about execution. It does not make arbitrary datasets compatible
with existing query contracts or anomaly policies.

## Validated flow

```text
local CSV/XLSX
  -> exact source preservation
  -> deterministic structural profile
  -> closed bounded semantic suggestions
  -> explicit versioned user decisions
  -> approved domain-specific mapping
  -> versioned local registry
  -> deterministic semantic/policy/execution readiness
  -> BLOCKED unless a validated executable adapter exists
```

The lifecycle prevents `RECEIVED -> READY`. The normal current outcomes are
`NEEDS_CONFIRMATION`, `BLOCKED` or `REJECTED`; the internal `REGISTERED` state is
recorded before readiness evaluation. No generic adapter is configured, so Phase
13 new datasets do not become `READY`.

## Synthetic acceptance matrix

| Scenario | Validated result |
|---|---|
| A — clean sales CSV | Profile/suggestions work; `SALES_RECORD` requires decisions; analysis is semantic-ready but execution-blocked. |
| B — `DT_MOV/VL_LIQ/CC/TIPO/EMP` | Structure succeeds; `CC` stays unknown and all other meanings remain suggestions. |
| C — accounting-like | DR/CR needs an explicit value map and is never rewritten as revenue, expense or cash. |
| D — payable-like | `PAYABLE` can be approved; no AP capability is invented. |
| E/F — absent/verified currency | Default is `UNKNOWN`; only explicit ISO value evidence confirms denomination. |
| G — ambiguous dates | No range is assigned before resolution; an explicit format contract enables reproducible ISO normalization and the registry range. |
| H — missing amount | Missingness is reported; no imputation or row deletion. |
| I — duplicate candidates | Exact duplicate candidates are counted and retained. |
| J/K/L — malicious column/shell/SQL text | Treated as inert data; no execution or authority change. |
| M — formulas/macros/external links/encryption | Controlled rejection; cached formula values are not trusted. |
| N — malformed/oversized | Explicit bounded rejection codes. |
| O/P — provider unavailable/malformed | Profile survives; invalid provider output fails closed; manual correction works. |
| Q/R — reject/correct | New mapping versions record the explicit decision and prior proposal. |
| S — changed schema | Profile/digest mismatch blocks silent mapping reuse. |
| T — capability discovery | Only semantic eligibility is reported; no new capability becomes available. |

## Privacy and security

No full dataset is sent to a model. Semantic packets contain shape, structural
summaries and bounded non-sensitive examples. Identifier/email/long numeric
signals suppress raw samples. No telemetry, remote provider, credential, prompt
transcript or arbitrary provider response is persisted. Tests require no network,
Ollama, GPU, secret or private financial data.

Source paths, ZIP members, XML, files, rows, columns and cells are bounded.
Symlinks/devices, traversal, archive expansion, formulas, macros and external
links fail closed. Dataset strings cannot select SQL, shell, imports, tools,
roles, domains or capabilities.

## Integrity, lineage and reconstruction

Reconstruction uses the exact source SHA-256 plus ingestion contract/limits,
selected sheet, profile version/digest and bounds, semantic mapping
version/digest and decision records, canonical normalization version, registry
schema/version and capability report. Stable source row numbers link canonical
records back to the source fingerprint/sheet. It never depends on a prior LLM
conversation.

## Existing datasets

Receiver General remains the established `ACCOUNTING_TRANSACTION` reference with
unknown currency and unresolved fiscal/summary semantics. Company Financials
remains the established `SALES_RECORD` reference with unknown currency, no
verified company identity and preserved placeholders. Phase 13 does not migrate,
rewrite or retroactively relabel either production snapshot; their existing
Financial Analysis and Anomaly implementations remain unchanged.

## Limitations

- XLSX support is a constrained formula-free Open XML subset, not a full Excel
  calculation engine.
- Local JSON state is single-user and not designed for concurrent writers.
- PII/sensitivity detection is conservative, not complete.
- Manual confirmation is required; critical meanings need extra evidence.
- Recognized future domains are non-executable.
- No generic financial/anomaly adapter, forecasting, RAG or AP/AR logic exists.
