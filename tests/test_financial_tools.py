"""Contract-level behavior on the pinned database and explicit numeric fixtures."""

from decimal import Decimal, localcontext
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from src.financial import FinancialCore
from src.financial import company_financials, receiver_general
from src.financial.arithmetic import percentage, rounded_ratio, statistics
from src.financial.contracts import CF, RG, CONTRACTS, DIMENSIONS
from src.financial.filters import normalize, predicates
from src.financial.models import ContractError
from src.financial.quality import select_rows


ROOT = Path(__file__).resolve().parents[1]


def request(name, **options):
    return {"contract_version": "1.0", "query_name": name,
            "dataset": CONTRACTS[name].dataset, **options}


class ArithmeticTests(unittest.TestCase):
    def test_exact_sum_scale_and_sign(self):
        self.assertEqual(statistics(["0.10", "0.20", "-0.001"], ["sum"]), {"sum": "0.299"})

    def test_empty_values_and_real_zero_differ(self):
        self.assertEqual(statistics([], ["count", "sum", "mean", "min", "max", "median"]),
                         {"count": 0, "sum": None, "mean": None, "min": None, "max": None, "median": None})
        self.assertEqual(statistics(["0.00"], ["sum"])["sum"], "0.00")

    def test_numeric_extrema_and_stable_ties(self):
        self.assertEqual(statistics(["10.0", "2.00", "10.00"], ["min", "max"]), {"min": "2.00", "max": "10.0"})

    def test_exact_medians_preserve_additional_digit(self):
        self.assertEqual(statistics(["1.00", "1.01"], ["median"])["median"], "1.005")
        self.assertEqual(statistics(["12.0", "2.00", "10.000"], ["median"])["median"], "10.000")

    def test_mean_single_rounding_half_even(self):
        self.assertEqual(statistics(["0.000000", "0.000001"], ["mean"])["mean"], "0.000000")
        self.assertEqual(statistics(["0.000001", "0.000002"], ["mean"])["mean"], "0.000002")
        self.assertEqual(rounded_ratio(-1, 3), "-0.333333")
        self.assertEqual(rounded_ratio(2500000000000000001, 10**24), "0.000003")

    def test_coverage_percentages(self):
        self.assertEqual(percentage(647, 700), "92.428571")
        self.assertIsNone(percentage(0, 0))
        self.assertEqual(percentage(0, 53), "0.000000")

    def test_exact_precision_limit_never_returns_subtotal(self):
        for values, operation in [(["9" * 60 + ".0"], "sum"), (["9" * 60 + ".0", "9" * 60 + ".0"], "median")]:
            with self.subTest(operation=operation), self.assertRaises(ContractError) as caught:
                statistics(values, [operation])
            self.assertEqual(caught.exception.error["code"], "exact_arithmetic_limit")

    def test_independent_of_decimal_process_context(self):
        with localcontext() as ctx:
            ctx.prec = 2
            ctx.rounding = "ROUND_DOWN"
            self.assertEqual(statistics(["100.00", "0.03"], ["sum", "mean"]),
                             {"sum": "100.03", "mean": "50.015000"})

    def test_rejects_noncanonical_or_float_authority(self):
        for token in [0.1, "1e3", "NaN", "Infinity", "01.00", "$1.00", "1"]:
            with self.subTest(token=token), self.assertRaises(ContractError):
                statistics([token], ["sum"])


class FinancialToolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core = FinancialCore(ROOT)
        cls.database_hash = hashlib.sha256((ROOT / "data/database/financial_manager.db").read_bytes()).hexdigest()

    def query(self, name, **options):
        return self.core.query(request(name, **options))

    def assert_accounting(self, response):
        r = response["records"]
        self.assertEqual(r["population"], r["filtered_out"] + r["filter_unavailable"] + r["candidates"])
        self.assertEqual(r["candidates"], r["used"] + r["excluded"])
        self.assertEqual(r["excluded"], sum(r["exclusion_reasons"].values()))
        self.assertEqual(r["filter_unavailable"], sum(r["filter_unavailable_reasons"].values()))
        for diagnostic in response["filter_diagnostics"]:
            self.assertEqual(sum(diagnostic[k] for k in ("matched", "nonmatching", "unavailable")), r["population"])
        def check(value):
            self.assertNotIsInstance(value, (float, Decimal))
            if isinstance(value, dict):
                if "coverage" in value:
                    cov = value["coverage"]
                    self.assertEqual(cov["candidates"], cov["used"] + cov["excluded"])
                    self.assertEqual(cov["excluded"], sum(cov["exclusion_reasons"].values()))
                for v in value.values(): check(v)
            elif isinstance(value, list):
                for v in value: check(v)
        check(response)
        json.dumps(response, allow_nan=False)

    def test_all_seventeen_named_contracts_and_envelopes(self):
        self.assertEqual(len(CONTRACTS), 17)
        for name, spec in CONTRACTS.items():
            with self.subTest(contract=name):
                module = receiver_general if spec.dataset == RG else company_financials
                options = {"group_by": "general_ledger_account"} if "accounting_dimension" in name else {}
                response = getattr(module, name)(self.core, **options)
                self.assertIn(response["status"], ("SUCCESS", "PARTIAL"))
                self.assertEqual(response["errors"], [])
                self.assertEqual(response["query_name"], name)
                self.assertEqual(len(response["metadata"]["snapshot"]), 7)
                self.assert_accounting(response)

    def test_record_counts_do_not_count_summary_lines(self):
        self.assertEqual(self.query("receiver_general_record_count")["result"], {"record_count": 9282})
        self.assertEqual(self.query("company_financials_record_count")["result"], {"record_count": 700})

    def test_rg_amount_exact_baseline(self):
        response = self.query("receiver_general_amount_summary", statistics=["count", "sum", "mean", "median", "min", "max"])
        amount = response["result"]["measures"]["accounting_amount"]
        self.assertEqual(amount["sum"], "3061288992129.16")
        self.assertEqual((amount["min"], amount["max"]), ("0.00", "39555794411.27"))
        self.assertEqual(amount["count"], 9282)
        self.assertEqual(response["currency"]["status"], "UNKNOWN")

    def test_direction_totals_preserve_codes_and_source_signs(self):
        response = self.query("receiver_general_amount_by_debit_credit")
        groups = {g["key"]["value"]: g["measures"]["accounting_amount"]["sum"] for g in response["result"]["groups"]}
        self.assertEqual(groups, {"CR": "51882502310.23", "DR": "3009406489818.93"})

    def test_sparse_dimensions_bucket_and_exclude(self):
        cases = [("receiver_general_amount_by_department", {}, 26),
                 ("receiver_general_amount_by_voucher_type", {}, 26)]
        cases += [("receiver_general_accounting_dimension_summary", {"group_by": d}, missing)
                  for d, missing in zip(DIMENSIONS, (9091, 2186, 9000, 178))]
        for name, options, missing in cases:
            with self.subTest(name=name, options=options):
                bucket = self.query(name, **options)
                excluded = self.query(name, missing_dimension="exclude", **options)
                self.assertEqual(bucket["result"]["dimension_coverage"]["unavailable"], missing)
                self.assertEqual(bucket["records"]["used"], 9282)
                self.assertEqual(excluded["records"]["excluded"], missing)
                self.assertEqual(bucket["result"]["groups"][-1]["key"], {"value": None, "kind": "unavailable"})
                self.assert_accounting(bucket)
                self.assert_accounting(excluded)

    def test_may_filter_recomputes_dimension_coverage(self):
        response = self.query("receiver_general_amount_by_department", period={"year": 2023, "month": 5})
        self.assertEqual(response["records"]["candidates"], 1063)
        self.assertEqual(response["result"]["dimension_coverage"]["unavailable"], 0)
        self.assertEqual(response["status"], "SUCCESS")

    def test_fiscal_and_calendar_filters_intersect_without_mapping(self):
        response = self.query("receiver_general_record_count", period={"year": 2023, "month": 5},
                              filters={"fiscal_year": {"eq": "2022/2023"}})
        self.assertEqual(response["status"], "SUCCESS")
        self.assertEqual(response["result"]["record_count"], 3)
        self.assertEqual(response["metadata"]["period"]["start_date"], "2023-05-01")

    def test_calendar_period_granularities(self):
        for granularity, length in [("day", 10), ("month", 7), ("year", 4)]:
            response = self.query("receiver_general_amount_by_period", granularity=granularity)
            self.assertTrue(all(len(g["key"]["value"]) == length for g in response["result"]["groups"]))
        monthly = self.query("company_financials_sales_by_period")
        self.assertEqual(len(monthly["result"]["groups"]), 16)
        annual = self.query("company_financials_sales_by_period", granularity="year")
        self.assertEqual([g["key"]["value"] for g in annual["result"]["groups"]], ["2013", "2014"])

    def test_sales_measure_totals_and_independent_coverage(self):
        response = self.query("company_financials_sales_summary", measures=["gross_sales", "discounts", "sales", "cogs", "profit"])
        metrics = response["result"]["measures"]
        self.assertEqual([metrics[m]["sum"] for m in metrics],
                         ["127931598.50", "9205248.27", "118726350.29", "101832648.00", "16893702.29"])
        self.assertEqual(metrics["discounts"]["coverage"]["used"], 647)
        self.assertEqual(metrics["profit"]["coverage"]["used"], 695)
        self.assertEqual(response["records"]["used"], 700)
        self.assertEqual(response["status"], "PARTIAL")

    def test_all_sales_groups_reconcile_to_available_totals(self):
        for suffix in ("period", "country", "segment", "product"):
            with self.subTest(group=suffix):
                response = self.query("company_financials_sales_by_" + suffix, measures=["sales", "profit", "discounts"])
                groups = response["result"]["groups"]
                for measure, total in [("sales", "118726350.29"), ("profit", "16893702.29"), ("discounts", "9205248.27")]:
                    values = [g["measures"][measure]["sum"] for g in groups if g["measures"][measure]["sum"] is not None]
                    self.assertEqual(statistics(values, ["sum"])["sum"], total)
                self.assert_accounting(response)

    def test_profit_sign_counts_and_unresolved_values(self):
        response = self.query("company_financials_profit_summary")
        result = response["result"]
        self.assertEqual((result["negative_count"], result["zero_count"], result["positive_count"]), (58, 0, 637))
        self.assertEqual(response["records"]["exclusion_reasons"], {"measure:profit:unresolved_placeholder": 5})

    def test_discount_analysis_coverage(self):
        response = self.query("company_financials_discount_analysis")
        result = response["result"]
        self.assertEqual(result["unresolved_placeholder_count"], 53)
        self.assertEqual(result["measures"]["discounts"]["coverage"]["percentage"], "92.428571")
        grouped = self.query("company_financials_discount_analysis", group_by="discount_band")
        missing = next(g for g in grouped["result"]["groups"] if g["key"]["value"] == "None")
        self.assertEqual(missing["key"]["kind"], "source_value")
        self.assertIsNone(missing["measures"]["discounts"]["sum"])
        self.assertEqual(missing["unresolved_placeholder_count"], 53)

    def test_placeholder_only_population_is_not_zero_or_no_matching_rows(self):
        filters = {"discount_band": {"eq": "None"}}
        response = self.query("company_financials_discount_analysis", filters=filters)
        self.assertEqual(response["status"], "NO_DATA")
        self.assertEqual(response["metadata"]["no_data_reason"], "no_numeric_values")
        self.assertEqual(response["records"]["candidates"], 53)
        self.assertIsNone(response["result"]["measures"]["discounts"]["sum"])
        self.assertEqual(self.query("company_financials_record_count", filters=filters)["result"]["record_count"], 53)

    def test_units_sold_not_currency(self):
        response = self.query("company_financials_units_sold_summary")
        self.assertIsNone(response["currency"])
        self.assertEqual(response["result"]["measures"]["units_sold"]["sum"], "1125806.00")
        self.assertEqual(response["result"]["measures"]["units_sold"]["unit"], "quantity")

    def test_extremes_numeric_order_limit_and_ties(self):
        high = self.query("receiver_general_extreme_amount_records", limit=2)
        self.assertEqual(high["result"]["items"][0]["accounting_amount"], "39555794411.27")
        self.assertEqual(high["records"]["not_returned"], 9280)
        low = self.query("receiver_general_extreme_amount_records", direction="lowest", limit=2)
        self.assertEqual([r["accounting_amount"] for r in low["result"]["items"]], ["0.00", "0.00"])
        self.assertLess(low["result"]["items"][0]["source_row_number"], low["result"]["items"][1]["source_row_number"])
        self.assert_accounting(high)

    def test_equality_membership_and_unknown_filter_records(self):
        response = self.query("receiver_general_record_count", filters={"department": {"eq": "037"}})
        self.assertEqual(response["records"]["filter_unavailable"], 26)
        self.assertEqual(response["status"], "PARTIAL")
        included = self.query("receiver_general_record_count", filters={"department": {"in": ["037", "037"], "nulls": "include"}})
        self.assertEqual(included["records"]["candidates"], response["records"]["candidates"] + 26)
        self.assertEqual(included["metadata"]["filters"]["department"]["in"], ["037"])
        self.assert_accounting(response)

    def test_explicit_null_selection_and_exclusion_are_known(self):
        for mode, expected in [("only", 26), ("exclude", 9256), ("include", 9282)]:
            response = self.query("receiver_general_record_count", filters={"department": {"nulls": mode}})
            self.assertEqual(response["records"]["candidates"], expected)
            self.assertEqual(response["records"]["filter_unavailable"], 0)
            self.assertEqual(response["status"], "SUCCESS")

    def test_no_matching_data_has_null_money_and_unknown_currency(self):
        response = self.query("company_financials_sales_summary", filters={"country": {"eq": "Absent"}})
        self.assertEqual(response["status"], "NO_DATA")
        self.assertEqual(response["metadata"]["no_data_reason"], "no_matching_records")
        self.assertIsNone(response["result"]["measures"]["sales"]["sum"])
        self.assertEqual(response["currency"]["status"], "UNKNOWN")

    def test_sql_injection_is_a_literal_value(self):
        response = self.query("company_financials_record_count", filters={"country": {"eq": "Canada' OR 1=1 --"}})
        self.assertEqual(response["result"]["record_count"], 0)

    def test_invalid_requests_return_structured_errors(self):
        cases = [None, [], {}, request("receiver_general_record_count", filters={"department": {"eq": 37}}),
                 request("receiver_general_record_count", sql="SELECT *"),
                 request("receiver_general_record_count", filters={"fiscal_month": {"eq": True}}),
                 request("receiver_general_record_count", filters={"department": {"eq": None}}),
                 request("receiver_general_record_count", filters={"department": {"eq": "037", "nulls": "only"}}),
                 request("receiver_general_record_count", period={"year": 2023, "month": True}),
                 request("receiver_general_record_count", period={"start_date": "2023-02-30", "end_date": "2023-03-31"}),
                 request("receiver_general_record_count", period={"month": 5}),
                 request("receiver_general_record_count", period={"year": 2023}, group_by="department"),
                 request("receiver_general_extreme_amount_records", limit=False),
                 request("receiver_general_extreme_amount_records", limit=101),
                 request("company_financials_discount_analysis", missing_dimension="exclude"),
                 request("company_financials_sales_summary", statistics=["summation"]),
                 request("company_financials_sales_summary", measures=["sales", "sales"]),
                 request("company_financials_record_count", contract_version="2.0"),
                 request("company_financials_record_count", dataset=RG)]
        for case in cases:
            with self.subTest(case=case):
                response = self.core.query(case)
                self.assertEqual(response["status"], "INVALID_REQUEST")
                self.assertTrue(response["errors"])
                self.assertIsNone(response["records"])
                self.assertIsNone(response["result"])
                json.dumps(response, allow_nan=False)

    def test_unsupported_requests_do_not_calculate_substitutes(self):
        cases = [request("company_financials_sales_by_period", granularity="day"),
                 request("company_financials_sales_summary", statistics=["share"]),
                 request("company_financials_sales_summary", statistics=["median"]),
                 request("company_financials_sales_summary", measures=["sale_price"]),
                 request("receiver_general_accounting_dimension_summary", group_by="fiscal_month"),
                 request("company_financials_record_count", period={"start_date": "2014-01-02", "end_date": "2014-01-31"})]
        for case in cases:
            with self.subTest(case=case):
                response = self.core.query(case)
                self.assertEqual(response["status"], "UNSUPPORTED")
                self.assertIsNone(response["result"])
                self.assertIsNone(response["records"])

    def test_invalid_precedes_unsupported_and_snapshot_access(self):
        with patch.object(self.core._snapshot, "open", side_effect=AssertionError("Must not read data")):
            response = self.query("company_financials_sales_by_period", granularity="day", measures=42)
        self.assertEqual(response["status"], "INVALID_REQUEST")

    def test_deterministic_response_and_input_not_mutated(self):
        payload = request("company_financials_sales_summary", filters={"country": {"in": ["France", "Canada"]}})
        before = json.dumps(payload)
        self.assertEqual(self.core.query(payload), self.core.query(payload))
        self.assertEqual(json.dumps(payload), before)

    def test_named_tools_cannot_override_identity(self):
        response = receiver_general.receiver_general_record_count(self.core, dataset=CF)
        self.assertEqual(response["status"], "INVALID_REQUEST")

    def test_readonly_connection_and_protected_database_hash(self):
        with self.core._snapshot.open() as connection:
            with self.assertRaises(sqlite3.OperationalError):
                connection.execute("DELETE FROM dataset_source")
        self.assertEqual(hashlib.sha256((ROOT / "data/database/financial_manager.db").read_bytes()).hexdigest(), self.database_hash)

    def test_tampered_snapshot_blocks_before_query(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data/database/financial_manager.db"
            path.parent.mkdir(parents=True)
            path.write_bytes(b"unapproved snapshot")
            response = FinancialCore(directory).query(request("company_financials_record_count"))
        self.assertEqual(response["status"], "DATA_QUALITY_BLOCKER")
        self.assertEqual(response["errors"][0]["code"], "snapshot_mismatch")

    def test_unexpected_internal_error_is_not_no_data(self):
        with patch("src.financial.core.calculate", side_effect=RuntimeError("unexpected")):
            with self.assertRaisesRegex(RuntimeError, "unexpected"):
                self.query("company_financials_sales_summary")


class FilterFixtureTests(unittest.TestCase):
    def test_and_false_overrides_unknown_and_unknown_reasons_are_disjoint(self):
        # Explicit test-only SQLite table; production artifacts are never modified.
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        connection.execute("CREATE TABLE fixture (department_number TEXT, journal_voucher_type_code TEXT)")
        connection.executemany("INSERT INTO fixture VALUES (?,?)", [(None, "B"), (None, None), ("037", "A")])
        normalized = normalize(request("receiver_general_record_count", filters={"department": {"eq": "037"}, "voucher_type": {"eq": "A"}}))
        expressions = predicates(normalized)
        sql = "SELECT d.*, " + ",".join(f"({s}) AS _filter_{i}" for i, (_, s, _) in enumerate(expressions)) + " FROM fixture d"
        parameters = [v for _, _, values in expressions for v in values]
        rows = [dict(r) for r in connection.execute(sql, parameters)]
        connection.close()
        for row in rows:
            row.update(department_number_status="source_missing" if row["department_number"] is None else "kept",
                       journal_voucher_type_code_status="source_missing" if row["journal_voucher_type_code"] is None else "kept")
        selected, unknown, counts, _ = select_rows(rows, [f for f, _, _ in expressions], RG)
        self.assertEqual((len(selected), len(unknown), counts["filtered_out"]), (1, 1, 1))
        self.assertEqual(counts["filter_unavailable_reasons"], {"department:source_missing": 1})


if __name__ == "__main__":
    unittest.main()
