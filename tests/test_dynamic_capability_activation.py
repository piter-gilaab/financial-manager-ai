import tempfile
import unittest
from io import StringIO
import json
from pathlib import Path

from src.cli.main import main
from src.execution import DynamicQueryRequest
from src.manager import FinancialManagerAgent
from src.onboarding import OnboardingManager
from src.onboarding.readiness import CapabilityDiscovery
from src.onboarding.registry import DatasetRegistry

from tests.execution_support import onboard_sales
from tests.onboarding_support import write_csv


def financial_capability(report):
    return next(
        item for item in report["capabilities"]
        if item["identifier"] == "FINANCIAL_ANALYSIS"
    )


def operation_states(capability):
    return {item["identifier"]: item["state"] for item in capability["operations"]}


def expected_states(**overrides):
    states = {
        "SALES_RECORD_COUNT": "BLOCKED",
        "SALES_SUMMARY": "BLOCKED",
        "SALES_BY_COUNTRY": "BLOCKED",
        "SALES_BY_PERIOD": "BLOCKED",
        "SALES_BY_SEGMENT": "BLOCKED",
        "SALES_BY_PRODUCT": "BLOCKED",
        "PROFIT_SUMMARY": "BLOCKED",
        "DISCOUNT_ANALYSIS": "BLOCKED",
        "UNITS_SOLD_SUMMARY": "BLOCKED",
    }
    states.update(overrides)
    return states


class DynamicCapabilityActivationTests(unittest.TestCase):
    def test_sales_record_activation_is_dataset_specific_and_operation_aware(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manager, state = onboard_sales(
                root,
                "date,sales\n2026-01-01,10.00\n",
            )

            report = manager.capabilities(state["dataset_id"])
            analysis = financial_capability(report)

            self.assertEqual(state["lifecycle_state"], "READY")
            self.assertEqual(state["readiness_state"], "READY")
            self.assertEqual(analysis["state"], "AVAILABLE_WITH_LIMITATIONS")
            self.assertEqual(analysis["execution_readiness"], "READY")
            self.assertEqual(operation_states(analysis), expected_states(
                SALES_RECORD_COUNT="SUPPORTED",
                SALES_SUMMARY="SUPPORTED",
                SALES_BY_PERIOD="SUPPORTED",
            ))
            self.assertEqual(report["canonical_domain"], "SALES_RECORD")
            self.assertEqual(report["currency"]["state"], "UNKNOWN")
            self.assertEqual(
                {item["identifier"]: tuple(item["required_semantics"])
                 for item in analysis["operations"]},
                {
                    "SALES_RECORD_COUNT": (),
                    "SALES_SUMMARY": ("SALES",),
                    "SALES_BY_COUNTRY": ("SALES", "COUNTRY"),
                    "SALES_BY_PERIOD": ("SALES", "TRANSACTION_DATE"),
                    "SALES_BY_SEGMENT": ("SALES", "SEGMENT"),
                    "SALES_BY_PRODUCT": ("SALES", "PRODUCT"),
                    "PROFIT_SUMMARY": ("PROFIT",),
                    "DISCOUNT_ANALYSIS": ("DISCOUNT",),
                    "UNITS_SOLD_SUMMARY": ("UNITS_SOLD",),
                },
            )

    def test_country_semantics_activate_only_its_sales_grouping(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manager, state = onboard_sales(
                root,
                "date,country,sales\n2026-01-01,Brazil,10.00\n",
                mappings={
                    "date": "TRANSACTION_DATE",
                    "country": "COUNTRY",
                    "sales": "SALES",
                },
            )

            analysis = financial_capability(manager.capabilities(state["dataset_id"]))

            self.assertEqual(operation_states(analysis), expected_states(
                SALES_RECORD_COUNT="SUPPORTED",
                SALES_SUMMARY="SUPPORTED",
                SALES_BY_COUNTRY="SUPPORTED",
                SALES_BY_PERIOD="SUPPORTED",
            ))
            self.assertIn("no arbitrary filters", " ".join(analysis["limitations"]).lower())

    def test_invalid_sales_values_leave_only_record_count_executable(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manager, state = onboard_sales(
                root,
                "date,sales\n2026-01-01,not-money\n",
            )

            analysis = financial_capability(manager.capabilities(state["dataset_id"]))

            self.assertEqual(analysis["state"], "AVAILABLE_WITH_LIMITATIONS")
            self.assertEqual(operation_states(analysis), expected_states(
                SALES_RECORD_COUNT="SUPPORTED",
            ))

    def test_unknown_and_confirmed_currency_are_disclosed_without_inference(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "unknown").mkdir()
            (root / "confirmed").mkdir()
            unknown_manager, unknown = onboard_sales(
                root / "unknown",
                "date,sales\n2026-01-01,10.00\n",
            )
            confirmed_manager, confirmed = onboard_sales(
                root / "confirmed",
                "date,sales,currency\n2026-01-01,10.00,USD\n",
                mappings={
                    "date": "TRANSACTION_DATE",
                    "sales": "SALES",
                    "currency": "CURRENCY",
                },
                currency_values={"USD": "USD"},
            )

            unknown_currency = unknown_manager.capabilities(unknown["dataset_id"])["currency"]
            confirmed_currency = confirmed_manager.capabilities(confirmed["dataset_id"])["currency"]

            self.assertEqual(unknown_currency, {"state": "UNKNOWN", "code": None})
            self.assertEqual(confirmed_currency, {"state": "CONFIRMED", "code": "USD"})
            self.assertEqual(
                financial_capability(unknown_manager.capabilities(unknown["dataset_id"]))["state"],
                "AVAILABLE_WITH_LIMITATIONS",
            )

    def test_optional_country_revocation_only_revokes_country_operation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manager, state = onboard_sales(
                root,
                "date,country,sales\n2026-01-01,Brazil,10.00\n",
                mappings={
                    "date": "TRANSACTION_DATE",
                    "country": "COUNTRY",
                    "sales": "SALES",
                },
            )
            before = operation_states(financial_capability(manager.capabilities(state["dataset_id"])))

            revised = manager.reject(
                state["dataset_id"], "country", evidence="Country meaning revoked",
            )
            after = operation_states(financial_capability(
                manager.capabilities(state["dataset_id"]),
            ))

            self.assertEqual(before["SALES_BY_COUNTRY"], "SUPPORTED")
            self.assertEqual(revised["lifecycle_state"], "READY")
            self.assertEqual(after, expected_states(
                SALES_RECORD_COUNT="SUPPORTED",
                SALES_SUMMARY="SUPPORTED",
                SALES_BY_PERIOD="SUPPORTED",
            ))

    def test_required_sales_revocation_blocks_the_unapproved_dataset(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manager, state = onboard_sales(
                root,
                "date,sales\n2026-01-01,10.00\n",
            )

            revised = manager.reject(
                state["dataset_id"], "sales", evidence="Sales meaning revoked",
            )
            analysis = financial_capability(manager.capabilities(state["dataset_id"]))

            self.assertEqual(revised["lifecycle_state"], "NEEDS_CONFIRMATION")
            self.assertEqual(analysis["state"], "BLOCKED")
            self.assertTrue(all(
                operation["state"] == "BLOCKED" for operation in analysis["operations"]
            ))

    def test_source_change_revokes_current_capability_report_and_execution(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manager, state = onboard_sales(
                root,
                "date,sales\n2026-01-01,10.00\n",
            )
            source = (
                root / "onboarding" / "artifacts" / state["dataset_id"]
                / "source" / "source.csv"
            )
            source.write_text("date,sales\n2026-01-01,999.00\n", encoding="utf-8")

            analysis = financial_capability(manager.capabilities(state["dataset_id"]))
            persisted = manager.status(state["dataset_id"])
            response = FinancialManagerAgent(
                onboarding_root=root / "onboarding",
            ).execute_dataset_request(DynamicQueryRequest(
                dataset_id=state["dataset_id"],
                operation="SALES_SUMMARY",
            ))

            self.assertEqual(analysis["state"], "BLOCKED")
            self.assertTrue(all(
                operation["state"] == "BLOCKED" for operation in analysis["operations"]
            ))
            self.assertEqual(persisted["lifecycle_state"], "BLOCKED")
            current = DatasetRegistry(root / "onboarding").get(state["dataset_id"])
            self.assertEqual(current.readiness_state, "BLOCKED")
            self.assertEqual(
                financial_capability(current.capability_readiness)["state"],
                "BLOCKED",
            )
            self.assertEqual(response["execution_status"], "DATA_QUALITY_BLOCKER")
            self.assertEqual(response["errors"][0]["code"], "BINDING_BLOCKED")

            source.write_text("date,sales\n2026-01-01,10.00\n", encoding="utf-8")
            restored = manager.capabilities(state["dataset_id"])

            self.assertEqual(
                financial_capability(restored)["state"],
                "AVAILABLE_WITH_LIMITATIONS",
            )
            self.assertEqual(manager.status(state["dataset_id"])["lifecycle_state"], "READY")

    def test_corrupt_registry_revokes_capability_without_exposing_artifacts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manager, state = onboard_sales(
                root,
                "date,sales\n2026-01-01,10.00\n",
            )
            registry_path = (
                root / "onboarding" / "registry" / state["dataset_id"] / "current.json"
            )
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            registry["row_count"] = 999
            registry_path.write_text(json.dumps(registry), encoding="utf-8")

            report = manager.capabilities(state["dataset_id"])
            analysis = financial_capability(report)

            self.assertEqual(analysis["state"], "BLOCKED")
            self.assertTrue(all(
                item["state"] == "BLOCKED" for item in analysis["operations"]
            ))
            self.assertNotIn(str(root), " ".join(analysis["reasons"]))

    def test_missing_static_adapter_prevents_activation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                "date,country,sales\n2026-01-01,Brazil,10.00\n",
                mappings={
                    "date": "TRANSACTION_DATE",
                    "country": "COUNTRY",
                    "sales": "SALES",
                },
            )
            registry = DatasetRegistry(root / "onboarding")
            entry = registry.get(state["dataset_id"])
            profile = registry.load_profile(state["dataset_id"], entry.profile_digest)
            mapping = registry.load_mapping(
                state["dataset_id"],
                entry.semantic_mapping_version,
                entry.semantic_mapping_digest,
            )

            report = CapabilityDiscovery(
                root / "onboarding",
                adapter_resolver=lambda domain, onboarding_root: None,
            ).evaluate(profile, mapping)
            analysis = report.capability("FINANCIAL_ANALYSIS")

            self.assertEqual(analysis.state, "BLOCKED_NOT_IMPLEMENTED")
            self.assertTrue(all(item.state == "BLOCKED" for item in analysis.operations))

    def test_recognized_unsupported_domain_is_not_activated_or_coerced(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = write_csv(
                root / "accounting.csv",
                "posting_date,amount\n2026-01-01,10.00\n",
            )
            manager = OnboardingManager(root / "onboarding")
            state = manager.add(source)
            manager.confirm(
                state["dataset_id"], "posting_date", "POSTING_DATE",
                evidence="Posting date approved",
            )
            manager.confirm(
                state["dataset_id"], "amount", "AMOUNT",
                evidence="Amount approved",
            )
            final = manager.confirm_domain(
                state["dataset_id"], "ACCOUNTING_TRANSACTION",
                evidence="Accounting domain approved",
            )

            analysis = financial_capability(manager.capabilities(final["dataset_id"]))

            self.assertEqual(analysis["state"], "BLOCKED_NOT_IMPLEMENTED")
            self.assertEqual(analysis["execution_readiness"], "BLOCKED")
            self.assertEqual(analysis["operations"], [])

    def test_manager_delegates_typed_request_to_existing_adapter_and_core(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                "date,sales\n2026-01-01,0.1\n2026-01-02,0.2\n",
            )
            manager = FinancialManagerAgent(onboarding_root=root / "onboarding")

            response = manager.execute_dataset_request(DynamicQueryRequest(
                dataset_id=state["dataset_id"],
                operation="SALES_SUMMARY",
            ))

            self.assertEqual(response["capability"], "FINANCIAL_ANALYSIS")
            self.assertEqual(response["manager_version"], "1.1")
            self.assertEqual(response["capability_status"], "AVAILABLE")
            self.assertEqual(
                response["dataset_capability"]["state"],
                "AVAILABLE_WITH_LIMITATIONS",
            )
            self.assertEqual(response["execution_status"], "SUCCESS")
            self.assertEqual(
                response["delegated_result"]["result"]["measures"]["sales"]["sum"],
                "0.3",
            )
            self.assertEqual(
                response["delegated_result"]["metadata"]["lineage"]["dataset_id"],
                state["dataset_id"],
            )

    def test_manager_rejects_unsupported_and_malicious_requests_as_data(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(root, "date,sales\n2026-01-01,10.00\n")
            manager = FinancialManagerAgent(onboarding_root=root / "onboarding")

            unsupported = manager.execute_dataset_request(DynamicQueryRequest(
                dataset_id=state["dataset_id"],
                operation="CASH_FLOW_FORECAST",
            ))
            malicious_operation = manager.execute_dataset_request(DynamicQueryRequest(
                dataset_id=state["dataset_id"],
                operation="__import__('os').system('id')",
            ))
            malicious_dataset = manager.execute_dataset_request(DynamicQueryRequest(
                dataset_id="../../etc/passwd",
                operation="SALES_SUMMARY",
            ))

            self.assertEqual(unsupported["execution_status"], "UNSUPPORTED")
            self.assertEqual(malicious_operation["execution_status"], "UNSUPPORTED")
            self.assertEqual(malicious_dataset["execution_status"], "INVALID_REQUEST")
            self.assertFalse((root / "etc" / "passwd").exists())

    def test_other_dynamic_capabilities_remain_blocked(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manager, state = onboard_sales(
                root,
                "date,country,sales\n2026-01-01,Brazil,10.00\n",
                mappings={
                    "date": "TRANSACTION_DATE",
                    "country": "COUNTRY",
                    "sales": "SALES",
                },
            )

            report = manager.capabilities(state["dataset_id"])
            states = {item["identifier"]: item["state"] for item in report["capabilities"]}

            self.assertEqual(states["ANOMALY_DETECTION"], "BLOCKED")
            self.assertEqual(states["CASH_FLOW_FORECASTING"], "BLOCKED")
            self.assertEqual(states["DOCUMENT_RETRIEVAL"], "BLOCKED")

    def test_cli_capability_discovery_shows_operations_domain_and_currency(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manager, state = onboard_sales(
                root,
                "date,country,sales\n2026-01-01,Brazil,10.00\n",
                mappings={
                    "date": "TRANSACTION_DATE",
                    "country": "COUNTRY",
                    "sales": "SALES",
                },
            )
            output = StringIO()

            code = main(
                ["dataset", "capabilities", state["dataset_id"]],
                onboarding=manager,
                stdout=output,
                stderr=StringIO(),
            )

            rendered = output.getvalue()
            self.assertEqual(code, 0)
            self.assertIn("Financial Analysis: AVAILABLE_WITH_LIMITATIONS", rendered)
            self.assertIn("Canonical domain: SALES_RECORD", rendered)
            self.assertIn("Currency: UNKNOWN", rendered)
            self.assertIn("SALES_RECORD_COUNT", rendered)
            self.assertIn("SALES_SUMMARY", rendered)
            self.assertIn("SALES_BY_COUNTRY", rendered)
            self.assertIn("SALES_BY_PERIOD", rendered)
            self.assertIn("SALES_BY_SEGMENT", rendered)
            self.assertIn("SALES_BY_PRODUCT", rendered)
            self.assertIn("PROFIT_SUMMARY", rendered)
            self.assertIn("DISCOUNT_ANALYSIS", rendered)
            self.assertIn("UNITS_SOLD_SUMMARY", rendered)
            self.assertIn("Limitations:", rendered)
            self.assertIn("No arbitrary filters", rendered)

    def test_legacy_capability_catalog_and_routing_remain_unchanged(self):
        manager = FinancialManagerAgent()

        catalog = {item["identifier"]: item["status"] for item in manager.list_capabilities()}

        self.assertEqual(catalog, {
            "FINANCIAL_ANALYSIS": "AVAILABLE",
            "ANOMALY_DETECTION": "AVAILABLE",
            "CASH_FLOW_FORECASTING": "BLOCKED",
            "DOCUMENT_RETRIEVAL": "BLOCKED",
        })
        self.assertEqual(
            manager.plan("How many Company Financials records are there?")["status"],
            "ROUTED",
        )


if __name__ == "__main__":
    unittest.main()
