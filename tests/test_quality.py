"""Query relevance, evidence scopes and incomplete-result behavior."""

import unittest
from unittest.mock import patch

from src.financial import FinancialCore
from src.financial.core import calculate
from src.financial.filters import normalize
from src.financial.quality import coverage


def payload(name, **options):
    dataset = "receiver_general" if name.startswith("receiver_general_") else "company_financials"
    return {"query_name": name, "dataset": dataset, "contract_version": "1.0", **options}


class QualityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core = FinancialCore()

    def query(self, name, **options):
        return self.core.query(payload(name, **options))

    @staticmethod
    def warnings(response):
        return {(w["code"], w["field"]): w for w in response["quality"]["warnings"]}

    def test_complete_result_with_informational_uncertainty(self):
        response = self.query("receiver_general_amount_summary")
        self.assertEqual(response["status"], "SUCCESS")
        warnings = self.warnings(response)
        for key in [("currency_unknown", "currency"), ("source_semantics_unresolved", "provenance"),
                    ("source_semantics_unresolved", "record_granularity")]:
            self.assertIn(key, warnings)
            self.assertIsNone(warnings[key]["affected_records"])
        self.assertEqual(response["errors"], [])

    def test_unrelated_missing_department_is_available_but_not_a_warning(self):
        response = self.query("receiver_general_record_count")
        self.assertEqual(response["status"], "SUCCESS")
        self.assertNotIn(("source_missing", "department_number"), self.warnings(response))
        flag = next(f for f in response["quality"]["flags"] if f["field"] == "department_number")
        self.assertEqual(flag["flag_count"], 26)
        self.assertFalse(flag["relevant"])

    def test_partial_dimension_even_when_bucket_retains_all_amounts(self):
        response = self.query("receiver_general_amount_by_department")
        self.assertEqual(response["status"], "PARTIAL")
        self.assertEqual(response["records"]["excluded"], 0)
        self.assertEqual(self.warnings(response)[("source_missing", "department_number")]["affected_records"], 26)

    def test_placeholder_counts_are_filtered_not_historical_constants(self):
        response = self.query("company_financials_discount_analysis", filters={"discount_band": {"eq": "Low"}})
        self.assertEqual(response["result"]["unresolved_placeholder_count"], 0)
        self.assertEqual(response["status"], "SUCCESS")
        self.assertNotIn(("unresolved_placeholder", "discounts"), self.warnings(response))

    def test_profit_missingness_is_separate_from_discounts(self):
        response = self.query("company_financials_profit_summary")
        warnings = self.warnings(response)
        self.assertEqual(warnings[("unresolved_placeholder", "profit")]["affected_records"], 5)
        self.assertNotIn(("unresolved_placeholder", "discounts"), warnings)
        self.assertIn(("source_semantics_unresolved", "profit"), warnings)

    def test_unknown_currency_relevant_only_to_money(self):
        for name, monetary in [("company_financials_sales_summary", True),
                               ("company_financials_record_count", False),
                               ("company_financials_units_sold_summary", False)]:
            with self.subTest(name=name):
                response = self.query(name)
                self.assertEqual(("currency_unknown", "currency") in self.warnings(response), monetary)
                flag = next(f for f in response["quality"]["flags"] if f["flag"] == "currency_unknown")
                self.assertEqual(flag["relevant"], monetary)

    def test_fiscal_uncertainty_follows_approved_step09_scope(self):
        key = ("fiscal_alignment_unresolved", "fiscal_period")
        plain = self.query("receiver_general_record_count")
        fiscal = self.query("receiver_general_record_count", filters={"fiscal_month": {"eq": 1}})
        chronological = self.query("receiver_general_amount_by_period")
        self.assertNotIn(key, self.warnings(plain))
        self.assertIn(key, self.warnings(fiscal))
        self.assertIn(key, self.warnings(chronological))
        self.assertEqual(fiscal["status"], "SUCCESS")

    def test_no_nonexistent_parser_or_key_conflict_warning(self):
        response = self.query("company_financials_sales_summary", measures=["sales", "profit", "discounts"])
        codes = {w["code"] for w in response["quality"]["warnings"]}
        self.assertTrue(codes.isdisjoint({"parsing_failed", "key_conflict", "provenance_unresolved", "semantic_unresolved"}))

    def test_full_flags_keep_provenance_tokens_order_and_relevance(self):
        response = self.query("company_financials_discount_analysis", quality_detail="full")
        flags = response["quality"]["flags"]
        self.assertEqual([f["flag_row_number"] for f in flags], sorted(f["flag_row_number"] for f in flags))
        placeholder = next(f for f in flags if f["flag"] == "unresolved_placeholder" and f["field"] == "discounts")
        self.assertEqual(placeholder["raw_value"].strip(), "$-")
        self.assertTrue(placeholder["record_id"])
        self.assertTrue(placeholder["source_sha256"])
        self.assertTrue(placeholder["relevant"])
        provenance = next(f for f in flags if f["field"] == "provenance")
        self.assertEqual(provenance["flag"], "source_semantics_unresolved")
        self.assertIsNone(provenance["record_id"])

    def test_warning_detail_does_not_change_calculations(self):
        summary = self.query("company_financials_discount_analysis")
        full = self.query("company_financials_discount_analysis", quality_detail="full")
        for field in ("result", "records", "currency", "status"):
            self.assertEqual(summary[field], full[field])
        self.assertEqual(summary["quality"]["warnings"], full["quality"]["warnings"])
        self.assertEqual(sum(f["flag_count"] for f in summary["quality"]["flags"]), len(full["quality"]["flags"]))

    def test_dataset_flags_are_not_multiplied_by_source_rows(self):
        response = self.query("receiver_general_amount_by_department")
        dataset_flags = [f for f in response["quality"]["flags"] if f["scope"] == "dataset"]
        self.assertTrue(dataset_flags)
        self.assertTrue(all(f["flag_count"] == 1 and f["affected_records"] is None for f in dataset_flags))

    def test_excluded_dimension_only_population_has_distinct_no_data_reason(self):
        response = self.query("receiver_general_amount_by_department", filters={"department": {"nulls": "only"}}, missing_dimension="exclude")
        self.assertEqual(response["status"], "NO_DATA")
        self.assertEqual(response["metadata"]["no_data_reason"], "no_group_eligible_records")
        self.assertEqual(response["records"]["candidates"], 26)
        self.assertEqual(response["result"]["groups"], [])

    def test_all_null_measure_group_remains_in_response(self):
        response = self.query("company_financials_discount_analysis", filters={"discount_band": {"eq": "None"}}, group_by="discount_band")
        self.assertEqual(response["status"], "NO_DATA")
        self.assertEqual(len(response["result"]["groups"]), 1)
        self.assertIsNone(response["result"]["groups"][0]["measures"]["discounts"]["sum"])

    def test_requested_period_beyond_extract_is_partial_not_zero_filled(self):
        response = self.query("company_financials_sales_by_period", period={"year": 2013})
        self.assertEqual(response["status"], "PARTIAL")
        self.assertIn(("period_coverage_limited", "period"), self.warnings(response))
        self.assertEqual(len(response["result"]["groups"]), 4)
        self.assertEqual(response["metadata"]["observed_period"]["start_date"], "2013-09-01")

    def test_extreme_context_warnings_only_for_returned_items(self):
        response = self.query("receiver_general_extreme_amount_records", limit=1)
        item = response["result"]["items"][0]
        fields = {"department": "department_number", "voucher_type": "journal_voucher_type_code"}
        warnings = self.warnings(response)
        for public, physical in fields.items():
            self.assertEqual(("source_missing", physical) in warnings, item[public] is None)
        self.assertEqual(response["records"]["used"], 9282)
        self.assertTrue(any(not f["relevant"] for f in response["quality"]["flags"] if f["scope"] != "dataset"))

    def test_precision_failure_is_a_blocker_without_partial_money(self):
        original = self.core._snapshot.read
        def fixture(connection, normalized):
            rows, flags, metadata, fields = original(connection, normalized)
            rows = rows[:1]
            rows[0]["journal_voucher_item_amount"] = "9" * 60 + ".0"
            return rows, flags, metadata, fields
        with patch.object(self.core._snapshot, "read", side_effect=fixture):
            response = self.query("receiver_general_amount_summary")
        self.assertEqual(response["status"], "DATA_QUALITY_BLOCKER")
        self.assertEqual(response["errors"][0]["code"], "exact_arithmetic_limit")
        self.assertIsNone(response["result"])
        self.assertEqual(response["quality"]["warnings"], [])


class CoverageFixtureTests(unittest.TestCase):
    def test_dimension_exclusion_precedes_measure_missingness(self):
        normalized = normalize(payload("company_financials_sales_by_country", measures=["discounts"], missing_dimension="exclude"))
        rows = [{"country": None, "country_status": "source_missing", "discounts": None,
                 "discounts_status": "unresolved_placeholder"}]
        records = {"candidates": 1}
        result, coverages, _, _, _ = calculate(rows, normalized, records)
        self.assertEqual(records["excluded"], 1)
        self.assertEqual(coverages["discounts"]["exclusion_reasons"], {"dimension:country:source_missing": 1})
        self.assertEqual(result["groups"], [])

    def test_multiple_missing_measures_exclude_row_only_once(self):
        normalized = normalize(payload("company_financials_sales_summary", measures=["profit", "discounts"]))
        rows = [{"profit": None, "profit_status": "unresolved_placeholder",
                 "discounts": None, "discounts_status": "unresolved_placeholder"},
                {"profit": "-1.00", "profit_status": "parsed",
                 "discounts": None, "discounts_status": "unresolved_placeholder"}]
        records = {"candidates": 2}
        _, coverages, _, _, _ = calculate(rows, normalized, records)
        self.assertEqual(records["exclusion_reasons"], {"no_requested_measure_available": 1})
        self.assertEqual(records["used"], 1)
        self.assertEqual((coverages["profit"]["used"], coverages["discounts"]["used"]), (1, 0))

    def test_nonreconciling_internal_counts_raise(self):
        with self.assertRaisesRegex(ValueError, "reconcile"):
            coverage(2, 1, [])


if __name__ == "__main__":
    unittest.main()
