from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

from src.manager import FinancialManagerAgent
from src.onboarding.decisions import SemanticDecisionService
from src.onboarding.ingestion import SafeFileIngestor
from src.onboarding.profiling import DeterministicProfiler
from src.onboarding.readiness import CapabilityDiscovery
from src.onboarding.registry import DatasetRegistry
from src.onboarding.semantics import SemanticMapper

from tests.onboarding_support import write_csv


FIXED_TIME = datetime(2026, 10, 3, 20, 0, tzinfo=timezone.utc)


class CapabilityDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.decisions = SemanticDecisionService(clock=lambda: FIXED_TIME)
        self.profiler = DeterministicProfiler()

    def _approve(self, profile, domain, columns):
        mapping = SemanticMapper().suggest(profile)
        mapping = self.decisions.approve_domain(mapping, domain=domain, evidence="owner")
        for column in columns:
            options = {}
            if column == "dr_cr":
                options["value_mapping"] = {"D": "DEBIT", "C": "CREDIT"}
            mapping = self.decisions.decide(
                mapping, column=column, decision="CONFIRM", evidence="owner", **options,
            )
        return mapping

    def test_sales_can_be_semantically_ready_for_analysis_but_not_executable(self):
        rows = tuple((f"2026-01-{index:02d}", "BR", str(index), str(index / 2))
                     for index in range(1, 31))
        profile = self.profiler.profile_from_rows(
            dataset_id="ds_sales", source_sha256="a" * 64,
            columns=("Date", "Country", "Sales", "Profit"), rows=rows,
        )
        mapping = self._approve(profile, "SALES_RECORD", ("Date", "Country", "Sales", "Profit"))

        report = CapabilityDiscovery().evaluate(profile, mapping)
        analysis = report.capability("FINANCIAL_ANALYSIS")
        anomaly = report.capability("ANOMALY_DETECTION")

        self.assertEqual(analysis.semantic_readiness, "READY")
        self.assertEqual(analysis.execution_readiness, "BLOCKED")
        self.assertEqual(analysis.state, "BLOCKED_NOT_IMPLEMENTED")
        self.assertIn("generic execution adapter", " ".join(analysis.reasons))
        self.assertEqual(anomaly.semantic_readiness, "READY")
        self.assertEqual(anomaly.policy_readiness, "BLOCKED")
        self.assertEqual(anomaly.state, "BLOCKED")
        self.assertTrue(report.all_blocked)

    def test_existing_anomaly_policy_is_not_applied_to_arbitrary_amount(self):
        rows = tuple(("2026-01-01", str(index)) for index in range(30))
        profile = self.profiler.profile_from_rows(
            dataset_id="ds_accounting", source_sha256="b" * 64,
            columns=("posting_date", "amount"), rows=rows,
        )
        mapping = self._approve(profile, "ACCOUNTING_TRANSACTION", ("posting_date", "amount"))
        anomaly = CapabilityDiscovery().evaluate(profile, mapping).capability("ANOMALY_DETECTION")

        self.assertEqual(anomaly.semantic_readiness, "READY")
        self.assertEqual(anomaly.policy_readiness, "BLOCKED")
        self.assertIn("approved screening policy", " ".join(anomaly.reasons))
        self.assertNotEqual(anomaly.state, "AVAILABLE")

    def test_sales_never_satisfies_cash_forecasting_and_tabular_data_never_enables_rag(self):
        profile = self.profiler.profile_from_rows(
            dataset_id="ds_sales", source_sha256="c" * 64,
            columns=("Date", "Sales"), rows=(("2026-01-01", "10"),),
        )
        mapping = self._approve(profile, "SALES_RECORD", ("Date", "Sales"))
        report = CapabilityDiscovery().evaluate(profile, mapping)
        forecast = report.capability("CASH_FLOW_FORECASTING")
        retrieval = report.capability("DOCUMENT_RETRIEVAL")

        self.assertEqual(forecast.state, "BLOCKED")
        self.assertIn("actual settled cash", " ".join(forecast.reasons))
        self.assertNotIn("sales as cash", " ".join(forecast.reasons).lower())
        self.assertEqual(retrieval.state, "BLOCKED")
        self.assertIn("document corpus", " ".join(retrieval.reasons))

    def test_payable_domain_is_recognized_but_no_ap_capability_is_invented(self):
        profile = self.profiler.profile_from_rows(
            dataset_id="ds_payable", source_sha256="d" * 64,
            columns=("invoice_id", "supplier", "due_date", "amount", "status"),
            rows=(("INV-1", "Vendor", "2026-10-10", "12.00", "OPEN"),),
        )
        mapping = self._approve(
            profile, "PAYABLE", ("invoice_id", "supplier", "due_date", "amount", "status"),
        )
        report = CapabilityDiscovery().evaluate(profile, mapping)

        self.assertEqual(mapping.status, "SEMANTICALLY_APPROVED")
        self.assertEqual(report.canonical_domain, "PAYABLE")
        self.assertEqual({item.identifier for item in report.capabilities}, {
            "FINANCIAL_ANALYSIS", "ANOMALY_DETECTION", "CASH_FLOW_FORECASTING", "DOCUMENT_RETRIEVAL",
        })
        self.assertTrue(report.all_blocked)
        self.assertIn("not implemented", " ".join(
            report.capability("FINANCIAL_ANALYSIS").reasons).lower())

    def test_registry_records_blocked_readiness_as_new_version(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = write_csv(root / "sales.csv", "Date,Sales\n2026-01-01,10\n")
            onboarding_root = root / "onboarding"
            ingested = SafeFileIngestor(onboarding_root, clock=lambda: FIXED_TIME).ingest(source)
            profile = self.profiler.profile(ingested)
            mapping = self._approve(profile, "SALES_RECORD", ("Date", "Sales"))
            registry = DatasetRegistry(onboarding_root, clock=lambda: FIXED_TIME)
            registered = registry.register(ingested, profile, mapping)
            report = CapabilityDiscovery().evaluate(profile, mapping)

            updated = registry.record_readiness(registered.dataset_id, report)

            self.assertEqual(updated.registry_version, registered.registry_version + 1)
            self.assertEqual(updated.lifecycle_state, "BLOCKED")
            self.assertEqual(updated.readiness_state, "BLOCKED")
            self.assertEqual(updated.capability_readiness, report.to_dict())

    def test_existing_manager_capabilities_are_unchanged(self):
        catalog = {item["identifier"]: item["status"] for item in FinancialManagerAgent().list_capabilities()}
        self.assertEqual(catalog, {
            "FINANCIAL_ANALYSIS": "AVAILABLE",
            "ANOMALY_DETECTION": "AVAILABLE",
            "CASH_FLOW_FORECASTING": "BLOCKED",
            "DOCUMENT_RETRIEVAL": "BLOCKED",
        })

    def test_arbitrary_callable_cannot_enable_new_dataset_capability(self):
        with self.assertRaises(TypeError):
            CapabilityDiscovery(executable_adapters={"FINANCIAL_ANALYSIS": lambda: None})


if __name__ == "__main__":
    unittest.main()
