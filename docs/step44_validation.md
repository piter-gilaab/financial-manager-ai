# Phase 13 — Step 44 validation

## Status

**PASS.** Local ingestion accepts bounded CSV and constrained Open XML XLSX
files as inert data, preserves exact source bytes, and emits a versioned,
data-only manifest.

## Implemented boundaries

- CSV: UTF-8/UTF-8-SIG, deterministic delimiter allowlist, strict quoting and
  whole-table width/header validation.
- XLSX: standard-library ZIP/XML parsing, explicit sheet selection for multiple
  nonempty sheets, and rejection of formulas, macros, external links, unsafe
  archive paths and excessive expansion.
- Files: regular files only; symlinks, devices/directories, unsupported
  extensions, content/extension mismatches and configured size limits fail
  closed.
- Bounds: bytes, archive entries/uncompressed size/ratio, sheets, rows, columns,
  header length and cell length are explicit in each ingestion manifest.
- Preservation: the caller's file is never changed; accepted exact bytes are
  stored under `data/onboarding/artifacts/<dataset_id>/source/` by default at
  the future facade boundary. Public manifests expose only the basename.

No spreadsheet formula is executed or trusted through a cached value. No row is
silently discarded and no financial meaning is assigned.

## Focused tests

`python -m unittest tests.test_onboarding_ingestion`

Result: **11 passed**. Cases cover source preservation, BOM/delimiter handling,
malformed/duplicate/empty/inconsistent CSV, resource bounds, path types,
formula-free XLSX including shared strings, sheet selection, formulas, macros,
external links, encryption, oversized cell references and bad archives.
