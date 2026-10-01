# Phase 9 — Step 28: presentation validation

## Result

**PASS_WITH_LIMITATIONS.** The Step 27 presentation contract is deterministic,
evidence-preserving, materially smaller than expanded output, and understandable
across the representative V1 workflows. One presentation defect was found and
fixed: concise Financial Analysis explanations repeated templated quality-warning
and quality-flag lines before the dedicated deduplicated warning section.

## Representative workflows

Each scenario ran through the real local `python -m src.cli ask` entry point.

| Workflow | Request | Outcome | Concise size |
|---|---|---:|---:|
| Financial summary | `Sales summary` | SUCCESS | 318 lines / 9,038 bytes |
| Grouped result | `Sales by country` | SUCCESS | 424 lines / 13,054 bytes |
| Partial result | `Discount analysis` | PARTIAL | 354 lines / 10,249 bytes |
| Anomaly screening | `Screen profit` | PARTIAL | 1,023 lines / 29,494 bytes |
| Blocked Forecasting | `Forecast cash flow next month` | CAPABILITY_UNAVAILABLE | 40 lines / 1,129 bytes |
| Blocked Document Retrieval | `What does invoice 123 say?` | CAPABILITY_UNAVAILABLE | 41 lines / 1,265 bytes |
| Clarification | `Check my financial data` | CLARIFICATION_REQUIRED | 25 lines / 744 bytes |
| Unsupported request | `What is the fraud probability?` | UNSUPPORTED | 19 lines / 601 bytes |
| Multi-capability | `Summarize sales and identify unusual sales records.` | SUCCESS | 1,202 lines / 35,108 bytes |

The outputs retain status, capability and routing context. Monetary workflows show
UNKNOWN currency. Partial workflows show coverage and exclusions. Screening states
that CANDIDATE is statistical investigation screening—not fraud, error, misconduct,
probability, or certainty—and explains NOT_ASSESSED. Blocked and clarification
outcomes do not execute an unavailable or unselected capability.

## Concise, full and JSON modes

Default human mode applies the documented first-10 preview and linked anomaly
reference policy. Returned, total and omitted counts reconcile, record order is the
authoritative order, and repeated runs are byte-for-byte deterministic for the
same request and snapshot. Stable record/reference identifiers identify displayed
evidence without suggesting a business identity.

`--full` retains the expanded human representation. For Profit screening it
contains the final authoritative record that concise mode omits and is materially
larger. `--json` parses without floating-point tokens and equals a fresh direct
`FinancialManagerAgent.ask()` response for partial analysis, anomaly screening and
multi-capability workflows. `--json --full` remains a controlled syntax error and
does not construct a response.

| Request | Concise | Full human | JSON |
|---|---:|---:|---:|
| `Sales summary` | 9,038 bytes | 15,300 bytes | 30,798 bytes |
| `Screen profit` | 29,494 bytes | 957,466 bytes | 1,239,329 bytes |
| Multi-capability request | 35,108 bytes | 958,867 bytes | 1,249,255 bytes |
| `Screen accounting amounts` | 31,852 bytes / 1,097 lines | 12,732,225 bytes / 468,070 lines | not remeasured |

The accounting-screening comparison directly reproduces the Step 25 excessive
expanded output and shows that concise mode remains a meaningful improvement. No
arbitrary byte target drove formatting choices; warning, omission, terminology,
coverage and linked-reference disclosure remain present.

## Warning and evidence checks

Exact duplicate warnings from nested and convenience envelopes appear once in the
dedicated concise warning section, with applicable step IDs. Every distinct real
Discount-analysis warning remains present. Large flag-row collections retain
explicit omission counts. The defect fix removes only templated `Quality warning:`
and `Quality flags:` lines from the concise explanation; `--full`, the warning
section, structured manager response and JSON are unchanged.

JSON equality and the existing manager/service integration tests confirm that the
presentation layer performs no financial arithmetic, SQL, routing, threshold
calculation, currency inference, candidate reclassification or evidence mutation.
The CLI adds no network, provider, credential, telemetry, persistence or data write.

## Remaining limitations

- The preview is fixed and stateless; there is no pagination.
- Screening and multi-capability output can still exceed 1,000 terminal lines
  because exact previewed assessments, references, warnings and lineage are verbose.
- The first 10 assessments are authoritative-order records, not a candidate-only or
  financial-value ranking, so they may not demonstrate every status.
- Technical identifiers are real evidence references, not verified transaction,
  company or business-event identities.
- Full human and JSON output intentionally remain large and sensitive.

