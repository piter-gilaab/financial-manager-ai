import tempfile
import unittest
from pathlib import Path

from src.execution import (
    BindingOutcome,
    DynamicQueryBinder,
    DynamicQueryParameters,
    DynamicQueryRequest,
    dynamic_operation_bindings,
)
from src.financial import FinancialCore
from src.onboarding import OnboardingManager
from src.onboarding.models import OnboardingError

from tests.execution_support import onboard_sales
from tests.onboarding_support import write_csv


ROOT = Path(__file__).resolve().parents[1]


class DynamicSalesDimensionTests(unittest.TestCase):
    def test_sales_by_period_groups_confirmed_transaction_dates_by_month_exactly(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                "date,sales\n"
                "2026-02-01,1.00\n"
                "2026-01-31,0.1\n"
                "2026-01-01,0.2\n",
            )

            response = DynamicQueryBinder(root / "onboarding").execute(
                DynamicQueryRequest(
                    dataset_id=state["dataset_id"],
                    operation="SALES_BY_PERIOD",
                )
            )

            self.assertEqual(response["status"], "SUCCESS")
            self.assertEqual(
                [
                    (group["key"], group["measures"]["sales"]["sum"])
                    for group in response["result"]["groups"]
                ],
                [
                    ({"value": "2026-01", "kind": "source_value"}, "0.3"),
                    ({"value": "2026-02", "kind": "source_value"}, "1.00"),
                ],
            )
            self.assertEqual(response["currency"]["status"], "UNKNOWN")
            self.assertEqual(response["result"]["dimension_coverage"]["policy"], "bucket")
            self.assertTrue(all(
                group["canonical_record_ids"]
                for group in response["result"]["groups"]
            ))

    def test_sales_by_segment_groups_exact_source_labels(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                "date,business unit,sales\n"
                "2026-01-01,Government,10.10\n"
                "2026-01-02,Enterprise,20.20\n"
                "2026-01-03,Government,-1.00\n",
                mappings={
                    "date": "TRANSACTION_DATE",
                    "business unit": "SEGMENT",
                    "sales": "SALES",
                },
            )

            response = DynamicQueryBinder(root / "onboarding").execute(
                DynamicQueryRequest(
                    dataset_id=state["dataset_id"],
                    operation="SALES_BY_SEGMENT",
                )
            )

            self.assertEqual(response["status"], "SUCCESS")
            self.assertEqual(
                [
                    (group["key"]["value"], group["measures"]["sales"]["sum"])
                    for group in response["result"]["groups"]
                ],
                [("Enterprise", "20.20"), ("Government", "9.10")],
            )

    def test_sales_by_product_preserves_case_and_malicious_values_as_data(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                "date,item,sales\n"
                "2026-01-01,Product A,1.00\n"
                "2026-01-02,product a,2.00\n"
                "2026-01-03,__import__('os'),3.00\n"
                "2026-01-04,DROP TABLE sales; --,4.00\n",
                mappings={
                    "date": "TRANSACTION_DATE",
                    "item": "PRODUCT",
                    "sales": "SALES",
                },
            )

            response = DynamicQueryBinder(root / "onboarding").execute(
                DynamicQueryRequest(
                    dataset_id=state["dataset_id"],
                    operation="SALES_BY_PRODUCT",
                )
            )

            self.assertEqual(response["status"], "SUCCESS")
            self.assertEqual(
                [group["key"]["value"] for group in response["result"]["groups"]],
                ["DROP TABLE sales; --", "Product A", "__import__('os')", "product a"],
            )

    def test_sales_by_period_accounts_for_missing_dates(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                "when,sales\n"
                "2026-01-01,10.00\n"
                ",20.00\n",
                mappings={"when": "TRANSACTION_DATE", "sales": "SALES"},
            )

            response = DynamicQueryBinder(root / "onboarding").execute(
                DynamicQueryRequest(
                    dataset_id=state["dataset_id"],
                    operation="SALES_BY_PERIOD",
                )
            )

            self.assertEqual(response["status"], "PARTIAL")
            self.assertEqual(response["result"]["dimension_coverage"], {
                "candidates": 2,
                "available": 1,
                "unavailable": 1,
                "unavailable_by_status": {"source_missing": 1},
                "percentage": "50.000000",
                "policy": "bucket",
            })
            unavailable = response["result"]["groups"][-1]
            self.assertEqual(unavailable["key"], {"value": None, "kind": "unavailable"})
            self.assertEqual(unavailable["measures"]["sales"]["sum"], "20.00")
            self.assertEqual(
                {warning["code"] for warning in response["quality"]["warnings"]},
                {"currency_unknown", "source_missing"},
            )

    def test_sales_by_period_buckets_approved_nonempty_missing_date_marker(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                "date,sales\n"
                "2026-01-01,10.00\n"
                "N/A,20.00\n",
            )

            response = DynamicQueryBinder(root / "onboarding").execute(
                DynamicQueryRequest(state["dataset_id"], "SALES_BY_PERIOD")
            )

            self.assertEqual(response["status"], "PARTIAL")
            self.assertEqual(response["result"]["dimension_coverage"], {
                "candidates": 2,
                "available": 1,
                "unavailable": 1,
                "unavailable_by_status": {"source_missing": 1},
                "percentage": "50.000000",
                "policy": "bucket",
            })
            self.assertEqual(
                response["result"]["groups"][-1]["key"],
                {"value": None, "kind": "unavailable"},
            )

    def test_renamed_date_supports_year_granularity_and_confirmed_currency(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                "sale happened,total,currency code\n"
                "2025-12-31,1.00,USD\n"
                "2026-01-01,2.00,USD\n",
                mappings={
                    "sale happened": "TRANSACTION_DATE",
                    "total": "SALES",
                    "currency code": "CURRENCY",
                },
                currency_values={"USD": "USD"},
            )

            response = DynamicQueryBinder(root / "onboarding").execute(
                DynamicQueryRequest(
                    dataset_id=state["dataset_id"],
                    operation="SALES_BY_PERIOD",
                    parameters=DynamicQueryParameters(granularity="YEAR"),
                )
            )

            self.assertEqual(response["status"], "SUCCESS")
            self.assertEqual(
                [group["key"]["value"] for group in response["result"]["groups"]],
                ["2025", "2026"],
            )
            self.assertEqual(response["currency"]["status"], "CONFIRMED")
            self.assertEqual(response["currency"]["code"], "USD")

    def test_ambiguous_date_requires_format_confirmation_before_registration(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = write_csv(
                root / "sales.csv",
                "date,sales\n01/02/2026,10.00\n02/03/2026,20.00\n",
            )
            manager = OnboardingManager(root / "onboarding")
            state = manager.add(source)

            with self.assertRaises(OnboardingError) as caught:
                manager.confirm(
                    state["dataset_id"], "date", "TRANSACTION_DATE",
                    evidence="Date meaning approved without an approved locale",
                )

            self.assertEqual(caught.exception.code, "date_format_required")

    def test_grouped_dimensions_bucket_exclude_and_reject_invalid_policy(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                "date,segment,product,sales\n"
                "2026-01-01,Government,Product A,10.00\n"
                "2026-01-02,,,20.00\n",
                mappings={
                    "date": "TRANSACTION_DATE",
                    "segment": "SEGMENT",
                    "product": "PRODUCT",
                    "sales": "SALES",
                },
            )
            binder = DynamicQueryBinder(root / "onboarding")

            bucket = binder.execute(DynamicQueryRequest(
                state["dataset_id"], "SALES_BY_SEGMENT",
            ))
            excluded = binder.execute(DynamicQueryRequest(
                state["dataset_id"], "SALES_BY_PRODUCT",
                DynamicQueryParameters(missing_dimension="EXCLUDE"),
            ))
            invalid = binder.bind(DynamicQueryRequest(
                state["dataset_id"], "SALES_BY_PRODUCT",
                DynamicQueryParameters(missing_dimension="DROP TABLE products"),
            ))

            self.assertEqual(bucket["result"]["groups"][-1]["key"]["kind"], "unavailable")
            self.assertEqual(bucket["result"]["groups"][-1]["measures"]["sales"]["sum"], "20.00")
            self.assertEqual(excluded["records"]["exclusion_reasons"], {
                "dimension:product:source_missing": 1,
            })
            self.assertEqual(invalid.outcome, BindingOutcome.INVALID_PARAMETER)

    def test_each_grouping_requires_only_its_confirmed_roles(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                "date,product,sales\n2026-01-01,Product A,10.00\n",
                mappings={
                    "date": "TRANSACTION_DATE",
                    "product": "PRODUCT",
                    "sales": "SALES",
                },
            )
            binder = DynamicQueryBinder(root / "onboarding")

            product = binder.bind(DynamicQueryRequest(
                state["dataset_id"], "SALES_BY_PRODUCT",
            ))
            segment = binder.bind(DynamicQueryRequest(
                state["dataset_id"], "SALES_BY_SEGMENT",
            ))

            self.assertEqual(product.outcome, BindingOutcome.BOUND)
            self.assertEqual(segment.outcome, BindingOutcome.MISSING_REQUIRED_SEMANTICS)

    def test_grouped_sales_excludes_missing_measure_and_preserves_negative_values(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                "date,product,sales\n"
                "2026-01-01,P,10.00\n"
                "2026-01-02,P,\n"
                "2026-01-03,Q,-5.00\n",
                mappings={
                    "date": "TRANSACTION_DATE",
                    "product": "PRODUCT",
                    "sales": "SALES",
                },
            )

            response = DynamicQueryBinder(root / "onboarding").execute(
                DynamicQueryRequest(state["dataset_id"], "SALES_BY_PRODUCT")
            )

            self.assertEqual(response["status"], "PARTIAL")
            self.assertEqual(
                [group["measures"]["sales"]["sum"] for group in response["result"]["groups"]],
                ["10.00", "-5.00"],
            )
            self.assertEqual(response["records"]["exclusion_reasons"], {
                "measure:sales:source_missing": 1,
            })

    def test_grouped_sales_parse_failure_is_not_also_reported_as_source_missing(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                "date,product,sales\n"
                "2026-01-01,P,10.00\n"
                "2026-01-02,P,-\n",
                mappings={
                    "date": "TRANSACTION_DATE",
                    "product": "PRODUCT",
                    "sales": "SALES",
                },
            )

            response = DynamicQueryBinder(root / "onboarding").execute(
                DynamicQueryRequest(state["dataset_id"], "SALES_BY_PRODUCT")
            )

            warnings = {
                (item["code"], item["field"], item["affected_records"])
                for item in response["quality"]["warnings"]
            }
            self.assertEqual(response["status"], "PARTIAL")
            self.assertEqual(response["records"]["exclusion_reasons"], {
                "measure:sales:parsing_failed": 1,
            })
            self.assertIn(("parsing_failed", "sales", 1), warnings)
            self.assertNotIn(("source_missing", "sales", 1), warnings)

    def test_arbitrary_dimension_is_not_in_the_closed_binding_catalog(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                "date,sales\n2026-01-01,10.00\n",
            )

            result = DynamicQueryBinder(root / "onboarding").bind(
                DynamicQueryRequest(state["dataset_id"], "SALES_BY_REGION")
            )

            self.assertEqual(result.outcome, BindingOutcome.UNSUPPORTED_OPERATION)
            self.assertNotIn(
                "SALES_BY_REGION",
                {item.operation.value for item in dynamic_operation_bindings("SALES_RECORD")},
            )

    def test_step59_readiness_exposes_the_closed_nine_operation_catalog(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manager, state = onboard_sales(
                root,
                "date,segment,product,sales\n2026-01-01,A,P,10.00\n",
                mappings={
                    "date": "TRANSACTION_DATE",
                    "segment": "SEGMENT",
                    "product": "PRODUCT",
                    "sales": "SALES",
                },
            )

            financial = next(
                item for item in manager.capabilities(state["dataset_id"])["capabilities"]
                if item["identifier"] == "FINANCIAL_ANALYSIS"
            )

            self.assertEqual(
                [item["identifier"] for item in financial["operations"]],
                [
                    "SALES_RECORD_COUNT",
                    "SALES_SUMMARY",
                    "SALES_BY_COUNTRY",
                    "SALES_BY_PERIOD",
                    "SALES_BY_SEGMENT",
                    "SALES_BY_PRODUCT",
                    "PROFIT_SUMMARY",
                    "DISCOUNT_ANALYSIS",
                    "UNITS_SOLD_SUMMARY",
                ],
            )

    def test_legacy_cf03_cf05_cf06_results_remain_unchanged(self):
        core = FinancialCore(ROOT)

        period = core._named("company_financials_sales_by_period", {})
        segment = core._named("company_financials_sales_by_segment", {})
        product = core._named("company_financials_sales_by_product", {})

        self.assertEqual(period["status"], "SUCCESS")
        self.assertEqual(len(period["result"]["groups"]), 16)
        self.assertEqual(segment["status"], "SUCCESS")
        self.assertEqual(product["status"], "SUCCESS")
        self.assertEqual(
            sum(group["record_count"] for group in product["result"]["groups"]),
            700,
        )


if __name__ == "__main__":
    unittest.main()
