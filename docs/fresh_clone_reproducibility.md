# Fresh-clone reproducibility

**Status: PASS.** A clone of committed V1 code can be made operational with
Python 3.14 and seven explicitly identified external custodian files: two raw CSVs
and the five artifacts from the approved processed run. No public acquisition,
redistribution permission, or notebook regeneration is implied.

## Clean-room method

The final test used commit `fce45ce` and a local clone outside the primary tree:

```sh
git clone --local --no-hardlinks \
  "/home/piter/Documentos/my workspace/financial-manager-ai" \
  /tmp/financial-manager-step24.XLiMZ1/repository-final
```

`--no-hardlinks` kept the clone's Git objects independent. Only committed files
were cloned; ignored and untracked files were absent. The primary working tree was
not copied or changed during clean-room commands.

The initial clone had no `.venv`, raw or processed data, SQLite database,
`__pycache__`, or other ignored runtime output. `python3.14 -B -m src.provisioning`
exited 1 and listed all seven missing files by exact relative path. It created no
data, performed no download, and still verified application imports plus 298 tests
with zero discovery import errors.

## Environment reconstruction

Inside the clone:

```sh
python3.14 -m venv .venv
.venv/bin/python -m pip install --no-index -r requirements.txt
```

Python was 3.14.7. The venv reported `include-system-site-packages = false`, its
interpreter and prefix were inside the clone, and `pip==26.2.1` was its only listed
package. The intentionally empty requirements file installed successfully with
`--no-index`; no package cache or primary `.venv` was used.

## Data provisioning stages

Stage A proved the committed clone intentionally lacks all required data and fails
clearly. Stage B copied only already-authorized local bytes as a stand-in for files
provided by an authorized project custodian:

```text
data/raw/Company Financials Dataset/Financials.csv
data/raw/Receiver General Accounting Transactions/tcrg-rgat.csv
data/processed/20260928T190320706702Z_0a18cf5b/cleaning_manifest.json
data/processed/20260928T190320706702Z_0a18cf5b/cleaning_review_flags.csv
data/processed/20260928T190320706702Z_0a18cf5b/cleaning_validation_report.json
data/processed/20260928T190320706702Z_0a18cf5b/company_financials_standardized.csv
data/processed/20260928T190320706702Z_0a18cf5b/receiver_general_standardized.csv
```

Every SHA-256 matched `src/database/approved_run.json`. The older processed run
and primary SQLite database were not copied. This test demonstrates local
reproducibility with authorized bytes; it does not establish a public source,
license, acquisition chain, or redistribution right.

## Approved processed-data behavior

Evidence from Git, `.gitignore`, `data/README.md`, notebooks, approval metadata,
and the loader establishes option **A**: the processed bundle is supplied
externally. Git does not distribute it, and the database builder requires it.
Notebooks 01–05 are protected historical evidence; there is no supported command
that reruns them to recreate and approve the bundle. Rebuilding processed data
would be a separate governed cleaning/approval operation.

## Database and provisioning validation

The documented command created the default database inside the clone:

```sh
.venv/bin/python -B -m src.database.initialize
```

It selected only run `20260928T190320706702Z_0a18cf5b` and passed schema/hash,
integrity, foreign-key, lineage, flag, exact-decimal, row-count, and smoke-query
checks. Results included 9,282 Receiver General records, 700 Company Financials
records, 29,944 quality flags, `protected_hashes_unchanged=true`, and
`disk_reload_passed=true`. The rebuilt database SHA-256 was
`dd935c816017f682d55aedf5dc6785b2e61307010e7da4f1f87dcd6463594258`;
byte identity is not required because `ingested_at` records build time.

After rebuilding, `python -m src.provisioning` returned `PASS`: Python/environment
metadata, approved bundle, rebuilt database, imports, and all 298 discovered tests
passed with zero import errors. Every reported root/database path pointed into the
clean clone.

## CLI validation

The actual module entry point was run for:

```sh
python -m src.cli capabilities
python -m src.cli plan "What were total sales by country?"
python -m src.cli ask "What were total sales by country?"
python -m src.cli ask "Find outliers in Profit" --json
python -m src.cli ask "What were total sales by country?" --json
```

Financial Analysis returned `SUCCESS` with five 140-record country groups.
Anomaly Detection returned the expected `PARTIAL` screening result with 700 items.
Both retained `UNKNOWN` currency. Capabilities showed Financial Analysis and
Anomaly Detection AVAILABLE, with Cash Flow Forecasting and Document Retrieval
BLOCKED for their existing reasons. No external provider was required.

## Tests, offline result, and hidden state

The complete clean-clone suite passed:

```text
Ran 298 tests in 300.524s
OK
```

The modified primary repository independently passed the same 298 tests in
294.576 seconds with zero failures, errors, or skips.

Package installation used `--no-index`. Database construction, provisioning, and
representative CLI commands also passed with a `sitecustomize` audit hook denying
all Python `socket.*` events. Network namespaces could not be used because this
sandbox disallowed `unshare -n`; the socket denial and existing offline/security
tests provide the application-level evidence.

A real 700-record query passed under `env -i`, with no home directory or inherited
environment variables. Tracked-file scanning found no primary or temporary clone
absolute paths. Database `source_file` and `processed_file` values were relative.
The clone did not inherit the primary `.venv`, database, caches, old processed run,
untracked documentation, shell configuration, or notebook execution state.

## Defects found and corrected

1. Ten required `src/financial` modules and three baseline test modules were
   untracked, so a committed clone could not import the CLI or reproduce the suite.
   Commit `a36f5e0` added only those existing runtime/test files.
2. Provisioning counted unittest `_FailedTest` import failures as successful test
   discovery. It now reports `import_errors` and fails discovery when any test
   module cannot import; a focused regression test covers this behavior.
3. Runtime snapshot access required the original SQLite byte hash even though the
   builder records a new `ingested_at`. It now accepts the bytes only after the
   existing schema, approved bundle, complete logical database validation, and
   read-only in-memory loading pass. Tampered snapshots remain blocked, and a new
   test proves a clean rebuild is queryable.

## Remaining manual requirements

An authorized project custodian must provide the exact two raw CSVs and five
approved processed artifacts. Their hashes must match the committed approval file.
The project has no verified public acquisition path or redistribution permission
for the complete input set, and provisioning intentionally performs no download.
Python 3.14 must already be installed locally. These are explicit prerequisites,
not hidden machine state.
