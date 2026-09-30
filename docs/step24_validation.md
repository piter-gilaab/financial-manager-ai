# Phase 8 — Step 24 validation

**Reproducibility status: PASS.** Final clean-room baseline: commit `fce45ce`.
Step 25 was not started.

## Method and result

Created `/tmp/financial-manager-step24.XLiMZ1/repository-final` with local
`git clone --local --no-hardlinks`. The initial clone contained only committed
files and correctly lacked `.venv`, all seven external data artifacts, SQLite,
caches, and ignored runtime files. Initial provisioning failed with the exact
missing paths and no traceback, download, fabricated data, or import error.

Created a Python 3.14.7 venv with system packages disabled and ran the empty
requirements install with `--no-index`. Copied only the two authorized raw CSVs
and five approved-run artifacts from existing local project assets. All hashes
matched approval metadata. No old processed run or database was copied.

The processed bundle is an external custodian input. Git does not distribute it,
and no supported workflow regenerates/approves it from notebooks. This is now
explicit in the Step 23 provisioning guide.

The documented database command passed every load/validation gate with 9,282 and
700 rows, exact decimals, complete lineage, 29,944 flags, integrity `ok`, zero
foreign-key violations, protected hashes unchanged, and passing smoke queries.
Final provisioning returned `PASS` against clone-local paths.

Representative CLI capability, plan, analysis, anomaly, and JSON commands passed.
Analysis returned `SUCCESS`; screening returned expected `PARTIAL`; currency
remained `UNKNOWN`; forecasting and retrieval remained BLOCKED.

## Defects and regression coverage

- Committed baseline omitted ten financial runtime modules and three tests. Added
  only those existing files in `a36f5e0`.
- Test discovery treated import failures as discovered tests. Added explicit
  import-error reporting and a focused regression test.
- Rebuilt SQLite passed provisioning but runtime rejected its timestamp-dependent
  byte hash. Snapshot access now relies on the existing full logical validation,
  retains read-only immutable-byte loading, reports the actual database hash, and
  still rejects tampering. Added a clean-rebuild runtime regression test.

The clean-clone suite passed **298 tests, 0 failures, 0 errors, 0 skipped** in
**300.524 seconds**.

The modified primary repository then passed the same **298 tests, 0 failures,
0 errors, 0 skipped** in **294.576 seconds**.

## Offline and hidden-state evidence

Empty requirements installed with `--no-index`. Builder, validator, and CLI passed
under a Python audit hook that denied socket events. `unshare -n` was unavailable
in the sandbox. A real query also passed under `env -i`. No tracked absolute path,
primary venv/database/cache, user-home configuration, environment variable,
untracked module, old run, or notebook state was required.

## Remaining manual input

An authorized custodian must supply the exact two raw CSVs and five approved
processed artifacts. This test used already-authorized local bytes and does not
prove public acquisition, license, or redistribution permission. Python 3.14 must
be installed. With those explicit inputs, V1 reconstruction is reproducible.
