"""V1 acceptance through real CLI subprocesses and approved local evidence."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from src.financial import FinancialCore
from src.anomaly import AnomalyService
from src.manager import FinancialManagerAgent


ROOT = Path(__file__).resolve().parents[1]

# Test-only instrumentation at OS/SQLite boundaries; application composition is
# unchanged. Every child must load this hook, and even swallowed attempts fail.
GUARD = '''
import os
import sys
from pathlib import Path

log = Path(os.environ["V1_ACCEPTANCE_AUDIT"])
log.write_text("ready\\n")
def boundary(event, args):
    forbidden = event.startswith("socket.") or event in (
        "subprocess.Popen", "os.system", "os.exec", "os.posix_spawn")
    forbidden |= event == "sqlite3.connect" and os.environ.get("V1_ACCEPTANCE_NO_DB") == "1"
    if forbidden:
        with log.open("a") as stream:
            stream.write(event + "\\n")
        raise RuntimeError("Acceptance boundary blocked")
sys.addaudithook(boundary)
'''


def asset_hashes():
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for directory in (ROOT / "data", ROOT / "notebooks")
            for p in directory.rglob("*") if p.is_file()}


class V1AcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        before = asset_hashes()

        def verify_assets():
            if asset_hashes() != before:
                raise AssertionError("Acceptance changed protected production assets")

        cls.addClassCleanup(verify_assets)
        cls.core = FinancialCore()
        cls.anomaly = AnomalyService()

    def cli(self, *args, no_database=False, cwd=ROOT, exit_code=0):
        with tempfile.TemporaryDirectory(prefix="v1-acceptance-") as directory:
            temporary = Path(directory)
            (temporary / "sitecustomize.py").write_text(GUARD)
            log = temporary / "audit.txt"
            env = os.environ.copy()
            env.update(PYTHONPATH=directory, V1_ACCEPTANCE_AUDIT=str(log),
                       V1_ACCEPTANCE_NO_DB="1" if no_database else "0",
                       V1_ACCEPTANCE_PRIVATE_ENV="acceptance-private-canary-93821")
            completed = subprocess.run([sys.executable, "-B", "-m", "src.cli", *args],
                                       cwd=cwd, env=env, capture_output=True, text=True, timeout=60)
            self.assertTrue(log.is_file(), "Offline boundary guard must load in the child")
            self.assertEqual(log.read_text(), "ready\n", "A prohibited operation was attempted")
        self.assertEqual(completed.returncode, exit_code, completed.stderr)
        if exit_code == 0:
            self.assertEqual(completed.stderr, "")
        else:
            self.assertEqual(completed.stdout, "")
            self.assertIn("Invalid CLI syntax.", completed.stderr)
        for secret in ("acceptance-private-canary-93821", str(ROOT), str(cwd), "Traceback (most recent call last)"):
            self.assertNotIn(secret, completed.stdout + completed.stderr)
        return completed.stdout

    def ask(self, question, **options):
        def reject_float(token):
            self.fail("Exact application evidence must not contain JSON floats: " + token)

        return json.loads(self.cli("ask", question, "--json", **options),
                          parse_float=reject_float, parse_constant=reject_float)

    def analysis(self, question, name, dataset, **options):
        response = self.ask(question)
        self.assertEqual(response["routing"]["status"], "ROUTED")
        self.assertEqual(len(response["results"]), 1)
        step = response["results"][0]
        self.assertEqual(step["capability"], "FINANCIAL_ANALYSIS")
        self.assertEqual(set(response["routing"]["steps"][0]["normalized_request"]), {"question"})
        delegated = step["response"]["delegated_result"]
        request = {"contract_version": "1.0", "query_name": name, "dataset": dataset, **options}
        self.assertEqual(delegated["tool_request"], request)
        expected = self.core.query(request)
        self.assertEqual(delegated["tool_result"], expected)
        self.assertEqual(response["execution_status"], expected["status"])
        self.assertEqual(step["response"]["warnings"], expected["quality"]["warnings"])
        self.assertEqual(response["warnings"], [{"step_id": 1, "items": expected["quality"]["warnings"]}])
        if expected["currency"] is not None:
            self.assertEqual(expected["currency"]["status"], "UNKNOWN")
            self.assertIsNone(expected["currency"]["code"])
            self.assertFalse(expected["currency"]["conversion_applied"])
        return expected

    def test_record_counts_traverse_both_domains_without_currency_or_company_inference(self):
        for label, dataset, count in (("Receiver General", "receiver_general", 9282),
                                      ("Company Financials", "company_financials", 700)):
            with self.subTest(dataset=dataset):
                evidence = self.analysis(label + " record count", dataset + "_record_count", dataset)
                self.assertEqual(evidence["status"], "SUCCESS")
                self.assertEqual(evidence["result"], {"record_count": count})
                self.assertIsNone(evidence["currency"])

    def test_sales_summary_exact_evidence_is_visible_in_both_output_modes(self):
        evidence = self.analysis("Sales summary", "company_financials_sales_summary",
                                 "company_financials", measures=["sales"])
        total = evidence["result"]["measures"]["sales"]["sum"]
        self.assertIsInstance(total, str)
        human = self.cli("ask", "Sales summary")
        for text in (total, "SUCCESS", "UNKNOWN", "currency_unknown", "Structured evidence:"):
            self.assertIn(text, human)

    def test_grouped_sales_and_explicit_month_preserve_contract_scope(self):
        evidence = self.analysis("Sales by country in May 2014", "company_financials_sales_by_country",
                                 "company_financials", measures=["sales"], period={"year": 2014, "month": 5})
        self.assertEqual(evidence["status"], "SUCCESS")
        self.assertEqual(evidence["records"]["candidates"], 35)
        self.assertEqual(evidence["metadata"]["group_by"], "country")
        self.assertEqual(len(evidence["result"]["groups"]), 5)

    def test_accounting_summary_keeps_exact_amount_and_unknown_denomination(self):
        evidence = self.analysis("Receiver General amount summary", "receiver_general_amount_summary",
                                 "receiver_general")
        self.assertEqual(evidence["result"]["measures"]["accounting_amount"]["sum"], "3061288992129.16")
        self.assertEqual(evidence["records"]["used"], 9282)

    def test_sparse_department_coverage_remains_partial_and_visible(self):
        evidence = self.analysis("Amounts by department", "receiver_general_amount_by_department",
                                 "receiver_general")
        self.assertEqual(evidence["status"], "PARTIAL")
        self.assertEqual(evidence["result"]["dimension_coverage"]["unavailable"], 26)
        self.assertTrue(any(w["code"] == "source_missing" for w in evidence["quality"]["warnings"]))
        self.assertEqual(evidence["result"]["groups"][-1]["key"], {"value": None, "kind": "unavailable"})

    def test_discount_placeholders_remain_excluded_in_user_evidence(self):
        evidence = self.analysis("Discount analysis", "company_financials_discount_analysis", "company_financials")
        self.assertEqual(evidence["status"], "PARTIAL")
        self.assertEqual(evidence["records"]["used"], 647)
        self.assertEqual(evidence["records"]["exclusion_reasons"], {"measure:discounts:unresolved_placeholder": 53})
        self.assertEqual(evidence["result"]["unresolved_placeholder_count"], 53)

    def test_descriptive_extremes_retain_lineage_without_screening_labels(self):
        evidence = self.analysis("Receiver General highest 2 amounts", "receiver_general_extreme_amount_records",
                                 "receiver_general", direction="highest", limit=2)
        self.assertEqual(evidence["records"]["returned"], 2)
        self.assertEqual(evidence["result"]["items"][0]["accounting_amount"], "39555794411.27")
        for item in evidence["result"]["items"]:
            self.assertTrue(item["record_id"])
            self.assertIsInstance(item["source_row_number"], int)
            self.assertNotIn("assessments", item)

    def screening(self, question, dataset, measure, peers):
        response = self.ask(question)
        self.assertEqual(response["routing"]["status"], "ROUTED")
        self.assertEqual(len(response["results"]), 1)
        step = response["results"][0]
        self.assertEqual(step["capability"], "ANOMALY_DETECTION")
        expected = self.anomaly.analyze({"analysis_version": "1.0", "dataset": dataset, "measure": measure})
        evidence = step["response"]["delegated_result"]
        self.assertEqual(evidence, expected)
        self.assertEqual(response["execution_status"], evidence["status"])
        self.assertEqual(step["response"]["warnings"], evidence["quality"]["warnings"])
        self.assertEqual(evidence["metadata"]["peer_definition"], peers)
        self.assertEqual(evidence["currency"]["status"], "UNKNOWN")
        self.assertIsNone(evidence["currency"]["code"])
        self.assertFalse(evidence["currency"]["conversion_applied"])
        self.assertEqual({a["status"] for i in evidence["result"]["items"] for a in i["assessments"].values()},
                         {"CANDIDATE", "NOT_SELECTED", "NOT_ASSESSED"})
        for item in evidence["result"]["items"]:
            self.assertTrue(item["lineage"]["record_id"])
            self.assertIsInstance(item["lineage"]["source_row_number"], int)
            if item["observed_value"] is not None:
                self.assertIsInstance(item["observed_value"], str)
        self.assertIn("requiring investigation", step["response"]["summary"])
        self.assertNotRegex(json.dumps(response).lower(), r"\b(fraud|misconduct|malicious|suspicious transaction)\b")
        return evidence

    def test_receiver_general_screening_retains_global_and_peer_evidence(self):
        evidence = self.screening("Screen accounting amounts", "receiver_general", "accounting_amount",
                                  ["debit_credit", "voucher_type"])
        self.assertEqual(evidence["status"], "PARTIAL")
        self.assertEqual(evidence["result"]["references"][0]["upper_fence"], "167264.64250")
        self.assertEqual(evidence["result"]["summary"]["peer"]["not_assessed"], 175)

    def test_profit_screening_retains_placeholders_signed_values_and_human_context(self):
        evidence = self.screening("Screen profit", "company_financials", "profit", ["segment", "sale_price"])
        self.assertEqual(evidence["records"]["exclusion_reasons"], {"measure:profit:unresolved_placeholder": 5})
        item = next(i for i in evidence["result"]["items"] if i["observed_value"] is None)
        self.assertEqual(item["assessments"]["global"]["status"], "NOT_ASSESSED")
        self.assertTrue(any(i["observed_value"] and i["observed_value"].startswith("-") for i in evidence["result"]["items"]))
        human = self.cli("ask", "Screen profit")
        for text in ("CANDIDATE", "NOT_SELECTED", "NOT_ASSESSED", "requiring investigation", "UNKNOWN",
                     "unresolved_placeholder", "sale_price", "numeric_peer_size", "lineage",
                     evidence["result"]["references"][0]["upper_fence"]):
            self.assertIn(text, human)
        self.assertIn("it is not fraud, error, misconduct, probability, or certainty", human)
        self.assertNotRegex(human.lower(), r"\b(malicious|suspicious transaction)\b")

    def test_default_screening_preview_is_bounded_and_uses_authoritative_order(self):
        evidence = self.anomaly.analyze({"analysis_version": "1.0", "dataset": "company_financials",
                                         "measure": "profit"})
        human = self.cli("ask", "Screen profit")
        items = evidence["result"]["items"]

        self.assertLess(len(human), 100_000)
        self.assertIn("Showing 10 of 700 items; 690 omitted.", human)
        self.assertIn('"returned_item_count": 10', human)
        self.assertIn('"total_item_count": 700', human)
        self.assertIn('"omitted_item_count": 690', human)
        positions = [human.index(item["lineage"]["record_id"]) for item in items[:10]]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("Use --full for expanded human output.", human)
        self.assertIn("Use --json for complete structured evidence.", human)

    def test_screening_preview_includes_references_used_by_previewed_assessments(self):
        evidence = self.anomaly.analyze({"analysis_version": "1.0", "dataset": "receiver_general",
                                         "measure": "accounting_amount"})
        human = self.cli("ask", "Screen accounting amounts")
        reference_ids = []
        for item in evidence["result"]["items"][:10]:
            for assessment in item["assessments"].values():
                reference_id = assessment["reference_id"]
                if reference_id is not None and reference_id not in reference_ids:
                    reference_ids.append(reference_id)
        references = {item["reference_id"]: item for item in evidence["result"]["references"]}

        self.assertGreater(len(reference_ids), 1)
        for reference_id in reference_ids:
            reference = references[reference_id]
            self.assertIn(reference_id, human)
            self.assertIn(reference["upper_fence"], human)
            self.assertIn(str(reference["numeric_size"]), human)

    def test_plan_reports_the_same_route_without_opening_database_or_producing_evidence(self):
        question = "Sales by country"
        plan = json.loads(self.cli("plan", question, "--json", no_database=True))
        self.assertEqual(plan, FinancialManagerAgent().plan(question))
        self.assertEqual(plan["status"], "ROUTED")
        self.assertEqual(plan["steps"][0]["capability"]["identifier"], "FINANCIAL_ANALYSIS")
        self.assertEqual(plan["steps"][0]["normalized_request"], {"question": question})
        self.assertNotIn("results", plan)
        human = self.cli("plan", "Find outliers in Profit", no_database=True)
        self.assertIn("Routing: ROUTED", human)
        self.assertIn("Anomaly Detection: AVAILABLE", human)

    def test_forecast_and_document_requests_explain_blockers_without_execution(self):
        for question, capability, name, reason in (
            ("Forecast cash flow next month", "CASH_FLOW_FORECASTING", "Cash Flow Forecasting", "actual cash inflows/outflows"),
            ("What does invoice 123 say?", "DOCUMENT_RETRIEVAL", "Document Retrieval", "no approved real financial-document corpus"),
        ):
            with self.subTest(capability=capability):
                response = self.ask(question, no_database=True)
                self.assertEqual(response["routing"]["status"], "BLOCKED")
                self.assertEqual(response["execution_status"], "CAPABILITY_UNAVAILABLE")
                self.assertEqual(response["execution_state"], "NOT_PERFORMED")
                self.assertEqual(response["results"], [])
                metadata = response["routing"]["steps"][0]["capability"]
                self.assertEqual(metadata["identifier"], capability)
                self.assertEqual(metadata["status"], "BLOCKED")
                self.assertIn(reason, metadata["reason"])
                human = self.cli("ask", question, no_database=True)
                self.assertIn(name + ": BLOCKED", human)
                self.assertIn(reason, human)

    def test_capability_and_dataset_ambiguity_request_clarification_without_queries(self):
        response = self.ask("Check my financial data", no_database=True)
        self.assertEqual(response["execution_status"], "CLARIFICATION_REQUIRED")
        self.assertEqual(response["execution_state"], "NOT_PERFORMED")
        self.assertEqual(response["results"], [])
        self.assertTrue(response["clarification"]["question"])
        human = self.cli("ask", "Check my financial data", no_database=True)
        self.assertIn("Clarification required:", human)
        self.assertIn(response["clarification"]["question"], human)
        dataset = self.ask("How many records are there?", no_database=True)
        self.assertEqual(dataset["routing"]["status"], "ROUTED")
        self.assertEqual(dataset["execution_status"], "CLARIFICATION_REQUIRED")
        self.assertEqual(dataset["clarification"]["field"], "dataset")
        self.assertIsNone(dataset["results"][0]["response"]["delegated_result"]["tool_result"])

    def test_unsupported_interpretations_do_not_invent_financial_results(self):
        for question in ("Receiver General total expenses", "Which company performed best?",
                         "Combine monetary totals across both datasets", "Convert sales to USD",
                         "What is the fraud probability?"):
            with self.subTest(question=question):
                response = self.ask(question, no_database=True)
                self.assertEqual(response["execution_status"], "UNSUPPORTED")
                for step in response["results"]:
                    self.assertEqual(step["capability"], "FINANCIAL_ANALYSIS")
                    self.assertIsNone(step["response"]["delegated_result"]["tool_result"])
                self.assertTrue(response["errors"])

    def test_multi_capability_results_remain_separate_and_match_independent_evidence(self):
        question = "Summarize sales and identify unusual sales records."
        response = self.ask(question)
        self.assertEqual(response["routing"]["status"], "MULTI_CAPABILITY")
        self.assertEqual(response["execution_status"], "SUCCESS")
        self.assertEqual([s["capability"] for s in response["results"]], ["FINANCIAL_ANALYSIS", "ANOMALY_DETECTION"])
        self.assertEqual([s["step_id"] for s in response["results"]], [1, 2])
        analysis, anomaly = [s["response"]["delegated_result"] for s in response["results"]]
        expected_analysis = self.core.query({"contract_version": "1.0", "dataset": "company_financials",
                                             "query_name": "company_financials_sales_summary", "measures": ["sales"]})
        anomaly_request = {"analysis_version": "1.0", "dataset": "company_financials", "measure": "sales"}
        self.assertEqual(analysis["tool_result"], expected_analysis)
        self.assertEqual(anomaly, self.anomaly.analyze(anomaly_request))
        self.assertEqual(response["routing"]["steps"][1]["normalized_request"], anomaly_request)
        self.assertEqual(response["not_performed"], [])
        self.assertNotIn("result", response)  # No aggregate financial answer above the two results.
        again = self.ask(question)
        self.assertEqual(again, response)

    def test_no_matching_records_return_no_data_without_a_zero_monetary_total(self):
        evidence = self.analysis('Sales where country="acceptance-no-match"', "company_financials_sales_summary",
                                 "company_financials", measures=["sales"],
                                 filters={"country": {"eq": "acceptance-no-match"}})
        self.assertEqual(evidence["status"], "NO_DATA")
        self.assertEqual(evidence["records"]["candidates"], 0)
        self.assertIsNone(evidence["result"]["measures"]["sales"]["sum"])

    def test_executable_questions_cannot_reach_sql_shell_imports_or_environment(self):
        with tempfile.TemporaryDirectory(prefix="v1-execution-fixture-") as directory:
            marker = Path(directory) / "executed"
            questions = (
                "SELECT * FROM company_financials",
                f"python __import__('pathlib').Path('{marker}').write_text('executed')",
                f"shell touch {marker}",
                "import importlib; importlib.import_module('src.database.initialize')",
                "__import__('os').environ['V1_ACCEPTANCE_PRIVATE_ENV']",
                "execute capability subprocess.Popen",
            )
            for question in questions:
                with self.subTest(question=question):
                    response = self.ask(question, no_database=True)
                    self.assertEqual(response["execution_status"], "UNSUPPORTED")
                    self.assertEqual(response["execution_state"], "NOT_PERFORMED")
                    self.assertEqual(response["results"], [])
                    self.assertFalse(marker.exists())

    def test_missing_local_assets_produce_a_controlled_blocker_through_real_entry_point(self):
        with tempfile.TemporaryDirectory(prefix="v1-private-installation-") as directory:
            # Copy application code only: a separate installation with no dataset.
            # The approved repository/database is never renamed or altered.
            root = Path(directory)
            shutil.copytree(ROOT / "src", root / "src", ignore=shutil.ignore_patterns("__pycache__"))
            response = self.ask("Sales summary", cwd=root, no_database=True)
            self.assertEqual(response["execution_status"], "DATA_QUALITY_BLOCKER")
            evidence = response["results"][0]["response"]["delegated_result"]["tool_result"]
            self.assertIsNone(evidence["result"])
            self.assertEqual(evidence["errors"][0]["code"], "snapshot_mismatch")
            human = self.cli("ask", "Sales summary", cwd=root, no_database=True)
            self.assertIn("DATA_QUALITY_BLOCKER", human)
            self.assertNotIn("FileNotFoundError", human)

    def test_malformed_cli_and_question_inputs_fail_safely_without_queries(self):
        for args in (("ask",), ("plan",), ("capabilities", "--capability", "os.system"),
                     ("--private-token=acceptance-private-canary-93821",)):
            with self.subTest(args=args):
                self.cli(*args, no_database=True, exit_code=2)
        response = self.ask("", no_database=True)
        self.assertEqual(response["execution_status"], "INVALID_REQUEST")
        self.assertEqual(response["results"], [])

    def test_capabilities_publish_the_real_registry_in_human_and_json_output(self):
        catalog = json.loads(self.cli("capabilities", "--json", no_database=True))
        self.assertEqual(catalog, FinancialManagerAgent().list_capabilities())
        self.assertEqual([(c["identifier"], c["status"]) for c in catalog], [
            ("FINANCIAL_ANALYSIS", "AVAILABLE"), ("ANOMALY_DETECTION", "AVAILABLE"),
            ("CASH_FLOW_FORECASTING", "BLOCKED"), ("DOCUMENT_RETRIEVAL", "BLOCKED")])
        human = self.cli("capabilities", no_database=True)
        for item in catalog:
            self.assertIn(item["name"] + ": " + item["status"], human)


if __name__ == "__main__":
    unittest.main()
