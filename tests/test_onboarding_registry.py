from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest

from src.onboarding.canonical import CanonicalMapper
from src.onboarding.decisions import SemanticDecisionService
from src.onboarding.ingestion import SafeFileIngestor
from src.onboarding.models import OnboardingError
from src.onboarding.profiling import DeterministicProfiler
from src.onboarding.registry import DatasetRegistry
from src.onboarding.semantics import SemanticMapper

from tests.onboarding_support import write_csv


FIXED_TIME = datetime(2026, 10, 3, 18, 0, tzinfo=timezone.utc)


class DatasetRegistryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.onboarding_root = self.root / "onboarding"
        self.registry = DatasetRegistry(self.onboarding_root, clock=lambda: FIXED_TIME)
        self.decisions = SemanticDecisionService(clock=lambda: FIXED_TIME)

    def tearDown(self):
        self.temporary.cleanup()

    def _approved_sales(self):
        source = write_csv(
            self.root / "sales.csv",
            "Date,Country,Sales\n2026-01-01,BR,10.50\n2026-01-02,CA,20.25\n",
        )
        ingested = SafeFileIngestor(self.onboarding_root, clock=lambda: FIXED_TIME).ingest(source)
        profile = DeterministicProfiler().profile(ingested)
        mapping = SemanticMapper().suggest(profile)
        mapping = self.decisions.approve_domain(mapping, domain="SALES_RECORD", evidence="owner")
        mapping = self.decisions.decide(mapping, column="Date", decision="CONFIRM", evidence="owner")
        mapping = self.decisions.decide(mapping, column="Country", decision="CONFIRM", evidence="owner")
        mapping = self.decisions.decide(mapping, column="Sales", decision="CONFIRM", evidence="owner")
        return ingested, profile, mapping

    def test_registry_persists_versioned_data_only_entry_without_absolute_path(self):
        ingested, profile, mapping = self._approved_sales()
        entry = self.registry.register(ingested, profile, mapping)

        self.assertEqual(entry.lifecycle_state, "REGISTERED")
        self.assertEqual(entry.registry_schema_version, "1.0")
        self.assertEqual(entry.registry_version, 1)
        self.assertEqual(entry.dataset_id, ingested.dataset_id)
        self.assertEqual(entry.source_fingerprint, ingested.source_sha256)
        self.assertEqual(entry.source_type, "CSV")
        self.assertEqual(entry.profile_digest, profile.profile_digest)
        self.assertEqual(entry.semantic_mapping_digest, mapping.mapping_digest)
        self.assertEqual(entry.canonical_domain, "SALES_RECORD")
        self.assertEqual(entry.currency_state, "UNKNOWN")
        self.assertEqual(entry.observed_date_range, ("2026-01-01", "2026-01-02"))
        self.assertEqual(entry.row_count, 2)
        self.assertEqual(entry.readiness_state, "BLOCKED")
        self.assertEqual(entry.lineage["source_row_offset"], 2)
        loaded = self.registry.get(ingested.dataset_id)
        self.assertEqual(loaded.to_dict(), entry.to_dict())
        current_path = self.onboarding_root / "registry" / ingested.dataset_id / "current.json"
        payload = current_path.read_text(encoding="utf-8")
        self.assertNotIn(str(self.root), payload)
        self.assertNotIn("<function", payload)
        self.assertEqual(json.loads(payload)["registry_version"], 1)

    def test_registry_versions_are_append_oriented_and_old_version_is_preserved(self):
        ingested, profile, mapping = self._approved_sales()
        first = self.registry.register(ingested, profile, mapping)
        first_path = self.onboarding_root / "registry" / ingested.dataset_id / "versions" / "1.json"
        first_bytes = first_path.read_bytes()

        revised = self.decisions.decide(
            mapping, column="Country", decision="CONFIRM", evidence="owner confirms country",
        )
        second = self.registry.register(ingested, profile, revised)

        self.assertEqual(second.registry_version, 2)
        self.assertEqual(first_path.read_bytes(), first_bytes)
        self.assertTrue((first_path.parent / "2.json").is_file())
        self.assertNotEqual(first.semantic_mapping_digest, second.semantic_mapping_digest)

    def test_unapproved_or_mismatched_artifacts_cannot_be_registered(self):
        ingested, profile, approved = self._approved_sales()
        unapproved = SemanticMapper().suggest(profile)
        other_profile = DeterministicProfiler().profile_from_rows(
            dataset_id=profile.dataset_id, source_sha256=profile.source_sha256,
            columns=("Date", "Amount"), rows=(("2026-01-01", "1"),),
        )
        for candidate_profile, candidate_mapping, code in (
            (profile, unapproved, "mapping_not_approved"),
            (other_profile, approved, "artifact_mismatch"),
        ):
            with self.subTest(code=code):
                with self.assertRaises(OnboardingError) as raised:
                    self.registry.register(ingested, candidate_profile, candidate_mapping)
                self.assertEqual(raised.exception.code, code)

    def test_canonical_spec_and_records_preserve_domain_and_source_lineage(self):
        ingested, profile, mapping = self._approved_sales()
        spec = CanonicalMapper().build_spec(profile, mapping)
        records = CanonicalMapper().map_records(ingested, spec)

        self.assertEqual(spec.canonical_domain, "SALES_RECORD")
        self.assertEqual(spec.fields["SALES"]["source_column"], "Sales")
        self.assertEqual(spec.fields["SALES"]["normalization"], "PARSE_DECIMAL_EXACT")
        self.assertNotIn("SIGN_INVERSION", json.dumps(spec.to_dict()))
        self.assertNotIn("CURRENCY_ASSIGNMENT", json.dumps(spec.to_dict()))
        self.assertEqual(records[0]["canonical_fields"]["SALES"]["normalized_value"], "10.50")
        self.assertEqual(records[0]["canonical_fields"]["COUNTRY"]["source_value"], "BR")
        self.assertEqual(records[0]["lineage"]["source_row_number"], 2)
        self.assertEqual(records[1]["lineage"]["source_row_number"], 3)
        self.assertNotEqual(records[0]["canonical_record_id"], records[1]["canonical_record_id"])

    def test_xlsx_canonical_lineage_preserves_actual_worksheet_row_number(self):
        from tests.onboarding_support import write_xlsx
        source = write_xlsx(
            self.root / "gapped.xlsx",
            sheets={"Sales": [["Date", "Sales"], ["2026-01-01", "10.00"]]},
            row_numbers={"Sales": [1, 5]},
        )
        ingested = SafeFileIngestor(self.onboarding_root, clock=lambda: FIXED_TIME).ingest(source)
        profile = DeterministicProfiler().profile(ingested)
        mapping = SemanticMapper().suggest(profile)
        mapping = self.decisions.approve_domain(mapping, domain="SALES_RECORD", evidence="owner")
        mapping = self.decisions.decide(mapping, column="Date", decision="CONFIRM", evidence="owner")
        mapping = self.decisions.decide(mapping, column="Sales", decision="CONFIRM", evidence="owner")
        records = CanonicalMapper().map_records(ingested, CanonicalMapper().build_spec(profile, mapping))

        self.assertEqual(records[0]["lineage"]["source_row_number"], 5)

    def test_accounting_mapping_never_reinterprets_dr_cr_as_revenue_expense_or_cash(self):
        profile = DeterministicProfiler().profile_from_rows(
            dataset_id="ds_accounting", source_sha256="b" * 64,
            columns=("posting_date", "amount", "dr_cr"),
            rows=(("2026-01-01", "-10.00", "D"), ("2026-01-02", "20.00", "C")),
        )
        mapping = SemanticMapper().suggest(profile)
        mapping = self.decisions.approve_domain(mapping, domain="ACCOUNTING_TRANSACTION", evidence="owner")
        mapping = self.decisions.decide(mapping, column="posting_date", decision="CONFIRM", evidence="owner")
        mapping = self.decisions.decide(mapping, column="amount", decision="CONFIRM", evidence="owner")
        mapping = self.decisions.decide(
            mapping, column="dr_cr", decision="CONFIRM", evidence="owner",
            value_mapping={"D": "DEBIT", "C": "CREDIT"},
        )
        spec = CanonicalMapper().build_spec(profile, mapping)
        rendered = json.dumps(spec.to_dict())
        self.assertNotIn("REVENUE", rendered)
        self.assertNotIn("EXPENSE", rendered)
        self.assertNotIn("CASH_DIRECTION", rendered)
        self.assertEqual(spec.fields["DEBIT_CREDIT_INDICATOR"]["normalization"], "PRESERVE_TEXT")

    def test_changed_schema_cannot_silently_reuse_previous_mapping(self):
        _, profile, mapping = self._approved_sales()
        changed = DeterministicProfiler().profile_from_rows(
            dataset_id="ds_changed", source_sha256="c" * 64,
            columns=("Date", "Country", "Net Sales"),
            rows=(("2026-01-01", "BR", "10.50"),),
        )
        with self.assertRaises(OnboardingError) as raised:
            CanonicalMapper().build_spec(changed, mapping)
        self.assertEqual(raised.exception.code, "artifact_mismatch")

    def test_approved_ambiguous_date_format_populates_registry_range(self):
        source = write_csv(self.root / "ambiguous.csv", "Date,Sales\n01/02/2026,10\n03/02/2026,20\n")
        ingested = SafeFileIngestor(self.onboarding_root, clock=lambda: FIXED_TIME).ingest(source)
        profile = DeterministicProfiler().profile(ingested)
        mapping = SemanticMapper().suggest(profile)
        mapping = self.decisions.approve_domain(mapping, domain="SALES_RECORD", evidence="owner")
        mapping = self.decisions.decide(
            mapping, column="Date", decision="CONFIRM", evidence="owner",
            date_format="DD/MM/YYYY",
        )
        mapping = self.decisions.decide(mapping, column="Sales", decision="CONFIRM", evidence="owner")

        entry = self.registry.register(ingested, profile, mapping)

        self.assertEqual(entry.observed_date_range, ("2026-02-01", "2026-02-03"))


if __name__ == "__main__":
    unittest.main()
