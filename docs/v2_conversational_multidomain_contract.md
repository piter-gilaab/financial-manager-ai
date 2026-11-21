# V2 Phase 2 — Conversational Multi-Domain Contract

Status: **IMPLEMENTED**.

The optional local mediator may select only one exact currently listed dataset,
one of the 9 existing SALES_RECORD operations, one of the 18 Phase 2 operations,
or one of the unchanged two anomaly operations. It may extract `MONTH | YEAR`,
`BUCKET | EXCLUDE` and an explicit ISO `as_of_date` only where allowed.

Missing aging/overdue date returns `CLARIFICATION_REQUIRED`. The mediator never
invents today, a dataset reference date, status, cash direction, currency,
filters, formulas, SQL or a nineteenth operation. An explicit date still passes
Manager/adapter equality validation against the approved dataset reference date.

The selected dataset's approved domain constrains safe follow-ups such as “Now
by account.” Ambiguous domain words do not create authority. Malformed, unsafe or
unavailable provider output fails closed and cannot redirect a selected Phase 2
dataset to legacy or SALES_RECORD execution.

Presentation receives bounded structured facts and copies authoritative values;
it performs no financial arithmetic. Sessions and transcripts remain
process-local and non-persistent.
