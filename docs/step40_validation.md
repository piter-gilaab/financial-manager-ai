# Phase 12 — Step 40 validation

## Decision

**PASS.** Authoritative evidence becomes analyst-style prose only through a
deterministic fact catalog and a fail-closed grounding guard. Tables and lists
are rendered by code directly from evidence.

## Implemented

- `grounding.py`:
  - `locate` accepts a single analysis or screening result, or a follow-up.
  - `build_packet` produces the `GroundedResponsePacket`, with fact IDs
    `F<n>`/`W<n>`, exact values, units, semantic type and source path.
  - Categorical ranks come from exact `Decimal` comparison; periods keep
    evidence order.
  - Groups and records are capped at 25 each, with omitted counts.
  - Coverage, exclusions, currency state and quality disclosures are included.
    For follow-ups, they are taken from the follow-up's own evidence.
  - No hashes, record IDs, paths, raw `$` tokens, flag lists or snake_case keys
    are included.
- `prompts.respond_request` separates SYSTEM RULES, `user_input` and
  `structured_evidence`.
- `validation.validate_natural_response` checks:
  - the exact schema, at most 1,200 characters and 12 lines, printable text;
  - that every fact and warning ID exists;
  - the allowed presentation and the language;
  - after NFKC normalization, rejects:
    - currency codes, symbols and names (including lowercase, dotted and
      "Canadian currency" forms);
    - fraud, error, certainty, probability and suspicion language;
    - forecast, cash, income and document claims, and future-tense claims;
    - multiplicative comparisons in words;
    - internal identifiers and markup;
    - spelled-out large numbers or bare scale words;
  - that every numeral matches a *declared* fact with the same sign, exactly or
    as a correct rounding, with percentages matched only to percentage facts.
- `presentation.py`:
  - code-owned localized templates for clarifications, blocked capabilities,
    refusals and session errors;
  - tables and lists for groups, extreme records, screening candidates
    (`A1`–`A10`) and follow-ups;
  - locale digit grouping done by string operations only;
  - mandatory notes for UNKNOWN currency, coverage and exclusions, missing
    group values, CANDIDATE/NOT_ASSESSED and source disclosures, plus the
    interpreted request.
- Selection: a record count gets text only; a summary gets text plus a metric
  list; groups, records and screening get text plus a table; a follow-up gets a
  list. Blocked outcomes and clarifications use templates.

## Tests

`tests/test_mediation_grounding.py`, 20 tests:

- exact fact values and code-owned ranks;
- no raw state in the packet;
- grounded PT/EN prose accepted;
- invented, derived and sign-dropped numbers rejected, and numbers taken from
  undeclared facts rejected;
- currency, fraud, capability, identifier and markup claims rejected;
- 22 bypasses found in review, now rejected;
- ratio claims written in words rejected;
- terminology that can be echoed safely;
- schema, ID, language, size and presentation failures;
- injection carried inside source values;
- the three-section prompt and bounded record facts;
- tables built from evidence in both locales;
- screening terminology and labels;
- follow-up disclosures;
- full verbalized turns for sales, record count, screening plus follow-up, and
  an ungrounded response that is never shown.

## Review and defects

Both boundary reviews found real gaps, all fixed test-first:

- guard bypasses (fullwidth, lowercase `usd`, `FY2026`, `pct`, spelled numbers,
  suspicion and future claims);
- numbers that were not tied to declared facts, and dropped signs;
- trigger words inside the packet's own terminology;
- snake_case labels;
- follow-ups losing their disclosures and hard-coding the currency;
- a missing coverage-percentage fact for groups;
- two-section instead of three-section prompts;
- duplicated helpers.

The final review reproduced one more gap, multiplicative comparisons written in
words, and it was fixed with a `derived_claim` rule.
