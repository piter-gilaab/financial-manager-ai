# Financial Manager AI V2 — 5–10 Minute Demo

Use synthetic data only. Start the API and Web with the commands in the
[usage guide](v2_usage_guide.md).

## 0:00–1:00 — Local-first workspace

Open Overview and health. Explain that Next.js and FastAPI run on loopback, data
stays local, and the LLM is optional. Show the exact four-domain capability catalog.

## 1:00–3:00 — Safe onboarding and explicit semantics

Upload a small synthetic payable CSV such as:

```csv
Supplier,Outstanding,Due,Status
Northwind,1250.00,2026-10-15,open
Contoso,500.00,2026-12-01,open
```

Show deterministic profile and mapping suggestions. Confirm `SUPPLIER`, `AMOUNT`,
`DUE_DATE`, complete `STATUS` mapping, domain `PAYABLE`, amount basis
`OUTSTANDING_BALANCE` and reference date `2026-11-01`. Emphasize that no suggestion
or filename creates authority.

## 3:00–5:00 — Operation readiness and multi-domain evidence

Open readiness, then run `PAYABLE_SUMMARY` and `PAYABLE_AGING` with
`as_of_date=2026-11-01`. Point out exact Decimal strings, currency state, coverage,
limitations and lineage. Briefly switch to pre-onboarded synthetic
`RECEIVABLE` and `CASH_TRANSACTION` fixtures and run one operation from each,
showing that cash direction is explicit rather than sign-inferred.

## 5:00–7:00 — Sales and anomaly screening

Open a synthetic eligible `SALES_RECORD` dataset (at least 30 non-constant Sales
and supplied Profit values). Run `SALES_BY_COUNTRY`, then
`SALES_ANOMALY_SCREEN`/`PROFIT_ANOMALY_SCREEN`. Show backend-returned quartiles,
fences, exclusions and candidate labels. State clearly: candidate for review,
never fraud/error/risk.

## 7:00–9:00 — Structured evidence and conversation

Open Ask Financial Manager. Select the exact dataset, ask for a ready closed
operation, and show that the answer cites the authoritative evidence. If no local
model is running, show the controlled provider-unavailable state and continue via
analysis controls. Reset the session to demonstrate process-local context.

## Closing

The differentiators are safe local onboarding, explicit semantics, current
operation readiness, deterministic multi-domain authority, exact evidence and a
bounded optional language layer. Do not present Forecasting, RAG, fraud detection,
ERP, auth, cloud or SaaS as implemented.
