# Phase 8 — Step 23 validation

Scope: environment and data provisioning for the implemented local V1 only. The
Step 21/22 starting baseline was **291 passing tests**. No fresh-clone or destructive
clean-room exercise was performed; that remains Step 24.

## Inspection and decisions

Inspected AGENTS.md, CONTEXT.md, README, the technical guide, V1 acceptance and
Step 22 validation, `.gitignore`, repository status/diff/tree, environment files,
all `src/` and `tests/`, database schema/approval/initializer/loader/validation,
the complete data directory layout, and documented acquisition evidence.

The operational code and unittest suite import only Python standard-library and
repository modules. The existing `.venv`, notebook kernels, and completed
regressions use Python 3.14.7. The supported V1 minor is therefore Python 3.14,
with 3.14.7 recorded as the validated patch in `.python-version`. An intentionally
empty `requirements.txt` documents that runtime and test installation has no
third-party packages. Pandas/Jupyter packages in the local environment belong to
historical notebook work and were not copied into the runtime manifest. No package
manager, package build, dependency, or capability was added.

## Provisioning artifacts

- `.python-version` records `3.14.7`.
- `requirements.txt` explicitly records the zero-third-party dependency set.
- `src/provisioning.py` provides `python -m src.provisioning`, a read-only JSON
  validator with deterministic exit status.
- `data/README.md` states exact required paths and distinguishes raw source bytes,
  the approved processed bundle, cleaning evidence, generated SQLite, and optional
  captured load output.
- `docs/environment_and_data_provisioning.md` documents setup, data placement,
  reconstruction, validation, CLI/tests, failures, and privacy boundaries.
- `.gitignore` continues to exclude raw data and `.venv`, and now excludes generated
  `data/database/*.db` and `data/database/load_validation_report.json`.
- README links the guide and gives the canonical short setup workflow.

The validator derives its required data paths from the existing
`src/database/approved_run.json`. It checks Python/environment metadata, app
imports, every required path, approved hashes and cleaning gates, the existing
database when present, CLI importability, and unittest discovery. Missing files
are listed by exact repository-relative path. With a missing database and valid
inputs it reports `READY_TO_BUILD`; with an invalid database it keeps the approved
bundle status separate and reports the database as `INVALID`. It performs no
download, rebuild, test execution, or source mutation.

## Data assumptions and acquisition limits

The required raw files remain:

```text
data/raw/Company Financials Dataset/Financials.csv
data/raw/Receiver General Accounting Transactions/tcrg-rgat.csv
```

The only loadable processed run remains
`20260928T190320706702Z_0a18cf5b`, with five hash-pinned artifacts. The older run
is historical and is never selected by recency. Notebooks 01–05 remain protected
pipeline evidence because the existing approval contract pins their hashes.

Notebook 01 identifies the official Receiver General catalogue/resources but also
states that the exact Kaggle listing/version and local-byte provenance chain are
unverified. A similarly named official download cannot be treated as the approved
local source without matching evidence. No authoritative acquisition URL, license,
or redistribution permission is documented for Company Financials. Provisioning
therefore requires exact approved files from an authorized project custodian and
does not automate acquisition or invent provenance.

## Database reconstruction

The existing `python -m src.database.initialize` remains the sole pipeline. No
second loader was created. It refuses an existing destination, permits only the
approved run, verifies protected sources, creates the existing schema and loads
inside one transaction, validates and reopens the database, and checks sources
again before publishing.

A Step 23 reconstruction to a new temporary path passed all existing load gates:
schema version/hash, integrity and foreign keys, 9,282 Receiver General rows, 700
Company Financials rows, complete lineage/flags, exact numeric preservation, and
smoke-query reconciliation. The builder reported `protected_hashes_unchanged=true`
and `disk_reload_passed=true`. The production database was not replaced; its
SHA-256 remained:

```text
8b9536867d7e1ee2e3fd8b0040d40f5806cf6ecb8afc38491cbc058de727c744
```

## Validation and tests

The following workflows passed from the repository root:

```sh
python3.14 --version
python -m pip install -r requirements.txt
python -m src.provisioning
python -m src.database.initialize --database <new-temporary-path>
python -m src.cli capabilities
python -B -m unittest tests.test_provisioning -v
python -B -m unittest discover -s tests -v
```

The validator reported Python 3.14.7, no third-party packages, a valid approved
bundle, valid production database, importable CLI, 296 discovered tests, no network
requirement, and no errors. `py_compile` passed for the new source/test modules and
`git diff --check` passed.

Five focused tests cover exact approved input/derivative paths, clear missing-data
failure, environment metadata consistency, offline/read-only validation with raw
hash preservation and rebuild readiness, and separation of valid data from an
invalid database diagnostic. The final regression passed **296 tests: 0 failures,
0 errors, 0 skipped** in **295.669 seconds**. This is the prior 291-test suite plus
five Step 23 tests.

Post-regression SHA-256 checks matched the Step 22 values for both raw CSVs, all
five protected notebooks, and the production database. Production dataset content
and financial semantics were not changed.

## Security and unresolved limitations

Provisioning remains local-first: no telemetry, external LLM, credential handling,
data upload, row transmission, undocumented automatic download, or network fallback
was added. The provisioning validator is explicitly exercised with socket creation
denied. Existing Step 19 controlled application boundaries remain unchanged.

Exact raw-data acquisition remains manual because documented provenance and
redistribution evidence are incomplete. The approved processed bundle must also be
present byte-for-byte; Step 23 does not recreate it by rerunning notebooks. Python
3.14.7 is the only patch version actually validated. The processed directories
were present but pre-existing and untracked in the inspected working tree; whether
the eventual repository snapshot delivers the approved bundle remains a Step 24
verification concern. Rebuilds are logically reconciled but are not byte-identical
because the existing database pipeline records `processing_run.ingested_at` at
build time. Pip upgrade can require a package index and is optional because V1 has
no third-party dependencies. Host access control and egress sandboxing remain
deployment responsibilities.

Step 23 is complete. Phase 8 Step 24 — Fresh Clone Reproducibility is the next
recommended step and was not started here.

Subsequent Step 24 validation resolved the processed-bundle question: the approved
five-file bundle is an explicitly required external custodian input, not a Git
artifact or a notebook-regenerated output. See
[`fresh_clone_reproducibility.md`](fresh_clone_reproducibility.md).
