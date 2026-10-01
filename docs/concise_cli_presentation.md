# Phase 9 — Step 27: concise CLI presentation

## Presentation problem

The manager returns complete structured evidence, but the former human renderer
printed every nested collection. Step 25 measured outputs up to about 12.7 MB and
468,000 lines. Step 27 changes only the human presentation boundary; manager,
Financial Core, anomaly, routing, and structured response contracts are unchanged.

## Output modes

- Default human `ask` output is concise. It keeps status, routing, capability,
  existing summary text, evidence context, currency, records, coverage,
  exclusions, warnings, limitations, errors, lineage, and terminology visible.
- `--full` restores the expanded human representation. It may be very large.
- `--json` emits the complete manager response with its existing semantics and
  exact decimal serialization. `--json` and `--full` are mutually exclusive.

`capabilities` and `plan` were already bounded and retain their existing human
content. Both options may appear before or after the subcommand.

## Deterministic preview policy

Every ordinary evidence list with more than 10 entries is displayed as the first
10 entries in its authoritative existing order. The renderer does not sort, sample,
rank, or classify entries. Each preview states `returned_item_count`,
`total_item_count`, and `omitted_item_count`, plus a readable “Showing X of Y”
notice. Nested large lists, including flag-row references, follow the same rule.
Warning entries are handled separately so all distinct warnings remain visible.
For anomaly evidence, the reference preview instead includes every authoritative
reference named by the first 10 displayed assessments, in the original reference
order. This prevents displayed rows from pointing to omitted fences or peer data;
the reference preview still discloses its returned, total, and omitted counts.

Existing record IDs, source-row lineage, reference IDs, values, fences, peer data,
and statuses remain unchanged when their entries are previewed. The renderer does
not invent identifiers. Existing long explanation text is capped at 2,000
characters with the exact omitted character count disclosed; the structured
evidence and warning presentation remain separate and available.

## Warnings and terminology

Concise mode displays an exact duplicate warning entry once even when convenience
envelopes repeat it. The displayed entry lists every orchestration step to which
it applies. Distinct warning entries remain present. Large collections
inside an individual warning receive the ordinary disclosed preview; the warning's
code, message, field, scope, and affected-record count remain visible. Neither the
manager response nor its nested warning collections are modified.

Presentation notes explain that:

- `UNKNOWN` currency means authoritative denomination evidence is absent;
- `CANDIDATE` is a statistical screening candidate for investigation, not fraud,
  error, misconduct, probability, or certainty;
- `NOT_ASSESSED` means that the stated assessment could not be performed; and
- coverage and exclusions describe which source records participated.

Internal enum values are not renamed or reclassified.

## Evidence-integrity rules

The formatter builds a display-only copy. It performs no financial arithmetic,
currency inference, routing, SQL, anomaly scoring, threshold calculation, or
candidate reclassification. Exact `Decimal` values use the existing fixed-point
serializer. Omitted display entries remain in the authoritative manager response,
which is available through `--json`; `--full` provides expanded human inspection.

## Limitations

This is a stateless preview, not pagination. It does not choose “most important”
or candidate-only rows, so a first-10 preview may not contain every result status.
`--full` and `--json` can still be large and may expose sensitive financial data
to the local terminal or redirected files. The CLI remains English-only with the
existing bounded request grammar.
