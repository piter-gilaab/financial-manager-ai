"""Phase 15 all-nine acceptance through persisted onboarding and Manager evidence."""

import json
from pathlib import Path
import tempfile
import unittest

from src.execution import DynamicQueryParameters, DynamicQueryRequest
from src.manager import FinancialManagerAgent
from src.onboarding import OnboardingManager
from src.onboarding.models import OnboardingError

from tests.execution_support import onboard_sales
from tests.onboarding_support import write_csv


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

MAPPINGS = {
    "TxnDate": "TRANSACTION_DATE",
    "Nation": "COUNTRY",
    "BusinessUnit": "SEGMENT",
    "Item": "PRODUCT",
    "Revenue": "SALES",
    "NetResult": "PROFIT",
    "RebateAmount": "DISCOUNT",
    "Qty": "UNITS_SOLD",
}

PRIMARY_CSV = (
    "TxnDate,Nation,BusinessUnit,Item,Revenue,NetResult,RebateAmount,Qty\n"
    "2025-12-31,Brazil,Government,Product A,0.1,5.00,1.00,1.25\n"
    "2026-01-01,,Enterprise,Product B,0.2,-2.00,2.00,999999999999999999999999999999.75\n"
    "2026-02-01,Canada,,DROP TABLE sales; --,0.3,0.00,N/A,\n"
    ",Canada,Retail,__import__('os'),-0.1,-,$-,0.5\n"
)


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


class DynamicAnalysisExpansionEndToEndTests(unittest.TestCase):
    def test_renamed_all_nine_unknown_currency_flow_preserves_exact_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            onboarding, state = onboard_sales(root, PRIMARY_CSV, mappings=MAPPINGS)
            dataset_id = state["dataset_id"]
            report = onboarding.capabilities(dataset_id)
            manager = FinancialManagerAgent(onboarding_root=root / "onboarding")

            self.assertEqual(tuple(operation_states(report)), OPERATIONS)
            self.assertEqual(set(operation_states(report).values()), {"SUPPORTED"})
            self.assertEqual(report["currency"], {"state": "UNKNOWN", "code": None})

            responses = {
                operation: manager.execute_dataset_request(DynamicQueryRequest(
                    dataset_id=dataset_id,
                    operation=operation,
                ))
                for operation in OPERATIONS
            }
            for operation, response in responses.items():
                with self.subTest(operation=operation):
                    self.assertIn(response["execution_status"], {"SUCCESS", "PARTIAL"})
                    evidence = response["delegated_result"]
                    self.assertEqual(evidence["query_name"], operation)
                    self.assertEqual(
                        evidence["metadata"]["lineage"]["dataset_id"], dataset_id,
                    )
                    self.assertNotIn(str(root), json.dumps(response))

            self.assertEqual(
                responses["SALES_SUMMARY"]["delegated_result"]
                ["result"]["measures"]["sales"]["sum"],
                "0.5",
            )
            month = responses["SALES_BY_PERIOD"]["delegated_result"]
            self.assertEqual(
                [group["key"] for group in month["result"]["groups"]],
                [
                    {"value": "2025-12", "kind": "source_value"},
                    {"value": "2026-01", "kind": "source_value"},
                    {"value": "2026-02", "kind": "source_value"},
                    {"value": None, "kind": "unavailable"},
                ],
            )
            year = manager.execute_dataset_request(DynamicQueryRequest(
                dataset_id=dataset_id,
                operation="SALES_BY_PERIOD",
                parameters=DynamicQueryParameters(granularity="YEAR"),
            ))["delegated_result"]
            self.assertEqual(
                [group["key"]["value"] for group in year["result"]["groups"]],
                ["2025", "2026", None],
            )

            country_bucket = responses["SALES_BY_COUNTRY"]["delegated_result"]
            country_exclude = manager.execute_dataset_request(DynamicQueryRequest(
                dataset_id=dataset_id,
                operation="SALES_BY_COUNTRY",
                parameters=DynamicQueryParameters(missing_dimension="EXCLUDE"),
            ))["delegated_result"]
            segment = responses["SALES_BY_SEGMENT"]["delegated_result"]
            segment_exclude = manager.execute_dataset_request(DynamicQueryRequest(
                dataset_id=dataset_id,
                operation="SALES_BY_SEGMENT",
                parameters=DynamicQueryParameters(missing_dimension="EXCLUDE"),
            ))["delegated_result"]
            product = responses["SALES_BY_PRODUCT"]["delegated_result"]
            self.assertEqual(country_bucket["result"]["groups"][-1]["key"]["kind"],
                             "unavailable")
            self.assertEqual(country_exclude["records"]["exclusion_reasons"], {
                "dimension:country:source_missing": 1,
            })
            self.assertEqual(segment["result"]["groups"][-1]["key"]["kind"],
                             "unavailable")
            self.assertEqual(segment_exclude["records"]["exclusion_reasons"], {
                "dimension:segment:source_missing": 1,
            })
            self.assertEqual(
                [group["key"]["value"] for group in product["result"]["groups"]],
                ["DROP TABLE sales; --", "Product A", "Product B", "__import__('os')"],
            )

            profit = responses["PROFIT_SUMMARY"]["delegated_result"]
            self.assertEqual(profit["result"]["measures"]["profit"]["sum"], "3.00")
            self.assertEqual(
                (profit["result"]["negative_count"], profit["result"]["zero_count"],
                 profit["result"]["positive_count"]),
                (1, 1, 1),
            )
            self.assertEqual(profit["records"]["exclusion_reasons"], {
                "measure:profit:parsing_failed": 1,
            })

            discount = responses["DISCOUNT_ANALYSIS"]["delegated_result"]
            self.assertEqual(discount["result"]["unavailable_value_count"], 2)
            self.assertEqual(discount["result"]["measures"]["discount"], {
                "count": 2,
                "sum": "3.00",
                "mean": "1.500000",
                "min": "1.00",
                "max": "2.00",
                "unit": "monetary",
                "coverage": {
                    "candidates": 4,
                    "used": 2,
                    "excluded": 2,
                    "exclusion_reasons": {
                        "measure:discount:parsing_failed": 1,
                        "measure:discount:source_missing": 1,
                    },
                    "percentage": "50.000000",
                },
            })

            units = responses["UNITS_SOLD_SUMMARY"]["delegated_result"]
            self.assertIsNone(units["currency"])
            self.assertEqual(
                units["result"]["measures"]["units_sold"]["sum"],
                "1000000000000000000000000000001.50",
            )
            self.assertEqual(
                units["result"]["measures"]["units_sold"]["coverage"]["excluded"],
                1,
            )

    def test_confirmed_currency_survives_readiness_manager_and_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            mappings = {**MAPPINGS, "CurrencyCode": "CURRENCY"}
            manager, state = onboard_sales(
                root,
                "TxnDate,Nation,BusinessUnit,Item,Revenue,NetResult,RebateAmount,Qty,CurrencyCode\n"
                "2026-01-01,Brazil,Government,Product A,10.00,2.00,1.00,2.5,USD\n",
                mappings=mappings,
                currency_values={"USD": "USD"},
            )
            dataset_id = state["dataset_id"]
            report = manager.capabilities(dataset_id)
            financial = FinancialManagerAgent(onboarding_root=root / "onboarding")

            self.assertEqual(report["currency"], {"state": "CONFIRMED", "code": "USD"})
            self.assertEqual(set(operation_states(report).values()), {"SUPPORTED"})
            for operation in (
                "SALES_SUMMARY", "SALES_BY_PERIOD", "PROFIT_SUMMARY", "DISCOUNT_ANALYSIS",
            ):
                with self.subTest(operation=operation):
                    evidence = financial.execute_dataset_request(DynamicQueryRequest(
                        dataset_id, operation,
                    ))["delegated_result"]
                    self.assertEqual(
                        (evidence["currency"]["status"], evidence["currency"]["code"]),
                        ("CONFIRMED", "USD"),
                    )
            units = financial.execute_dataset_request(DynamicQueryRequest(
                dataset_id, "UNITS_SOLD_SUMMARY",
            ))["delegated_result"]
            self.assertIsNone(units["currency"])

    def test_missing_optional_semantics_produce_truthful_partial_readiness(self):
        cases = (
            ("Country", "SALES_BY_COUNTRY"),
            ("Profit", "PROFIT_SUMMARY"),
            ("Units", "UNITS_SOLD_SUMMARY"),
        )
        for label, blocked_operation in cases:
            with self.subTest(missing=label), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                mappings = dict(MAPPINGS)
                missing_column = {
                    "Country": "Nation",
                    "Profit": "NetResult",
                    "Units": "Qty",
                }[label]
                mappings.pop(missing_column)
                headers = [column for column in MAPPINGS if column != missing_column]
                values = {
                    "TxnDate": "2026-01-01",
                    "Nation": "Brazil",
                    "BusinessUnit": "Government",
                    "Item": "Product A",
                    "Revenue": "10.00",
                    "NetResult": "2.00",
                    "RebateAmount": "1.00",
                    "Qty": "2",
                }
                csv_text = ",".join(headers) + "\n" + ",".join(
                    values[column] for column in headers
                ) + "\n"
                onboarding, state = onboard_sales(root, csv_text, mappings=mappings)

                states = operation_states(onboarding.capabilities(state["dataset_id"]))

                self.assertEqual(states[blocked_operation], "BLOCKED")
                self.assertEqual(states["SALES_SUMMARY"], "SUPPORTED")
                self.assertTrue(any(
                    state == "SUPPORTED" for state in states.values()
                ))

    def test_optional_revocation_recovery_and_sales_anchor_revocation_are_current(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            onboarding, state = onboard_sales(root, PRIMARY_CSV, mappings=MAPPINGS)
            dataset_id = state["dataset_id"]
            baseline = operation_states(onboarding.capabilities(dataset_id))
            optional = (
                ("Nation", "COUNTRY", "SALES_BY_COUNTRY"),
                ("BusinessUnit", "SEGMENT", "SALES_BY_SEGMENT"),
                ("Item", "PRODUCT", "SALES_BY_PRODUCT"),
                ("NetResult", "PROFIT", "PROFIT_SUMMARY"),
                ("RebateAmount", "DISCOUNT", "DISCOUNT_ANALYSIS"),
                ("Qty", "UNITS_SOLD", "UNITS_SOLD_SUMMARY"),
            )
            for column, role, operation in optional:
                with self.subTest(operation=operation):
                    OnboardingManager(root / "onboarding").reject(
                        dataset_id, column, evidence=f"Revoke {role}",
                    )
                    revoked = operation_states(
                        OnboardingManager(root / "onboarding").capabilities(dataset_id)
                    )
                    self.assertEqual(
                        {key for key in OPERATIONS if revoked[key] != baseline[key]},
                        {operation},
                    )
                    OnboardingManager(root / "onboarding").confirm(
                        dataset_id, column, role, evidence=f"Restore {role}",
                    )
                    self.assertEqual(
                        operation_states(
                            OnboardingManager(root / "onboarding").capabilities(dataset_id)
                        ),
                        baseline,
                    )

            OnboardingManager(root / "onboarding").reject(
                dataset_id, "Revenue", evidence="Revoke SALES anchor",
            )
            blocked = OnboardingManager(root / "onboarding").capabilities(dataset_id)
            self.assertEqual(set(operation_states(blocked).values()), {"BLOCKED"})
            restored = OnboardingManager(root / "onboarding").confirm(
                dataset_id, "Revenue", "SALES", evidence="Restore SALES anchor",
            )
            self.assertEqual(restored["lifecycle_state"], "READY")
            self.assertEqual(
                operation_states(
                    OnboardingManager(root / "onboarding").capabilities(dataset_id)
                ),
                baseline,
            )

    def test_invalid_nonmissing_date_fails_closed_before_readiness(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = write_csv(
                root / "invalid-date.csv",
                "TxnDate,Revenue\nnot-a-date,10.00\n",
            )
            onboarding = OnboardingManager(root / "onboarding")
            dataset_id = onboarding.add(source)["dataset_id"]
            onboarding.confirm(
                dataset_id, "TxnDate", "TRANSACTION_DATE", evidence="Date approved",
            )
            onboarding.confirm(
                dataset_id, "Revenue", "SALES", evidence="Sales approved",
            )

            with self.assertRaises(OnboardingError) as caught:
                onboarding.confirm_domain(
                    dataset_id, "SALES_RECORD", evidence="Domain approved",
                )

            self.assertEqual(caught.exception.code, "canonical_parse_failure")
            self.assertEqual(
                onboarding.status(dataset_id)["lifecycle_state"],
                "NEEDS_CONFIRMATION",
            )


if __name__ == "__main__":
    unittest.main()
