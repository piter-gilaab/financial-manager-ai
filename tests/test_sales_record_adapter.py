import tempfile
import unittest
from pathlib import Path

from src.execution import (
    AdapterExecutionRequest,
    AdapterOutcome,
    MissingDimensionPolicy,
    SalesRecordOperation,
    adapter_for,
)
from src.financial.core import calculate
from src.financial.filters import normalize

from tests.execution_support import onboard_sales


class SalesRecordAdapterTests(unittest.TestCase):
    def test_registered_sales_record_count_executes_through_static_adapter(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                "date,country,sales\n2026-01-01,Brazil,10.10\n2026-01-02,Chile,20.20\n",
            )

            adapter = adapter_for("SALES_RECORD", root / "onboarding")
            response = adapter.execute(AdapterExecutionRequest(
                dataset_id=state["dataset_id"],
                operation=SalesRecordOperation.SALES_RECORD_COUNT,
            ))

            self.assertEqual(response["status"], "SUCCESS")
            self.assertEqual(response["result"], {"record_count": 2})
            self.assertIsNone(response["currency"])
            self.assertEqual(response["records"]["population"], 2)
            self.assertEqual(response["records"]["used"], 2)
            self.assertEqual(len(response["metadata"]["lineage"]["records"]), 2)
            self.assertTrue(all(
                item["participation"] == "USED"
                for item in response["metadata"]["lineage"]["records"]
            ))

    def test_sales_summary_uses_exact_arithmetic_and_accounts_for_missing_values(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                "date,country,sales\n"
                "2026-01-01,Brazil,0.1\n"
                "2026-01-02,Brazil,0.2\n"
                "2026-01-03,Chile,\n"
                "2026-01-04,Chile,-1.25\n",
            )

            response = adapter_for("SALES_RECORD", root / "onboarding").execute(
                AdapterExecutionRequest(
                    dataset_id=state["dataset_id"],
                    operation=SalesRecordOperation.SALES_SUMMARY,
                )
            )

            self.assertEqual(response["status"], "PARTIAL")
            sales = response["result"]["measures"]["sales"]
            self.assertEqual((sales["count"], sales["sum"]), (3, "-0.95"))
            self.assertEqual(sales["coverage"], {
                "candidates": 4,
                "used": 3,
                "excluded": 1,
                "exclusion_reasons": {"measure:sales:source_missing": 1},
                "percentage": "75.000000",
            })
            self.assertEqual(response["currency"]["status"], "UNKNOWN")
            self.assertEqual(response["records"]["used"], 3)
            self.assertEqual(response["records"]["excluded"], 1)
            self.assertEqual(response["metadata"]["arithmetic"]["decimal_precision"], 60)
            self.assertTrue(response["metadata"]["arithmetic"]["exact_operations_trap_rounding"])
            excluded = [
                item for item in response["metadata"]["lineage"]["records"]
                if item["participation"] == "EXCLUDED"
            ]
            self.assertEqual(excluded[0]["source_row_number"], 4)
            self.assertEqual(excluded[0]["exclusion_reason"], "measure:sales:source_missing")

    def test_profile_approved_na_marker_remains_missing_during_execution(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                "date,sales\n2026-01-01,10.00\n2026-01-02,N/A\n",
            )

            response = adapter_for("SALES_RECORD", root / "onboarding").execute(
                AdapterExecutionRequest(
                    dataset_id=state["dataset_id"],
                    operation=SalesRecordOperation.SALES_SUMMARY,
                )
            )

            self.assertEqual(response["status"], "PARTIAL")
            self.assertEqual(response["result"]["measures"]["sales"]["sum"], "10.00")
            self.assertEqual(response["records"]["exclusion_reasons"], {
                "measure:sales:source_missing": 1,
            })

    def test_sales_by_country_uses_confirmed_renamed_columns_and_inert_source_labels(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                "SaleDate,__class__,Revenue\n"
                "2026-01-01,Brazil,1.10\n"
                "2026-01-02,Canada' OR 1=1 --,2.20\n"
                "2026-01-03,,3.30\n",
                mappings={
                    "SaleDate": "TRANSACTION_DATE",
                    "__class__": "COUNTRY",
                    "Revenue": "SALES",
                },
            )

            response = adapter_for("SALES_RECORD", root / "onboarding").execute(
                AdapterExecutionRequest(
                    dataset_id=state["dataset_id"],
                    operation=SalesRecordOperation.SALES_BY_COUNTRY,
                )
            )

            self.assertEqual(response["status"], "PARTIAL")
            groups = response["result"]["groups"]
            self.assertEqual([group["key"] for group in groups], [
                {"value": "Brazil", "kind": "source_value"},
                {"value": "Canada' OR 1=1 --", "kind": "source_value"},
                {"value": None, "kind": "unavailable"},
            ])
            self.assertEqual(
                [group["measures"]["sales"]["sum"] for group in groups],
                ["1.10", "2.20", "3.30"],
            )
            self.assertEqual(response["result"]["dimension_coverage"]["unavailable"], 1)
            self.assertEqual(response["records"]["used"], 3)
            self.assertTrue(all(group["canonical_record_ids"] for group in groups))

    def test_confirmed_currency_is_preserved_from_approved_mapping(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                "date,sales,currency\n2026-01-01,10.00,USD\n2026-01-02,20.00,USD\n",
                mappings={
                    "date": "TRANSACTION_DATE",
                    "sales": "SALES",
                    "currency": "CURRENCY",
                },
                currency_values={"USD": "USD"},
            )

            response = adapter_for("SALES_RECORD", root / "onboarding").execute(
                AdapterExecutionRequest(
                    dataset_id=state["dataset_id"],
                    operation=SalesRecordOperation.SALES_SUMMARY,
                )
            )

            self.assertEqual(response["status"], "SUCCESS")
            self.assertEqual(response["currency"]["status"], "CONFIRMED")
            self.assertEqual(response["currency"]["code"], "USD")
            self.assertFalse(response["currency"]["conversion_applied"])
            self.assertFalse(any(
                warning["code"] == "currency_unknown"
                for warning in response["quality"]["warnings"]
            ))

    def test_multiple_confirmed_currencies_block_scalar_monetary_summary(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                "date,sales,currency\n2026-01-01,10.00,USD\n2026-01-02,20.00,BRL\n",
                mappings={
                    "date": "TRANSACTION_DATE",
                    "sales": "SALES",
                    "currency": "CURRENCY",
                },
                currency_values={"USD": "USD", "BRL": "BRL"},
            )
            adapter = adapter_for("SALES_RECORD", root / "onboarding")
            request = AdapterExecutionRequest(
                dataset_id=state["dataset_id"],
                operation=SalesRecordOperation.SALES_SUMMARY,
            )

            self.assertEqual(adapter.validate(request).outcome, AdapterOutcome.QUALITY_BLOCKER)
            response = adapter.execute(request)
            self.assertEqual(response["status"], "DATA_QUALITY_BLOCKER")
            self.assertEqual(response["errors"][0]["code"], "QUALITY_BLOCKER")
            self.assertIsNone(response["result"])

    def test_missing_country_can_be_explicitly_excluded(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                "date,country,sales\n2026-01-01,Brazil,10.00\n2026-01-02,,20.00\n",
                mappings={
                    "date": "TRANSACTION_DATE",
                    "country": "COUNTRY",
                    "sales": "SALES",
                },
            )
            response = adapter_for("SALES_RECORD", root / "onboarding").execute(
                AdapterExecutionRequest(
                    dataset_id=state["dataset_id"],
                    operation=SalesRecordOperation.SALES_BY_COUNTRY,
                    missing_dimension=MissingDimensionPolicy.EXCLUDE,
                )
            )

            self.assertEqual(response["status"], "PARTIAL")
            self.assertEqual(len(response["result"]["groups"]), 1)
            self.assertEqual(response["records"]["exclusion_reasons"], {
                "dimension:country:source_missing": 1,
            })
            self.assertEqual(response["records"]["used"], 1)

    def test_summary_matches_legacy_core_result_semantics_for_equivalent_records(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                "date,sales\n2026-01-01,10.10\n2026-01-02,20.20\n2026-01-03,-1.00\n",
            )
            adapter_result = adapter_for("SALES_RECORD", root / "onboarding").execute(
                AdapterExecutionRequest(
                    dataset_id=state["dataset_id"],
                    operation=SalesRecordOperation.SALES_SUMMARY,
                )
            )

            legacy_request = normalize({
                "contract_version": "1.0",
                "query_name": "company_financials_sales_summary",
                "dataset": "company_financials",
            })
            legacy_records = {"candidates": 3}
            legacy_result, _, _, _, _ = calculate([
                {"sales": value, "sales_status": "parsed"}
                for value in ("10.10", "20.20", "-1.00")
            ], legacy_request, legacy_records)

            self.assertEqual(
                adapter_result["result"]["measures"]["sales"],
                legacy_result["measures"]["sales"],
            )
            self.assertEqual(
                adapter_result["records"]["used"], legacy_records["used"],
            )

    def test_country_exclusion_matches_legacy_group_coverage_semantics(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                "date,country,sales\n2026-01-01,Brazil,10.00\n2026-01-02,,20.00\n",
                mappings={
                    "date": "TRANSACTION_DATE",
                    "country": "COUNTRY",
                    "sales": "SALES",
                },
            )
            adapter_result = adapter_for("SALES_RECORD", root / "onboarding").execute(
                AdapterExecutionRequest(
                    dataset_id=state["dataset_id"],
                    operation=SalesRecordOperation.SALES_BY_COUNTRY,
                    missing_dimension=MissingDimensionPolicy.EXCLUDE,
                )
            )
            legacy_request = normalize({
                "contract_version": "1.0",
                "query_name": "company_financials_sales_by_country",
                "dataset": "company_financials",
                "missing_dimension": "exclude",
            })
            legacy_records = {
                "population": 2,
                "filtered_out": 0,
                "filter_unavailable": 0,
                "candidates": 2,
                "used": 0,
                "excluded": 0,
                "exclusion_reasons": {},
                "filter_unavailable_reasons": {},
            }
            legacy_result, _, _, _, _ = calculate([
                {"country": "Brazil", "country_status": "kept",
                 "sales": "10.00", "sales_status": "parsed"},
                {"country": None, "country_status": "source_missing",
                 "sales": "20.00", "sales_status": "parsed"},
            ], legacy_request, legacy_records)

            self.assertEqual(
                adapter_result["result"]["measure_coverage"],
                legacy_result["measure_coverage"],
            )
            self.assertEqual(adapter_result["records"], legacy_records)

    def test_duplicate_row_candidates_are_disclosed_without_deletion(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                "date,sales\n2026-01-01,10.00\n2026-01-01,10.00\n",
            )

            response = adapter_for("SALES_RECORD", root / "onboarding").execute(
                AdapterExecutionRequest(
                    dataset_id=state["dataset_id"],
                    operation=SalesRecordOperation.SALES_SUMMARY,
                )
            )

            self.assertEqual(response["result"]["measures"]["sales"]["sum"], "20.00")
            warning = next(
                item for item in response["quality"]["warnings"]
                if item["code"] == "duplicate_row_candidates"
            )
            self.assertEqual(warning["affected_records"], 1)

    def test_exact_arithmetic_limit_blocks_without_partial_total(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            huge = "9" * 60 + ".0"
            _, state = onboard_sales(
                root,
                f"date,sales\n2026-01-01,{huge}\n2026-01-02,1.0\n",
            )

            response = adapter_for("SALES_RECORD", root / "onboarding").execute(
                AdapterExecutionRequest(
                    dataset_id=state["dataset_id"],
                    operation=SalesRecordOperation.SALES_SUMMARY,
                )
            )

            self.assertEqual(response["status"], "DATA_QUALITY_BLOCKER")
            self.assertIsNone(response["result"])
            self.assertEqual(response["errors"][0]["code"], "QUALITY_BLOCKER")


if __name__ == "__main__":
    unittest.main()
