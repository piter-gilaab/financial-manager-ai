# Environment and data provisioning

This procedure provisions the implemented local V1. Run every command from the
repository root. It does not rerun data cleaning or perform the Step 24 fresh-clone
exercise.

## Prerequisites and Python environment

Use Python **3.14**. The validated patch version is **3.14.7**, recorded in
`.python-version`. The operational CLI, SQLite builder, validator, and unittest
suite use only the Python standard library and repository source. Historical
notebooks used Pandas/Jupyter, but notebook reproduction is outside the V1 runtime
and is not required to build the database from the approved processed run.

```sh
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

`requirements.txt` intentionally contains no installable packages. Do not create
or commit `.venv`; it is Git-ignored. The pip upgrade is the only command here
that can contact a package index and is optional for this zero-dependency V1.

## Required data

The exact layout and artifact roles are listed in [`data/README.md`](../data/README.md).
Database construction requires all of the following:

- the two raw CSVs at their exact paths and approved hashes;
- all five artifacts under
  `data/processed/20260928T190320706702Z_0a18cf5b/`;
- tracked notebooks 01–05, whose hashes are protected pipeline evidence;
- `src/database/approved_run.json` and `src/database/schema.sql`.

Raw CSVs are authoritative source bytes and are Git-ignored. Cleaning never
mutates them. The approved processed run is a derivative of those sources, but it
is the only accepted database input bundle and must remain byte-for-byte unchanged.
Its standardized CSVs, cleaning manifest, validation report, and review flags are
all authoritative for loading. The older processed run is historical and is not
selected. The SQLite database and `data/database/load_validation_report.json` are
generated local artifacts and are Git-ignored.

Step 24 confirmed that the approved processed bundle is an external custodian
input alongside the raw CSVs. It is not distributed by Git and there is no
supported command that regenerates it from the notebooks. Obtain its exact five
hash-approved files from the authorized project custodian and place them at the
paths above before rebuilding SQLite.

The Receiver General notebook records official publisher links, but the exact
provenance chain to the local CSV and its recorded Kaggle redistribution remain
unverified. No exact public acquisition URL, license, or redistribution permission
is documented for Company Financials. Obtain the exact hash-approved files from an
authorized project custodian. The project does not download or guess replacements.

## Validate the environment

After placing the data, run:

```sh
python -m src.provisioning
```

The JSON report verifies Python and environment metadata, application imports,
required file presence, approved hashes and cleaning gates, the existing database
when present, CLI importability, and unittest discovery. It exits 0 on a usable
configuration. If the database is absent but every approved input validates, the
database section reports `READY_TO_BUILD` and gives the exact builder command.
No test is executed by this validator, and no file or network resource is changed.

## Reconstruct SQLite

The existing builder is the sole supported pipeline:

```sh
python -m src.database.initialize
```

It creates `data/database/financial_manager.db` only when that path does not
already exist. It accepts only approved run
`20260928T190320706702Z_0a18cf5b`, checks every protected hash and cleaning gate,
loads the existing schema in one transaction, validates the result, reopens it
read-only, and verifies that protected files did not change. It never rewrites raw
or processed data and refuses to replace an existing database.

To verify reconstruction while preserving the current database, choose a new
destination:

```sh
python -m src.database.initialize --database /tmp/financial_manager.rebuilt.db
```

The builder prints its validation report as JSON. Redirect it only if you want a
local report, for example `> data/database/load_validation_report.json`. If the
default database must be replaced, first preserve or remove it deliberately, then
run the default command; the builder itself will not overwrite it.

Reconstruction is logically reproducible and fully reconciled to the approved
artifacts. SQLite file bytes are not expected to have a stable SHA-256 because the
existing `processing_run.ingested_at` records the build time.

## Run the CLI and tests

```sh
python -m src.cli capabilities
python -m src.cli plan "Find outliers in Profit"
python -m src.cli ask "What were total sales by country?" --json
python -B -m unittest discover -s tests -v
```

The CLI requires the default validated database path. The test command is the
full regression suite; the provisioning validator only confirms discovery.

## Common failures

- **Wrong Python version:** recreate `.venv` with Python 3.14; 3.14.7 is the
  validated version.
- **Missing file:** use the exact relative path printed by the validator. Names,
  spaces, and capitalization matter.
- **Approved hash mismatch:** restore the exact approved file. Do not edit a raw,
  processed, report, or notebook artifact to make validation pass.
- **Existing database:** the builder intentionally refuses replacement. Use a new
  `--database` path or deliberately preserve/remove the old default first.
- **Unapproved processed run:** only the pinned run ID loads; copying or renaming
  another run does not approve it.
- **CLI snapshot blocker:** validate the default database and its source bundle;
  the CLI will not silently use a stale or different snapshot.

## Security and privacy

Provisioning is local-first. The validator, database builder, tests, and CLI add no
telemetry, data upload, external LLM, credential use, undocumented download, or
network fallback. Raw data, approved artifacts, SQLite rows, questions, and output
remain local. Keep raw sources, databases, reports, terminal output, and shell
history protected according to their sensitivity. These controls preserve the
Step 19 application boundaries; host access control and network sandboxing remain
deployment responsibilities.
