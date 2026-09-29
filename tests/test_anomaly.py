"""Statistical screening tests; synthetic observations exist only in this file."""

from contextlib import contextmanager
from copy import deepcopy
from decimal import Decimal, localcontext
import hashlib
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

from src.anomaly import AnomalyService
from src.agents import FinancialAnalysisAgent
from src.financial.contracts import CF, RG


ROOT = Path(__file__).resolve().parents[1]


def request(dataset=RG, measure="accounting_amount", **options):
    return {"analysis_version": "1.0", "dataset": dataset, "measure": measure, **options}


def fixture_rows(values, dataset=RG, measure="accounting_amount", *, start=1, peer="A"):
    rows = []
    for position, token in enumerate(values, start):
        row = {"record_id": f"fixture-{position:04d}", "run_id": "TEST_ONLY", "source_id": dataset,
               "source_row_number": position, "processed_row_number": position}
        fields = {"journal_voucher_item_amount": token, "credit_debit_code": "DR", "journal_voucher_type_code": peer,
                  "accounting_effective_date": "2023-05-01"} if dataset == RG else {
                      measure: token, "segment": peer, "sale_price": "10.00", "period_date": "2014-05-01"}
        for name, value in fields.items():
            row[name] = value
            row[name + "_raw"] = "" if value is None else value
            row[name + "_status"] = "source_missing" if value is None else "parsed"
        rows.append(row)
    return rows


def sequence(size):
    return [f"{i}.00" for i in range(size)]


def flag(row, field, code, number=1):
    return {"flag_row_number": number, "record_id": row["record_id"], "scope": "field",
            "field": field, "flag": code, "rule_id": "TEST_ONLY", "status": row[field + "_status"],
            "reason": "Test fixture unavailable observation.", "raw_value": row[field + "_raw"]}


class FixtureSnapshot:
    def __init__(self, rows, flags):
        self.rows, self.flags = rows, flags

    @contextmanager
    def open(self):
        yield None

    def read(self, connection, normalized):
        return self.rows, self.flags, {"fixture": "TEST_ONLY"}, []


def fixture_analysis(rows, dataset=RG, measure="accounting_amount", flags=(), **options):
    service = AnomalyService()
    with patch.object(service, "_snapshot", FixtureSnapshot(rows, list(flags))):
        return service.analyze(request(dataset, measure, **options))


class BaselineFixtureTests(unittest.TestCase):
    def test_clear_upper_extreme_and_ordinary_record(self):
        r = fixture_analysis(fixture_rows(sequence(30) + ["1000.00"]))
        self.assertEqual(r["status"], "SUCCESS")
        self.assertEqual(r["result"]["items"][-1]["assessments"]["peer"]["status"], "CANDIDATE")
        self.assertEqual(r["result"]["items"][15]["assessments"]["peer"]["status"], "NOT_SELECTED")
        self.assertEqual(r["result"]["references"][0]["upper_fence"], "45.000")

    def test_exact_boundary_is_not_selected_and_fraction_above_is_candidate(self):
        for token, expected in [("45.000", "NOT_SELECTED"), ("45.0000000001", "CANDIDATE")]:
            with self.subTest(token=token):
                r = fixture_analysis(fixture_rows(sequence(30) + [token]))
                self.assertEqual(r["result"]["items"][-1]["assessments"]["global"]["status"], expected)
                self.assertEqual(r["result"]["items"][-1]["observed_value"], token)

    def test_lower_signed_profit_and_ordinary_negative_values(self):
        r = fixture_analysis(fixture_rows(["-1000.00"] + sequence(30), CF, "profit"), CF, "profit")
        assessed = r["result"]["items"][0]["assessments"]["peer"]
        self.assertEqual((assessed["status"], assessed["tail"]), ("CANDIDATE", "lower"))
        rows = fixture_rows([f"-{i}.00" for i in range(1, 31)], CF, "profit")
        r = fixture_analysis(rows, CF, "profit")
        self.assertTrue(all(i["assessments"]["peer"]["status"] == "NOT_SELECTED" for i in r["result"]["items"]))

    def test_minimum_is_thirty_available_values_not_thirty_rows(self):
        r = fixture_analysis(fixture_rows(sequence(29) + [None]))
        self.assertEqual(r["result"]["summary"]["global"]["not_assessed"], 30)
        self.assertEqual(r["result"]["references"][0]["numeric_size"], 29)
        self.assertIsNone(r["result"]["references"][0]["q1"])
        r = fixture_analysis(fixture_rows(sequence(30)))
        self.assertEqual(r["result"]["summary"]["peer"]["not_assessed"], 0)

    def test_tiny_peer_abstains_without_global_fallback(self):
        rows = fixture_rows(sequence(30)) + fixture_rows(sequence(29), start=31, peer="B")
        r = fixture_analysis(rows)
        self.assertEqual(r["result"]["summary"]["global"]["not_assessed"], 0)
        self.assertEqual(r["result"]["summary"]["peer"]["not_assessed"], 29)
        self.assertEqual(r["result"]["comparison"]["both_assessed"], 30)
        self.assertEqual(r["status"], "PARTIAL")

    def test_zero_iqr_abstains_even_with_single_large_value(self):
        r = fixture_analysis(fixture_rows(["1.00"] * 30 + ["999.00"]))
        self.assertEqual(r["result"]["summary"]["peer"]["not_assessed_reasons"], {"zero_iqr": 31})
        self.assertEqual(r["result"]["references"][0]["iqr"], "0.00")
        self.assertIsNone(r["result"]["references"][0]["upper_fence"])

    def test_unresolved_measure_remains_null_and_not_assessed(self):
        rows = fixture_rows(sequence(30) + [None], CF, "profit")
        rows[-1].update(profit_status="unresolved_placeholder", profit_raw="$-")
        r = fixture_analysis(rows, CF, "profit", [flag(rows[-1], "profit", "unresolved_placeholder")])
        item = r["result"]["items"][-1]
        self.assertIsNone(item["observed_value"])
        self.assertEqual(item["observed_raw"], "$-")
        self.assertEqual(item["assessments"]["peer"]["reason"], "measure:profit:unresolved_placeholder")
        self.assertEqual(r["records"]["excluded"], 1)
        self.assertTrue(any(r["quality"]["warnings"][i]["code"] == "unresolved_placeholder" for i in item["quality_warning_indices"]))

    def test_missing_peer_labels_are_not_a_synthetic_category(self):
        rows = fixture_rows(sequence(30) + ["1000.00"])
        rows[-1].update(journal_voucher_type_code=None, journal_voucher_type_code_status="source_missing")
        r = fixture_analysis(rows)
        item = r["result"]["items"][-1]
        self.assertEqual(item["assessments"]["global"]["status"], "CANDIDATE")
        self.assertEqual(item["assessments"]["peer"]["status"], "NOT_ASSESSED")
        self.assertIsNone(item["assessments"]["peer"]["reference_id"])
        self.assertEqual(len(r["result"]["references"]), 2)
        self.assertEqual(r["result"]["dimension_coverage"]["voucher_type"]["unavailable"], 1)

    def test_missing_sale_price_is_relevant_without_changing_core_field_catalog(self):
        rows = fixture_rows(sequence(30) + ["1000.00"], CF, "sales")
        rows[-1].update(sale_price=None, sale_price_status="source_missing", sale_price_raw="")
        r = fixture_analysis(rows, CF, "sales", [flag(rows[-1], "sale_price", "source_missing")])
        warnings = r["quality"]["warnings"]
        self.assertTrue(any(w["field"] == "sale_price" and w["code"] == "source_missing" for w in warnings))
        self.assertEqual(r["result"]["items"][-1]["assessments"]["peer"]["reason"], "dimension:sale_price:source_missing")

    def test_multiple_missing_dependencies_reported_with_disjoint_priority(self):
        rows = fixture_rows(sequence(30) + [None])
        rows[-1].update(credit_debit_code=None, credit_debit_code_status="source_missing",
                        journal_voucher_type_code=None, journal_voucher_type_code_status="source_missing")
        r = fixture_analysis(rows)
        self.assertEqual(len(r["result"]["items"][-1]["unavailable_dependencies"]), 3)
        self.assertEqual(r["result"]["summary"]["peer"]["not_assessed_reasons"], {"dimension:debit_credit:source_missing": 1})
        self.assertEqual(r["records"]["excluded"], 1)

    def test_numeric_price_equality_not_string_scale_defines_peer(self):
        rows = fixture_rows(sequence(30), CF, "sales")
        rows[-1]["sale_price"] = "10.0"
        r = fixture_analysis(rows, CF, "sales")
        self.assertEqual(len(r["result"]["references"]), 2)
        self.assertEqual(r["result"]["references"][1]["numeric_size"], 30)

    def test_deterministic_order_lineage_and_no_input_mutation(self):
        rows = fixture_rows(sequence(30) + ["1000.00"])
        before = deepcopy(rows)
        a, b = fixture_analysis(rows), fixture_analysis(list(reversed(rows)))
        self.assertEqual(a, b)
        self.assertEqual(rows, before)
        self.assertEqual(a["result"]["items"][-1]["lineage"], {k: rows[-1][k] for k in ("record_id", "run_id", "source_id", "source_row_number", "processed_row_number")})

    def test_decimal_context_does_not_affect_fences_or_decisions(self):
        rows = fixture_rows(sequence(30) + ["45.0000000001"])
        expected = fixture_analysis(rows)
        with localcontext() as ctx:
            ctx.prec = 2
            ctx.rounding = "ROUND_DOWN"
            self.assertEqual(fixture_analysis(rows), expected)

    def test_precision_overflow_is_blocker_not_rounded_assessment(self):
        r = fixture_analysis(fixture_rows(sequence(30) + ["9" * 61 + ".0"]))
        self.assertEqual(r["status"], "DATA_QUALITY_BLOCKER")
        self.assertIsNone(r["result"])
        self.assertEqual(r["errors"][0]["code"], "exact_arithmetic_limit")

    def test_malformed_numeric_or_inconsistent_status_is_blocker(self):
        for token, status in [(1.1, "parsed"), ("NaN", "parsed"), ("1.00", "unresolved_placeholder"), (None, "parsed")]:
            with self.subTest(token=token, status=status):
                rows = fixture_rows(sequence(30))
                rows[-1].update(journal_voucher_item_amount=token, journal_voucher_item_amount_status=status)
                r = fixture_analysis(rows)
                self.assertEqual(r["status"], "DATA_QUALITY_BLOCKER")
                self.assertIsNone(r["result"])

    def test_all_null_is_partial_with_explicit_abstentions_not_zero_or_normal(self):
        r = fixture_analysis(fixture_rows([None] * 30, CF, "profit"), CF, "profit")
        self.assertEqual(r["status"], "PARTIAL")
        self.assertEqual(r["records"]["used"], 0)
        self.assertEqual(r["result"]["summary"]["global"]["not_assessed"], 30)
        self.assertIsNone(r["result"]["references"][0]["upper_fence"])


class AnomalyIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.service = AnomalyService(ROOT)

    def analyze(self, dataset=RG, measure="accounting_amount", **options):
        return self.service.analyze(request(dataset, measure, **options))

    def assert_reconciles(self, r):
        def exact_json(value):
            self.assertNotIsInstance(value, (float, Decimal))
            if isinstance(value, dict):
                for item in value.values():
                    exact_json(item)
            elif isinstance(value, list):
                for item in value:
                    exact_json(item)
        exact_json(r)
        counts, result = r["records"], r["result"]
        self.assertEqual(counts["population"], counts["filtered_out"] + counts["filter_unavailable"] + counts["candidates"])
        self.assertEqual(counts["candidates"], counts["used"] + counts["excluded"])
        self.assertEqual(sum(counts["exclusion_reasons"].values()), counts["excluded"])
        self.assertEqual(len(result["items"]), counts["candidates"])
        for mode, summary in result["summary"].items():
            self.assertEqual(counts["candidates"], sum(summary[k] for k in ("candidate", "not_selected", "not_assessed")))
            self.assertEqual(sum(summary["not_assessed_reasons"].values()), summary["not_assessed"])
        comp = result["comparison"]
        self.assertEqual(comp["both_assessed"], sum(comp[k] for k in comp if k != "both_assessed"))
        refs = {ref["reference_id"]: ref for ref in result["references"]}
        for item in result["items"]:
            for assessment in item["assessments"].values():
                if assessment["reference_id"] is not None:
                    self.assertIn(assessment["reference_id"], refs)
                if assessment["status"] != "NOT_ASSESSED":
                    self.assertGreaterEqual(assessment["numeric_peer_size"], 30)
            self.assertTrue(all(0 <= i < len(r["quality"]["warnings"]) for i in item["quality_warning_indices"]))
        json.dumps(r, allow_nan=False)

    def test_rg_reproduces_documented_eda_global_and_peer_population(self):
        r = self.analyze()
        self.assertEqual(r["status"], "PARTIAL")
        self.assertEqual(r["result"]["summary"]["global"]["candidate"], 2194)
        self.assertEqual(r["result"]["summary"]["peer"], {"candidate": 937, "not_selected": 8170, "not_assessed": 175,
                          "not_assessed_reasons": {"dimension:voucher_type:source_missing": 26, "insufficient_numeric_records": 149}})
        self.assertEqual(r["result"]["comparison"], {"both_assessed": 9107, "both_candidate": 298,
                         "global_only_candidate": 1788, "peer_only_candidate": 639, "neither_candidate": 6382})
        self.assertEqual(r["result"]["references"][0]["upper_fence"], "167264.64250")
        self.assert_reconciles(r)

    def test_sales_reproduces_eda_seven_pricing_peers_and_disagreement(self):
        r = self.analyze(CF, "sales")
        self.assertEqual(r["status"], "SUCCESS")
        refs = r["result"]["references"][1:]
        self.assertEqual(len(refs), 7)
        self.assertEqual({ref["numeric_size"] for ref in refs}, {100})
        self.assertEqual(r["result"]["summary"]["global"]["candidate"], 53)
        self.assertEqual(r["result"]["summary"]["peer"]["candidate"], 5)
        self.assertEqual(r["result"]["comparison"]["both_candidate"], 0)
        self.assert_reconciles(r)

    def test_profit_excludes_five_placeholders_and_keeps_signed_values(self):
        r = self.analyze(CF, "profit")
        self.assertEqual(r["status"], "PARTIAL")
        self.assertEqual(r["records"]["used"], 695)
        self.assertEqual(r["records"]["excluded"], 5)
        self.assertEqual(r["result"]["summary"]["global"]["candidate"], 102)
        self.assertEqual(r["result"]["summary"]["peer"]["candidate"], 7)
        negatives = [i for i in r["result"]["items"] if i["observed_value"] is not None and Decimal(i["observed_value"]) < 0]
        self.assertEqual(len(negatives), 58)
        self.assertTrue(any(i["assessments"]["peer"]["status"] == "NOT_SELECTED" for i in negatives))
        self.assert_reconciles(r)

    def test_quality_relevance_unknown_currency_and_no_unrelated_warning(self):
        r = self.analyze()
        warnings = {(w["code"], w["field"]) for w in r["quality"]["warnings"]}
        self.assertIn(("source_missing", "journal_voucher_type_code"), warnings)
        self.assertNotIn(("source_missing", "department_number"), warnings)
        self.assertIn(("currency_unknown", "currency"), warnings)
        self.assertEqual(r["currency"]["status"], "UNKNOWN")
        self.assertIsNone(r["currency"]["code"])
        self.assertFalse(r["currency"]["conversion_applied"])
        self.assertFalse(any(w[0] in ("parsing_failed", "key_conflict") for w in warnings))
        r = self.analyze(CF, "sales")
        self.assertFalse(any(w["code"] == "unresolved_placeholder" for w in r["quality"]["warnings"]))

    def test_record_warnings_link_only_applicable_source_flags(self):
        r = self.analyze(CF, "profit", quality_detail="full")
        for item in r["result"]["items"]:
            warnings = [r["quality"]["warnings"][i] for i in item["quality_warning_indices"]]
            self.assertEqual(any(w["code"] == "unresolved_placeholder" for w in warnings), item["observed_value"] is None)
        placeholder = next(f for f in r["quality"]["flags"] if f["flag"] == "unresolved_placeholder" and f["field"] == "profit")
        self.assertTrue(placeholder["relevant"])
        self.assertTrue(placeholder["source_sha256"])

    def test_detail_mode_does_not_change_decisions_or_references(self):
        a, b = self.analyze(CF, "sales"), self.analyze(CF, "sales", quality_detail="full")
        for field in ("status", "result", "records", "currency"):
            self.assertEqual(a[field], b[field])

    def test_month_filter_recomputes_peers_and_preserves_temporal_uncertainty(self):
        r = self.analyze(CF, "sales", period={"year": 2014, "month": 5})
        self.assertEqual(r["records"]["candidates"], 35)
        self.assertEqual(r["result"]["summary"]["peer"]["not_assessed"], 35)
        self.assertEqual(r["result"]["references"][0]["numeric_size"], 35)
        self.assertEqual(r["status"], "PARTIAL")
        rg = self.analyze(period={"year": 2023, "month": 5})
        self.assertTrue(any(w["code"] == "fiscal_alignment_unresolved" for w in rg["quality"]["warnings"]))
        self.assert_reconciles(rg)

    def test_null_filter_membership_accounting_and_literal_sql_shape(self):
        r = self.analyze(filters={"voucher_type": {"eq": "does-not-exist"}})
        self.assertEqual(r["status"], "NO_DATA")
        self.assertEqual(r["records"]["filter_unavailable"], 26)
        self.assert_reconciles(r)
        r = self.analyze(CF, "sales", filters={"product": {"eq": "'; DROP TABLE x; --"}})
        self.assertEqual(r["status"], "NO_DATA")
        self.assertEqual(r["records"]["candidates"], 0)

    def test_no_accusatory_or_normal_classification_and_no_probability(self):
        r = self.analyze(CF, "profit")
        text = json.dumps(r).lower()
        for term in (r'\bfraud\w*\b', r'\bmalicious\b', r'\bnormal\b', r'\bfraud_probability\b', r'\binvalid transactions\b'):
            self.assertIsNone(re.search(term, text))
        self.assertEqual(r["errors"], [])
        self.assertEqual({a["status"] for i in r["result"]["items"] for a in i["assessments"].values()},
                         {"CANDIDATE", "NOT_SELECTED", "NOT_ASSESSED"})

    def test_lineage_and_deterministic_repeat_offline(self):
        with patch("socket.socket", side_effect=AssertionError("network disabled")), \
             patch("socket.create_connection", side_effect=AssertionError("network disabled")):
            a, b = self.analyze(CF, "sales"), self.analyze(CF, "sales")
        self.assertEqual(a, b)
        self.assertEqual(len({i["lineage"]["record_id"] for i in a["result"]["items"]}), 700)
        self.assertEqual([i["lineage"]["source_row_number"] for i in a["result"]["items"]], list(range(1, 701)))
        self.assertEqual(a["metadata"]["snapshot"]["database_sha256"], hashlib.sha256((ROOT / "data/database/financial_manager.db").read_bytes()).hexdigest())

    def test_production_database_is_unchanged(self):
        path = ROOT / "data/database/financial_manager.db"
        before = hashlib.sha256(path.read_bytes()).hexdigest()
        self.analyze()
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), before)


class AnomalyValidationTests(unittest.TestCase):
    def test_invalid_requests_do_not_open_database(self):
        service = AnomalyService()
        cases = [None, [], {}, request(analysis_version="2.0"), request(dataset="company"), request(measure=None),
                 request(group_by="department"), request(sql="SELECT 1"), request(method="magic"),
                 request(filters={"sale_price": {"eq": "10.00"}}), request(period={"year": True})]
        with patch.object(service._snapshot, "open", side_effect=AssertionError("must not query")):
            for payload in cases:
                with self.subTest(payload=payload):
                    self.assertEqual(service.analyze(payload)["status"], "INVALID_REQUEST")

    def test_unapproved_measures_and_partial_month_are_unsupported(self):
        service = AnomalyService()
        for payload in [request(CF, "discounts"), request(CF, "units_sold"), request(RG, "expenses"),
                        request(CF, "sales", period={"start_date": "2014-05-02", "end_date": "2014-05-31"})]:
            with self.subTest(payload=payload):
                self.assertEqual(service.analyze(payload)["status"], "UNSUPPORTED")

    def test_missing_or_changed_snapshot_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            r = AnomalyService(directory).analyze(request())
        self.assertEqual(r["status"], "DATA_QUALITY_BLOCKER")
        self.assertIsNone(r["result"])

    def test_agent_registry_and_unsupported_detection_remain_unchanged(self):
        agent = FinancialAnalysisAgent()
        self.assertEqual(len(agent.registry.catalog()), 17)
        self.assertEqual(agent.ask("Find sales anomalies")["agent_status"], "UNSUPPORTED")

    def test_unexpected_internal_failure_is_not_silenced(self):
        service = AnomalyService()
        with patch.object(service._snapshot, "open", side_effect=RuntimeError("fixture failure")):
            with self.assertRaisesRegex(RuntimeError, "fixture failure"):
                service.analyze(request())


if __name__ == "__main__":
    unittest.main()
