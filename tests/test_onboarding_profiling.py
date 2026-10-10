from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

from src.onboarding.ingestion import SafeFileIngestor
from src.onboarding.profiling import DeterministicProfiler

from tests.onboarding_support import write_csv


class DeterministicProfilingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.profiler = DeterministicProfiler(max_examples=3, max_frequencies=3)

    def tearDown(self):
        self.temporary.cleanup()

    def _profile(self, text: str):
        source = write_csv(self.root / "fixture.csv", text)
        ingested = SafeFileIngestor(
            self.root / "store",
            clock=lambda: datetime(2026, 10, 3, tzinfo=timezone.utc),
        ).ingest(source)
        return self.profiler.profile(ingested)

    def test_profile_shape_missingness_cardinality_duplicates_and_digest(self):
        profile = self._profile(
            "Date,Country,Sales\n"
            "2026-01-01,BR,10.50\n"
            "2026-01-02,CA,\n"
            "2026-01-01,BR,10.50\n"
        )

        self.assertEqual(profile.status, "PROFILED")
        self.assertEqual(profile.row_count, 3)
        self.assertEqual(profile.column_count, 3)
        self.assertEqual(profile.duplicate_row_candidates, 1)
        sales = profile.column("Sales")
        self.assertEqual(sales.missing_count, 1)
        self.assertEqual(sales.missing_percentage, "33.333333")
        self.assertEqual(sales.unique_count, 1)
        self.assertEqual(sales.structural_type, "DECIMAL")
        self.assertEqual(sales.decimal_parse_success, 2)
        self.assertEqual(sales.numeric_min, "10.50")
        self.assertEqual(sales.numeric_max, "10.50")
        self.assertEqual(sales.decimal_scales, (2,))
        self.assertEqual(profile.profile_version, "1.0")
        self.assertEqual(len(profile.profile_digest), 64)
        self.assertEqual(profile.to_dict(), self.profiler.profile_from_rows(
            dataset_id=profile.dataset_id,
            source_sha256=profile.source_sha256,
            columns=("Date", "Country", "Sales"),
            rows=(("2026-01-01", "BR", "10.50"), ("2026-01-02", "CA", ""),
                  ("2026-01-01", "BR", "10.50")),
        ).to_dict())

    def test_source_representation_and_decimal_observation_do_not_assign_currency(self):
        profile = self._profile("Amount\n\"$1,234.50\"\n-$2.00\n")
        amount = profile.column("Amount")

        self.assertEqual(amount.source_representation, "STRING")
        self.assertEqual(amount.structural_type, "DECIMAL")
        self.assertEqual(amount.decimal_parse_success, 2)
        self.assertEqual(amount.numeric_min, "-2.00")
        self.assertEqual(amount.numeric_max, "1234.50")
        self.assertIn("monetary_formatting_observed", amount.formatting_observations)
        self.assertIn("currency_symbol_observed", amount.formatting_observations)
        self.assertEqual(profile.currency_state, "UNKNOWN")
        self.assertNotIn("USD", str(profile.to_dict()))
        self.assertNotIn("BRL", str(profile.to_dict()))

    def test_dates_require_unambiguous_format_before_range(self):
        profile = self._profile(
            "ISO_Date,Ambiguous_Date\n"
            "2026-01-02,01/02/2026\n"
            "2026-02-03,02/03/2026\n"
        )
        iso = profile.column("ISO_Date")
        ambiguous = profile.column("Ambiguous_Date")

        self.assertEqual(iso.structural_type, "DATE")
        self.assertEqual(iso.date_min, "2026-01-02")
        self.assertEqual(iso.date_max, "2026-02-03")
        self.assertEqual(ambiguous.structural_type, "AMBIGUOUS_DATE")
        self.assertIsNone(ambiguous.date_min)
        self.assertIsNone(ambiguous.date_max)
        self.assertEqual(ambiguous.date_parse_success, 0)
        self.assertEqual(ambiguous.ambiguous_date_count, 2)

    def test_likely_identifiers_suppress_raw_examples(self):
        profile = self._profile(
            "account_number,email,description\n"
            "001234567890,alice@example.com,office\n"
            "001234567891,bob@example.com,travel\n"
            "001234567892,carol@example.com,office\n"
        )

        for name in ("account_number", "email"):
            column = profile.column(name)
            self.assertTrue(column.likely_sensitive)
            self.assertTrue(column.possible_identifier)
            self.assertEqual(column.examples, ())
            self.assertEqual(column.frequencies, ())
            self.assertIn("raw_samples_suppressed", column.patterns)
        description = profile.column("description")
        self.assertFalse(description.likely_sensitive)
        self.assertEqual(description.examples, ("office", "travel"))
        self.assertEqual(description.frequencies[0], ("office", 2))

    def test_examples_and_frequency_summaries_are_bounded_and_first_observed(self):
        profile = self._profile("Category\nA\nB\nC\nD\nA\n")
        category = profile.column("Category")

        self.assertEqual(category.examples, ("A", "B", "C"))
        self.assertEqual(category.frequencies, (("A", 2), ("B", 1), ("C", 1)))
        self.assertEqual(category.categorical_cardinality, 4)

    def test_high_cardinality_unique_text_suppresses_raw_samples(self):
        values = "\n".join(f"reference-{index:02d}-unique" for index in range(20))
        profile = self._profile(f"external_reference\n{values}\n")
        column = profile.column("external_reference")

        self.assertTrue(column.possible_identifier)
        self.assertTrue(column.likely_sensitive)
        self.assertEqual(column.examples, ())
        self.assertEqual(column.frequencies, ())
        self.assertIn("high_cardinality", column.patterns)


if __name__ == "__main__":
    unittest.main()
