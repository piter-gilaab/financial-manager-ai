# V1 data provisioning

The V1 reads one approved, hash-pinned cleaning run. Keep source and derived
artifacts in these exact locations:

```text
data/
├── raw/                                           # authoritative source bytes; Git-ignored
│   ├── Company Financials Dataset/
│   │   └── Financials.csv
│   └── Receiver General Accounting Transactions/
│       └── tcrg-rgat.csv
├── processed/
│   └── 20260928T190320706702Z_0a18cf5b/           # approved derivative bundle
│       ├── cleaning_manifest.json
│       ├── cleaning_review_flags.csv
│       ├── cleaning_validation_report.json
│       ├── company_financials_standardized.csv
│       └── receiver_general_standardized.csv
└── database/                                      # generated locally; Git-ignored
    ├── financial_manager.db
    └── load_validation_report.json                # optional captured builder output
```

The two raw CSVs are authoritative inputs. They are never edited by cleaning,
loading, validation, or querying. Their approved SHA-256 values and the five
processed artifact hashes are pinned in
[`src/database/approved_run.json`](../src/database/approved_run.json). The
processed CSVs preserve source tokens and lineage; the manifest, cleaning report,
and review flags are part of the approved bundle, not disposable logs.

The older processed directory `20260928T185710790098Z_ca58a74d` is historical and
is not accepted by the database loader. Directory order or recency never selects
a run. The SQLite database and its load report are generated derivatives and can
be reconstructed from the approved run. Do not commit raw CSVs, local databases,
or ad hoc validation output.

The repository records an official Receiver General catalogue and resource links
in notebook 01, but it does not establish that the current local bytes are an
exact version of those public resources. The recorded Kaggle redistribution lacks
an exact listing, uploader, version, and download date. No authoritative public
acquisition URL, license, or redistribution permission is documented for the
Company Financials CSV. Obtain the exact approved bytes through an authorized
project custodian; do not substitute a similarly named download. Provisioning
performs no network access or automatic download.

See [environment and data provisioning](../docs/environment_and_data_provisioning.md)
for hash validation and database reconstruction commands.
