"""Step 20 command/presentation tests, not the later acceptance phase."""

from copy import deepcopy
from decimal import Decimal
from io import StringIO
import json
from pathlib import Path
import subprocess
import sys
import hashlib
import tempfile
import unittest
from unittest.mock import patch

from src.cli.main import main
from src.agents import FinancialAnalysisAgent
from src.financial import FinancialCore
from src.manager import FinancialManagerAgent

ROOT = Path(__file__).resolve().parents[1]


class CLIStub:
    def __init__(self):
        self.calls = []
        self.catalog = [{"identifier": "FINANCIAL_ANALYSIS", "name": "Analysis fixture",
                         "status": "DEFERRED", "reason": "Fixture readiness reason.",
                         "limitations": ["Fixture limitation."], "documentation": []}]
        self.plan_result = {"routing_version": "1.0", "original_request": "fixture", "status": "BLOCKED",
                            "reason_code": "capability_unavailable", "message": "Fixture readiness reason.",
                            "steps": [{"step_id": 1, "capability": self.catalog[0], "notes": [],
                                       "normalized_request": {}, "original_clause": "fixture", "reason_code": "fixture"}],
                            "clarification": None, "blockers": [self.catalog[0]]}
        evidence = {"status": "PARTIAL", "result": {"amount": "123.000000000000000001"},
                    "currency": {"status": "UNKNOWN", "code": None},
                    "records": {"used": 2, "excluded": 1},
                    "quality": {"warnings": [{"code": "fixture_missing"}], "flags": []}}
        response = {"execution_status": "PARTIAL", "summary": "Fixture explanation.",
                    "delegated_result": {"tool_result": evidence, "evidence_sha256": "fixture-digest"},
                    "warnings": evidence["quality"]["warnings"], "errors": [],
                    "limitations": ["Fixture limitation."], "clarification": None}
        self.answer = {"execution_status": "PARTIAL", "execution_state": "PERFORMED", "routing": self.plan_result,
                       "results": [{"step_id": 1, "capability": "FINANCIAL_ANALYSIS", "response": response}],
                       "warnings": [], "errors": [], "limitations": [], "not_performed": [], "clarification": None}

    def list_capabilities(self):
        self.calls.append(("capabilities",))
        return self.catalog

    def plan(self, question):
        self.calls.append(("plan", question))
        return self.plan_result

    def ask(self, question):
        self.calls.append(("ask", question))
        return self.answer


class CLITests(unittest.TestCase):
    def test_closed_output_pipe_has_no_shutdown_traceback(self):
        process = subprocess.Popen([sys.executable, "-B", "-m", "src.cli", "capabilities", "--json"],
                                   cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        process.stdout.close()
        error = process.stderr.read()
        process.stderr.close()
        self.assertEqual(process.wait(timeout=10), 1)
        self.assertNotIn("Traceback", error)
        self.assertNotIn("Exception ignored", error)
        self.assertNotIn(str(ROOT), error)

    def test_anomaly_display_keeps_candidates_thresholds_peers_and_lineage(self):
        manager, out, err = CLIStub(), StringIO(), StringIO()
        response = manager.answer["results"][0]["response"]
        response["summary"] = "CANDIDATE records require investigation; NOT_ASSESSED remains unassessed."
        response["delegated_result"] = {"status": "PARTIAL", "measure": "profit",
            "currency": {"code": None, "status": "UNKNOWN"},
            "result": {"references": [{"reference_id": "peer:1", "upper_fence": "12.000001", "numeric_size": 30,
                        "peer_definition": ["segment", "sale_price"]}],
                       "items": [{"lineage": {"record_id": "fixture-9", "source_row_number": 9},
                                  "observed_value": "12.0000010001", "assessments": {
                                      "global": {"status": "CANDIDATE", "reference_id": "peer:1"},
                                      "peer": {"status": "NOT_ASSESSED"}}},
                                 {"assessments": {"global": {"status": "NOT_SELECTED"}}}]},
            "quality": {"warnings": [{"code": "currency_unknown"}], "flags": []}}
        before = deepcopy(manager.answer)
        self.assertEqual(main(["ask", "Screen profit"], manager=manager, stdout=out, stderr=err), 0)
        for term in ("CANDIDATE", "NOT_SELECTED", "NOT_ASSESSED", "12.0000010001", "12.000001",
                     '"numeric_size": 30', "segment", "sale_price", "fixture-9", "currency_unknown", "UNKNOWN"):
            self.assertIn(term, out.getvalue())
        self.assertIn("CANDIDATE = statistical screening candidate for investigation", out.getvalue())
        self.assertIn("it is not fraud, error, misconduct, probability, or certainty", out.getvalue())
        self.assertNotIn("suspicious transaction", out.getvalue().lower())
        self.assertEqual(manager.answer, before)

    def test_default_human_output_previews_large_evidence_without_mutation(self):
        manager, out, err = CLIStub(), StringIO(), StringIO()
        evidence = manager.answer["results"][0]["response"]["delegated_result"]["tool_result"]
        evidence["result"]["items"] = [
            {"lineage": {"record_id": f"fixture-{index:03d}"}, "observed_value": str(index)}
            for index in range(25)
        ]
        before = deepcopy(manager.answer)

        self.assertEqual(main(["ask", "Screen profit"], manager=manager, stdout=out, stderr=err), 0)

        rendered = out.getvalue()
        self.assertLess(len(rendered), 10_000)
        self.assertIn("Showing 10 of 25 items; 15 omitted.", rendered)
        self.assertIn("fixture-000", rendered)
        self.assertIn("fixture-009", rendered)
        self.assertNotIn("fixture-010", rendered)
        self.assertIn("Use --full for expanded human output.", rendered)
        self.assertIn("Use --json for complete structured evidence.", rendered)
        self.assertEqual(manager.answer, before)
        self.assertEqual(err.getvalue(), "")

    def test_default_human_output_bounds_repeated_explanation_detail(self):
        manager, out = CLIStub(), StringIO()
        manager.answer["results"][0]["response"]["summary"] = "Summary.\n" + ("quality-detail " * 1_000)

        self.assertEqual(main(["ask", "Sales"], manager=manager, stdout=out, stderr=StringIO()), 0)

        rendered = out.getvalue()
        self.assertLess(len(rendered), 10_000)
        self.assertIn("characters omitted from explanation", rendered)

    def test_concise_warning_display_deduplicates_exact_entries_only(self):
        manager, out = CLIStub(), StringIO()
        evidence = manager.answer["results"][0]["response"]["delegated_result"]["tool_result"]
        duplicate = {"code": "fixture_missing", "message": "Same warning.", "scope": "measure"}
        distinct = {"code": "currency_unknown", "message": "Different warning.", "scope": "dataset"}
        evidence["quality"]["warnings"] = [duplicate, distinct]
        manager.answer["results"][0]["response"]["warnings"] = [deepcopy(duplicate), deepcopy(distinct)]
        manager.answer["warnings"] = [{"step_id": 1, "items": [deepcopy(duplicate), deepcopy(distinct)]}]

        self.assertEqual(main(["ask", "Sales"], manager=manager, stdout=out, stderr=StringIO()), 0)

        rendered = out.getvalue()
        self.assertEqual(rendered.count("Same warning."), 1)
        self.assertEqual(rendered.count("Different warning."), 1)
        self.assertIn("fixture_missing", rendered)
        self.assertIn("currency_unknown", rendered)

    def test_concise_explanation_does_not_repeat_structured_warning_lines(self):
        manager, out = CLIStub(), StringIO()
        warning = {"code": "fixture_missing", "message": "Same warning.", "scope": "measure"}
        response = manager.answer["results"][0]["response"]
        response["summary"] = (
            "Result summary.\n"
            'Quality warning: {"code": "fixture_missing", "message": "Same warning."}.\n'
            'Quality flags: [{"flag": "fixture_missing"}].\n'
            "Result conclusion."
        )
        response["delegated_result"]["tool_result"]["quality"]["warnings"] = [warning]
        response["warnings"] = [deepcopy(warning)]
        manager.answer["warnings"] = [{"step_id": 1, "items": [deepcopy(warning)]}]

        self.assertEqual(main(["ask", "Sales"], manager=manager, stdout=out, stderr=StringIO()), 0)

        rendered = out.getvalue()
        self.assertIn("Result summary.", rendered)
        self.assertIn("Result conclusion.", rendered)
        self.assertNotIn("Quality warning:", rendered)
        self.assertNotIn("Quality flags:", rendered)
        self.assertEqual(rendered.count("Same warning."), 1)

    def test_concise_warning_display_keeps_all_distinct_warnings(self):
        manager, out = CLIStub(), StringIO()
        warnings = [{"code": f"warning_{index}", "message": f"Distinct warning {index}."}
                    for index in range(12)]
        evidence = manager.answer["results"][0]["response"]["delegated_result"]["tool_result"]
        evidence["quality"]["warnings"] = warnings

        self.assertEqual(main(["ask", "Sales"], manager=manager, stdout=out, stderr=StringIO()), 0)

        for warning in warnings:
            self.assertIn(warning["code"], out.getvalue())
            self.assertIn(warning["message"], out.getvalue())

    def test_deduplicated_warning_retains_every_applicable_step(self):
        manager, out = CLIStub(), StringIO()
        warning = {"code": "currency_unknown", "message": "Currency is UNKNOWN.", "scope": "dataset"}
        first = manager.answer["results"][0]
        first["response"]["delegated_result"]["tool_result"]["quality"]["warnings"] = [warning]
        first["response"]["warnings"] = [deepcopy(warning)]
        second = deepcopy(first)
        second.update(step_id=2, capability="ANOMALY_DETECTION")
        manager.answer["results"].append(second)
        manager.answer["warnings"] = [
            {"step_id": 1, "items": [deepcopy(warning)]},
            {"step_id": 2, "items": [deepcopy(warning)]},
        ]

        self.assertEqual(main(["ask", "Sales and screening"], manager=manager,
                              stdout=out, stderr=StringIO()), 0)

        rendered = out.getvalue()
        self.assertEqual(rendered.count("Currency is UNKNOWN."), 1)
        self.assertIn('"applies_to_steps": [', rendered)
        context = rendered[rendered.index('"applies_to_steps": ['):]
        self.assertLess(context.index("1"), context.index("2"))

    def test_terminology_notes_follow_structured_evidence_not_message_words(self):
        manager, out = CLIStub(), StringIO()
        response = manager.answer["results"][0]["response"]
        response["summary"] = "User text mentions UNKNOWN and CANDIDATE."
        evidence = response["delegated_result"]["tool_result"]
        evidence["currency"] = None
        evidence["quality"]["warnings"] = []
        response["warnings"] = []

        self.assertEqual(main(["ask", "Sales"], manager=manager, stdout=out, stderr=StringIO()), 0)

        rendered = out.getvalue()
        self.assertNotIn("UNKNOWN currency means", rendered)
        self.assertNotIn("CANDIDATE = statistical screening candidate", rendered)

    def test_large_all_linked_reference_preview_discloses_zero_omissions(self):
        manager, out = CLIStub(), StringIO()
        response = manager.answer["results"][0]["response"]
        response["delegated_result"] = {
            "status": "SUCCESS",
            "result": {
                "references": [{"reference_id": "global"}]
                              + [{"reference_id": f"peer:{index}"} for index in range(1, 11)],
                "items": [
                    {"assessments": {"global": {"reference_id": "global"},
                                      "peer": {"reference_id": f"peer:{index}"}}}
                    for index in range(1, 11)
                ],
            },
            "currency": {"status": "UNKNOWN", "code": None},
            "quality": {"warnings": [], "flags": []},
        }
        response["warnings"] = []

        self.assertEqual(main(["ask", "Screen values"], manager=manager,
                              stdout=out, stderr=StringIO()), 0)

        rendered = out.getvalue()
        self.assertIn("Showing 11 of 11 linked items; 0 omitted.", rendered)
        self.assertIn('"returned_item_count": 11', rendered)
        self.assertIn('"omitted_item_count": 0', rendered)

    def test_full_human_mode_exposes_expanded_evidence(self):
        manager, out, err = CLIStub(), StringIO(), StringIO()
        evidence = manager.answer["results"][0]["response"]["delegated_result"]["tool_result"]
        evidence["result"]["items"] = [
            {"lineage": {"record_id": f"fixture-{index:03d}"}, "observed_value": str(index)}
            for index in range(25)
        ]

        self.assertEqual(main(["ask", "Screen profit", "--full"], manager=manager, stdout=out, stderr=err), 0)

        self.assertIn("fixture-024", out.getvalue())
        self.assertNotIn("items; 15 omitted", out.getvalue())
        self.assertNotIn("Use --json for complete structured evidence.", out.getvalue())
        self.assertEqual(err.getvalue(), "")

    def test_json_and_full_modes_are_mutually_exclusive(self):
        manager, out, err = CLIStub(), StringIO(), StringIO()

        self.assertEqual(main(["ask", "Sales", "--json", "--full"], manager=manager, stdout=out, stderr=err), 2)

        self.assertEqual(manager.calls, [])
        self.assertEqual(out.getvalue(), "")
        self.assertIn("Invalid CLI syntax", err.getvalue())

    def test_help_uses_requested_stream_without_constructing_manager(self):
        for args in (["--help"], ["ask", "--help"], ["plan", "--help"], ["capabilities", "--help"]):
            out, err = StringIO(), StringIO()
            with patch("src.cli.main.FinancialManagerAgent", side_effect=AssertionError("Help must not construct manager")):
                self.assertEqual(main(args, stdout=out, stderr=err), 0)
            self.assertIn("usage:", out.getvalue())
            self.assertEqual(err.getvalue(), "")

    def test_help_output_failure_uses_controlled_error(self):
        class BrokenOutput(StringIO):
            def write(self, text):
                raise OSError("/private/fixture-secret")

        err = StringIO()
        self.assertEqual(main(["--help"], stdout=BrokenOutput(), stderr=err), 1)
        self.assertIn("Unable to complete", err.getvalue())
        self.assertNotIn("fixture-secret", err.getvalue())

    def test_interruption_returns_controlled_cancellation_without_traceback(self):
        class InterruptedManager(CLIStub):
            def ask(self, question):
                raise KeyboardInterrupt()

        for args in (["ask", "Sales"], ["ask", "Sales", "--json"]):
            out, err = StringIO(), StringIO()
            self.assertEqual(main(args, manager=InterruptedManager(), stdout=out, stderr=err), 1)
            self.assertEqual(out.getvalue(), "")
            self.assertEqual(err.getvalue(), "Command cancelled.\n")

    def test_capability_and_plan_json_equal_complete_manager_return_values(self):
        manager = CLIStub()
        for args, expected in ((["capabilities", "--json"], manager.catalog),
                               (["plan", "Find unusual profit values", "--json"], manager.plan_result)):
            out = StringIO()
            self.assertEqual(main(args, manager=manager, stdout=out, stderr=StringIO()), 0)
            self.assertEqual(json.loads(out.getvalue()), expected)

    def test_clarification_and_not_performed_steps_stay_visible(self):
        manager, out = CLIStub(), StringIO()
        manager.answer.update(execution_status="CLARIFICATION_REQUIRED", execution_state="NOT_PERFORMED", results=[],
                              clarification={"field": "dataset", "question": "Which dataset?", "choices": ["RG", "CF"]},
                              not_performed=[{"step_id": 2, "reason": "previous_step_not_answered"}])
        self.assertEqual(main(["ask", "Record count"], manager=manager, stdout=out, stderr=StringIO()), 0)
        self.assertIn("Clarification required:", out.getvalue())
        self.assertIn("Which dataset?", out.getvalue())
        self.assertIn("previous_step_not_answered", out.getvalue())

    def test_all_structured_application_outcomes_exit_normally(self):
        for status in ("SUCCESS", "PARTIAL", "NO_DATA", "INVALID_REQUEST", "UNSUPPORTED", "DATA_QUALITY_BLOCKER",
                       "CLARIFICATION_REQUIRED", "PROVIDER_UNAVAILABLE", "PROVIDER_ERROR", "CAPABILITY_UNAVAILABLE"):
            manager, out, err = CLIStub(), StringIO(), StringIO()
            manager.answer["execution_status"] = status
            self.assertEqual(main(["ask", "Sales", "--json"], manager=manager, stdout=out, stderr=err), 0)
            self.assertEqual(json.loads(out.getvalue())["execution_status"], status)
            self.assertEqual(err.getvalue(), "")

    def test_constructor_and_serialization_failures_do_not_emit_partial_output(self):
        for json_mode in ([], ["--json"]):
            out, err = StringIO(), StringIO()
            with patch("src.cli.main.FinancialManagerAgent", side_effect=RuntimeError("private-constructor")):
                self.assertEqual(main(["capabilities"] + json_mode, stdout=out, stderr=err), 1)
            self.assertEqual(out.getvalue(), "")
            self.assertNotIn("private-constructor", err.getvalue())
        for value in (Decimal("NaN"), Decimal("Infinity"), object()):
            manager, out, err = CLIStub(), StringIO(), StringIO()
            manager.answer["results"][0]["response"]["delegated_result"]["tool_result"]["result"]["amount"] = value
            self.assertEqual(main(["ask", "Sales", "--json"], manager=manager, stdout=out, stderr=err), 1)
            self.assertEqual(out.getvalue(), "")
            self.assertIn("Unable to complete", err.getvalue())

    def test_human_decimal_display_keeps_scale_without_float_cast(self):
        manager, out = CLIStub(), StringIO()
        manager.answer["results"][0]["response"]["delegated_result"]["tool_result"]["result"]["amount"] = Decimal("0.123456789123456789000")
        self.assertEqual(main(["ask", "Sales"], manager=manager, stdout=out, stderr=StringIO()), 0)
        self.assertIn('"0.123456789123456789000"', out.getvalue())

    def test_module_entry_point_help_is_available_without_installation(self):
        completed = subprocess.run([sys.executable, "-B", "-m", "src.cli", "--help"],
                                   cwd=ROOT, capture_output=True, text=True, check=False)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        for command in ("ask", "plan", "capabilities", "--json"):
            self.assertIn(command, completed.stdout)
        self.assertEqual(completed.stderr, "")

    def test_human_terminal_controls_are_escaped_without_mutating_evidence(self):
        manager, out, err = CLIStub(), StringIO(), StringIO()
        manager.answer["results"][0]["response"]["summary"] = "Fixture \x1b[2J\r\u202e text"
        before = deepcopy(manager.answer)
        self.assertEqual(main(["ask", "Sales"], manager=manager, stdout=out, stderr=err), 0)
        for char in ("\x1b", "\r", "\u202e"):
            self.assertNotIn(char, out.getvalue())
        self.assertIn("\\u001b", out.getvalue())
        self.assertEqual(manager.answer, before)

    def test_application_exceptions_have_fixed_message_without_private_details(self):
        class BrokenManager(CLIStub):
            def ask(self, question):
                raise RuntimeError("/private/fixture.db API_KEY=fixture-secret SELECT hidden FROM balances")

        for args in (["ask", "Sales"], ["ask", "Sales", "--json"]):
            out, err = StringIO(), StringIO()
            self.assertEqual(main(args, manager=BrokenManager(), stdout=out, stderr=err), 1)
            self.assertEqual(out.getvalue(), "")
            self.assertIn("Unable to complete", err.getvalue())
            for term in ("fixture-secret", "/private", "SELECT", "Traceback", "RuntimeError"):
                self.assertNotIn(term, err.getvalue())

    def test_invalid_syntax_is_controlled_without_echoing_arguments_or_invoking_manager(self):
        manager = CLIStub()
        for args in ([], ["ask"], ["plan"], ["ask", "unquoted", "words"],
                     ["/private/fixture-secret"], ["capabilities", "--api-key=fixture-secret"],
                     ["capabilities", "--js"]):
            with self.subTest(args=args):
                out, err = StringIO(), StringIO()
                self.assertEqual(main(args, manager=manager, stdout=out, stderr=err), 2)
                self.assertEqual(out.getvalue(), "")
                self.assertIn("Invalid CLI syntax", err.getvalue())
                self.assertNotIn("fixture-secret", err.getvalue())
                self.assertNotIn("Traceback", err.getvalue())
        self.assertEqual(manager.calls, [])

    def test_json_is_complete_exact_and_does_not_mutate_evidence(self):
        manager = CLIStub()
        exact = Decimal("-123.450000000000000000000001")
        evidence = manager.answer["results"][0]["response"]["delegated_result"]["tool_result"]
        evidence["result"]["amount"] = exact
        evidence["result"]["lineage"] = {"record_id": "fixture-007", "source_row_number": 7}
        before = deepcopy(manager.answer)
        for args in (["--json", "ask", "Sales"], ["ask", "Sales", "--json"]):
            out, err = StringIO(), StringIO()
            self.assertEqual(main(args, manager=manager, stdout=out, stderr=err), 0)
            parsed = json.loads(out.getvalue())
            displayed = parsed["results"][0]["response"]["delegated_result"]["tool_result"]
            self.assertEqual(displayed["result"]["amount"], "-123.450000000000000000000001")
            expected = deepcopy(before)
            expected["results"][0]["response"]["delegated_result"]["tool_result"]["result"]["amount"] = "-123.450000000000000000000001"
            self.assertEqual(parsed, expected)
            self.assertEqual(err.getvalue(), "")
        self.assertEqual(manager.answer, before)

    def test_ask_preserves_question_evidence_currency_warnings_and_coverage(self):
        manager, out, err = CLIStub(), StringIO(), StringIO()
        before = deepcopy(manager.answer)
        question = 'Sales where country="Canada"'
        self.assertEqual(main(["ask", question], manager=manager, stdout=out, stderr=err), 0)
        self.assertEqual(manager.calls, [("ask", question)])
        for text in ("PARTIAL", "123.000000000000000001", "UNKNOWN", '"excluded": 1', "fixture_missing", "Fixture limitation."):
            self.assertIn(text, out.getvalue())
        self.assertEqual(manager.answer, before)
        self.assertEqual(err.getvalue(), "")

    def test_plan_delegates_unchanged_question_and_displays_routing_without_execution(self):
        manager, out, err = CLIStub(), StringIO(), StringIO()
        question = "Find unusual profit values"
        self.assertEqual(main(["plan", question], manager=manager, stdout=out, stderr=err), 0)
        self.assertEqual(manager.calls, [("plan", question)])
        self.assertIn("Routing: BLOCKED", out.getvalue())
        self.assertIn("Analysis fixture: DEFERRED", out.getvalue())
        self.assertIn("Fixture readiness reason.", out.getvalue())
        self.assertEqual(err.getvalue(), "")

    def test_capabilities_displays_manager_metadata_without_a_second_registry(self):
        manager, out, err = CLIStub(), StringIO(), StringIO()
        code = main(["capabilities"], manager=manager, stdout=out, stderr=err)
        self.assertEqual(code, 0)
        self.assertEqual(manager.calls, [("capabilities",)])
        self.assertIn("Analysis fixture: DEFERRED", out.getvalue())
        self.assertIn("Fixture readiness reason.", out.getvalue())
        self.assertIn("Fixture limitation.", out.getvalue())
        self.assertEqual(err.getvalue(), "")


class CLIManagerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manager = FinancialManagerAgent()

    def run_cli(self, args):
        out, err = StringIO(), StringIO()
        code = main(args, manager=self.manager, stdout=out, stderr=err)
        return code, out.getvalue(), err.getvalue()

    def test_real_capabilities_come_from_registry(self):
        code, out, err = self.run_cli(["capabilities", "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out), self.manager.list_capabilities())
        self.assertEqual([c["status"] for c in json.loads(out)], ["AVAILABLE", "AVAILABLE", "BLOCKED", "BLOCKED"])
        self.assertEqual(err, "")

    def test_real_blocked_capabilities_display_documented_reason_without_crashing(self):
        for question, name, reason in (("Forecast cash flow next month", "Cash Flow Forecasting", "actual cash inflows/outflows"),
                                       ("What does invoice 123 say?", "Document Retrieval", "no approved real financial-document corpus")):
            code, out, err = self.run_cli(["ask", question])
            self.assertEqual(code, 0)
            self.assertIn(name + ": BLOCKED", out)
            self.assertIn(reason, out)
            self.assertIn("NOT_PERFORMED", out)
            self.assertEqual(err, "")

    def test_real_unknown_intent_and_unsupported_sql_stay_owned_by_manager(self):
        for question, status in (("Check my financial data", "CLARIFICATION_REQUIRED"),
                                 ("SELECT * FROM company_financials", "UNSUPPORTED"),
                                 ("Which company performed best?", "UNSUPPORTED")):
            code, out, err = self.run_cli(["ask", question, "--json"])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)["execution_status"], status)
            self.assertEqual(err, "")

    def test_real_plan_matches_manager_without_executing_a_financial_query(self):
        # Missing project root permits planning but would block any actual query.
        with tempfile.TemporaryDirectory() as root:
            manager = FinancialManagerAgent(financial_analysis=FinancialAnalysisAgent(FinancialCore(root)))
            out = StringIO()
            self.assertEqual(main(["plan", "Sales by country", "--json"], manager=manager, stdout=out, stderr=StringIO()), 0)
            self.assertEqual(json.loads(out.getvalue()), manager.plan("Sales by country"))
            self.assertEqual(json.loads(out.getvalue())["status"], "ROUTED")

    def test_real_partial_analysis_json_preserves_complete_response_offline(self):
        expected = self.manager.ask("Discount analysis")
        with patch("socket.socket", side_effect=AssertionError("No network")), \
             patch("socket.create_connection", side_effect=AssertionError("No network")):
            code, out, err = self.run_cli(["ask", "Discount analysis", "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out), expected)
        self.assertEqual(json.loads(out)["execution_status"], "PARTIAL")
        self.assertIn("UNKNOWN", out)
        self.assertEqual(err, "")

    def test_real_anomaly_json_keeps_evidence_and_source_files_unchanged(self):
        files = [p for p in (ROOT / "data").rglob('*') if p.is_file()]
        before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
        expected = self.manager.ask("Screen profit")
        code, out, err = self.run_cli(["ask", "Screen profit", "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out), expected)
        self.assertIn("CANDIDATE", out)
        self.assertIn("upper_fence", out)
        self.assertIn("lineage", out)
        self.assertEqual(err, "")
        self.assertEqual(before, {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT / "data").rglob('*') if p.is_file()})

    def test_actual_snapshot_error_keeps_step19_sanitization(self):
        with tempfile.TemporaryDirectory(prefix="step20-private-") as root:
            manager = FinancialManagerAgent(financial_analysis=FinancialAnalysisAgent(FinancialCore(root)))
            out, err = StringIO(), StringIO()
            self.assertEqual(main(["ask", "Sales"], manager=manager, stdout=out, stderr=err), 0)
            self.assertIn("DATA_QUALITY_BLOCKER", out.getvalue())
            self.assertNotIn(root, out.getvalue() + err.getvalue())
            self.assertNotIn("Traceback", out.getvalue() + err.getvalue())


if __name__ == "__main__":
    unittest.main()
