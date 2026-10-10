import tempfile
import unittest
from io import StringIO
import json
from pathlib import Path

from src.cli.main import main
from src.execution import (
    BindingOutcome,
    BindingResult,
    DynamicQueryBinder,
    DynamicQueryRequest,
    SalesRecordOperation,
)
from src.execution.sales_record import SalesRecordExecutionAdapter
from src.manager import FinancialManagerAgent
from src.onboarding import OnboardingManager
from src.onboarding.readiness import CapabilityDiscovery
from src.onboarding.registry import DatasetRegistry

from tests.execution_support import onboard_sales


OPERATIONS = (
    "SALES_RECORD_COUNT",
    "SALES_SUMMARY",
    "SALES_BY_COUNTRY",
    "SALES_BY_PERIOD",
    "SALES_BY_SEGMENT",
    "SALES_BY_PRODUCT",
    "PROFIT_SUMMARY",
    "DISCOUNT_ANALYSIS",
    "UNITS_SOLD_SUMMARY",
)

ALL_MAPPINGS = {
    "when": "TRANSACTION_DATE",
    "nation": "COUNTRY",
    "business unit": "SEGMENT",
    "item": "PRODUCT",
    "revenue": "SALES",
    "net result": "PROFIT",
    "rebate amount": "DISCOUNT",
    "quantity": "UNITS_SOLD",
}


def financial_analysis(report):
    return next(
        item for item in report["capabilities"]
        if item["identifier"] == "FINANCIAL_ANALYSIS"
    )


def operation_states(report):
    return {
        item["identifier"]: item["state"]
        for item in financial_analysis(report)["operations"]
    }


class DynamicCapabilityExpansionTests(unittest.TestCase):
    def test_all_approved_semantics_activate_exactly_nine_operations(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manager, state = onboard_sales(
                root,
                "when,nation,business unit,item,revenue,net result,rebate amount,quantity\n"
                "2026-01-01,Brazil,Government,Product A,0.1,5.00,1.00,2.5\n"
                "2026-02-01,Canada,Enterprise,Product B,0.2,-1.00,2.00,3\n",
                mappings=ALL_MAPPINGS,
            )

            report = manager.capabilities(state["dataset_id"])
            analysis = financial_analysis(report)

            self.assertEqual(analysis["state"], "AVAILABLE_WITH_LIMITATIONS")
            self.assertEqual(tuple(operation_states(report)), OPERATIONS)
            self.assertEqual(set(operation_states(report).values()), {"SUPPORTED"})
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

    def test_all_unavailable_optional_measures_block_only_their_operations(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manager, state = onboard_sales(
                root,
                "when,nation,business unit,item,revenue,net result,rebate amount,quantity\n"
                "2026-01-01,Brazil,Government,Product A,10.00,N/A,$-,\n",
                mappings=ALL_MAPPINGS,
            )

            states = operation_states(manager.capabilities(state["dataset_id"]))

            self.assertEqual(states, {
                "SALES_RECORD_COUNT": "SUPPORTED",
                "SALES_SUMMARY": "SUPPORTED",
                "SALES_BY_COUNTRY": "SUPPORTED",
                "SALES_BY_PERIOD": "SUPPORTED",
                "SALES_BY_SEGMENT": "SUPPORTED",
                "SALES_BY_PRODUCT": "SUPPORTED",
                "PROFIT_SUMMARY": "BLOCKED",
                "DISCOUNT_ANALYSIS": "BLOCKED",
                "UNITS_SOLD_SUMMARY": "BLOCKED",
            })

    def test_exact_arithmetic_quality_blockers_are_not_advertised_supported(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            huge = "9" * 60
            manager, state = onboard_sales(
                root,
                "when,nation,business unit,item,revenue,net result,rebate amount,quantity\n"
                f"2026-01-01,Brazil,Government,Product A,{huge},{huge},{huge},{huge}\n"
                f"2026-01-02,Brazil,Government,Product A,{huge},{huge},{huge},{huge}\n",
                mappings=ALL_MAPPINGS,
            )

            states = operation_states(manager.capabilities(state["dataset_id"]))

            self.assertEqual(states, {
                "SALES_RECORD_COUNT": "SUPPORTED",
                "SALES_SUMMARY": "BLOCKED",
                "SALES_BY_COUNTRY": "BLOCKED",
                "SALES_BY_PERIOD": "BLOCKED",
                "SALES_BY_SEGMENT": "BLOCKED",
                "SALES_BY_PRODUCT": "BLOCKED",
                "PROFIT_SUMMARY": "BLOCKED",
                "DISCOUNT_ANALYSIS": "BLOCKED",
                "UNITS_SOLD_SUMMARY": "BLOCKED",
            })

    def test_partial_readiness_uses_only_operation_specific_optional_roles(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manager, state = onboard_sales(
                root,
                "when,item,revenue,net result\n"
                "2026-01-01,Product A,10.00,2.00\n",
                mappings={
                    "when": "TRANSACTION_DATE",
                    "item": "PRODUCT",
                    "revenue": "SALES",
                    "net result": "PROFIT",
                },
            )

            report = manager.capabilities(state["dataset_id"])

            self.assertEqual(financial_analysis(report)["state"], "AVAILABLE_WITH_LIMITATIONS")
            self.assertEqual(operation_states(report), {
                "SALES_RECORD_COUNT": "SUPPORTED",
                "SALES_SUMMARY": "SUPPORTED",
                "SALES_BY_COUNTRY": "BLOCKED",
                "SALES_BY_PERIOD": "SUPPORTED",
                "SALES_BY_SEGMENT": "BLOCKED",
                "SALES_BY_PRODUCT": "SUPPORTED",
                "PROFIT_SUMMARY": "SUPPORTED",
                "DISCOUNT_ANALYSIS": "BLOCKED",
                "UNITS_SOLD_SUMMARY": "BLOCKED",
            })

    def test_optional_role_revocation_and_persisted_recovery_are_isolated(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manager, state = onboard_sales(
                root,
                "when,nation,business unit,item,revenue,net result,rebate amount,quantity\n"
                "2026-01-01,Brazil,Government,Product A,10.00,2.00,1.00,3\n",
                mappings=ALL_MAPPINGS,
            )
            dataset_id = state["dataset_id"]
            baseline = operation_states(manager.capabilities(dataset_id))

            segment_rejected = manager.reject(
                dataset_id, "business unit", evidence="Segment authority revoked",
            )
            after_segment = operation_states(
                OnboardingManager(root / "onboarding").capabilities(dataset_id)
            )

            self.assertEqual(segment_rejected["lifecycle_state"], "READY")
            self.assertEqual(
                {key for key in OPERATIONS if baseline[key] != after_segment[key]},
                {"SALES_BY_SEGMENT"},
            )
            self.assertEqual(after_segment["SALES_BY_SEGMENT"], "BLOCKED")

            segment_restored = OnboardingManager(root / "onboarding").confirm(
                dataset_id,
                "business unit",
                "SEGMENT",
                evidence="Segment authority restored",
            )
            after_segment_restore = operation_states(
                OnboardingManager(root / "onboarding").capabilities(dataset_id)
            )
            self.assertGreater(
                segment_restored["mapping_version"], segment_rejected["mapping_version"],
            )
            self.assertEqual(after_segment_restore, baseline)

            profit_rejected = OnboardingManager(root / "onboarding").reject(
                dataset_id, "net result", evidence="Profit authority revoked",
            )
            after_profit = operation_states(
                OnboardingManager(root / "onboarding").capabilities(dataset_id)
            )
            self.assertEqual(
                {key for key in OPERATIONS if baseline[key] != after_profit[key]},
                {"PROFIT_SUMMARY"},
            )
            self.assertEqual(after_profit["PROFIT_SUMMARY"], "BLOCKED")

            profit_restored = OnboardingManager(root / "onboarding").confirm(
                dataset_id,
                "net result",
                "PROFIT",
                evidence="Profit authority restored",
            )
            recovered = operation_states(
                OnboardingManager(root / "onboarding").capabilities(dataset_id)
            )
            self.assertGreater(
                profit_restored["mapping_version"], profit_rejected["mapping_version"],
            )
            self.assertEqual(recovered, baseline)

    def test_transaction_date_anchor_revocation_blocks_domain_and_recovers_from_current_mapping(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manager, state = onboard_sales(
                root,
                "when,revenue\n2026-01-01,10.00\n",
                mappings={"when": "TRANSACTION_DATE", "revenue": "SALES"},
            )
            dataset_id = state["dataset_id"]
            baseline = operation_states(manager.capabilities(dataset_id))

            rejected = manager.reject(
                dataset_id, "when", evidence="Transaction date authority revoked",
            )
            blocked = operation_states(manager.capabilities(dataset_id))

            self.assertEqual(rejected["lifecycle_state"], "NEEDS_CONFIRMATION")
            self.assertEqual(set(blocked.values()), {"BLOCKED"})

            restored = OnboardingManager(root / "onboarding").confirm(
                dataset_id,
                "when",
                "TRANSACTION_DATE",
                evidence="Transaction date authority restored",
            )
            recovered = operation_states(
                OnboardingManager(root / "onboarding").capabilities(dataset_id)
            )

            self.assertGreater(restored["mapping_version"], rejected["mapping_version"])
            self.assertEqual(recovered, baseline)

    def test_confirmed_multiple_currency_blocks_only_monetary_operations(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manager, state = onboard_sales(
                root,
                "when,nation,business unit,item,revenue,net result,rebate amount,quantity,curr\n"
                "2026-01-01,Brazil,Government,Product A,10.00,2.00,1.00,3,USD\n"
                "2026-01-02,Canada,Enterprise,Product B,20.00,4.00,2.00,4,EUR\n",
                mappings={**ALL_MAPPINGS, "curr": "CURRENCY"},
                currency_values={"USD": "USD", "EUR": "EUR"},
            )

            report = manager.capabilities(state["dataset_id"])

            self.assertEqual(report["currency"], {
                "state": "CONFIRMED_MULTIPLE", "code": None,
            })
            self.assertEqual(operation_states(report), {
                "SALES_RECORD_COUNT": "SUPPORTED",
                "SALES_SUMMARY": "BLOCKED",
                "SALES_BY_COUNTRY": "BLOCKED",
                "SALES_BY_PERIOD": "BLOCKED",
                "SALES_BY_SEGMENT": "BLOCKED",
                "SALES_BY_PRODUCT": "BLOCKED",
                "PROFIT_SUMMARY": "BLOCKED",
                "DISCOUNT_ANALYSIS": "BLOCKED",
                "UNITS_SOLD_SUMMARY": "SUPPORTED",
            })

    def test_adapter_catalog_mismatch_cannot_report_operation_supported(self):
        class ProfitOmittingAdapter(SalesRecordExecutionAdapter):
            @staticmethod
            def supported_operations():
                return tuple(
                    operation for operation in SalesRecordOperation
                    if operation is not SalesRecordOperation.PROFIT_SUMMARY
                )

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manager, state = onboard_sales(
                root,
                "when,nation,business unit,item,revenue,net result,rebate amount,quantity\n"
                "2026-01-01,Brazil,Government,Product A,10.00,2.00,1.00,3\n",
                mappings=ALL_MAPPINGS,
            )
            registry = DatasetRegistry(root / "onboarding")
            entry = registry.get(state["dataset_id"])
            profile = registry.load_profile(state["dataset_id"], entry.profile_digest)
            mapping = registry.load_mapping(
                state["dataset_id"],
                entry.semantic_mapping_version,
                entry.semantic_mapping_digest,
            )
            discovery = CapabilityDiscovery(
                root / "onboarding",
                adapter_resolver=lambda domain, onboarding_root: (
                    ProfitOmittingAdapter(onboarding_root)
                    if domain == "SALES_RECORD" else None
                ),
            )

            report = discovery.evaluate(profile, mapping).to_dict()

            self.assertEqual(operation_states(report)["PROFIT_SUMMARY"], "BLOCKED")
            profit = next(
                item for item in financial_analysis(report)["operations"]
                if item["identifier"] == "PROFIT_SUMMARY"
            )
            self.assertEqual(
                profit["reasons"],
                ["Binding validation returned ADAPTER_UNAVAILABLE."],
            )
            self.assertTrue(all(
                state == "SUPPORTED"
                for operation, state in operation_states(report).items()
                if operation != "PROFIT_SUMMARY"
            ))

    def test_binder_unavailable_operation_cannot_be_reported_supported(self):
        class ProfitUnavailableBinder:
            def __init__(self, *args, **kwargs):
                self.delegate = DynamicQueryBinder(*args, **kwargs)

            def bind(self, request):
                if request.operation == "PROFIT_SUMMARY":
                    return BindingResult(
                        BindingOutcome.UNSUPPORTED_OPERATION,
                        "The operation is unavailable from the binder.",
                    )
                return self.delegate.bind(request)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                "when,nation,business unit,item,revenue,net result,rebate amount,quantity\n"
                "2026-01-01,Brazil,Government,Product A,10.00,2.00,1.00,3\n",
                mappings=ALL_MAPPINGS,
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
                binder_factory=ProfitUnavailableBinder,
            ).evaluate(profile, mapping).to_dict()

            self.assertEqual(operation_states(report)["PROFIT_SUMMARY"], "UNSUPPORTED")
            self.assertTrue(all(
                state == "SUPPORTED"
                for operation, state in operation_states(report).items()
                if operation != "PROFIT_SUMMARY"
            ))

    def test_cli_human_and_json_expose_nine_typed_operation_states_and_reasons(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manager, state = onboard_sales(
                root,
                "when,revenue\n2026-01-01,10.00\n",
                mappings={"when": "TRANSACTION_DATE", "revenue": "SALES"},
            )
            human = StringIO()
            structured = StringIO()

            self.assertEqual(main(
                ["dataset", "capabilities", state["dataset_id"]],
                onboarding=manager,
                stdout=human,
                stderr=StringIO(),
            ), 0)
            self.assertEqual(main(
                ["dataset", "capabilities", state["dataset_id"], "--json"],
                onboarding=manager,
                stdout=structured,
                stderr=StringIO(),
            ), 0)

            rendered = human.getvalue()
            self.assertEqual(sum(name in rendered for name in OPERATIONS), len(OPERATIONS))
            self.assertIn("- SALES_BY_PERIOD: SUPPORTED", rendered)
            self.assertIn(
                "- PROFIT_SUMMARY: BLOCKED "
                "(Binding validation returned MISSING_REQUIRED_SEMANTICS.)",
                rendered,
            )
            report = json.loads(structured.getvalue())
            self.assertEqual(tuple(operation_states(report)), OPERATIONS)
            profit = next(
                item for item in financial_analysis(report)["operations"]
                if item["identifier"] == "PROFIT_SUMMARY"
            )
            self.assertEqual(profit["state"], "BLOCKED")
            self.assertEqual(
                profit["reasons"],
                ["Binding validation returned MISSING_REQUIRED_SEMANTICS."],
            )

    def test_manager_executes_all_six_phase15_operations_through_existing_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                "when,nation,business unit,item,revenue,net result,rebate amount,quantity\n"
                "2026-01-01,Brazil,Government,Product A,0.1,5.00,1.00,2.5\n"
                "2026-02-01,Canada,Enterprise,Product B,0.2,-1.00,2.00,3\n",
                mappings=ALL_MAPPINGS,
            )
            manager = FinancialManagerAgent(onboarding_root=root / "onboarding")

            for operation in OPERATIONS[3:]:
                with self.subTest(operation=operation):
                    response = manager.execute_dataset_request(DynamicQueryRequest(
                        dataset_id=state["dataset_id"],
                        operation=operation,
                    ))
                    self.assertEqual(response["execution_status"], "SUCCESS")
                    self.assertEqual(
                        response["delegated_result"]["query_name"],
                        operation,
                    )
                    self.assertEqual(
                        response["delegated_result"]["metadata"]["lineage"]["dataset_id"],
                        state["dataset_id"],
                    )


if __name__ == "__main__":
    unittest.main()
