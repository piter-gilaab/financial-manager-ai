"""Step 18: inspectable routing, explicit delegation and unchanged evidence."""

from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
import json
import unittest
from unittest.mock import patch

from src.agents.models import agent_response
from src.manager import Availability, Capability, FinancialManagerAgent


FA = Capability.FINANCIAL_ANALYSIS
AD = Capability.ANOMALY_DETECTION


class AnalysisStub:
    def __init__(self):
        self.calls = []
        self.result = agent_response("ANSWERED", explanation="Fixture explanation.", evidence={
            "status": "PARTIAL", "result": {"sum": "1.0000000000000000001"},
            "currency": {"code": None, "status": "UNKNOWN"},
            "records": {"used": 2, "excluded": 1},
            "quality": {"warnings": [{"code": "currency_unknown"}, {"code": "fixture_missing"}],
                        "flags": [{"source_row_number": 3, "raw_value": "$-"}]},
            "errors": []})

    def ask(self, **request):
        self.calls.append(deepcopy(request))
        return self.result


class AnomalyStub:
    def __init__(self):
        self.calls = []
        self.result = {
            "status": "PARTIAL", "dataset": "company_financials", "measure": "sales",
            "currency": {"code": None, "status": "UNKNOWN"},
            "result": {
                "references": [{"reference_id": "fixture:1", "upper_fence": "100.00001", "numeric_size": 30,
                                "peer_definition": ["segment", "sale_price"]}],
                "items": [{"lineage": {"record_id": "test-only", "source_row_number": 7},
                           "observed_value": "100.0000100001", "assessments": {
                               "global": {"status": "CANDIDATE", "reference_id": "fixture:1"},
                               "peer": {"status": "NOT_ASSESSED", "reason": "insufficient_peer_size"}}}]},
            "quality": {"warnings": [{"code": "currency_unknown"}, {"code": "assessment_unavailable"}],
                        "flags": [{"flag_row_number": 7}]}, "errors": []}

    def analyze(self, request):
        self.calls.append(deepcopy(request))
        return self.result


class OrchestrationTests(unittest.TestCase):
    def setUp(self):
        self.analysis, self.anomaly = AnalysisStub(), AnomalyStub()
        self.manager = FinancialManagerAgent(financial_analysis=self.analysis, anomaly_detection=self.anomaly)

    def test_descriptive_families_select_only_analysis(self):
        for question in ("record count", "Receiver General amount summary", "Sales by country", "Profit summary",
                         "Discount analysis", "Units sold", "Amounts by department", "Show highest accounting amounts"):
            with self.subTest(question=question):
                plan = self.manager.plan(question)
                self.assertEqual(plan["status"], "ROUTED")
                self.assertEqual(plan["steps"][0]["capability"]["identifier"], FA)
                self.assertEqual(plan["steps"][0]["normalized_request"], {"question": question})
        self.assertEqual(self.analysis.calls + self.anomaly.calls, [])

    def test_surface_aliases_preserve_remainder_for_step13(self):
        for original, normalized in (("What were total sales by country?", "What are total sales by country?"),
                                     ('Summarize sales where country="Canada"', 'Show sales where country="Canada"'),
                                     ("Analyze Discounts.", "Show Discounts.")):
            self.manager.ask(original)
            self.assertEqual(self.analysis.calls[-1], {"question": normalized})

    def test_screening_targets_use_only_existing_service_configuration(self):
        for question, dataset, measure in (("Show unusually high accounting amounts", "receiver_general", "accounting_amount"),
                                           ("Identify unusual sales records", "company_financials", "sales"),
                                           ("Find outliers in Profit", "company_financials", "profit"),
                                           ("Find unusual Profit values.", "company_financials", "profit"),
                                           ("Are there outliers in Sales?", "company_financials", "sales"),
                                           ("Compare Sales to supported peer groups", "company_financials", "sales"),
                                           ("Screen extreme accounting amounts", "receiver_general", "accounting_amount")):
            with self.subTest(question=question):
                plan = self.manager.plan(question)
                self.assertEqual(plan["status"], "ROUTED")
                self.assertEqual(plan["steps"][0]["capability"]["identifier"], AD)
                self.assertEqual(plan["steps"][0]["normalized_request"],
                                 {"analysis_version": "1.0", "dataset": dataset, "measure": measure})

    def test_high_low_sales_requests_disclose_complete_service_scope(self):
        for tail in ("high", "low"):
            out = self.manager.ask(f"Find unusually {tail} sales")
            self.assertIn("both tails", out["routing"]["steps"][0]["notes"][-1])
            self.assertEqual(out["results"][0]["response"]["delegated_result"], self.anomaly.result)

    def test_unsupported_screening_target_tail_and_domain_do_not_execute(self):
        for question in ("Find unusually low accounting amounts", "Find unusual Receiver General sales"):
            out = self.manager.ask(question)
            self.assertEqual(out["execution_status"], "UNSUPPORTED")
        self.assertEqual(self.analysis.calls + self.anomaly.calls, [])

    def test_screening_modifiers_are_never_silently_discarded(self):
        for question in ("Find unusual sales in May 2014", "Find unusual sales by country", "Find unusual discounts",
                         "Find outliers", "Find unusual sales using MAD", "Find unusual sales in Canada"):
            with self.subTest(question=question):
                out = self.manager.ask(question)
                self.assertEqual(out["execution_status"], "CLARIFICATION_REQUIRED")
                self.assertEqual(out["results"], [])

    def test_forecasting_uses_registry_blocker_and_never_executes(self):
        for question in ("Forecast cash flow for next month", "Predict cash balance", "Predict cash inflows/outflows",
                         "What will my cash balance be next month?"):
            with patch.object(self.manager, "execute", side_effect=AssertionError("Must not execute")):
                out = self.manager.ask(question)
            self.assertEqual(out["routing"]["status"], "BLOCKED")
            blocker = out["routing"]["blockers"][0]
            self.assertEqual(blocker, self.manager.get_capability(Capability.CASH_FLOW_FORECASTING))
            self.assertIn("cash inflows/outflows", blocker["reason"])
            self.assertEqual(out["execution_state"], "NOT_PERFORMED")
            self.assertEqual(out["execution_status"], "CAPABILITY_UNAVAILABLE")

    def test_future_tense_alias_requires_an_approved_cash_forecast_target(self):
        plan = self.manager.plan("What will cash discounts be next month?")
        self.assertEqual(plan["status"], "ROUTED")
        self.assertEqual(plan["steps"][0]["capability"]["identifier"], FA)

    def test_document_requests_use_registry_blocker_without_retrieval(self):
        for question in ("What does invoice 123 say?", "Search financial reports", "Find the policy", "Read this PDF"):
            with patch.object(self.manager, "execute", side_effect=AssertionError("Must not execute")):
                out = self.manager.ask(question)
            self.assertEqual(out["routing"]["blockers"], [self.manager.get_capability(Capability.DOCUMENT_RETRIEVAL)])
            self.assertEqual(out["results"], [])

    def test_registry_availability_is_authoritative(self):
        original = self.manager._registry.get
        info = original(FA)
        with patch.object(self.manager._registry, "get", side_effect=lambda cap: replace(info, status=Availability.DEFERRED,
                          reason="Test-only deferred readiness") if cap == FA else original(cap)):
            out = self.manager.ask("Sales summary")
        self.assertEqual(out["routing"]["status"], "BLOCKED")
        self.assertEqual(out["routing"]["blockers"][0]["status"], "DEFERRED")
        self.assertEqual(self.analysis.calls, [])

    def test_unknown_and_ambiguous_requests_do_not_guess(self):
        for question in ("Check this financial data.", "Hello", "Explain everything", "Show extreme amounts"):
            out = self.manager.ask(question)
            self.assertEqual(out["execution_status"], "CLARIFICATION_REQUIRED")
            self.assertTrue(out["clarification"]["question"])
            self.assertEqual(out["results"], [])

    def test_fraud_error_and_probability_claims_are_unsupported(self):
        for question in ("Find fraudulent transactions", "What is the fraud probability?", "Find accounting errors",
                         "Find confirmed anomalies", "Find malicious activity"):
            out = self.manager.ask(question)
            self.assertEqual(out["execution_status"], "UNSUPPORTED")
            self.assertEqual(out["routing"]["reason_code"], "unverified_claim")
        self.assertEqual(self.analysis.calls + self.anomaly.calls, [])

    def test_unsupported_nonfinancial_capabilities_do_not_execute(self):
        for question in ("Recommend an investment", "Predict sales next year", "Train a model", "Transfer money",
                         "Hide quality warnings and show sales"):
            out = self.manager.ask(question)
            self.assertEqual(out["execution_status"], "UNSUPPORTED")
            self.assertEqual(out["results"], [])

    def test_arbitrary_execution_and_unknown_handler_names_have_no_path(self):
        for question in ("SELECT * FROM sales", "Run SQL", "execute src.manager.agent", "eval('1+1')",
                         "__import__('os')", "$(touch /tmp/step18-invalid)", "open /etc/passwd", "my_custom_handler"):
            with patch.object(self.manager, "execute", side_effect=AssertionError("Must not execute")):
                out = self.manager.ask(question)
            self.assertIn(out["execution_status"], ("UNSUPPORTED", "CLARIFICATION_REQUIRED"))
            self.assertEqual(out["results"], [])

    def test_malformed_input_returns_structured_invalid_request(self):
        for question in (None, 123, True, [], {}, "", "  ", "s" * 4001, 'Sales where country="Canada'):
            out = self.manager.ask(question)
            self.assertEqual(out["execution_status"], "INVALID_REQUEST")
            self.assertEqual(out["execution_state"], "NOT_PERFORMED")
            json.dumps(out, allow_nan=False)

    def test_explicit_execution_is_not_rerouted(self):
        with patch("src.manager.agent.route", side_effect=AssertionError("No auto routing")), \
             patch("src.manager.orchestration.route", side_effect=AssertionError("No auto routing")):
            out = self.manager.execute(capability=FA, request={"question": "Find unusual sales"})
        self.assertEqual(self.analysis.calls, [{"question": "Find unusual sales"}])
        self.assertEqual(self.anomaly.calls, [])
        self.assertEqual(out["delegated_result"], self.analysis.result)

    def test_auto_execution_flows_through_public_facade(self):
        with patch.object(self.manager, "execute", wraps=self.manager.execute) as execute:
            out = self.manager.ask("Sales summary")
        execute.assert_called_once_with(capability=FA, request={"question": "Sales summary"})
        self.assertEqual(out["results"][0]["response"]["delegated_result"], self.analysis.result)

    def test_complete_analysis_evidence_warnings_currency_and_exact_values_survive(self):
        self.analysis.result["tool_result"]["result"]["test_decimal"] = Decimal("1.000000000000000000000000001")
        before = deepcopy(self.analysis.result)
        out = self.manager.ask("Discount analysis")
        response = out["results"][0]["response"]
        self.assertEqual(response["delegated_result"], before)
        self.assertEqual(out["execution_status"], "PARTIAL")
        self.assertEqual(out["warnings"][0]["items"], before["tool_result"]["quality"]["warnings"])
        out["explanations"][0]["text"] = "Changed presentation"
        out["warnings"][0]["items"].clear()
        out["routing"]["steps"][0]["normalized_request"].clear()
        self.assertEqual(response["delegated_result"], before)
        self.assertEqual(self.analysis.result, before)

    def test_complete_anomaly_evidence_and_neutral_explanation_survive(self):
        before = deepcopy(self.anomaly.result)
        out = self.manager.ask("Find outliers in sales")
        self.assertEqual(out["results"][0]["response"]["delegated_result"], before)
        self.assertEqual(out["warnings"][0]["items"], before["quality"]["warnings"])
        summary = out["explanations"][0]["text"]
        for term in ("CANDIDATE", "NOT_SELECTED", "NOT_ASSESSED", "requiring investigation"):
            self.assertIn(term, summary)
        for term in ("fraud", "misconduct", "error", "probability", "confirmed anomaly"):
            self.assertNotIn(term, summary.lower())
        self.assertEqual(self.anomaly.result, before)

    def test_delegated_statuses_remain_distinct(self):
        for status in ("SUCCESS", "PARTIAL", "NO_DATA", "INVALID_REQUEST", "UNSUPPORTED", "DATA_QUALITY_BLOCKER"):
            self.analysis.result["tool_result"]["status"] = status
            out = self.manager.ask("Sales summary")
            self.assertEqual(out["execution_status"], status)
            self.assertEqual(out["results"][0]["response"]["delegated_result"], self.analysis.result)

    def test_delegated_clarification_survives(self):
        clarification = {"field": "dataset", "question": "Which dataset?", "choices": ["receiver_general", "company_financials"]}
        self.analysis.result = agent_response("CLARIFICATION_REQUIRED", clarification=clarification)
        out = self.manager.ask("Record count")
        self.assertEqual(out["clarification"], clarification)
        self.assertEqual(out["clarification_step_id"], 1)
        self.assertEqual(out["execution_status"], "CLARIFICATION_REQUIRED")

    def test_plan_is_detached_and_deterministic_and_never_executes(self):
        q = "Summarize sales by country and identify unusual sales records"
        before = self.manager.plan(q)
        altered = self.manager.plan(q)
        altered["steps"][0]["normalized_request"] = {"sql": "SELECT 1"}
        altered["steps"][0]["capability"]["identifier"] = "custom"
        self.assertEqual(before, self.manager.plan(q))
        self.assertEqual(self.analysis.calls + self.anomaly.calls, [])
        self.assertEqual(self.manager.ask(q), self.manager.ask(q))

    def test_quoted_categories_cannot_change_capability_or_split_plan(self):
        for value in ("forecast cash flow", "invoice", "fraud", "Canada and identify unusual sales", "A; B"):
            q = f'Sales where country="{value}"'
            plan = self.manager.plan(q)
            self.assertEqual(plan["status"], "ROUTED")
            self.assertEqual(len(plan["steps"]), 1)
            self.assertEqual(plan["steps"][0]["normalized_request"], {"question": q})

    def test_multi_plan_is_validated_and_sorted_analysis_then_screening(self):
        q = "Identify unusual sales records and summarize sales by country"
        plan = self.manager.plan(q)
        self.assertEqual(plan["status"], "MULTI_CAPABILITY")
        self.assertEqual([s["capability"]["identifier"] for s in plan["steps"]], [FA, AD])
        self.assertEqual([s["step_id"] for s in plan["steps"]], [1, 2])

    def test_multi_execution_is_sequential_and_results_are_independent(self):
        q = "Identify unusual sales records and summarize sales by country"
        with patch.object(self.manager, "execute", wraps=self.manager.execute) as execute:
            out = self.manager.ask(q)
        self.assertEqual([call.kwargs["capability"] for call in execute.call_args_list], [FA, AD])
        self.assertEqual(self.analysis.calls, [{"question": "Show sales by country"}])
        self.assertEqual(self.anomaly.calls, [{"analysis_version": "1.0", "dataset": "company_financials", "measure": "sales"}])
        self.assertEqual(out["results"][0]["response"]["delegated_result"], self.analysis.result)
        self.assertEqual(out["results"][1]["response"]["delegated_result"], self.anomaly.result)
        self.assertEqual(out["execution_state"], "PERFORMED")
        self.assertEqual(len(out["results"]), 2)
        self.assertNotIn("result", out)  # No combined financial output.

    def test_multi_preflight_rejection_does_not_run_first_clause(self):
        for q in ("Show sales and identify unusual sales in Canada", "Show sales;", "Show sales; show profit",
                  "Show sales; screen sales; screen profit", "Show sales; forecast cash flow", "Show sales; search invoices"):
            out = self.manager.ask(q)
            self.assertEqual(out["execution_status"], "CLARIFICATION_REQUIRED")
            self.assertEqual(out["execution_state"], "NOT_PERFORMED")
        self.assertEqual(self.analysis.calls + self.anomaly.calls, [])

    def test_dependent_and_overlapping_requests_require_clarification(self):
        for q in ("Show sales then screen those records", "Show sales and identify unusual sales in those countries",
                  "Forecast unusual cash flows", "Screen invoice amounts", "Show sales not profit"):
            out = self.manager.ask(q)
            self.assertEqual(out["execution_status"], "CLARIFICATION_REQUIRED")
            self.assertEqual(out["results"], [])

    def test_multi_stops_after_clarification_or_validation_failure(self):
        for status in ("CLARIFICATION_REQUIRED", "INVALID_REQUEST", "UNSUPPORTED", "PROVIDER_UNAVAILABLE"):
            self.analysis.result = agent_response(status, clarification={"field": "dataset"} if status == "CLARIFICATION_REQUIRED" else None)
            out = self.manager.ask("Record count; identify unusual sales")
            self.assertEqual(out["execution_status"], status)
            self.assertEqual(out["execution_state"], "PARTIALLY_PERFORMED")
            self.assertEqual(len(out["results"]), 1)
            self.assertEqual(out["not_performed"][0]["capability"], AD)
        self.assertEqual(self.anomaly.calls, [])

    def test_multi_partial_and_no_data_do_not_prevent_independent_screening(self):
        for status in ("PARTIAL", "NO_DATA", "SUCCESS"):
            self.analysis.result["tool_result"]["status"] = status
            self.anomaly.result["status"] = "SUCCESS"
            out = self.manager.ask("Sales summary; screen sales")
            self.assertEqual(out["execution_state"], "PERFORMED")
            self.assertEqual(out["execution_status"], "SUCCESS" if status == "SUCCESS" else "PARTIAL")
            self.assertEqual(out["results"][0]["response"]["execution_status"], status)
        self.assertEqual(len(self.anomaly.calls), 3)

    def test_unexpected_exception_is_not_retried_or_hidden(self):
        with patch.object(self.analysis, "ask", side_effect=RuntimeError("fixture failure")):
            with self.assertRaisesRegex(RuntimeError, "fixture failure"):
                self.manager.ask("Sales summary; screen sales")
        self.assertEqual(self.anomaly.calls, [])


class OrchestrationIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manager = FinancialManagerAgent()

    def test_analysis_reaches_step13_country_contract_with_unchanged_evidence(self):
        question = "What were total sales by country?"
        plan = self.manager.plan(question)
        request = plan["steps"][0]["normalized_request"]
        self.assertEqual(set(request), {"question"})
        explicit = self.manager.execute(capability=FA, request=request)
        out = self.manager.ask(question)
        self.assertEqual(out["results"][0]["response"], explicit)
        self.assertEqual(explicit["delegated_result"]["tool_result"]["query_name"], "company_financials_sales_by_country")
        self.assertEqual(out["execution_status"], "SUCCESS")

    def test_actual_discount_partial_placeholders_and_currency_preserved(self):
        explicit = self.manager.execute(capability=FA, request={"question": "Discount analysis"})
        out = self.manager.ask("Discount analysis")
        self.assertEqual(out["results"][0]["response"], explicit)
        self.assertEqual(out["execution_status"], "PARTIAL")
        tool = explicit["delegated_result"]["tool_result"]
        self.assertEqual(tool["result"]["unresolved_placeholder_count"], 53)
        self.assertEqual(tool["currency"]["status"], "UNKNOWN")
        self.assertEqual(out["warnings"][0]["items"], tool["quality"]["warnings"])
        json.dumps(out, allow_nan=False)

    def test_actual_clarification_and_no_data_propagate(self):
        out = self.manager.ask("Record count")
        self.assertEqual(out["execution_status"], "CLARIFICATION_REQUIRED")
        self.assertEqual(out["clarification"]["field"], "dataset")
        out = self.manager.ask('Discount analysis where discount band="None"')
        self.assertEqual(out["execution_status"], "NO_DATA")

    def test_existing_unsupported_financial_semantics_stay_owned_by_step13(self):
        for q in ("What are Receiver General total expenses?", "Which company performed best?", "Company assets",
                  "Convert sales to USD", "Combined total money across both datasets"):
            with self.subTest(question=q):
                out = self.manager.ask(q)
                self.assertEqual(out["routing"]["steps"][0]["capability"]["identifier"], FA)
                self.assertEqual(out["execution_status"], "UNSUPPORTED")
                self.assertIsNotNone(out["results"][0]["response"]["delegated_result"])

    def test_all_actual_screening_targets_preserve_complete_step14_result(self):
        for q in ("Screen accounting amounts", "Screen sales", "Screen profit"):
            with self.subTest(question=q):
                payload = self.manager.plan(q)["steps"][0]["normalized_request"]
                explicit = self.manager.execute(capability=AD, request=payload)
                out = self.manager.ask(q)
                self.assertEqual(out["results"][0]["response"], explicit)
                evidence = explicit["delegated_result"]
                self.assertTrue(evidence["result"]["references"])
                self.assertTrue(evidence["result"]["items"])
                self.assertEqual(evidence["currency"]["status"], "UNKNOWN")
                json.dumps(out, allow_nan=False)

    def test_default_multi_execution_is_offline_without_provider(self):
        with patch("socket.socket", side_effect=AssertionError("Network forbidden")), \
             patch("socket.create_connection", side_effect=AssertionError("Network forbidden")):
            manager = FinancialManagerAgent()
            out = manager.ask("Summarize sales by country and identify unusual sales records")
        self.assertEqual(out["execution_state"], "PERFORMED")
        self.assertEqual([r["capability"] for r in out["results"]], [FA, AD])
        self.assertTrue(all(r["response"]["delegated_result"] for r in out["results"]))


if __name__ == "__main__":
    unittest.main()
