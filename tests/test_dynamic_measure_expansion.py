import tempfile
import unittest
from pathlib import Path

from src.execution import BindingOutcome, DynamicQueryBinder, DynamicQueryRequest
from src.financial import FinancialCore
from src.onboarding.semantics import SEMANTIC_ROLE_VALUE_KINDS

from tests.execution_support import onboard_sales


ROOT = Path(__file__).resolve().parents[1]


class DynamicMeasureExpansionTests(unittest.TestCase):
    def test_profit_summary_preserves_signs_missingness_and_exact_total(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                "date,sales,recorded profit\n"
                "2026-01-01,100.00,20.00\n"
                "2026-01-02,200.00,-10.00\n"
                "2026-01-03,300.00,0.00\n"
                "2026-01-04,400.00,N/A\n",
                mappings={
                    "date": "TRANSACTION_DATE",
                    "sales": "SALES",
                    "recorded profit": "PROFIT",
                },
            )

            response = DynamicQueryBinder(root / "onboarding").execute(
                DynamicQueryRequest(state["dataset_id"], "PROFIT_SUMMARY")
            )

            self.assertEqual(response["status"], "PARTIAL")
            self.assertEqual(response["result"]["record_count"], 4)
            self.assertEqual(
                response["result"]["measures"]["profit"]["sum"],
                "10.00",
            )
            self.assertEqual(
                (
                    response["result"]["negative_count"],
                    response["result"]["zero_count"],
                    response["result"]["positive_count"],
                ),
                (1, 1, 1),
            )
            self.assertEqual(
                response["records"]["exclusion_reasons"],
                {"measure:profit:source_missing": 1},
            )
            self.assertEqual(response["currency"]["status"], "UNKNOWN")

    def test_discount_analysis_is_monetary_cf08_summary_with_coverage(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                "date,sales,discount amount\n"
                "2026-01-01,100.00,10.00\n"
                "2026-01-02,200.00,N/A\n"
                "2026-01-03,300.00,30.00\n",
                mappings={
                    "date": "TRANSACTION_DATE",
                    "sales": "SALES",
                    "discount amount": "DISCOUNT",
                },
            )

            response = DynamicQueryBinder(root / "onboarding").execute(
                DynamicQueryRequest(state["dataset_id"], "DISCOUNT_ANALYSIS")
            )

            self.assertEqual(response["status"], "PARTIAL")
            self.assertEqual(response["result"]["record_count"], 3)
            self.assertEqual(response["result"]["unavailable_value_count"], 1)
            self.assertEqual(response["result"]["measures"]["discount"], {
                "count": 2,
                "sum": "40.00",
                "mean": "20.000000",
                "min": "10.00",
                "max": "30.00",
                "unit": "monetary",
                "coverage": {
                    "candidates": 3,
                    "used": 2,
                    "excluded": 1,
                    "exclusion_reasons": {"measure:discount:source_missing": 1},
                    "percentage": "66.666667",
                },
            })
            self.assertEqual(response["currency"]["status"], "UNKNOWN")

    def test_units_sold_summary_preserves_fractional_large_exact_quantities_without_currency(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                "date,sales,quantity\n"
                "2026-01-01,10.00,1.25\n"
                "2026-01-02,20.00,999999999999999999999999999999.75\n"
                "2026-01-03,30.00,\n",
                mappings={
                    "date": "TRANSACTION_DATE",
                    "sales": "SALES",
                    "quantity": "UNITS_SOLD",
                },
            )

            response = DynamicQueryBinder(root / "onboarding").execute(
                DynamicQueryRequest(state["dataset_id"], "UNITS_SOLD_SUMMARY")
            )

            self.assertEqual(response["status"], "PARTIAL")
            self.assertIsNone(response["currency"])
            self.assertEqual(response["result"]["measures"]["units_sold"], {
                "count": 2,
                "sum": "1000000000000000000000000000001.00",
                "min": "1.25",
                "max": "999999999999999999999999999999.75",
                "unit": "quantity",
                "coverage": {
                    "candidates": 3,
                    "used": 2,
                    "excluded": 1,
                    "exclusion_reasons": {"measure:units_sold:source_missing": 1},
                    "percentage": "66.666667",
                },
            })

    def test_nonmissing_profit_placeholder_is_explicitly_excluded_not_zero(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                "date,sales,profit\n"
                "2026-01-01,10.00,5.00\n"
                "2026-01-02,20.00,-\n",
                mappings={
                    "date": "TRANSACTION_DATE",
                    "sales": "SALES",
                    "profit": "PROFIT",
                },
            )

            response = DynamicQueryBinder(root / "onboarding").execute(
                DynamicQueryRequest(state["dataset_id"], "PROFIT_SUMMARY")
            )

            self.assertEqual(response["status"], "PARTIAL")
            self.assertEqual(response["result"]["measures"]["profit"]["sum"], "5.00")
            self.assertEqual(response["result"]["zero_count"], 0)
            self.assertEqual(response["records"]["exclusion_reasons"], {
                "measure:profit:parsing_failed": 1,
            })
            self.assertIn(
                ("parsing_failed", "profit", 1),
                {
                    (item["code"], item["field"], item["affected_records"])
                    for item in response["quality"]["warnings"]
                },
            )

    def test_nonmissing_discount_placeholder_is_excluded_without_rate_inference(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                "date,sales,discount\n"
                "2026-01-01,100.00,10.00\n"
                "2026-01-02,200.00,$-\n",
                mappings={
                    "date": "TRANSACTION_DATE",
                    "sales": "SALES",
                    "discount": "DISCOUNT",
                },
            )

            response = DynamicQueryBinder(root / "onboarding").execute(
                DynamicQueryRequest(state["dataset_id"], "DISCOUNT_ANALYSIS")
            )

            self.assertEqual(response["status"], "PARTIAL")
            self.assertEqual(response["result"]["measures"]["discount"]["sum"], "10.00")
            self.assertEqual(response["result"]["unavailable_value_count"], 1)
            self.assertEqual(response["records"]["exclusion_reasons"], {
                "measure:discount:parsing_failed": 1,
            })

    def test_ambiguous_discount_rate_is_blocked_without_monetary_role_confirmation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                "date,sales,discount rate\n2026-01-01,100.00,0.10\n",
                mappings={"date": "TRANSACTION_DATE", "sales": "SALES"},
            )

            result = DynamicQueryBinder(root / "onboarding").bind(
                DynamicQueryRequest(state["dataset_id"], "DISCOUNT_ANALYSIS")
            )

            self.assertEqual(result.outcome, BindingOutcome.MISSING_REQUIRED_SEMANTICS)
            self.assertEqual(SEMANTIC_ROLE_VALUE_KINDS["DISCOUNT"], "MONETARY_AMOUNT")

    def test_confirmed_currency_is_preserved_for_profit_and_discount_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                "date,sales,profit,discount,units,currency\n"
                "2026-01-01,100.00,20.00,10.00,2.5,USD\n",
                mappings={
                    "date": "TRANSACTION_DATE",
                    "sales": "SALES",
                    "profit": "PROFIT",
                    "discount": "DISCOUNT",
                    "units": "UNITS_SOLD",
                    "currency": "CURRENCY",
                },
                currency_values={"USD": "USD"},
            )
            binder = DynamicQueryBinder(root / "onboarding")

            profit = binder.execute(DynamicQueryRequest(
                state["dataset_id"], "PROFIT_SUMMARY",
            ))
            discount = binder.execute(DynamicQueryRequest(
                state["dataset_id"], "DISCOUNT_ANALYSIS",
            ))
            units = binder.execute(DynamicQueryRequest(
                state["dataset_id"], "UNITS_SOLD_SUMMARY",
            ))

            self.assertEqual((profit["currency"]["status"], profit["currency"]["code"]),
                             ("CONFIRMED", "USD"))
            self.assertEqual((discount["currency"]["status"], discount["currency"]["code"]),
                             ("CONFIRMED", "USD"))
            self.assertIsNone(units["currency"])

    def test_each_summary_requires_only_its_own_measure_role(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                "date,sales,profit\n2026-01-01,100.00,20.00\n",
                mappings={
                    "date": "TRANSACTION_DATE",
                    "sales": "SALES",
                    "profit": "PROFIT",
                },
            )
            binder = DynamicQueryBinder(root / "onboarding")

            profit = binder.bind(DynamicQueryRequest(
                state["dataset_id"], "PROFIT_SUMMARY",
            ))
            discount = binder.bind(DynamicQueryRequest(
                state["dataset_id"], "DISCOUNT_ANALYSIS",
            ))

            self.assertEqual(profit.outcome, BindingOutcome.BOUND)
            self.assertEqual(discount.outcome, BindingOutcome.MISSING_REQUIRED_SEMANTICS)

    def test_all_missing_units_are_no_data_not_zero(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                "date,sales,units\n"
                "2026-01-01,10.00,N/A\n"
                "2026-01-02,20.00,\n",
                mappings={
                    "date": "TRANSACTION_DATE",
                    "sales": "SALES",
                    "units": "UNITS_SOLD",
                },
            )

            response = DynamicQueryBinder(root / "onboarding").execute(
                DynamicQueryRequest(state["dataset_id"], "UNITS_SOLD_SUMMARY")
            )

            self.assertEqual(response["status"], "NO_DATA")
            self.assertEqual(response["metadata"]["no_data_reason"], "no_numeric_values")
            self.assertIsNone(response["result"]["measures"]["units_sold"]["sum"])
            self.assertEqual(response["result"]["measures"]["units_sold"]["count"], 0)

    def test_arithmetic_precision_failure_returns_no_partial_authoritative_total(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            huge = "9" * 60
            _, state = onboard_sales(
                root,
                f"date,sales,profit\n2026-01-01,1.00,{huge}\n2026-01-02,2.00,{huge}\n",
                mappings={
                    "date": "TRANSACTION_DATE",
                    "sales": "SALES",
                    "profit": "PROFIT",
                },
            )

            response = DynamicQueryBinder(root / "onboarding").execute(
                DynamicQueryRequest(state["dataset_id"], "PROFIT_SUMMARY")
            )

            self.assertEqual(response["status"], "DATA_QUALITY_BLOCKER")
            self.assertIsNone(response["result"])
            self.assertEqual(response["errors"][0]["code"], "QUALITY_BLOCKER")

    def test_malicious_header_is_inert_and_arbitrary_measure_operation_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                "date,sales,__import__('os').system('echo bad')\n"
                "2026-01-01,100.00,-5.00\n",
                mappings={
                    "date": "TRANSACTION_DATE",
                    "sales": "SALES",
                    "__import__('os').system('echo bad')": "PROFIT",
                },
            )
            binder = DynamicQueryBinder(root / "onboarding")

            profit = binder.execute(DynamicQueryRequest(
                state["dataset_id"], "PROFIT_SUMMARY",
            ))
            arbitrary = binder.bind(DynamicQueryRequest(
                state["dataset_id"], "MEASURE_SUMMARY:__import__('os')",
            ))

            self.assertEqual(profit["result"]["measures"]["profit"]["sum"], "-5.00")
            self.assertEqual(arbitrary.outcome, BindingOutcome.UNSUPPORTED_OPERATION)

    def test_legacy_cf07_cf08_cf09_results_remain_unchanged(self):
        core = FinancialCore(ROOT)

        profit = core._named("company_financials_profit_summary", {})
        discount = core._named("company_financials_discount_analysis", {})
        units = core._named("company_financials_units_sold_summary", {})

        self.assertEqual(profit["result"]["measures"]["profit"]["sum"], "16893702.29")
        self.assertEqual(profit["result"]["negative_count"], 58)
        self.assertEqual(discount["result"]["unresolved_placeholder_count"], 53)
        self.assertEqual(units["result"]["measures"]["units_sold"]["sum"], "1125806.00")
        self.assertIsNone(units["currency"])

if __name__ == "__main__":
    unittest.main()
