# Phase 5 — Step 14 validation

Scope: Financial Anomaly Detection only, implemented as deterministic descriptive
investigation screening. Both datasets passed separate restricted readiness gates
in [anomaly detection](anomaly_detection.md). No Step 15/16, agent extension,
forecast, RAG, application interface or deployment was implemented.

## Readiness and implemented behavior

| Dataset / measure | Readiness | Rule and peer evidence |
|---|---|---|
| Receiver General accounting amount | READY for descriptive screening | Upper-tail Tukey IQR; direction × voucher-type peers established by EDA sections 12–14 |
| Company Financials Sales | READY for descriptive screening | Two-sided Tukey IQR; segment × sale-price peers established by EDA sections 14–15 |
| Company Financials Profit | READY for descriptive screening | Same pricing peers and two-sided rule, independently excluding unavailable Profit values while preserving negative observations |

This is not a validation of fraud/error detection, statistical significance,
independence, financial comparability or prediction accuracy. No labels were
created, no models were trained, and no performance claims are made. The
30-numeric-record guard and positive-IQR requirement reproduce the explicit
exploratory policy in both EDAs. Other peer definitions/measures and alternative
methods are deferred with reasons in the architecture document.

## Approved-snapshot observations

These values were computed by the new read-only service and checked against the
existing EDA evidence, using exact decimals rather than notebook floats. Counts
are assertions on this approved snapshot, not hard-coded production decisions.

| Measure | Selected rows | Global candidates | Peer candidates | Peer NOT_ASSESSED | Assessed by both |
|---|---:|---:|---:|---:|---:|
| RG accounting amount | 9,282 | 2,194 | 937 | 175 | 9,107 |
| CF Sales | 700 | 53 | 5 | 0 | 700 |
| CF Profit | 700 | 102 | 7 | 5 | 695 |

RG peer abstentions: 26 missing voucher labels and 149 rows in groups below 30.
The 55 complete observed peer groups include 25 eligible groups. Among the
9,107 records assessed by both rules: 298 selected by both, 1,788 global-only,
639 peer-only and 6,382 by neither. Missing department/subledger/ledger labels
do not silently exclude records from the implemented direction/voucher peers.

CF has seven pricing groups of 100 rows before target missingness. Sales has
zero overlap between its 53 global and five peer candidates. Profit has two
selected by both, 100 global-only and five peer-only among its 695 assessed
records. The five unresolved Profit tokens are NOT_ASSESSED in both modes;
all 58 negative Profit values remain intact. The 53 unresolved Discounts are
unchanged and are not silently used as numeric values or unrelated Sales warnings.

Exact global reference fences:

- RG: upper `167264.64250`; no lower-tail rule.
- Sales: lower `-351796.250`, upper `628801.750`.
- Profit: lower `-26842.950`, upper `52549.770`.

All amounts and fences remain in unknown source denomination. No currency was
assigned or converted. Global and peer denominators are disclosed separately.

## Test results

Focused run:

```sh
.venv/bin/python -B -m unittest discover -s tests -p test_anomaly.py -v
```

32 passed, 0 failures, 0 errors, 0 skipped; 11.563 seconds. A subsequent small
test refinement added recursive checks against float/Decimal leakage in JSON
results; the final full regression below includes that refinement.

Full final run:

```sh
.venv/bin/python -B -m unittest discover -s tests -v
```

| Suite | Passed | Failed | Errors | Skipped |
|---|---:|---:|---:|---:|
| Phase 3 database | 17 | 0 | 0 | 0 |
| Phase 4 financial tools | 37 | 0 | 0 | 0 |
| Phase 4 quality | 19 | 0 | 0 | 0 |
| Phase 4 currency/FX | 22 | 0 | 0 | 0 |
| Step 13 agent | 36 | 0 | 0 | 0 |
| Step 14 anomaly service | 32 | 0 | 0 | 0 |
| **Total** | **163** | **0** | **0** | **0** |

Elapsed time: **136.655 seconds**. Counts are unittest methods; subtests are not
inflated into additional tests. All previous 131 methods remain unchanged and
pass. No network tests or unavailable modules were skipped.

## Acceptance checks

| Requirement | Verified result |
|---|---|
| Clear fixture extreme and ordinary values | Candidate vs NOT_SELECTED follows strict exact fences, including equality and tiny decimal differences |
| Signed observations | Lower-tail Profit fixture supported; ordinary negative values are not selected merely for being negative |
| Minimum peer size | 29 numeric values plus one missing value is insufficient; 30 numeric values is eligible when IQR is positive |
| Small/flat peers | NOT_ASSESSED with reason; no global fallback, invented normal class or zero-IQR division |
| Missing measure/group | Missing and placeholder values remain null; missing labels create no synthetic peer; all unavailable dependencies disclosed |
| Record accounting | Selection, numeric coverage, global/peer abstentions and jointly assessed comparison denominators reconcile |
| Exact computation | Isolated precision-60 context, strict overflow blocker, no float authority or JSON float/Decimal leakage |
| Determinism and lineage | Repeated calls and reversed fixture order agree; source/run/row IDs and snapshot hashes retained; input objects not mutated |
| Quality reuse | Original flags, currency/provenance/semantic warnings preserved; extra compound-peer dependencies are relevant; unrelated missing fields remain irrelevant |
| Per-record evidence | Reference IDs resolve; warning indices link dataset and affected-row evidence without inventing/multiplying source flags |
| No accusatory classification | Only CANDIDATE, NOT_SELECTED, NOT_ASSESSED; no probability or business-validity label |
| Offline operation | Actual snapshot screening succeeds with socket creation disabled; no network/provider or new dependency introduced |
| Controlled read-only selection | Reuses validated snapshot and parameterized Core filters; SQL-shaped categories remain literal values; SQL/group/method input rejected |
| Failure behavior | Invalid/unsupported requests fail before data access; missing snapshot and malformed/excess-precision data block; unexpected internal failures propagate |
| Agent separation | Existing 17-tool registry and rejection of anomaly requests remain unchanged; no mathematics added to prompts |
| Snapshot consistency | Current reference counts match existing EDA; no synthetic records written into production |

## Protected files and modifications

A pre-Step-14 inventory hashed **95 existing files** across source, tests, data,
notebooks and documentation. After the full test run, **93 were unchanged**.
The two intentional existing-file changes are:

- `src/financial/quality.py`: optional keyword-only `additional_fields` for
  trusted statistical peer dependencies. No existing caller passes it; the
  previous 19 quality tests and all analytical/agent tests pass unchanged.
- `README.md`: documents the separate screening service and links this step.

Unchanged: production database, raw/processed data, both historical cleaning
runs, manifest/validation/review artifacts, schema, approved-run pins, notebooks,
Step 09 contracts, all previous tests and Step 13 implementation. No schema or
database metadata changes occurred. Temporary databases remain confined to
existing database tests.

Database SHA-256:
`8b9536867d7e1ee2e3fd8b0040d40f5806cf6ecb8afc38491cbc058de727c744`.

DDL SHA-256:
`7a815fe0ffbfa68849f5e3e1394d9e9e7fb117c771c7b318c0ab50fe75a83fe5`.

Created:

- `src/anomaly/__init__.py`
- `src/anomaly/baseline.py`
- `src/anomaly/service.py`
- `tests/test_anomaly.py`
- `docs/anomaly_detection.md`
- `docs/step14_validation.md`

Pre-existing unrelated work was retained. No dependency, generated production
dataset, fitted model, credentials or external-service adapter was added.

## Limitations and stop

Current references are in-sample and sensitive to selected-cohort composition.
Thirty observations is an exploratory guard, not a sufficiency guarantee. Price
and accounting peer labels do not establish independent comparable financial
events. Unknown denomination, source provenance, RG summary/detail overlap and
fiscal alignment, sparse dimensions, CF entity/grain ambiguity, placeholder
semantics and fractional quantities remain unresolved. No statistical candidate
is an accusation, error finding or certified invalid observation.

The next recommended step is a separately authorized **Step 15 forecasting
readiness assessment**, beginning with verification of cash-flow target semantics
and adequate history. Forecasting and RAG were not started.
