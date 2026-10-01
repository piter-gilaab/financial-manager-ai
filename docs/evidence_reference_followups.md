# Phase 10 — Step 32: evidence-reference follow-ups

## Scope

`FinancialManagerSession.follow_up(reference=..., intent=...)` provides one
explicit, bounded reference type: `ANOMALY_RECORD`. It is navigation over fresh
structured anomaly evidence, not conversational memory or an evidence cache.

Supported intents are exactly:

- `why_selected`;
- `record_detail`.

Both return the same structured authoritative detail. They do not invoke general
pronoun resolution or generate a fraud/error conclusion.

Financial Analysis record references are not implemented. Existing financial
results do not expose one uniform display-reference contract across the approved
queries, and Step 32 does not invent entity identities for symmetry.

## Issuance and bounded state

After one successful/partial, single-capability anomaly screening request, the
session identifies records whose global or peer assessment is `CANDIDATE` and
issues opaque local handles for at most the first ten in authoritative result
order. The operation response exposes only `{handle, kind}` pairs.

The frozen session state retains only:

- opaque handle and issuing session identity;
- capability, dataset and supported measure;
- authoritative lineage `record_id`;
- logical snapshot binding; and
- a canonical semantic result digest.

Before issuance and on every state read, run identifiers must match the approved
run-ID format, lineage and stored digests must be exact lowercase SHA-256 values,
and every result item, assessment and reference must have the closed structured
shape. A candidate assessment must resolve to a structured fence reference;
malformed or unresolvable evidence never enters conversational state.

It does not retain rows, observed values, assessments, fences, warnings, complete
results or explanation text. `status()` exposes only the evidence-context kind,
capability, dataset, measure and reference count; it masks the opaque handles as
well as lineage identifiers and financial/statistical evidence.

Starting another request replaces the entire evidence context. Reset, cancellation
or expiry removes it. The hard maximum is ten handles for one active result
context; there is no accumulated reference history.

## Logical snapshot binding

Each handle binds to:

- approved run ID from consistent result lineage;
- dataset;
- schema digest;
- manifest digest;
- validation digest;
- quality-flags digest;
- dataset source digest; and
- processed-data digest.

The physical `database_sha256` is intentionally excluded from logical equality
and the semantic result digest. A valid database rebuilt from the same approved
artifacts may have different bytes because of ingestion timestamps, as established
by Step 24. Full existing snapshot validation still occurs in the authoritative
service before any result is available.

The result digest is computed from the exact structured anomaly response after
removing only `metadata.snapshot.database_sha256`. It is an integrity/staleness
guard, not stored evidence and not an identifier supplied by the user.

## Deterministic resolution

Resolution follows this sequence:

```text
explicit follow_up(handle, intent)
  -> validate live session and evidence context
  -> require exact session-issued handle and supported intent
  -> reconstruct canonical anomaly question from dataset/measure
  -> FinancialManagerAgent.ask (fresh Step 18 routing and registry validation)
  -> AnomalyService fresh deterministic execution
  -> verify logical snapshot and semantic result digest
  -> locate exact lineage record_id
  -> return structured detail copied from the fresh result
```

The detail contains dataset/measure, logical snapshot metadata, digest, source
lineage, observed value/raw/status, peer values, global and peer assessment plus
their exact referenced fence records, unavailable dependencies and applicable
quality warnings. `CANDIDATE`, `NOT_SELECTED` and `NOT_ASSESSED` retain their
existing meanings.

No explanation, summary or prior caller-owned result participates in resolution.
Mutating a prior operation response cannot affect the session or follow-up.

## Stale and invalid references

`STALE_REFERENCE` is returned without old evidence when fresh routing/execution no
longer yields the approved anomaly result, capability availability changes, the
logical snapshot or semantic digest differs, or the lineage identifier does not
resolve.

Other controlled outcomes include:

- `UNKNOWN_REFERENCE` for unknown, altered, cross-session or malformed handles;
- `NO_EVIDENCE_CONTEXT` when no anomaly handle context is active;
- `UNSUPPORTED_FOLLOW_UP` for any other intent; and
- `SESSION_EXPIRED` or `INCOMPATIBLE_STATE` for unavailable session state.

Invalid/spoofed references and unsupported intents do not execute and do not
extend session activity. No cryptographic token service is introduced for this
local, process-only boundary; membership in the immutable session-local map is the
authority check.

## Privacy and security

The session never accepts user-provided record IDs as authority. Handles cannot
select capability implementations, query names, SQL, shell/functions, modules or
database paths. Fresh execution occurs only through `manager.ask`; the current
registry remains authoritative and blocked capabilities have no reference path.

The implementation is in-memory only, uses no persistence, telemetry, network or
external provider, and opens no database itself. Database access and all anomaly
calculation remain owned by the existing verified snapshot and `AnomalyService`.

Operation results contain sensitive financial evidence because that is the
explicit caller request; the session state does not retain that result. Callers,
host memory and saved output remain outside the state-retention guarantee.

## Unsupported behavior

There is no implicit “this one,” display-position lookup, arbitrary user evidence
ID, full-result caching, historical snapshot storage, general explanation memory,
financial-record follow-up, filtered/custom anomaly reconstruction, Forecasting,
RAG, CLI conversation, persistence or multi-user session service.
