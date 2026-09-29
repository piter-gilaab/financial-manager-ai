"""Behavior tests against real SQLite, using only stdlib unittest."""

from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import json
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from src.database.connection import connect
from src.database.initialize import apply_schema, build_database
from src.database.loaders import APPROVED_RUN_ID, digest, load_bundle, read_approved_bundle
from src.database.validation import validate_database

ROOT = Path(__file__).resolve().parents[1]


class DatabaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.directory = Path(cls.temp.name)
        cls.path = cls.directory / "first.db"
        cls.bundle = read_approved_bundle(ROOT)
        cls.result = build_database(ROOT, cls.path)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_approved_run_and_row_counts(self):
        self.assertEqual(self.result["run_id"], APPROVED_RUN_ID)
        self.assertEqual(self.result["datasets"]["receiver_general"]["rows"], 9282)
        self.assertEqual(self.result["datasets"]["company_financials"]["rows"], 700)
        with connect(self.path, readonly=True) as c:
            self.assertEqual(c.execute("SELECT COUNT(*) FROM processing_run").fetchone()[0], 1)

    def test_every_processed_field_roundtrips(self):
        with connect(self.path, readonly=True) as c:
            report = validate_database(c, self.bundle)
        self.assertEqual(report["result"], "PASS")
        self.assertTrue(report["checks"])

    def test_decimal_precision_negative_values_and_extremes(self):
        with connect(self.path, readonly=True) as c:
            value = c.execute("SELECT journal_voucher_item_amount, typeof(journal_voucher_item_amount) FROM receiver_general_accounting_record WHERE journal_voucher_item_amount='39555794411.27'").fetchone()
            self.assertEqual(tuple(value), ("39555794411.27", "text"))
            profit = [r[0] for r in c.execute("SELECT profit FROM company_financial_sales_record WHERE profit IS NOT NULL")]
            self.assertEqual(sum(Decimal(v) < 0 for v in profit), 58)
            self.assertIn("-40617.50", profit)
            self.assertEqual(c.execute("SELECT DECIMAL_SUM(journal_voucher_item_amount) FROM receiver_general_accounting_record").fetchone()[0], "3061288992129.16")
            self.assertEqual(c.execute("SELECT DECIMAL_SUM(v) FROM (SELECT '0.10' AS v UNION ALL SELECT '0.20')").fetchone()[0], "0.30")
            self.assertIsNone(c.execute("SELECT DECIMAL_SUM(NULL)").fetchone()[0])

    def test_placeholders_source_nulls_and_literal_category(self):
        with connect(self.path, readonly=True) as c:
            self.assertEqual(c.execute("SELECT COUNT(*) FROM company_financial_sales_record WHERE discounts IS NULL AND discounts_status='unresolved_placeholder'").fetchone()[0], 53)
            self.assertEqual(c.execute("SELECT COUNT(*) FROM company_financial_sales_record WHERE profit IS NULL AND profit_status='unresolved_placeholder'").fetchone()[0], 5)
            self.assertEqual(c.execute("SELECT COUNT(*) FROM company_financial_sales_record WHERE discount_band='None'").fetchone()[0], 53)
            self.assertEqual(c.execute("SELECT COUNT(*) FROM data_quality_flag WHERE flag='source_missing'").fetchone()[0], 29876)

    def test_lineage_and_identifier_strings(self):
        with connect(self.path, readonly=True) as c:
            self.assertEqual(c.execute("SELECT COUNT(*) FROM source_record").fetchone()[0], 9982)
            row = c.execute("SELECT department_number,typeof(department_number) FROM receiver_general_accounting_record WHERE department_number='037' LIMIT 1").fetchone()
            self.assertEqual(tuple(row), ("037", "text"))
            self.assertEqual(c.execute("SELECT COUNT(*) FROM source_record s LEFT JOIN run_dataset r ON s.run_id=r.run_id AND s.source_id=r.source_id WHERE r.run_id IS NULL").fetchone()[0], 0)

    def test_currency_unknown(self):
        with connect(self.path, readonly=True) as c:
            for table in ("receiver_general_accounting_record", "company_financial_sales_record"):
                self.assertEqual(c.execute(f"SELECT COUNT(*) FROM {table} WHERE currency_status!='UNKNOWN' OR currency_code IS NOT NULL OR original_currency IS NOT NULL OR currency_source IS NOT NULL").fetchone()[0], 0)

    def test_integrity_and_quality_flags(self):
        self.assertEqual(self.result["integrity_check"], "ok")
        self.assertEqual(self.result["foreign_key_violations"], 0)
        self.assertEqual(self.result["quality_flags"], len(self.bundle.flags))
        self.assertEqual(self.result["flag_counts"], self.bundle.report["review_flag_counts"])

    def test_smoke_queries(self):
        smoke = self.result["smoke_queries"]
        self.assertEqual(smoke["sales_total"][0]["exact_total"], "118726350.29")
        self.assertEqual(len(smoke["profit_by_period"]), 16)
        self.assertEqual(smoke["rg_date_range"]["records"], 9282)

    def test_foreign_keys_status_and_domain_constraints(self):
        with connect(self.path) as c:
            c.execute("BEGIN")
            with self.assertRaises(sqlite3.IntegrityError):
                c.execute("DELETE FROM run_dataset WHERE source_id='receiver_general'")
            with self.assertRaises(sqlite3.IntegrityError):
                c.execute("UPDATE company_financial_sales_record SET source_id='receiver_general'")
            with self.assertRaises(sqlite3.IntegrityError):
                c.execute("UPDATE company_financial_sales_record SET discounts='0.00' WHERE discounts_status='unresolved_placeholder'")
            with self.assertRaises(sqlite3.IntegrityError):
                c.execute("UPDATE receiver_general_accounting_record SET journal_voucher_item_amount='1e9'")
            with self.assertRaises(sqlite3.IntegrityError):
                c.execute("UPDATE company_financial_sales_record SET currency_code='USD'")
            c.rollback()

    def test_wrong_run_is_rejected_without_output(self):
        target = self.directory / "wrong-run.db"
        with self.assertRaisesRegex(ValueError, "explicitly approved"):
            build_database(ROOT, target, run_id="20260928T185710790098Z_ca58a74d")
        self.assertFalse(target.exists())

    def test_hash_tampering_rejected(self):
        original = Path.read_bytes
        target = self.bundle.directory / "company_financials_standardized.csv"

        def changed(path):
            data = original(path)
            return data + b"\n" if path == target else data

        with patch.object(Path, "read_bytes", changed):
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                read_approved_bundle(ROOT)

    def test_existing_database_not_replaced(self):
        before = digest(self.path.read_bytes())
        with self.assertRaisesRegex(ValueError, "Refusing to replace"):
            build_database(ROOT, self.path)
        self.assertEqual(digest(self.path.read_bytes()), before)

    def test_atomic_rollback_removes_schema_and_partial_data(self):
        path = self.directory / "rollback.db"
        with connect(path) as c:
            c.execute("BEGIN IMMEDIATE")
            apply_schema(c)
            load_bundle(c, self.bundle)
            with self.assertRaises(sqlite3.IntegrityError):
                c.execute("INSERT INTO source_record VALUES(?,?,?,?,?)", ("x" * 64, "missing-run", "receiver_general", 1, 1))
            c.rollback()
            self.assertEqual(c.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0], 0)

    def test_validation_failure_does_not_publish(self):
        path = self.directory / "failed-build.db"
        original = validate_database

        def fail_after_load(c, bundle):
            original(c, bundle)
            raise ValueError("Simulated failed hard gate")

        with patch("src.database.initialize.validate_database", fail_after_load):
            with self.assertRaisesRegex(ValueError, "Simulated failed hard gate"):
                build_database(ROOT, path)
        self.assertFalse(path.exists())
        self.assertFalse(list(self.directory.glob(".financial_manager_*")))

    def test_postcommit_reload_failure_does_not_publish(self):
        path = self.directory / "failed-reload.db"
        calls = 0

        def fail_on_reload(c, bundle):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise ValueError("Simulated disk reload failure")
            return validate_database(c, bundle)

        with patch("src.database.initialize.validate_database", fail_on_reload):
            with self.assertRaisesRegex(ValueError, "Simulated disk reload"):
                build_database(ROOT, path)
        self.assertFalse(path.exists())

    def test_clean_rebuild_same_schema_and_record_keys(self):
        path = self.directory / "rebuild.db"
        second = build_database(ROOT, path)
        self.assertEqual(second["datasets"], self.result["datasets"])
        with connect(self.path, readonly=True) as first, connect(path, readonly=True) as rebuilt:
            query = "SELECT name,sql FROM sqlite_master ORDER BY name"
            self.assertEqual([tuple(r) for r in first.execute(query)], [tuple(r) for r in rebuilt.execute(query)])
            query = "SELECT * FROM source_record ORDER BY record_id"
            self.assertEqual([tuple(r) for r in first.execute(query)], [tuple(r) for r in rebuilt.execute(query)])

    def test_raw_processed_and_notebooks_unchanged(self):
        self.bundle.verify_unchanged()


if __name__ == "__main__":
    unittest.main()
