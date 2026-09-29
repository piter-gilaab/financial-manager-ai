"""Verify one approved immutable bundle and load its representations unchanged."""

from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
import csv
import io
import json
import re

APPROVED_RUN_ID = "20260928T190320706702Z_0a18cf5b"
APPROVAL_PATH = Path(__file__).with_name("approved_run.json")
TABLES = {
    "receiver_general": "receiver_general_accounting_record",
    "company_financials": "company_financial_sales_record",
}
LINEAGE_FIELDS = {"source_file", "source_sha256", "source_row_number"}
NULL_STATUSES = {"source_missing", "unresolved_placeholder", "parsing_failed"}
VALUE_STATUSES = {"kept", "parsed", "standardized"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return sha256(data).hexdigest()


def record_id(run_id, dataset, row_number):
    return digest(json.dumps([run_id, dataset, row_number], separators=(",", ":")).encode())


def read_csv(data, headers):
    reader = csv.DictReader(io.StringIO(data.decode("utf-8"), newline=""))
    require(reader.fieldnames == list(headers), "Processed CSV header mismatch")
    rows = list(reader)
    require(all(set(r) == set(headers) and all(isinstance(v, str) for v in r.values())
                for r in rows), "Malformed processed CSV width")
    return rows


def decode(token, spec):
    """Decode only the processed contract; never reinterpret raw companions."""
    if token == "" and spec["nullable"]:
        return None
    kind = spec["type"]
    if kind == "integer":
        require(re.fullmatch(r"[0-9]+", token) is not None, "Invalid processed integer")
        value = int(token)
        require(str(value) == token, "Noncanonical processed integer")
        return value
    if kind == "decimal":
        require(re.fullmatch(r"-?(?:0|[1-9][0-9]*)\.[0-9]+", token) is not None,
                "Invalid processed decimal")
        require(format(Decimal(token), "f") == token, "Decimal text changed")
    elif kind == "date":
        require(date.fromisoformat(token).isoformat() == token, "Invalid date representation")
    else:
        require(kind == "string", "Unknown manifest type")
    return token


@dataclass
class Bundle:
    root: Path
    directory: Path
    approval: dict
    manifest: dict
    report: dict
    artifacts: dict
    rows: dict
    flags: list

    def verify_unchanged(self):
        for name, expected in self.approval["artifacts"].items():
            require(digest((self.directory / name).read_bytes()) == expected,
                    f"Approved artifact changed: {name}")
        for relative, expected in self.approval["protected_inputs"].items():
            require(digest((self.root / relative).read_bytes()) == expected,
                    f"Protected input changed: {relative}")


def read_approved_bundle(project_root, *, run_id=APPROVED_RUN_ID):
    require(run_id == APPROVED_RUN_ID, "Only the explicitly approved cleaning run may load")
    root = Path(project_root).resolve()
    approval = json.loads(APPROVAL_PATH.read_text(encoding="utf-8"))
    require(approval["run_id"] == run_id, "Approval run mismatch")
    directory = root / "data" / "processed" / run_id
    artifacts = {name: (directory / name).read_bytes() for name in approval["artifacts"]}
    for name, data in artifacts.items():
        require(digest(data) == approval["artifacts"][name], f"Approved hash mismatch: {name}")
    manifest = json.loads(artifacts["cleaning_manifest.json"])
    report = json.loads(artifacts["cleaning_validation_report.json"])
    require(manifest["run_id"] == report["run_id"] == run_id, "Run metadata mismatch")
    require(report["result"] == "PASS" and report["hard_checks"] and
            all(c["passed"] is True for c in report["hard_checks"]), "Cleaning gates did not pass")
    require(all(report["staged_disk_roundtrip"].values()), "Cleaning round trips did not pass")
    require(all(v == 0 for v in report["scope"].values()), "Unexpected cleaning scope")
    require(set(manifest["datasets"]) == set(TABLES), "Unexpected source domains")
    for name, expected in manifest["artifact_sha256"].items():
        require(digest(artifacts[name]) == expected, f"Manifest artifact mismatch: {name}")
    for relative, expected in manifest["protected_inputs"].items():
        require(approval["protected_inputs"].get(relative) == expected, "Source approval mismatch")
    rows = {}
    for dataset, meta in manifest["datasets"].items():
        schema = meta["output_schema"]
        require(len(meta["original_header_map"]) == 16, "Source field mapping mismatch")
        raw_rows = read_csv(artifacts[meta["output_file"]], schema)
        rows[dataset] = [{f: decode(r[f], spec) for f, spec in schema.items()} for r in raw_rows]
        require(len(rows[dataset]) == meta["rows"], "Manifest row count mismatch")
        for number, row in enumerate(rows[dataset], 1):
            require(row["source_row_number"] == number and row["source_file"] == meta["source_file"]
                    and row["source_sha256"] == meta["source_sha256"], "Processed lineage mismatch")
            require(row["currency_status"] == "UNKNOWN" and all(row[f] is None for f in
                    ("original_currency", "currency_code", "currency_source")), "Currency changed")
            for field in meta["original_header_map"].values():
                status = row[field + "_status"]
                require(status in NULL_STATUSES | VALUE_STATUSES, "Unknown field status")
                require((row[field] is None) == (status in NULL_STATUSES), "Null/status mismatch")
                require(status != "parsing_failed", "Unreviewed parsing failure")
                if status == "source_missing":
                    require(row[field + "_raw"] == "", "Source-null raw token mismatch")
            # Reconcile status distributions to the approved report, not hardcoded null counts.
        counts = {f: dict(Counter(r[f + "_status"] for r in rows[dataset]))
                  for f in meta["original_header_map"].values()}
        require(counts == report["parse_counts"][dataset], "Parse counts differ from cleaning report")
    flags = read_csv(artifacts["cleaning_review_flags.csv"], manifest["review_flags_schema"])
    require(dict(Counter(r["flag"] for r in flags)) == report["review_flag_counts"],
            "Flag counts differ from cleaning report")
    bundle = Bundle(root, directory, approval, manifest, report, artifacts, rows, flags)
    bundle.verify_unchanged()
    return bundle


def insert_rows(connection, table, records):
    if not records:
        return
    columns = list(records[0])
    # Table/column names are code or the hash-pinned manifest, never caller SQL.
    statement = f'INSERT INTO "{table}" (' + ",".join(f'"{f}"' for f in columns) + ") VALUES ("
    statement += ",".join("?" for _ in columns) + ")"
    connection.executemany(statement, [tuple(r[f] for f in columns) for r in records])


def load_bundle(connection, bundle):
    require(connection.in_transaction, "Loading requires an explicit outer transaction")
    m = bundle.manifest
    run_id = m["run_id"]
    insert_rows(connection, "processing_run", [{
        "run_id": run_id, "schema_version": 1,
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "manifest_sha256": digest(bundle.artifacts["cleaning_manifest.json"]),
        "validation_sha256": digest(bundle.artifacts["cleaning_validation_report.json"]),
        "flags_sha256": digest(bundle.artifacts["cleaning_review_flags.csv"]),
        "manifest_json": bundle.artifacts["cleaning_manifest.json"].decode("utf-8"),
        "validation_json": bundle.artifacts["cleaning_validation_report.json"].decode("utf-8"),
        "approval_json": json.dumps(bundle.approval),
    }])
    for dataset, meta in m["datasets"].items():
        insert_rows(connection, "dataset_source", [{"source_id": dataset,
            "name": "Receiver General Accounting Transactions" if dataset == "receiver_general" else "Company Financials Dataset",
            "domain": "accounting" if dataset == "receiver_general" else "sales"}])
        insert_rows(connection, "run_dataset", [{"run_id": run_id, "source_id": dataset,
            "source_file": meta["source_file"], "source_sha256": meta["source_sha256"],
            "processed_file": str((bundle.directory / meta["output_file"]).relative_to(bundle.root)),
            "processed_sha256": digest(bundle.artifacts[meta["output_file"]]),
            "expected_rows": meta["rows"], "output_schema_json": json.dumps(meta["output_schema"])}])
        lineage, domain = [], []
        for position, row in enumerate(bundle.rows[dataset], 1):
            key = record_id(run_id, dataset, row["source_row_number"])
            identity = {"record_id": key, "run_id": run_id, "source_id": dataset}
            lineage.append({**identity, "source_row_number": row["source_row_number"], "processed_row_number": position})
            domain.append({**identity, **{f: v for f, v in row.items() if f not in LINEAGE_FIELDS}})
        insert_rows(connection, "source_record", lineage)
        insert_rows(connection, TABLES[dataset], domain)
    flags = []
    for position, flag in enumerate(bundle.flags, 1):
        dataset = flag["dataset"]
        require(dataset in TABLES, "Unknown flag source")
        meta = m["datasets"][dataset]
        require(flag["source_file"] == meta["source_file"] and flag["source_sha256"] == meta["source_sha256"],
                "Flag source lineage mismatch")
        key = None
        if flag["scope"] != "dataset":
            number = int(flag["source_row_number"])
            require(1 <= number <= len(bundle.rows[dataset]), "Flag row out of range")
            require(str(number) == flag["source_row_number"], "Noncanonical flag row")
            key = record_id(run_id, dataset, number)
            if flag["scope"] == "field":
                require(flag["field"] in meta["original_header_map"].values(), "Unknown flagged field")
                row = bundle.rows[dataset][number - 1]
                require(row[flag["field"] + "_raw"] == flag["raw_value"], "Flag token mismatch")
                require(row[flag["field"] + "_status"] == flag["flag"], "Flag status mismatch")
        flags.append({"run_id": run_id, "source_id": dataset, "record_id": key, "flag_row_number": position,
                      **{f: v for f, v in flag.items() if f != "dataset"}})
    insert_rows(connection, "data_quality_flag", flags)
