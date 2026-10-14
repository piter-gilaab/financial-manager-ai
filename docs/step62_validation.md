# Step 62 — SALES_RECORD dynamic anomaly adapter validation

## Result

PASS. Step 62 implements only `SALES_ANOMALY_SCREEN` and
`PROFIT_ANOMALY_SCREEN` for approved dynamic `SALES_RECORD` datasets. The
interface is a typed, code-owned request and operation enum in `src.anomaly`;
it is not connected to the Financial Manager, conversation routing or a new
execution CLI.

## Module and policy decision

The adapter lives in `src/anomaly/dynamic.py`, beside the established anomaly
policy. It obtains an immutable authenticated canonical-record projection from
the existing `SalesRecordExecutionAdapter`, then delegates reference and record
classification to the existing `src.anomaly.baseline.reference` and
`assessment` primitives. This keeps onboarding artifact authentication in the
execution module and Tukey policy authority in the anomaly module. There is no
second quartile implementation.

Both operations are statically registered to one confirmed semantic role and
`tukey_iqr` v1.0. The only scope is `GLOBAL`. Requests for another operation,
measure or grouping are unsupported; no caller-selected function, class,
column, policy or peer definition is resolved.

## Deterministic behavior

- usable values are exact canonical `Decimal` values under the isolated
  precision-60 context;
- quartiles use linear `(n - 1) × p`; fences use `1.5 × IQR` and strict
  comparisons in both tails;
- fewer than 30 usable values blocks with
  `insufficient_numeric_records`; zero IQR blocks with `zero_iqr`;
- missing and non-missing unparseable tokens remain distinct
  `NOT_ASSESSED` records; they are never zero or `NOT_SELECTED`;
- negative Sales and Profit retain their sign and are selected only by a
  fence;
- UNKNOWN denomination is disclosed and allowed, one CONFIRMED ISO code is
  preserved, and CONFIRMED_MULTIPLE blocks without classifications;
- arithmetic failure blocks the entire result; no partial fences or candidate
  set are returned;
- records sort by source row and canonical record ID.

The typed result contains the global reference, reconciled counts, every record
assessment, bounded candidate references, currency, quality disclosures,
limitations and full dataset/registry/profile/mapping/confirmed-column/
canonical/source/policy lineage. Normal evidence contains no filesystem path.

## Compatibility and integrity

Synthetic Sales and Profit cohorts were evaluated through the legacy Company
Financials global policy primitive and the dynamic adapter. Threshold semantics
and every `CANDIDATE`/`NOT_SELECTED` decision matched. Receiver General and
Company Financials services were not migrated or modified.

Dynamic tests cover renamed columns, inert malicious-looking values, stale
mapping, stale profile, changed source bytes, stable column lineage, exact fence
equality, sample size, zero IQR, exact decimals, currency and deterministic
ordering. The existing execution adapter contract continues to cover registry,
schema and stable-column fail-closed behavior.

One reproduced precision defect was fixed: canonical exact decimal values are
now serialized with fixed-point `format(value, "f")`, so a valid small value is
not converted to an exponent token that the canonical parser rejects.

## Verification

Focused Step 62 and adjacent legacy/integrity suites:

```text
90 passed
0 failed
0 errors
0 skipped
```

`git diff --check` passed.

## Review gate

The parallel Standards review found no hard standards violation and initially
reported two design smells: a private preparation type leaking across the seam,
and duplicated measure selection. The seam now returns a public immutable
projection, and record field selection is concentrated in one closed accessor.

The parallel Spec review initially found incomplete typed evidence/lineage,
missing currency on the multiple-currency blocker, implicit ordering, missing
integrity/negative-Sales coverage and this absent validation record. Those
findings were corrected and retested. No review finding identified policy
divergence, float authority, inclusive comparison, fallback behavior, arbitrary
screening, source mutation, dynamic dispatch, LLM authority or an affirmative
fraud/suspicion claim.

Step 62 does not implement Step 63 readiness, Step 64 Manager/evidence
integration or Step 65 end-to-end validation.
