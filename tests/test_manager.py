"""Step 17 public facade: explicit delegation, unchanged evidence and offline execution."""

from copy import deepcopy
from dataclasses import FrozenInstanceError
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from src.agents import FinancialAnalysisAgent
from src.agents.models import agent_response
from src.anomaly import AnomalyService
from src.manager import Availability, Capability, FinancialManagerAgent
from src.manager.registry import CAPABILITIES


ROOT = Path(__file__).resolve().parents[1]
FA = Capability.FINANCIAL_ANALYSIS
AD = Capability.ANOMALY_DETECTION


def analysis_fixture(status="PARTIAL"):
    tool = {"query_name": "fixture_contract", "status": status, "dataset": "company_financials",
            "result": {"amount": "1.001000000000000001", "record_count": 2},
            "currency": {"status": "UNKNOWN", "code": None},
            "records": {"used": 2, "excluded": 1},
            "quality": {"warnings": [{"code": "fixture_missing", "affected_records": 1},
                                     {"code": "currency_unknown", "affected_records": None}],
                        "flags": [{"flag_row_number": 99, "raw_value": "$-"}]},
            "metadata": {"fixture": True, "source_sha256": "test-only"}, "errors": []}
    if status in ("INVALID_REQUEST", "UNSUPPORTED", "DATA_QUALITY_BLOCKER"):
        tool["errors"] = [{"code": "fixture_rejection", "field": "test", "message": "Test-only rejection."}]
    return agent_response("ANSWERED" if status in ("SUCCESS", "PARTIAL", "NO_DATA") else "TOOL_REJECTED",
                          evidence=tool, explanation="Original fixture explanation.")


def anomaly_fixture(status="PARTIAL"):
    return {"analysis_version": "1.0", "service": "financial_anomaly_detection", "status": status,
            "dataset": "company_financials", "measure": "profit", "currency": {"status": "UNKNOWN", "code": None},
            "result": {"references": [{"reference_id": "peer:1", "upper_fence": "45.000", "numeric_size": 30,
                                       "peer_definition": ["segment", "sale_price"], "peer_values": {"segment": "Test", "sale_price": "10.00"}}],
                       "items": [{"lineage": {"record_id": "fixture-only", "source_row_number": 1},
                                  "observed_value": "45.0000000001", "assessments": {
                                      "global": {"status": "CANDIDATE", "reference_id": "peer:1"},
                                      "peer": {"status": "NOT_ASSESSED", "reason": "fixture_reason"}}}],
                       "summary": {"global": {"candidate": 1}, "peer": {"not_assessed": 1}}},
            "quality": {"warnings": [{"code": "currency_unknown"}, {"code": "assessment_unavailable"}],
                        "flags": [{"flag_row_number": 3, "relevant": True}]},
            "records": {"candidates": 1}, "metadata": {"method": {"minimum_numeric_records": 30}}, "errors": []}


class StubAnalysis:
    def __init__(self, result=None):
        self.result = analysis_fixture() if result is None else result
        self.calls = []

    def ask(self, **payload):
        self.calls.append(deepcopy(payload))
        return self.result


class StubAnomaly:
    def __init__(self, result=None):
        self.result = anomaly_fixture() if result is None else result
        self.calls = []

    def analyze(self, payload):
        self.calls.append(deepcopy(payload))
        return self.result


class ManagerTests(unittest.TestCase):
    def setUp(self):
        self.analysis, self.anomaly = StubAnalysis(), StubAnomaly()
        self.manager = FinancialManagerAgent(financial_analysis=self.analysis, anomaly_detection=self.anomaly)

    def test_exact_four_capabilities_and_truthful_availability(self):
        catalog = self.manager.list_capabilities()
        self.assertEqual([(c["identifier"], c["status"]) for c in catalog], [
            ("FINANCIAL_ANALYSIS", "AVAILABLE"), ("ANOMALY_DETECTION", "AVAILABLE"),
            ("CASH_FLOW_FORECASTING", "BLOCKED"), ("DOCUMENT_RETRIEVAL", "BLOCKED")])
        for info in catalog:
            self.assertTrue(info["limitations"])
            self.assertTrue(all((ROOT / p).is_file() for p in info["documentation"]))
            self.assertNotIn("handler", info)
        self.assertEqual(self.analysis.calls + self.anomaly.calls, [])

    def test_listing_and_lookup_are_deterministic_detached_metadata(self):
        expected = self.manager.list_capabilities()
        self.assertEqual(self.manager.list_capabilities(), expected)
        item = self.manager.get_capability(FA)
        self.assertEqual(item, expected[0])
        item["status"] = "BLOCKED"
        item["limitations"].clear()
        self.assertEqual(self.manager.list_capabilities(), expected)
        self.assertIsNone(self.manager.get_capability("unknown"))
        self.assertIsNone(self.manager.get_capability([]))
        json.dumps(expected, allow_nan=False)

    def test_internal_capability_metadata_is_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            CAPABILITIES[0].status = Availability.BLOCKED

    def test_explicit_analysis_delegates_exact_arguments_once(self):
        payload = {"question": "Sales summary", "dataset": "company_financials", "parameters": {"quality_detail": "full"}}
        out = self.manager.execute(capability=FA, request=payload)
        self.assertEqual(self.analysis.calls, [payload])
        self.assertEqual(self.anomaly.calls, [])
        self.assertEqual(out["delegated_result"], self.analysis.result)
        self.assertEqual(out["capability_status"], "AVAILABLE")

    def test_analysis_quality_currency_status_and_original_explanation_preserved(self):
        before = deepcopy(self.analysis.result)
        out = self.manager.execute(capability=FA, request={"question": "Discount analysis"})
        self.assertEqual(out["execution_status"], "PARTIAL")
        self.assertEqual(out["delegated_status"], "ANSWERED")
        self.assertEqual(out["warnings"], before["tool_result"]["quality"]["warnings"])
        self.assertEqual(out["summary"], before["explanation"]["text"])
        self.assertEqual(out["delegated_result"], before)
        self.assertEqual(self.analysis.result, before)

    def test_analysis_success_partial_no_data_and_tool_failures_map_without_loss(self):
        for status in ("SUCCESS", "PARTIAL", "NO_DATA", "INVALID_REQUEST", "UNSUPPORTED", "DATA_QUALITY_BLOCKER"):
            with self.subTest(status=status):
                self.analysis.result = analysis_fixture(status)
                out = self.manager.execute(capability=FA, request={"question": "Sales summary"})
                self.assertEqual(out["execution_status"], status)
                self.assertEqual(out["delegated_result"], self.analysis.result)
                self.assertEqual(out["errors"], self.analysis.result["tool_result"]["errors"])

    def test_agent_clarification_and_provider_failures_propagate(self):
        clarification = {"code": "dataset_required", "field": "dataset", "question": "Which dataset?", "choices": ["receiver_general", "company_financials"]}
        for status in ("CLARIFICATION_REQUIRED", "INVALID_REQUEST", "UNSUPPORTED", "PROVIDER_ERROR", "PROVIDER_UNAVAILABLE"):
            with self.subTest(status=status):
                self.analysis.result = agent_response(status, explanation="Delegate outcome.",
                                                     clarification=clarification if status == "CLARIFICATION_REQUIRED" else None,
                                                     errors=[] if status == "CLARIFICATION_REQUIRED" else [{"code": "fixture_reason"}])
                out = self.manager.execute(capability=FA, request={"question": "record count"})
                self.assertEqual(out["execution_status"], status)
                self.assertEqual(out["clarification"], self.analysis.result["clarification"])
                self.assertEqual(out["delegated_result"], self.analysis.result)
                self.assertEqual(out["warnings"], [])

    def test_explicit_anomaly_delegates_original_request_once(self):
        payload = {"analysis_version": "1.0", "dataset": "company_financials", "measure": "profit"}
        out = self.manager.execute(capability=AD, request=payload)
        self.assertEqual(self.anomaly.calls, [payload])
        self.assertEqual(self.analysis.calls, [])
        self.assertEqual(out["delegated_result"], self.anomaly.result)

    def test_anomaly_thresholds_status_lineage_and_quality_preserved(self):
        before = deepcopy(self.anomaly.result)
        out = self.manager.execute(capability=AD, request={})
        self.assertEqual(out["delegated_result"], before)
        self.assertEqual(out["warnings"], before["quality"]["warnings"])
        self.assertEqual(self.anomaly.result, before)
        self.assertIn("screening candidates requiring investigation", out["summary"])
        self.assertIn("NOT_ASSESSED", out["summary"])
        for claim in ("fraud", "misconduct", "confirmed anomaly", "probability", "error"):
            self.assertNotIn(claim, out["summary"].lower())

    def test_anomaly_statuses_and_failures_remain_distinct(self):
        for status in ("SUCCESS", "PARTIAL", "NO_DATA", "INVALID_REQUEST", "UNSUPPORTED", "DATA_QUALITY_BLOCKER"):
            with self.subTest(status=status):
                self.anomaly.result = anomaly_fixture(status)
                if status in ("INVALID_REQUEST", "UNSUPPORTED", "DATA_QUALITY_BLOCKER"):
                    self.anomaly.result.update(result=None, errors=[{"code": "fixture_failure"}])
                out = self.manager.execute(capability=AD, request={})
                self.assertEqual(out["execution_status"], status)
                self.assertEqual(out["delegated_result"], self.anomaly.result)
                self.assertEqual(out["errors"], self.anomaly.result["errors"])

    def test_blocked_forecasting_never_executes_any_dependency(self):
        out = self.manager.execute(capability=Capability.CASH_FLOW_FORECASTING, request={"horizon": 12})
        self.assertEqual(out["capability_status"], "BLOCKED")
        self.assertEqual(out["execution_status"], "CAPABILITY_UNAVAILABLE")
        self.assertIsNone(out["delegated_result"])
        self.assertIsNone(out["delegated_status"])
        self.assertIn("actual cash inflows/outflows", out["summary"])
        self.assertIn("currency remains unresolved", out["summary"])
        self.assertEqual(self.analysis.calls + self.anomaly.calls, [])

    def test_blocked_rag_reports_design_and_absent_production_corpus(self):
        out = self.manager.execute(capability=Capability.DOCUMENT_RETRIEVAL, request={"question": "Find invoices"})
        self.assertEqual(out["execution_status"], "CAPABILITY_UNAVAILABLE")
        self.assertIn("no approved real financial-document corpus", out["summary"])
        self.assertIn("DEFERRED", out["summary"])
        self.assertIsNone(out["delegated_result"])
        self.assertEqual(self.analysis.calls + self.anomaly.calls, [])

    def test_availability_check_precedes_any_unavailable_request_inspection(self):
        out = self.manager.execute(capability=Capability.DOCUMENT_RETRIEVAL, request=object())
        self.assertEqual(out["execution_status"], "CAPABILITY_UNAVAILABLE")
        self.assertEqual(self.analysis.calls + self.anomaly.calls, [])

    def test_unknown_missing_and_malformed_capabilities_are_rejected(self):
        for capability in (None, "", "financial_analysis", "SQL", "src.anomaly.service", "__import__", "analyze", [], {}, 17):
            with self.subTest(capability=capability):
                out = self.manager.execute(capability=capability, request={"question": "Sales summary"})
                self.assertEqual(out["execution_status"], "INVALID_REQUEST")
                self.assertEqual(out["errors"][0]["code"], "unknown_capability")
                self.assertIsNone(out["capability_status"])
        self.assertEqual(self.manager.execute()["execution_status"], "INVALID_REQUEST")
        self.assertEqual(self.analysis.calls + self.anomaly.calls, [])

    def test_nonobject_or_nonserializable_payloads_are_rejected_without_delegation(self):
        circular = {}; circular["self"] = circular
        for capability in (FA, AD):
            for payload in (None, "Sales summary", [], {1: "bad"}, {"x": object()}, {"x": float("nan")}, circular):
                with self.subTest(capability=capability, payload_type=type(payload)):
                    out = self.manager.execute(capability=capability, request=payload)
                    self.assertEqual(out["execution_status"], "INVALID_REQUEST")
                    self.assertEqual(out["errors"][0]["code"], "malformed_request")
        self.assertEqual(self.analysis.calls + self.anomaly.calls, [])

    def test_analysis_call_shape_is_validated_without_parsing_question(self):
        for payload in ({}, {"question": []}, {"question": "Sales", "sql": "SELECT 1"}, {"question": "Sales", "provider": "remote"}):
            self.assertEqual(self.manager.execute(capability=FA, request=payload)["execution_status"], "INVALID_REQUEST")
        self.assertEqual(self.analysis.calls, [])
        self.manager.execute(capability=FA, request={"question": "Exact untouched question", "dataset": None, "parameters": {"unknown": True}})
        self.assertEqual(self.analysis.calls[-1]["parameters"], {"unknown": True})

    def test_explicit_selection_is_never_rerouted_or_retried(self):
        self.analysis.result = agent_response("UNSUPPORTED", explanation="No interpretation.")
        out = self.manager.execute(capability=FA, request={"question": "Find anomalous sales"})
        self.assertEqual(out["execution_status"], "UNSUPPORTED")
        self.assertEqual(len(self.analysis.calls), 1)
        self.assertEqual(self.anomaly.calls, [])

    def test_caller_request_is_isolated_from_mutating_injected_adapter(self):
        payload = {"question": "Sales", "parameters": {"filters": {"country": {"eq": "Canada"}}}}
        before = deepcopy(payload)
        def mutate(**supplied):
            supplied["parameters"]["filters"].clear()
            return self.analysis.result
        with patch.object(self.analysis, "ask", side_effect=mutate):
            self.manager.execute(capability=FA, request=payload)
        self.assertEqual(payload, before)

    def test_returned_evidence_and_warning_mirrors_are_independent_copies(self):
        before = deepcopy(self.analysis.result)
        out = self.manager.execute(capability=FA, request={"question": "Sales"})
        out["warnings"][0]["code"] = "caller-change"
        self.assertEqual(out["delegated_result"], before)
        out["delegated_result"]["tool_result"]["quality"]["flags"].clear()
        self.assertEqual(self.analysis.result, before)
        out["summary"] = "Caller text cannot modify evidence."
        self.assertEqual(self.analysis.result, before)

    def test_decimal_objects_are_not_cast_by_facade(self):
        # Actual services serialize decimals as strings; a trusted test adapter
        # demonstrates that the facade performs no numeric serialization/coercion.
        exact = Decimal("1.000000000000000000000000000000000000001")
        self.analysis.result["tool_result"]["result"]["test_decimal"] = exact
        out = self.manager.execute(capability=FA, request={"question": "Sales"})
        self.assertEqual(out["delegated_result"]["tool_result"]["result"]["test_decimal"], exact)
        self.assertIsInstance(out["delegated_result"]["tool_result"]["result"]["test_decimal"], Decimal)

    def test_unexpected_service_failure_propagates_without_fallback(self):
        with patch.object(self.analysis, "ask", side_effect=RuntimeError("fixture failure")):
            with self.assertRaisesRegex(RuntimeError, "fixture failure"):
                self.manager.execute(capability=FA, request={"question": "Sales"})
        self.assertEqual(self.anomaly.calls, [])

    def test_unknown_delegate_status_is_not_misrepresented_as_success(self):
        self.analysis.result["agent_status"] = "UNRECOGNIZED"
        with self.assertRaises(ValueError):
            self.manager.execute(capability=FA, request={"question": "Sales"})
        self.anomaly.result["status"] = "UNRECOGNIZED"
        with self.assertRaises(ValueError):
            self.manager.execute(capability=AD, request={})

    def test_repeated_fixture_execution_is_deterministic(self):
        for capability, payload in ((FA, {"question": "Sales"}), (AD, {})):
            self.assertEqual(self.manager.execute(capability=capability, request=payload),
                             self.manager.execute(capability=capability, request=payload))


class ManagerIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.analysis = FinancialAnalysisAgent()
        cls.anomaly = AnomalyService()
        cls.manager = FinancialManagerAgent(financial_analysis=cls.analysis, anomaly_detection=cls.anomaly)

    def test_actual_analysis_response_is_preserved_completely(self):
        payload = {"question": "Discount analysis", "parameters": {"quality_detail": "full"}}
        direct = self.analysis.ask(**payload)
        out = self.manager.execute(capability=FA, request=payload)
        self.assertEqual(out["delegated_result"], direct)
        self.assertEqual(out["execution_status"], "PARTIAL")
        self.assertEqual(out["warnings"], direct["tool_result"]["quality"]["warnings"])
        self.assertEqual(out["delegated_result"]["tool_result"]["currency"]["status"], "UNKNOWN")
        self.assertEqual(out["delegated_result"]["tool_result"]["result"]["unresolved_placeholder_count"], 53)
        json.dumps(out, allow_nan=False)

    def test_actual_clarification_and_no_data_propagate(self):
        out = self.manager.execute(capability=FA, request={"question": "record count"})
        self.assertEqual(out["execution_status"], "CLARIFICATION_REQUIRED")
        self.assertEqual(out["clarification"]["field"], "dataset")
        out = self.manager.execute(capability=FA, request={"question": 'Discount analysis where discount band="None"'})
        self.assertEqual(out["execution_status"], "NO_DATA")
        self.assertIsNone(out["delegated_result"]["tool_result"]["result"]["measures"]["discounts"]["sum"])

    def test_actual_anomaly_all_evidence_preserved_for_both_domains(self):
        for dataset, measure in (("receiver_general", "accounting_amount"), ("company_financials", "sales"), ("company_financials", "profit")):
            with self.subTest(dataset=dataset, measure=measure):
                payload = {"analysis_version": "1.0", "dataset": dataset, "measure": measure}
                direct = self.anomaly.analyze(payload)
                out = self.manager.execute(capability=AD, request=payload)
                self.assertEqual(out["delegated_result"], direct)
                self.assertEqual(out["execution_status"], direct["status"])
                self.assertEqual(out["warnings"], direct["quality"]["warnings"])
                json.dumps(out, allow_nan=False)

    def test_actual_not_assessed_and_no_data_are_not_normalized(self):
        payload = {"analysis_version": "1.0", "dataset": "company_financials", "measure": "sales", "period": {"year": 2014, "month": 5}}
        out = self.manager.execute(capability=AD, request=payload)
        self.assertEqual(out["execution_status"], "PARTIAL")
        self.assertEqual(out["delegated_result"]["result"]["summary"]["peer"]["not_assessed"], 35)
        payload["filters"] = {"product": {"eq": "absent category"}}
        out = self.manager.execute(capability=AD, request=payload)
        self.assertEqual(out["execution_status"], "NO_DATA")

    def test_domain_validation_remains_owned_by_selected_implementation(self):
        analysis = self.manager.execute(capability=FA, request={"question": "Sales", "parameters": {"statistics": ["made_up"]}})
        self.assertEqual(analysis["execution_status"], "INVALID_REQUEST")
        self.assertIsNotNone(analysis["delegated_result"])
        self.assertEqual(analysis["errors"], analysis["delegated_result"]["errors"])
        anomaly = self.manager.execute(capability=AD, request={"analysis_version": "1.0", "dataset": "company_financials", "measure": "discounts"})
        self.assertEqual(anomaly["execution_status"], "UNSUPPORTED")
        self.assertIsNotNone(anomaly["delegated_result"])

    def test_sql_and_function_names_never_create_execution_paths(self):
        for capability, payload in ((FA, {"question": "SELECT * FROM records"}),
                                   (AD, {"sql": "SELECT * FROM records"}),
                                   (FA, {"question": "execute python"})):
            with self.subTest(capability=capability, payload=payload):
                out = self.manager.execute(capability=capability, request=payload)
                self.assertIn(out["execution_status"], ("INVALID_REQUEST", "UNSUPPORTED"))

    def test_default_manager_executes_offline_without_external_provider(self):
        with patch("socket.socket", side_effect=AssertionError("Network forbidden")), \
             patch("socket.create_connection", side_effect=AssertionError("Network forbidden")):
            manager = FinancialManagerAgent()
            self.assertEqual(len(manager.list_capabilities()), 4)
            analysis = manager.execute(capability=FA, request={"question": "Company Financials record count"})
            anomaly = manager.execute(capability=AD, request={"analysis_version": "1.0", "dataset": "company_financials", "measure": "sales"})
        self.assertEqual(analysis["execution_status"], "SUCCESS")
        self.assertEqual(anomaly["execution_status"], "SUCCESS")

    def test_data_and_database_hashes_unchanged_after_both_delegations(self):
        files = [p for p in (ROOT / "data").rglob('*') if p.is_file()]
        before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
        self.manager.execute(capability=FA, request={"question": "Profit summary"})
        self.manager.execute(capability=AD, request={"analysis_version": "1.0", "dataset": "company_financials", "measure": "profit"})
        self.assertEqual(before, {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in files})


if __name__ == "__main__":
    unittest.main()
