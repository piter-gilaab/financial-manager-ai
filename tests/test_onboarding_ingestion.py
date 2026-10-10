from datetime import datetime, timezone
import hashlib
from pathlib import Path
import tempfile
import unittest

from src.onboarding.ingestion import SafeFileIngestor
from src.onboarding.models import IngestionLimits, OnboardingError

from tests.onboarding_support import mark_xlsx_encrypted, write_csv, write_xlsx


FIXED_TIME = datetime(2026, 10, 3, 12, 0, tzinfo=timezone.utc)


class SafeFileIngestionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.sources = self.root / "incoming"
        self.sources.mkdir()
        self.store = self.root / "onboarding"
        self.ingestor = SafeFileIngestor(self.store, clock=lambda: FIXED_TIME)

    def tearDown(self):
        self.temporary.cleanup()

    def test_csv_is_preserved_with_manifest_and_no_absolute_path(self):
        source = write_csv(self.sources / "sales.csv", "Date,Sales\n2026-01-01,12.50\n")
        before = source.read_bytes()

        result = self.ingestor.ingest(source, provenance_note="synthetic fixture")

        self.assertEqual(result.status, "INGESTED")
        self.assertEqual(result.source_filename, "sales.csv")
        self.assertEqual(result.detected_format, "CSV")
        self.assertEqual(result.source_sha256, hashlib.sha256(before).hexdigest())
        self.assertEqual(result.byte_size, len(before))
        self.assertEqual(result.ingested_at, "2026-10-03T12:00:00Z")
        self.assertTrue(result.dataset_id.startswith("ds_"))
        self.assertTrue(result.ingestion_run_id.startswith("ing_"))
        self.assertEqual(result.columns, ("Date", "Sales"))
        self.assertEqual(result.rows, (("2026-01-01", "12.50"),))
        self.assertEqual(source.read_bytes(), before)
        stored = self.store / "artifacts" / result.dataset_id / "source" / "source.csv"
        self.assertEqual(stored.read_bytes(), before)
        rendered = str(result.to_dict())
        self.assertNotIn(str(self.root), rendered)
        self.assertNotIn("callable", rendered)

    def test_utf8_bom_and_semicolon_are_supported_deterministically(self):
        source = self.sources / "bom.csv"
        source.write_bytes("Date;Sales\n2026-01-01;10\n".encode("utf-8-sig"))

        result = self.ingestor.ingest(source)

        self.assertEqual(result.encoding, "UTF-8-SIG")
        self.assertEqual(result.delimiter, ";")
        self.assertEqual(result.columns, ("Date", "Sales"))

    def test_malformed_duplicate_empty_or_inconsistent_csv_is_rejected(self):
        fixtures = {
            "duplicate.csv": "Date,Date\n2026-01-01,2026-01-02\n",
            "empty_header.csv": "Date,\n2026-01-01,1\n",
            "width.csv": "Date,Sales\n2026-01-01,1,extra\n",
            "quote.csv": 'Date,Sales\n"2026-01-01,1\n',
            "empty.csv": "",
        }
        for name, content in fixtures.items():
            with self.subTest(name=name):
                source = write_csv(self.sources / name, content)
                with self.assertRaises(OnboardingError) as raised:
                    self.ingestor.ingest(source)
                self.assertIn(raised.exception.code, {
                    "empty_file", "invalid_header", "duplicate_columns",
                    "inconsistent_rows", "malformed_csv",
                })

    def test_invalid_utf8_and_bounded_rows_columns_cells_and_bytes_fail_closed(self):
        limits = IngestionLimits(max_file_bytes=80, max_rows=1, max_columns=2, max_cell_chars=4)
        ingestor = SafeFileIngestor(self.store, limits=limits, clock=lambda: FIXED_TIME)
        cases = [
            ("invalid.csv", b"A,B\n\xff,1\n", "invalid_encoding"),
            ("rows.csv", b"A,B\n1,2\n3,4\n", "row_limit_exceeded"),
            ("columns.csv", b"A,B,C\n1,2,3\n", "column_limit_exceeded"),
            ("cell.csv", b"A,B\n12345,2\n", "cell_limit_exceeded"),
            ("large.csv", b"A\n" + b"x" * 81, "file_too_large"),
        ]
        for name, content, code in cases:
            with self.subTest(name=name):
                source = self.sources / name
                source.write_bytes(content)
                with self.assertRaises(OnboardingError) as raised:
                    ingestor.ingest(source)
                self.assertEqual(raised.exception.code, code)

    def test_non_regular_symlink_directory_and_unsupported_types_are_rejected(self):
        regular = write_csv(self.sources / "regular.csv", "A\n1\n")
        link = self.sources / "link.csv"
        link.symlink_to(regular)
        directory = self.sources / "directory.csv"
        directory.mkdir()
        unsupported = self.sources / "source.xlsm"
        unsupported.write_bytes(b"PK")
        for source, code in (
            (link, "symlink_not_allowed"),
            (directory, "not_regular_file"),
            (unsupported, "unsupported_format"),
        ):
            with self.subTest(source=source.name):
                with self.assertRaises(OnboardingError) as raised:
                    self.ingestor.ingest(source)
                self.assertEqual(raised.exception.code, code)

    def test_xlsx_reads_selected_formula_free_sheet_as_data(self):
        source = write_xlsx(
            self.sources / "sales.xlsx",
            sheets={"Sales": [["Date", "Sales"], ["2026-01-01", "12.50"]]},
        )

        result = self.ingestor.ingest(source)

        self.assertEqual(result.detected_format, "XLSX")
        self.assertEqual(result.source_sheet, "Sales")
        self.assertEqual(result.columns, ("Date", "Sales"))
        self.assertEqual(result.rows, (("2026-01-01", "12.50"),))

    def test_xlsx_shared_strings_are_resolved_as_inert_text(self):
        source = write_xlsx(
            self.sources / "shared.xlsx",
            sheets={"Sales": [["Date", "Sales"], ["2026-01-01", "12.50"]]},
            shared_strings=True,
        )

        result = self.ingestor.ingest(source)

        self.assertEqual(result.columns, ("Date", "Sales"))
        self.assertEqual(result.rows, (("2026-01-01", "12.50"),))

    def test_xlsx_requires_explicit_sheet_when_multiple_nonempty_sheets_exist(self):
        source = write_xlsx(
            self.sources / "multi.xlsx",
            sheets={"Sales": [["Date"], ["2026-01-01"]], "Costs": [["Amount"], ["3"]]},
        )
        with self.assertRaises(OnboardingError) as raised:
            self.ingestor.ingest(source)
        self.assertEqual(raised.exception.code, "sheet_selection_required")

        result = self.ingestor.ingest(source, sheet="Costs")

        self.assertEqual(result.source_sheet, "Costs")
        self.assertEqual(result.columns, ("Amount",))

    def test_xlsx_formula_macro_external_link_and_bad_zip_are_rejected(self):
        cases = {
            "formula.xlsx": (dict(sheets={"Sheet1": [["Amount"], ["1+1"]]}, formula=True),
                             "formula_not_allowed"),
            "external.xlsx": (dict(sheets={"Sheet1": [["Amount"], ["1"]]}, external_link=True),
                              "external_link_not_allowed"),
            "macro.xlsx": (dict(sheets={"Sheet1": [["Amount"], ["1"]]}, macro=True),
                           "macro_not_allowed"),
        }
        for name, (options, code) in cases.items():
            with self.subTest(name=name):
                source = write_xlsx(self.sources / name, **options)
                with self.assertRaises(OnboardingError) as raised:
                    self.ingestor.ingest(source)
                self.assertEqual(raised.exception.code, code)
        bad = self.sources / "bad.xlsx"
        bad.write_bytes(b"not a zip")
        with self.assertRaises(OnboardingError) as raised:
            self.ingestor.ingest(bad)
        self.assertEqual(raised.exception.code, "malformed_xlsx")

    def test_xlsx_huge_cell_reference_is_rejected_before_blank_expansion(self):
        source = write_xlsx(
            self.sources / "huge-reference.xlsx",
            sheets={"Sheet1": [["Amount"], ["1"]]},
            cell_reference_override="ZZZZ999999",
        )
        with self.assertRaises(OnboardingError) as raised:
            self.ingestor.ingest(source)
        self.assertEqual(raised.exception.code, "column_limit_exceeded")

    def test_encrypted_xlsx_is_rejected_with_controlled_code(self):
        source = mark_xlsx_encrypted(write_xlsx(
            self.sources / "encrypted.xlsx",
            sheets={"Sheet1": [["Amount"], ["1"]]},
        ))
        with self.assertRaises(OnboardingError) as raised:
            self.ingestor.ingest(source)
        self.assertEqual(raised.exception.code, "encrypted_xlsx_not_allowed")


if __name__ == "__main__":
    unittest.main()
