"""Read-only, source-reconciled validation of the SQLite representation."""

from collections import Counter, defaultdict
from decimal import Decimal, Inexact, Rounded, localcontext
import json

from .loaders import TABLES, LINEAGE_FIELDS, digest, record_id, require


def exact_total(tokens):
    values = [Decimal(t) for t in tokens if t is not None]
    if not values:
        return None
    with localcontext() as ctx:
        ctx.prec = 60
        ctx.traps[Inexact] = ctx.traps[Rounded] = True
        return format(sum(values, Decimal(0)), "f")


def read_domain(connection, bundle, dataset):
    table = TABLES[dataset]
    rows = connection.execute(f'''SELECT d.*, s.source_row_number, s.processed_row_number,
        r.source_file, r.source_sha256 FROM {table} d
        JOIN source_record s ON s.record_id=d.record_id AND s.run_id=d.run_id AND s.source_id=d.source_id
        JOIN run_dataset r ON r.run_id=s.run_id AND r.source_id=s.source_id
        WHERE d.run_id=? ORDER BY s.processed_row_number''', (bundle.manifest["run_id"],)).fetchall()
    return [dict(r) for r in rows]


def smoke_queries(connection, bundle):
    """Numerical preservation checks; unknown-currency sums are not business totals."""
    outputs = {}
    run_id = bundle.manifest["run_id"]
    queries = [
        ("rg_amount_by_direction", "receiver_general", ["credit_debit_code"], "journal_voucher_item_amount"),
        ("rg_count_by_voucher", "receiver_general", ["journal_voucher_type_code"], None),
        ("sales_total", "company_financials", [], "sales"),
        ("profit_by_period", "company_financials", ["period_date"], "profit"),
        ("sales_category_counts", "company_financials", ["country", "segment", "product"], None),
    ]
    for name, dataset, dimensions, measure in queries:
        columns = dimensions + ["COUNT(*) AS records"]
        if measure:
            columns += [f"COUNT({measure}) AS available", f"DECIMAL_SUM({measure}) AS exact_total"]
        sql = "SELECT " + ", ".join(columns) + " FROM " + TABLES[dataset] + " WHERE run_id=?"
        if dimensions:
            sql += " GROUP BY " + ",".join(dimensions)
        actual = [dict(r) for r in connection.execute(sql, (run_id,))]
        groups = defaultdict(list)
        for r in bundle.rows[dataset]:
            groups[tuple(r[d] for d in dimensions)].append(r)
        expected = {}
        for key, rows in groups.items():
            value = {**dict(zip(dimensions, key)), "records": len(rows)}
            if measure:
                value.update(available=sum(r[measure] is not None for r in rows),
                             exact_total=exact_total([r[measure] for r in rows]))
            expected[key] = value
        require({tuple(r[d] for d in dimensions): r for r in actual} == expected,
                f"Smoke query does not reconcile: {name}")
        outputs[name] = actual
    dates = [r["accounting_effective_date"] for r in bundle.rows["receiver_general"]]
    start, end = min(dates), max(dates)
    count = connection.execute("SELECT COUNT(*) FROM receiver_general_accounting_record WHERE run_id=? AND accounting_effective_date BETWEEN ? AND ?",
                               (run_id, start, end)).fetchone()[0]
    require(count == len(dates), "Effective-date range query mismatch")
    outputs["rg_date_range"] = {"from": start, "through": end, "records": count}
    outputs["record_counts"] = {ds: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                                for ds, table in TABLES.items()}
    return outputs


def validate_database(connection, bundle):
    checks = []

    def check(condition, name):
        require(condition, name)
        checks.append(name)

    check(connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1, "foreign_keys_enabled")
    integrity = [r[0] for r in connection.execute("PRAGMA integrity_check")]
    foreign = list(connection.execute("PRAGMA foreign_key_check"))
    check(integrity == ["ok"], "integrity_check")
    check(foreign == [], "foreign_key_check")
    run_id = bundle.manifest["run_id"]
    runs = connection.execute("SELECT * FROM processing_run").fetchall()
    check(len(runs) == 1 and runs[0]["run_id"] == run_id, "approved_cleaning_run")
    run = dict(runs[0])
    for column, artifact in [("manifest", "cleaning_manifest.json"), ("validation", "cleaning_validation_report.json")]:
        check(run[column + "_json"] == bundle.artifacts[artifact].decode("utf-8") and
              run[column + "_sha256"] == digest(bundle.artifacts[artifact]), column + "_metadata")
    check(run["flags_sha256"] == digest(bundle.artifacts["cleaning_review_flags.csv"]) and
          json.loads(run["approval_json"]) == bundle.approval, "approval_and_flag_hashes")
    dataset_results = {}
    check(connection.execute("SELECT COUNT(*) FROM run_dataset").fetchone()[0] == len(TABLES), "run_dataset_count")
    check(connection.execute("SELECT COUNT(*) FROM dataset_source").fetchone()[0] == len(TABLES), "dataset_source_count")
    for dataset, table in TABLES.items():
        meta = bundle.manifest["datasets"][dataset]
        rows = read_domain(connection, bundle, dataset)
        source = bundle.rows[dataset]
        check(len(rows) == len(source) == meta["rows"] == (9282 if dataset == "receiver_general" else 700), dataset + ".row_count")
        check(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == len(rows), dataset + ".no_extra_rows")
        stored_meta = dict(connection.execute("SELECT * FROM run_dataset WHERE run_id=? AND source_id=?", (run_id, dataset)).fetchone())
        for f in ("source_file", "source_sha256"):
            check(stored_meta[f] == meta[f], dataset + "." + f)
        check(stored_meta["processed_sha256"] == digest(bundle.artifacts[meta["output_file"]]) and
              stored_meta["processed_file"] == str((bundle.directory / meta["output_file"]).relative_to(bundle.root)) and
              stored_meta["expected_rows"] == len(source) and json.loads(stored_meta["output_schema_json"]) == meta["output_schema"],
              dataset + ".processed_lineage_metadata")
        for position, (actual, expected) in enumerate(zip(rows, source), 1):
            require(actual["record_id"] == record_id(run_id, dataset, expected["source_row_number"]) and
                    actual["run_id"] == run_id and actual["source_id"] == dataset and
                    actual["processed_row_number"] == position, "Lineage record identity mismatch")
            for field, spec in meta["output_schema"].items():
                require(type(actual[field]) is type(expected[field]) and actual[field] == expected[field],
                        f"Stored value/type changed: {dataset}:{position}:{field}")
        checks.append(dataset + ".all_fields_types_tokens_statuses_lineage_roundtrip")
        fields = list(meta["original_header_map"].values())
        keys = [tuple(r[f] for f in meta["candidate_key"]) for r in rows]
        missing = sum(any(v is None for v in key) for key in keys)
        duplicates = len(keys) - len(set(keys))
        expected_keys = bundle.report["key_results"][dataset]
        check(duplicates == expected_keys["cleaned_repetitions"] and missing == expected_keys["missing_components"], dataset + ".candidate_key")
        check(len(rows) == len({tuple(r[f] for f in fields) for r in rows}), dataset + ".full_duplicates")
        nulls = {f: sum(r[f] is None for r in rows) for f in fields}
        statuses = {f: dict(Counter(r[f + "_status"] for r in rows)) for f in fields}
        check(nulls == bundle.report["null_reconciliation"][dataset]["typed"], dataset + ".null_counts")
        check(statuses == bundle.report["parse_counts"][dataset], dataset + ".status_counts")
        for f, expected in bundle.report["numeric_reconciliation"][dataset].items():
            values = [Decimal(r[f]) for r in rows if r[f] is not None]
            check(len(values) == expected["numeric_count"] and
                  sum(v < 0 for v in values) == expected["negative_count"] and
                  sum(v == 0 for v in values) == expected["zero_count"] and
                  min(values) == Decimal(expected["minimum"]) and max(values) == Decimal(expected["maximum"]), dataset + "." + f + ".numeric_preservation")
            if "total" in expected:
                total = connection.execute(f"SELECT DECIMAL_SUM({f}) FROM {table} WHERE run_id=?", (run_id,)).fetchone()[0]
                check(total == expected["total"], dataset + "." + f + ".exact_sum")
        check(all(r["currency_status"] == "UNKNOWN" and r["currency_code"] is None and
                  r["original_currency"] is None and r["currency_source"] is None for r in rows), dataset + ".currency")
        if dataset == "company_financials":
            five = meta["candidate_key"][:-1]
            repeated = len(rows) - len({tuple(r[f] for f in five) for r in rows})
            check(repeated == len(source) - len({tuple(r[f] for f in five) for r in source}), "sales.five_field_repetitions")
            check(sum(r["discount_band"] == "None" for r in rows) == sum(r["discount_band"] == "None" for r in source), "sales.literal_None")
        dataset_results[dataset] = {"rows": len(rows), "candidate_key_repetitions": duplicates,
                                    "source_missing": sum(c.get("source_missing", 0) for c in statuses.values()),
                                    "unresolved_placeholders": sum(c.get("unresolved_placeholder", 0) for c in statuses.values()),
                                    "parsing_failures": sum(c.get("parsing_failed", 0) for c in statuses.values())}
    check(connection.execute("SELECT COUNT(*) FROM source_record").fetchone()[0] == sum(len(r) for r in bundle.rows.values()), "complete_lineage")
    flags = [dict(r) for r in connection.execute("SELECT * FROM data_quality_flag ORDER BY flag_row_number")]
    check(len(flags) == len(bundle.flags), "quality_flag_count")
    for position, (actual, expected) in enumerate(zip(flags, bundle.flags), 1):
        expected_key = None if expected["scope"] == "dataset" else record_id(run_id, expected["dataset"], int(expected["source_row_number"]))
        require(actual["record_id"] == expected_key and actual["run_id"] == run_id and
                actual["flag_row_number"] == position, "Flag target mismatch")
        for field, token in expected.items():
            column = "source_id" if field == "dataset" else field
            require(actual[column] == token, "Quality flag changed: " + field)
    checks.append("all_quality_flags_roundtrip")
    flag_counts = dict(Counter(r["flag"] for r in flags))
    check(flag_counts == bundle.report["review_flag_counts"], "quality_flags_reconcile")
    actual_tables = {r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    check(actual_tables == {"schema_version", "dataset_source", "processing_run", "run_dataset", "source_record", "data_quality_flag", *TABLES.values()}, "only_approved_tables_no_fake_entities_or_fx")
    for table in TABLES.values():
        check({r[2] for r in connection.execute(f"PRAGMA foreign_key_list({table})")} == {"source_record"}, table + ".no_business_join")
    smoke = smoke_queries(connection, bundle)
    checks.append("smoke_queries_reconcile")
    return {"result": "PASS", "run_id": run_id, "checks": checks, "datasets": dataset_results,
            "quality_flags": len(flags), "flag_counts": flag_counts, "integrity_check": integrity[0],
            "foreign_key_violations": len(foreign), "smoke_queries": smoke}
