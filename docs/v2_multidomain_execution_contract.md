# V2 Phase 2 — Multi-Domain Execution Contract

Status: **IMPLEMENTED — PHASE 2**.

Phase 2 adds deterministic execution for `PAYABLE`, `RECEIVABLE` and
`CASH_TRANSACTION` without changing the existing `SALES_RECORD` stack. The
authority chain is semantic confirmation → current readiness →
`FinancialManagerAgent` → static adapter → Financial Core → structured evidence.

## Closed interface

`DynamicQueryRequest` binds one exact `dataset_id`, one allowlisted operation and
only `missing_dimension`, `granularity` or `as_of_date` where the catalog permits.
There is no query text, caller-selected column, formula, SQL, filter, aggregation
function, adapter name or runtime import.

The static registry maps only:

- `SALES_RECORD` → `SalesRecordExecutionAdapter`;
- `PAYABLE` → `PayableExecutionAdapter`;
- `RECEIVABLE` → `ReceivableExecutionAdapter`; and
- `CASH_TRANSACTION` → `CashTransactionExecutionAdapter`.

## Shared implementation

The three Phase 2 adapters share authenticated artifact loading, canonical
mapping, current source/profile/mapping/registry validation, currency gates,
quality evidence and lineage. The `src.financial.multidomain` Core module owns
exact summaries, closed grouping, aging, overdue eligibility, cash magnitudes
and net cash. The adapters never expose the shared implementation as an
arbitrary financial query engine.

All monetary inputs use canonical exact decimal text and the Core's precision-60
exact arithmetic. Missing and parse-failed values are distinct and are never
imputed. Original source values and signs remain in record lineage.

## Evidence

Evidence includes dataset/domain operation identity, status, exact result,
record accounting, exclusions, coverage, currency state/code, quality warnings,
limitations implicit in the closed contract and source/profile/mapping/registry/
adapter/catalog/Core lineage. Authoritative monetary values are strings, never
binary floats.

`UNKNOWN` currency produces qualified unverified-source-denomination evidence;
`CONFIRMED` preserves the approved ISO code without FX; `CONFIRMED_MULTIPLE`
allows count only and blocks monetary operations.

## Scope boundary

This implementation adds no API, FastAPI dependency, frontend, Next.js,
forecasting, RAG, arbitrary query language, PostgreSQL, auth, multitenancy or new
anomaly operation.
