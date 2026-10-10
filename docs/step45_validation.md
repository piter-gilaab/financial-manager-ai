# Phase 13 — Step 45 validation

## Status

**PASS.** Structural profiling is deterministic, bounded, serializable and
completed before any semantic provider is consulted.

## Profile behavior

The versioned profile reports shape, ordered columns, missing counts and exact
six-place percentages, cardinality, exact duplicate-row candidates, primitive
observations, parse counts, `Decimal` ranges/scales, unambiguous ISO date ranges,
ambiguous-date counts, bounded first-observed examples/frequencies, formatting
observations and possible-identifier/sensitivity signals.

Source strings are preserved separately from structural observations. Monetary
formatting can be reported, but `currency_state` remains `UNKNOWN`. Binary float
is not used. `DD/MM/YYYY`-shaped values remain `AMBIGUOUS_DATE` with no date
range. Rows are neither imputed nor deleted; duplicate records are reported only.

Raw examples and frequency values are suppressed for identifier-name,
mixed/all email-like, long numeric identifier-like and high-cardinality unique
text columns. This is a conservative signal, not a claim of complete PII
detection.

## Reproducibility

The profile digest covers the source fingerprint, profile version, structural
results and sample bounds using canonical sorted JSON. Sampling is deterministic
and never random.

## Focused tests

`python -m unittest tests.test_onboarding_profiling tests.test_onboarding_ingestion`

Result: **13 passed**. Tests cover counts, missingness, duplicates, decimals,
currency non-inference, ambiguous dates, sensitive-value suppression,
deterministic bounds and prior ingestion behavior.
