from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from src.onboarding.canonical import CanonicalMapper, canonical_spec_from_dict
from src.onboarding.decisions import SemanticDecisionService
from src.onboarding.ingestion import SafeFileIngestor
from src.onboarding.models import OnboardingError
from src.onboarding.preparation import PreparationEngine
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
        self.assertNotIn("preparation_digest", json.loads(payload))
        self.assertNotIn("quality_report_digest", json.loads(payload))
        before_read = current_path.read_bytes()
        self.registry.get(ingested.dataset_id)
        self.assertEqual(current_path.read_bytes(), before_read)

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

    def test_v21_registry_links_authenticated_preparation_quality_and_canonical_view(self):
        ingested, profile, mapping = self._approved_sales()
        engine = PreparationEngine()
        preparation = engine.prepare(ingested, profile)
        quality = engine.assess(preparation, profile, mapping)
        canonical = CanonicalMapper().build_spec(
            profile, mapping, preparation=preparation,
        )

        entry = self.registry.register(
            ingested, profile, mapping, preparation=preparation, quality=quality,
            canonical=canonical,
        )

        self.assertEqual(entry.preparation_digest, preparation.preparation_digest)
        self.assertEqual(entry.quality_report_digest, quality.quality_report_digest)
        self.assertIsNotNone(entry.canonical_view_digest)
        canonical_path = (
            self.onboarding_root / "artifacts" / ingested.dataset_id / "canonical"
            / f"{entry.canonical_view_digest}.json"
        )
        payload = json.loads(canonical_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["preparation_digest"], preparation.preparation_digest)
        self.assertEqual(payload["source_fingerprint"], ingested.source_sha256)
        self.assertEqual(payload["canonical_view_digest"], entry.canonical_view_digest)
        self.assertEqual(self.registry.get(ingested.dataset_id), entry)

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
        self.assertEqual(spec.version, "1.0")
        self.assertNotIn("cell_lineage", spec.lineage_policy)
        self.assertNotIn("preparation_digest", spec.to_dict())
        self.assertEqual(spec.fields["SALES"]["source_column"], "Sales")
        self.assertEqual(spec.fields["SALES"]["normalization"], "PARSE_DECIMAL_EXACT")
        self.assertNotIn("SIGN_INVERSION", json.dumps(spec.to_dict()))
        self.assertNotIn("CURRENCY_ASSIGNMENT", json.dumps(spec.to_dict()))
        self.assertEqual(records[0]["canonical_fields"]["SALES"]["normalized_value"], "10.50")
        self.assertEqual(records[0]["canonical_fields"]["COUNTRY"]["source_value"], "BR")
        self.assertEqual(records[0]["lineage"]["source_row_number"], 2)
        self.assertNotIn("source_fingerprint", records[0]["lineage"])
        self.assertNotIn("transformations", records[0]["canonical_fields"]["SALES"])
        self.assertEqual(records[1]["lineage"]["source_row_number"], 3)
        self.assertNotEqual(records[0]["canonical_record_id"], records[1]["canonical_record_id"])

    def test_prepared_canonical_spec_authenticates_preparation_and_preserves_cell_lineage(self):
        source = write_csv(
            self.root / "prepared-sales.csv",
            "Date,Country,Sales\n2026-01-01,NA,0.10\n2026-01-02,BR,\n",
        )
        ingested = SafeFileIngestor(
            self.onboarding_root, clock=lambda: FIXED_TIME,
        ).ingest(source)
        profile = DeterministicProfiler().profile(ingested)
        preparation = PreparationEngine().prepare(ingested, profile)
        mapping = SemanticMapper().suggest(profile)
        mapping = self.decisions.approve_domain(
            mapping, domain="SALES_RECORD", evidence="owner",
        )
        for column in ("Date", "Country", "Sales"):
            mapping = self.decisions.decide(
                mapping, column=column, decision="CONFIRM", evidence="owner",
            )

        mapper = CanonicalMapper()
        spec = mapper.build_spec(profile, mapping, preparation=preparation)
        records = mapper.map_records_with_status(ingested, spec)

        self.assertEqual(spec.version, "1.1")
        self.assertEqual(spec.preparation_digest, preparation.preparation_digest)
        self.assertEqual(spec.source_fingerprint, ingested.source_sha256)
        self.assertEqual(spec.canonical_view_digest, spec.spec_digest)
        country = records[0]["canonical_fields"]["COUNTRY"]
        sales = records[0]["canonical_fields"]["SALES"]
        missing_sales = records[1]["canonical_fields"]["SALES"]
        self.assertEqual(country["source_value"], "NA")
        self.assertEqual(country["normalized_value"], "NA")
        self.assertEqual(country["source_column_id"], spec.fields["COUNTRY"]["column_id"])
        self.assertEqual(sales["normalized_value"], "0.10")
        self.assertIn(
            "PARSE_DECIMAL_EXACT",
            {item["id"] for item in sales["transformations"]},
        )
        self.assertEqual(missing_sales["status"], "source_missing")
        self.assertIsNone(missing_sales["normalized_value"])
        self.assertEqual(records[0]["lineage"]["source_fingerprint"], ingested.source_sha256)

        tampered = spec.to_dict()
        tampered["fields"]["SALES"]["normalization"] = "EXECUTE_SQL"
        tampered["spec_digest"] = ""
        tampered["canonical_view_digest"] = None
        digest = hashlib.sha256(json.dumps(
            tampered, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        ).encode("utf-8")).hexdigest()
        tampered["spec_digest"] = digest
        tampered["canonical_view_digest"] = digest
        with self.assertRaises(OnboardingError) as raised:
            canonical_spec_from_dict(tampered)
        self.assertEqual(raised.exception.code, "canonical_spec_corrupt")

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
