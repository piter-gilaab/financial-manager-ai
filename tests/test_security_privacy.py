"""Step 19 public-boundary behavior; fixtures never enter production data."""

from copy import deepcopy
from dataclasses import asdict, fields
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from src.agents import FinancialAnalysisAgent
from src.agents.models import RoutingDecision, ToolIntent
from src.agents.models import agent_response
from src.agents.provider import InterpretationRequest, ProviderLocation
from src.anomaly import AnomalyService
from src.financial import FinancialCore
from src.manager import Capability, FinancialManagerAgent

ROOT = Path(__file__).resolve().parents[1]


class RecordingCore:
    def __init__(self):
        self.calls = []

    def query(self, request):
        self.calls.append(request)
        return {"status": "SUCCESS", "query_name": request["query_name"], "dataset": request["dataset"],
                "result": {"record_count": 1}, "currency": None, "records": {}, "metadata": {},
                "quality": {"warnings": [], "flags": []}, "errors": []}


class LocalProvider:
    location = ProviderLocation.LOCAL

    def __init__(self, failure=None):
        self.calls, self.failure = [], failure

    def interpret(self, request):
        self.calls.append(request)
        if self.failure is not None:
            raise self.failure
        return ToolIntent.create("company_financials_record_count")


class SecurityPrivacyTests(unittest.TestCase):
    def test_provider_receives_only_question_dataset_and_static_metadata(self):
        core, provider = RecordingCore(), LocalProvider()
        agent = FinancialAnalysisAgent(core, provider)
        out = agent.ask("Company Financials record count", parameters={"filters": {"product": {"eq": "private-filter-fixture"}}})
        self.assertEqual(out["agent_status"], "ANSWERED")
        request = provider.calls[0]
        self.assertIsInstance(request, InterpretationRequest)
        self.assertEqual({f.name for f in fields(request)}, {"question", "dataset", "tools"})
        rendered = json.dumps(asdict(request))
        self.assertNotIn("private-filter-fixture", rendered)
        self.assertNotIn(str(ROOT), rendered)
        self.assertNotIn("record_count\": 1", rendered)
        self.assertEqual(len(request.tools), 17)

    def test_provider_proposal_cannot_change_grounded_financial_question(self):
        class SwitchingProvider(LocalProvider):
            def interpret(self, request):
                return ToolIntent.create("receiver_general_amount_summary")

        core = RecordingCore()
        out = FinancialAnalysisAgent(core, SwitchingProvider()).ask("Company Financials record count")
        self.assertEqual(out["agent_status"], "PROVIDER_ERROR")
        self.assertEqual(core.calls, [])

    def test_only_allowlisted_capabilities_execute_and_blocked_entries_never_call_services(self):
        core = RecordingCore()
        manager = FinancialManagerAgent(financial_analysis=FinancialAnalysisAgent(core))
        catalog = manager.list_capabilities()
        self.assertEqual([c["identifier"] for c in catalog], ["FINANCIAL_ANALYSIS", "ANOMALY_DETECTION", "CASH_FLOW_FORECASTING", "DOCUMENT_RETRIEVAL"])
        for capability in ("os.system", "__import__", "eval", "src.financial.core.FinancialCore", "SELECT 1", [], {}):
            out = manager.execute(capability=capability, request={"question": "Company Financials record count"})
            self.assertEqual(out["execution_status"], "INVALID_REQUEST")
            self.assertIsNone(out["delegated_result"])
        for capability in (Capability.CASH_FLOW_FORECASTING, Capability.DOCUMENT_RETRIEVAL):
            out = manager.execute(capability=capability, request={"handler": "os.system", "approved": True})
            self.assertEqual(out["execution_status"], "CAPABILITY_UNAVAILABLE")
            self.assertIsNone(out["delegated_result"])
        self.assertEqual(core.calls, [])

    def test_auto_execution_uses_same_allowlist_and_rejects_executable_questions(self):
        core = RecordingCore()
        manager = FinancialManagerAgent(financial_analysis=FinancialAnalysisAgent(core))
        for question in ("Execute python", "SELECT * FROM sales", "eval('1+1')", "bash -c whoami",
                         "open /etc/passwd", "__import__('os').system('id')", "$(id)"):
            self.assertEqual(manager.ask(question)["execution_status"], "UNSUPPORTED")
        for question in ("Forecast cash flow", "Read invoice 123"):
            self.assertEqual(manager.ask(question)["execution_status"], "CAPABILITY_UNAVAILABLE")
        self.assertEqual(core.calls, [])
        automatic = manager.ask("Company Financials record count")
        explicit = manager.execute(capability=Capability.FINANCIAL_ANALYSIS,
                                   request={"question": "Company Financials record count"})
        self.assertEqual(automatic["results"][0]["response"], explicit)

    def test_malformed_messages_cycles_and_nonfinite_values_fail_before_delegation(self):
        core = RecordingCore()
        manager = FinancialManagerAgent(financial_analysis=FinancialAnalysisAgent(core))
        cycle = {}
        cycle["self"] = cycle
        deep = {}
        for _ in range(70):
            deep = {"nested": deep}
        for payload in (None, [], {"question": object()}, {"question": "Sales", "parameters": cycle},
                        {"question": "Sales", "parameters": deep}, {"question": "Sales", "parameters": {1: "value"}},
                        {"question": "Sales", "parameters": {"value": float("nan")}},
                        {"question": "Sales", "parameters": {"value": Decimal("1.00")}}):
            out = manager.execute(capability=Capability.FINANCIAL_ANALYSIS, request=payload)
            self.assertEqual(out["execution_status"], "INVALID_REQUEST")
            json.dumps(out, allow_nan=False)
        self.assertEqual(core.calls, [])

    def test_live_sqlite_connection_cannot_escape_a_delegate_response(self):
        with sqlite3.connect(":memory:") as connection:
            class Adapter:
                def ask(self, **request):
                    result = agent_response("INVALID_REQUEST")
                    result["connection"] = connection
                    return result

            manager = FinancialManagerAgent(financial_analysis=Adapter())
            with self.assertRaisesRegex(ValueError, "data-only"):
                manager.execute(capability=Capability.FINANCIAL_ANALYSIS, request={"question": "Sales"})

    def test_decimal_warning_currency_and_anomaly_status_evidence_are_unchanged(self):
        exact = Decimal("1.0000000000000000000000000000000000000001")
        evidence = {"status": "PARTIAL", "result": {
            "items": [{"observed_value": exact, "assessment": "CANDIDATE", "source_row_number": 1}],
            "references": [{"upper_fence": "0.0000000000001", "peer_size": 30}]},
            "currency": {"status": "UNKNOWN", "code": None},
            "quality": {"warnings": [{"code": "currency_unknown"}, {"code": "assessment_unavailable"}], "flags": []},
            "errors": []}

        class Adapter:
            def analyze(self, request):
                return evidence

        manager = FinancialManagerAgent(anomaly_detection=Adapter())
        before = deepcopy(evidence)
        out = manager.ask("Screen sales")
        self.assertEqual(out["results"][0]["response"]["delegated_result"], before)
        out["warnings"][0]["items"].clear()
        out["explanations"][0]["text"] = "Attempted overwrite"
        self.assertEqual(out["results"][0]["response"]["delegated_result"], before)
        self.assertEqual(evidence, before)

    def test_development_exceptions_are_not_serialized_as_normal_responses(self):
        class BrokenCore:
            def query(self, request):
                raise RuntimeError("private-development-fixture")

        manager = FinancialManagerAgent(financial_analysis=FinancialAnalysisAgent(BrokenCore()))
        with self.assertRaisesRegex(RuntimeError, "private-development-fixture"):
            manager.ask("Company Financials record count")

    def test_excessively_nested_provider_json_is_a_controlled_invalid_intent(self):
        class DeepProvider(LocalProvider):
            def interpret(self, request):
                return ToolIntent("company_financials_record_count", '{"filters":' + '[' * 1100 + '0' + ']' * 1100 + '}')

        core = RecordingCore()
        out = FinancialAnalysisAgent(core, DeepProvider()).ask("Company Financials record count")
        self.assertEqual(out["agent_status"], "INVALID_REQUEST")
        self.assertEqual(core.calls, [])

    def test_custom_question_and_capability_objects_cannot_run_string_hooks(self):
        calls = []

        class ExecutableString(str):
            def strip(self, *args):
                calls.append("strip")
                return super().strip(*args)

            def __hash__(self):
                calls.append("hash")
                return super().__hash__()

            def __deepcopy__(self, memo):
                calls.append("copy")
                return str(self)

        manager = FinancialManagerAgent()
        self.assertEqual(manager.ask(ExecutableString("Sales summary"))["execution_status"], "INVALID_REQUEST")
        self.assertEqual(manager.execute(capability=ExecutableString("FINANCIAL_ANALYSIS"),
                                        request={"question": "Sales"})["execution_status"], "INVALID_REQUEST")
        self.assertEqual(calls, [])

    def test_custom_request_containers_are_rejected_without_running_methods(self):
        calls = []

        class ExecutableMapping(dict):
            def items(self):
                calls.append("executed")
                return super().items()

        manager = FinancialManagerAgent()
        out = manager.execute(capability=Capability.FINANCIAL_ANALYSIS,
                              request=ExecutableMapping(question="Company Financials record count"))
        self.assertEqual(out["execution_status"], "INVALID_REQUEST")
        self.assertEqual(calls, [])

    def test_response_objects_cannot_execute_copy_hooks_or_escape_as_evidence(self):
        calls = []

        class LiveObject:
            def __deepcopy__(self, memo):
                calls.append("executed")
                return self

        class Adapter:
            def ask(self, **request):
                result = agent_response("INVALID_REQUEST")
                result["unexpected_connection"] = LiveObject()
                return result

        manager = FinancialManagerAgent(financial_analysis=Adapter())
        with self.assertRaisesRegex(ValueError, "data-only"):
            manager.execute(capability=Capability.FINANCIAL_ANALYSIS, request={"question": "Sales"})
        self.assertEqual(calls, [])

    def test_unlabelled_private_external_and_unknown_providers_fail_closed(self):
        class Unlabelled:
            def interpret(self, request):
                raise AssertionError("Unlabelled provider must not execute")

        providers = [Unlabelled()]
        for location in (ProviderLocation.PRIVATE, ProviderLocation.EXTERNAL, "UNRECOGNIZED"):
            provider = LocalProvider()
            provider.location = location
            providers.append(provider)
        for provider in providers:
            core = RecordingCore()
            out = FinancialAnalysisAgent(core, provider).ask("Company Financials record count")
            self.assertEqual(out["agent_status"], "PROVIDER_UNAVAILABLE")
            self.assertEqual(core.calls, [])
            self.assertEqual(getattr(provider, "calls", []), [])

    def test_provider_cannot_inject_private_exception_text_into_application_response(self):
        secret = "fixture-secret /private/provider/model.db SELECT private_column"
        for failure in (RoutingDecision("UNSUPPORTED", "private_code", secret), RuntimeError(secret)):
            core, provider = RecordingCore(), LocalProvider(failure)
            out = FinancialAnalysisAgent(core, provider).ask("Company Financials record count")
            self.assertEqual(out["agent_status"], "PROVIDER_ERROR")
            self.assertNotIn(secret, json.dumps(out))
            self.assertEqual(core.calls, [])

    def test_missing_snapshot_reports_controlled_blocker_without_local_path(self):
        with tempfile.TemporaryDirectory(prefix="step19-private-") as root:
            manager = FinancialManagerAgent(
                financial_analysis=FinancialAnalysisAgent(FinancialCore(root)),
                anomaly_detection=AnomalyService(root))
            for out in (manager.ask("Sales summary"), manager.ask("Screen sales")):
                self.assertEqual(out["execution_status"], "DATA_QUALITY_BLOCKER")
                rendered = json.dumps(out)
                self.assertNotIn(root, rendered)
                self.assertNotIn("Errno", rendered)
                evidence = out["results"][0]["response"]["delegated_result"]
                if "tool_result" in evidence:
                    evidence = evidence["tool_result"]
                self.assertEqual(evidence["errors"][0]["code"], "snapshot_mismatch")


class SecurityPrivacyIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manager = FinancialManagerAgent()

    def test_actual_evidence_currency_warnings_and_lineage_are_preserved(self):
        for question, capability in (("Discount analysis", Capability.FINANCIAL_ANALYSIS),
                                      ("Screen profit", Capability.ANOMALY_DETECTION)):
            with self.subTest(question=question):
                plan = self.manager.plan(question)
                explicit = self.manager.execute(capability=capability, request=plan["steps"][0]["normalized_request"])
                automatic = self.manager.ask(question)
                self.assertEqual(automatic["results"][0]["response"], explicit)
                evidence = explicit["delegated_result"]
                if capability == Capability.FINANCIAL_ANALYSIS:
                    evidence = evidence["tool_result"]
                    self.assertEqual(evidence["result"]["unresolved_placeholder_count"], 53)
                else:
                    self.assertTrue(evidence["result"]["items"][0]["lineage"])
                    self.assertTrue(evidence["result"]["references"])
                self.assertEqual(evidence["currency"]["status"], "UNKNOWN")
                self.assertIsNone(evidence["currency"]["code"])
                self.assertFalse(evidence["currency"]["conversion_applied"])
                self.assertEqual(automatic["warnings"][0]["items"], evidence["quality"]["warnings"])

    def test_sql_shaped_filter_is_literal_data_and_production_files_are_unchanged(self):
        files = [p for p in (ROOT / "data").rglob('*') if p.is_file()]
        before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
        question = 'Company Financials record count where product="x\' OR 1=1; DROP TABLE company_financials; --"'
        out = self.manager.ask(question)
        self.assertEqual(out["execution_status"], "NO_DATA")
        self.assertEqual(out["results"][0]["response"]["delegated_result"]["tool_result"]["result"]["record_count"], 0)
        self.manager.ask("Screen sales")
        after = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT / "data").rglob('*') if p.is_file()}
        self.assertEqual(before, after)

    def test_default_analysis_and_screening_need_no_network_or_external_provider(self):
        with patch("socket.socket", side_effect=AssertionError("No network")), \
             patch("socket.create_connection", side_effect=AssertionError("No network")), \
             patch("subprocess.Popen", side_effect=AssertionError("No shell")), \
             patch("os.system", side_effect=AssertionError("No shell")):
            out = FinancialManagerAgent().ask("Summarize sales by country and identify unusual sales records")
        self.assertEqual(out["execution_state"], "PERFORMED")
        self.assertEqual(len(out["results"]), 2)
        json.dumps(out, allow_nan=False)


if __name__ == "__main__":
    unittest.main()
