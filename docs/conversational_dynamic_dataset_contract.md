# Phase 17 — Step 66: Conversational Dynamic Dataset Contract

## Purpose and scope

This contract makes the already-approved dynamic `SALES_RECORD` Financial
Analysis path available through the existing process-local conversation. It does
not create a query language or give a model dataset, execution, financial or
readiness authority.

The only conversational dynamic operations are:

1. `SALES_RECORD_COUNT`
2. `SALES_SUMMARY`
3. `SALES_BY_COUNTRY`
4. `SALES_BY_PERIOD`
5. `SALES_BY_SEGMENT`
6. `SALES_BY_PRODUCT`
7. `PROFIT_SUMMARY`
8. `DISCOUNT_ANALYSIS`
9. `UNITS_SOLD_SUMMARY`

Dynamic anomaly execution, Forecasting, Document Retrieval/RAG, other domains,
arbitrary queries and fuzzy filesystem discovery are outside Steps 66–67.

## Authority chain

```text
user language
  -> optional local LLM mediation
  -> strictly validated closed intent
  -> deterministic dataset resolution
  -> current dataset and operation readiness
  -> FinancialManagerAgent.execute_dataset_request
  -> DynamicQueryBinder
  -> static SALES_RECORD adapter
  -> Financial Core
  -> authoritative structured evidence
  -> grounded response
```

The model may identify language and select only values supplied in the current
closed prompt. It cannot write executable request text, inspect files, select a
column or adapter, create SQL/formulas, calculate values, infer currency or
override readiness.

## Dataset selection and resolution

Resolution order is fixed:

1. one exact, syntactically valid, currently registered `dataset_id` explicitly
   present in the user's turn;
2. the current session selection, after fresh validation;
3. an exact ID the user supplies after a code-owned bounded choice prompt.

An explicit target replaces the previous selection only after successful current
validation. With one or more eligible datasets and neither an exact target nor a
current selection, the result is `CLARIFICATION_REQUIRED`; code never chooses an
entry on the user's behalf. Multiple exact IDs are ambiguous. Malformed, unknown,
model-invented or out-of-catalog IDs are rejected/fall back and never become a
selection.

There is no selection by path, filename, label substring, recency, directory,
“latest”, fuzzy match or model-created alias. A dataset must authenticate as a
current registered `SALES_RECORD` and have at least one supported Financial
Analysis operation to enter the eligible catalog.

## Bounded dataset catalog

The interpretation prompt receives at most **20** eligible datasets. This limit
is consistent with the existing bounded conversational/evidence conventions and
keeps local provider input finite. Entries contain only:

- exact opaque `dataset_id`;
- approved canonical domain;
- current Financial Analysis state; and
- identifiers of currently supported operations.

The prompt never receives source paths or filenames, rows, values, samples,
profiles, mappings, registry artifacts, readiness internals or full metadata. If
an exact valid ID occurs in the user's text, deterministic resolution reserves a
slot for it before the remaining sorted catalog entries. Catalog truncation never
authorizes choosing an omitted ID. If ambiguity remains, the application asks
for an exact ID.

## Session dataset context

`FinancialManagerSession` may retain one active dynamic dataset selection and one
last successful closed dynamic operation descriptor. This state is typed,
data-only, local process memory; it contains no rows, financial values, source
paths, provider output, transcript or arbitrary natural-language memory.

Selection is session-scoped and is never shared or persisted. Reset, expiry and
cancel clear it. A different session starts without it. Every use revalidates the
current catalog/readiness; a deleted, revoked, stale, corrupt, wrong-domain or
otherwise ineligible selection is cleared and produces controlled
clarification/blocking behavior rather than silent reuse.

Legacy clarification and anomaly-evidence contexts remain separate and retain
their existing lifecycle and authority.

## Closed parameters

`SALES_BY_PERIOD` accepts `MONTH` or `YEAR`; omitted granularity retains the
deterministic contract default `MONTH`. `SALES_BY_COUNTRY`,
`SALES_BY_PERIOD`, `SALES_BY_SEGMENT` and `SALES_BY_PRODUCT` accept only
`BUCKET` or `EXCLUDE`; omission retains `BUCKET`. Summary/count operations accept
neither parameter.

There is no quarter, week, day, arbitrary measure/dimension/grouping/filter,
formula, sort expression, SQL or source-column selector. An invalid or misplaced
parameter is rejected or clarified and is never silently discarded.

## Language and bounded follow-ups

Examples that may resolve to the closed actions include:

- “Use dataset ds_….” / “Analyze dataset ds_….”
- “How many sales records are there?”
- “Show total sales.”
- “Show sales by country/month/year/segment/product.”
- “Summarize profit.” / “Analyze discounts.” / “Summarize units sold.”

After explicit selection, “Now by product” and “Show it by month” may be rebuilt
from the active dataset, the last closed dynamic operation and an allowlisted new
operation/parameter. No prose history is stored. “And Canada?” would require an
unapproved arbitrary filter and therefore asks for a complete supported request.

“Analyze my data” and “Show the sales” require clarification when multiple
eligible datasets exist and none is selected. Code does not guess.

## Readiness, evidence and currency

Conversation never promotes dataset readiness. Before each execution the Manager
recomputes the current dataset projection, and binder/adapter execution repeats
artifact and source checks. A blocked operation returns its controlled readiness
reason; no other operation or measure is substituted. Missing Profit never causes
Sales to be returned as Profit, and Profit is never derived.

`UNKNOWN`, `CONFIRMED` and `CONFIRMED_MULTIPLE` remain evidence/readiness states.
The model may explain a state present in approved evidence but cannot infer or
assign a currency. All numeric claims must come from `GroundedResponsePacket`
facts derived from the unchanged dynamic evidence. The existing grounding guard
remains strict, and tables/lists are rendered by code. Mediation performs no
financial arithmetic, rankings, percentages or differences.

## Deferred and blocked capabilities

A conversational request for dynamic anomalies is deliberately unsupported in
Steps 66–67 and must never call `execute_dataset_anomaly_request`. The explicit
typed Phase 16 Manager path remains unchanged. Forecasting and Document
Retrieval/RAG remain `BLOCKED`; a selected tabular dataset changes neither gate.

## Security, privacy and compatibility

Dataset IDs, labels, headers, values and user text are inert data. The path adds
no `eval`, `exec`, shell, subprocess, raw SQL, dynamic import, untrusted
`getattr`, runtime code generation or caller-selected adapter. Prompt injection
cannot expand the catalog or change dispatch authority.

The existing local-first provider rule remains. Only the bounded catalog is sent
for interpretation and only bounded evidence facts are sent for response
generation. There is no telemetry, transcript or dataset persistence in
conversation state.

Legacy conversational Financial Analysis, legacy anomaly conversation,
clarifications, evidence handles, slash commands and deterministic provider
fallback remain available without selecting a dynamic dataset. No dynamic
selection is required for a legacy request.
