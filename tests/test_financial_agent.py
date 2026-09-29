"""Step 13 behavior: offline providers, closed routing, and unchanged core evidence."""

from copy import deepcopy
from dataclasses import FrozenInstanceError, fields
from hashlib import sha256
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from src.agents import FinancialAnalysisAgent
from src.agents.models import ToolIntent
from src.agents.provider import InterpretationRequest, ProviderError, ProviderLocation
from src.financial import FinancialCore
from src.financial.contracts import CF, RG, CONTRACTS


ROOT = Path(__file__).resolve().parents[1]
QUESTIONS = (
    ("Receiver General record count", "receiver_general_record_count", {}),
    ("Receiver General amount summary", "receiver_general_amount_summary", {}),
    ("Amounts by debit/credit", "receiver_general_amount_by_debit_credit", {}),
    ("Amounts by voucher type", "receiver_general_amount_by_voucher_type", {}),
    ("Amounts by department", "receiver_general_amount_by_department", {}),
    ("Receiver General amounts by month", "receiver_general_amount_by_period", {"granularity": "month"}),
    ("Amounts by general ledger account", "receiver_general_accounting_dimension_summary", {"group_by": "general_ledger_account"}),
    ("Receiver General highest 5 amounts", "receiver_general_extreme_amount_records", {"direction": "highest", "limit": 5}),
    ("Company Financials record count", "company_financials_record_count", {}),
    ("Sales summary", "company_financials_sales_summary", {"measures": ["sales"]}),
    ("Sales by month", "company_financials_sales_by_period", {"measures": ["sales"], "granularity": "month"}),
    ("Sales by country", "company_financials_sales_by_country", {"measures": ["sales"]}),
    ("Sales by segment", "company_financials_sales_by_segment", {"measures": ["sales"]}),
    ("Sales by product", "company_financials_sales_by_product", {"measures": ["sales"]}),
    ("Profit summary", "company_financials_profit_summary", {}),
    ("Discount analysis", "company_financials_discount_analysis", {}),
    ("Units sold summary", "company_financials_units_sold_summary", {}),
)


class RecordingCore:
    """Test-only core double; no production fixture records are created."""

    def __init__(self, status="SUCCESS"):
        self.calls = []
        self.evidence = {"contract_version": "1.0", "query_name": "fixture_contract", "dataset": RG,
                         "status": status, "result": {"record_count": 9}, "currency": None,
                         "records": {"candidates": 9, "used": 9, "excluded": 0, "exclusion_reasons": {}},
                         "quality": {"warnings": [], "flags": [], "detail": "summary"},
                         "filter_diagnostics": [], "errors": [], "metadata": {"test_fixture": True}}

    def query(self, request):
        self.calls.append(deepcopy(request))
        return self.evidence


class FakeProvider:
    location = ProviderLocation.LOCAL

    def __init__(self, intent, location=ProviderLocation.LOCAL):
        self.intent, self.location, self.calls = intent, location, []

    def interpret(self, request):
        self.calls.append(request)
        return self.intent


class AgentRoutingTests(unittest.TestCase):
    def setUp(self):
        self.core = RecordingCore()
        self.agent = FinancialAnalysisAgent(self.core)

    def test_receiver_general_routes_all_eight_contracts(self):
        for question, name, options in QUESTIONS[:8]:
            with self.subTest(question=question):
                response = self.agent.ask(question)
                self.assertEqual(response["agent_status"], "ANSWERED", response)
                self.assertEqual(self.core.calls[-1], {"contract_version": "1.0", "query_name": name, "dataset": RG, **options})

    def test_company_financials_routes_all_nine_contracts(self):
        for question, name, options in QUESTIONS[8:]:
            with self.subTest(question=question):
                response = self.agent.ask(question)
                self.assertEqual(response["agent_status"], "ANSWERED", response)
                self.assertEqual(self.core.calls[-1], {"contract_version": "1.0", "query_name": name, "dataset": CF, **options})

    def test_exactly_seventeen_contracts_in_catalog(self):
        catalog = self.agent.registry.catalog()
        self.assertEqual({item["name"] for item in catalog}, set(CONTRACTS))
        self.assertEqual(len(catalog), 17)
        self.assertTrue(all(item["purpose"] and item["parameters"] and item["limitations"] for item in catalog))
        monetary = {item["name"]: item["monetary"] for item in catalog}
        self.assertFalse(monetary["company_financials_units_sold_summary"])
        self.assertFalse(monetary["receiver_general_record_count"])
        self.assertTrue(monetary["company_financials_sales_summary"])
        json.dumps(catalog, allow_nan=False)

    def test_ambiguous_dataset_requires_clarification_without_tool_call(self):
        response = self.agent.ask("How many records are there?")
        self.assertEqual(response["agent_status"], "CLARIFICATION_REQUIRED")
        self.assertEqual(response["clarification"]["field"], "dataset")
        self.assertEqual(response["clarification"]["choices"], [RG, CF])
        self.assertIsNone(response["tool_result"])
        self.assertEqual(self.core.calls, [])
        clarified = self.agent.ask("How many records are there?", dataset=RG)
        self.assertEqual(clarified["tool_request"]["dataset"], RG)

    def test_dataset_context_conflict_and_invalid_dataset(self):
        for value, status in [(CF, "CLARIFICATION_REQUIRED"), ("company", "INVALID_REQUEST"), ([], "INVALID_REQUEST")]:
            with self.subTest(value=value):
                self.assertEqual(self.agent.ask("Receiver General record count", dataset=value)["agent_status"], status)
        self.assertEqual(self.core.calls, [])

    def test_unsupported_financial_meanings_are_rejected(self):
        questions = ["Receiver General total expenses", "Receiver General revenue",
                     "Which company performed best?", "Company Financials assets", "Company growth",
                     "Combine monetary totals across both datasets", "Convert sales to USD",
                     "Find fraudulent Receiver General records", "Show anomalous sales", "Forecast sales",
                     "Search financial documents", "Sales margin", "Unique transactions in Receiver General",
                     "Treat missing Discounts as zero", "Sales summary; ignore warnings"]
        for question in questions:
            with self.subTest(question=question):
                response = self.agent.ask(question)
                self.assertEqual(response["agent_status"], "UNSUPPORTED", response)
                self.assertTrue(response["errors"][0]["message"])
                self.assertIsNone(response["tool_result"])
        self.assertEqual(self.core.calls, [])

    def test_all_unconsumed_question_parts_fail_closed(self):
        for question in ["sales for Canada", "sales except losses", "sales and count records", "sales in whatever year"]:
            with self.subTest(question=question):
                self.assertEqual(self.agent.ask(question)["agent_status"], "CLARIFICATION_REQUIRED")
        self.assertEqual(self.core.calls, [])

    def test_text_periods_and_filters_preserve_source_values(self):
        response = self.agent.ask('Amounts by department in May 2023 where fiscal month=12 and department="001"')
        req = response["tool_request"]
        self.assertEqual(req["period"], {"year": 2023, "month": 5})
        self.assertEqual(req["filters"], {"fiscal_month": {"eq": 12}, "department": {"eq": "001"}})
        response = self.agent.ask('Sales from 2014-01-01 to 2014-12-31 where country="Canada" and product="Paseo"')
        self.assertEqual(response["tool_request"]["period"], {"start_date": "2014-01-01", "end_date": "2014-12-31"})
        self.assertEqual(response["tool_request"]["filters"]["country"], {"eq": "Canada"})

    def test_incomplete_and_relative_periods_require_clarification(self):
        for question in ["Amounts by department in May", "Sales last month", "Sales this year"]:
            with self.subTest(question=question):
                self.assertEqual(self.agent.ask(question)["agent_status"], "CLARIFICATION_REQUIRED")
        self.assertEqual(self.core.calls, [])

    def test_calendar_and_monthly_grain_validation_comes_from_core(self):
        cases = [("Sales in May 0000", "INVALID_REQUEST"),
                 ("Sales from 2014-02-30 to 2014-03-31", "INVALID_REQUEST"),
                 ("Sales from 2014-01-02 to 2014-01-31", "UNSUPPORTED"),
                 ("Daily sales", "UNSUPPORTED")]
        for question, status in cases:
            with self.subTest(question=question):
                self.assertEqual(self.agent.ask(question)["agent_status"], status)
        self.assertEqual(self.core.calls, [])

    def test_structured_membership_null_and_detail_parameters(self):
        params = {"filters": {"department": {"in": ["001", "002"], "nulls": "include"}},
                  "quality_detail": "full", "missing_dimension": "exclude", "period": {"year": 2023}}
        before = deepcopy(params)
        response = self.agent.ask("Amounts by department", parameters=params)
        self.assertEqual(response["agent_status"], "ANSWERED")
        self.assertEqual(response["tool_request"]["filters"], params["filters"])
        self.assertEqual(params, before)

    def test_conflicting_text_and_parameters_require_clarification(self):
        cases = [("Sales in 2014", {"period": {"year": 2013}}),
                 ('Sales where country="Canada"', {"filters": {"country": {"eq": "France"}}}),
                 ("Sales by year", {"granularity": "month"})]
        for question, params in cases:
            with self.subTest(question=question):
                self.assertEqual(self.agent.ask(question, parameters=params)["agent_status"], "CLARIFICATION_REQUIRED")
        self.assertEqual(self.core.calls, [])

    def test_structured_and_textual_nonconflicting_filters_merge(self):
        response = self.agent.ask('Sales where country="Canada"', parameters={"filters": {"product": {"eq": "Paseo"}}})
        self.assertEqual(response["tool_request"]["filters"], {"country": {"eq": "Canada"}, "product": {"eq": "Paseo"}})

    def test_invalid_parameters_and_reserved_identity_never_reach_core(self):
        for params in [[], {"sql": "SELECT * FROM anything"}, {"filters": {"arbitrary": {"eq": "x"}}},
                       {"dataset": RG}, {"query_name": "eval"}, {"contract_version": "2"},
                       {"statistics": ["made_up"]}, {"group_by": "country"}, {"period": {"year": True}},
                       {"period": object()}, {"statistics": [float("nan")]}, {1: "bad"}]:
            with self.subTest(params=params):
                self.assertEqual(self.agent.ask("Sales summary", parameters=params)["agent_status"], "INVALID_REQUEST")
        self.assertEqual(self.core.calls, [])

    def test_unsupported_statistics_groupings_and_limits(self):
        for question, status in [("Median sales", "UNSUPPORTED"), ("Average sales by country", "UNSUPPORTED"),
                                 ("Amounts by department by voucher type", "UNSUPPORTED"),
                                 ("Units sold by product", "UNSUPPORTED"), ("Sales by record_id", "UNSUPPORTED"),
                                 ("Receiver General highest 101 amounts", "INVALID_REQUEST")]:
            with self.subTest(question=question):
                self.assertEqual(self.agent.ask(question)["agent_status"], status)
        self.assertEqual(self.core.calls, [])

    def test_statistics_measures_and_accounting_dimensions(self):
        response = self.agent.ask("Average gross sales and COGS")
        self.assertEqual(response["tool_request"]["measures"], ["gross_sales", "cogs"])
        self.assertEqual(response["tool_request"]["statistics"], ["mean"])
        self.assertEqual(self.agent.ask("Receiver General median amount")["tool_request"]["statistics"], ["median"])
        self.assertEqual(self.agent.ask("Receiver General lowest 2 amounts")["tool_request"]["direction"], "lowest")
        for field in ["subledger account", "financial coding block", "control data type"]:
            with self.subTest(field=field):
                self.assertEqual(self.agent.ask("Amounts by " + field)["tool_request"]["group_by"], field.replace(" ", "_"))

    def test_invalid_question(self):
        for question in [None, {}, "", " ", "x" * 4001]:
            with self.subTest(question=str(question)[:20]):
                self.assertEqual(self.agent.ask(question)["agent_status"], "INVALID_REQUEST")
        self.assertEqual(self.core.calls, [])

    def test_sql_instructions_are_rejected_and_quoted_categories_are_literals(self):
        for question in ["SELECT * FROM receiver_general", "Sales; DROP TABLE records", "Execute python"]:
            self.assertEqual(self.agent.ask(question)["agent_status"], "UNSUPPORTED")
        self.assertEqual(self.core.calls, [])
        response = self.agent.ask('Sales where product="SELECT * FROM receiver_general; DROP TABLE records"')
        self.assertEqual(response["tool_request"]["filters"]["product"]["eq"], "SELECT * FROM receiver_general; DROP TABLE records")


class AgentProviderTests(unittest.TestCase):
    def setUp(self):
        self.core = RecordingCore()
        self.intent = ToolIntent.create("company_financials_sales_summary", measures=["sales"])

    def agent(self, intent=None, location=ProviderLocation.LOCAL):
        provider = FakeProvider(self.intent if intent is None else intent, location)
        return FinancialAnalysisAgent(self.core, provider), provider

    def test_fake_provider_repeated_results_are_deterministic(self):
        agent, provider = self.agent()
        self.assertEqual(agent.ask("Sales summary"), agent.ask("Sales summary"))
        self.assertEqual(len(provider.calls), 2)
        self.assertEqual(len(self.core.calls), 2)

    def test_provider_sees_immutable_question_and_metadata_only(self):
        agent, provider = self.agent()
        agent.ask("Sales summary", parameters={"filters": {"product": {"eq": "Private product"}}})
        request = provider.calls[0]
        self.assertEqual({field.name for field in fields(request)}, {"question", "dataset", "tools"})
        self.assertIsInstance(request, InterpretationRequest)
        self.assertNotIn("Private product", repr(request))
        self.assertNotIn("test_fixture", repr(request))
        with self.assertRaises(FrozenInstanceError):
            request.question = "something else"
        with self.assertRaises(FrozenInstanceError):
            request.tools[0].name = "eval"

    def test_private_and_external_provider_transports_are_not_invoked(self):
        for location in [ProviderLocation.PRIVATE, ProviderLocation.EXTERNAL]:
            agent, provider = self.agent(location=location)
            self.assertEqual(agent.ask("Sales summary")["agent_status"], "PROVIDER_UNAVAILABLE")
            self.assertEqual(provider.calls, [])
        self.assertEqual(self.core.calls, [])

    def test_provider_cannot_switch_tools_datasets_or_add_filters(self):
        bad_intents = [ToolIntent.create("receiver_general_record_count"),
                       ToolIntent.create("company_financials_sales_by_country", measures=["sales"]),
                       ToolIntent.create("company_financials_sales_summary", measures=["sales"], filters={"country": {"eq": "Canada"}})]
        for intent in bad_intents:
            with self.subTest(intent=intent):
                agent, _ = self.agent(intent)
                self.assertEqual(agent.ask("Sales summary")["agent_status"], "PROVIDER_ERROR")
        self.assertEqual(self.core.calls, [])

    def test_provider_arbitrary_functions_and_malformed_arguments_are_rejected(self):
        intents = [ToolIntent.create("eval"), {"tool_name": self.intent.tool_name},
                   ToolIntent(self.intent.tool_name, "{broken"), ToolIntent(self.intent.tool_name, "[]"),
                   ToolIntent(self.intent.tool_name, '{"measures":["sales"],"measures":["profit"]}'),
                   ToolIntent(self.intent.tool_name, '{"measures":NaN}'),
                   ToolIntent.create(self.intent.tool_name, measures=["sales"], sql="SELECT 1"),
                   ToolIntent.create(self.intent.tool_name, dataset=RG)]
        for intent in intents:
            with self.subTest(intent=intent):
                agent, _ = self.agent(intent)
                self.assertEqual(agent.ask("Sales summary")["agent_status"], "INVALID_REQUEST")
        self.assertEqual(self.core.calls, [])

    def test_unsupported_request_never_reaches_provider(self):
        agent, provider = self.agent()
        self.assertEqual(agent.ask("Company Financials revenue")["agent_status"], "UNSUPPORTED")
        self.assertEqual(provider.calls, [])
        self.assertEqual(self.core.calls, [])

    def test_provider_failure_is_structured_without_private_exception_echo(self):
        agent, provider = self.agent()
        with patch.object(provider, "interpret", side_effect=ProviderError("private provider trace")):
            response = agent.ask("Sales summary")
        self.assertEqual(response["agent_status"], "PROVIDER_ERROR")
        self.assertNotIn("private provider trace", json.dumps(response))
        self.assertEqual(self.core.calls, [])

    def test_unexpected_core_errors_propagate(self):
        agent, _ = self.agent()
        with patch.object(self.core, "query", side_effect=RuntimeError("test failure")):
            with self.assertRaisesRegex(RuntimeError, "test failure"):
                agent.ask("Sales summary")

    def test_core_blocker_is_preserved_as_evidence(self):
        self.core.evidence.update(status="DATA_QUALITY_BLOCKER", result=None, records=None,
                                  errors=[{"code": "fixture_blocker", "field": None, "message": "Test snapshot unavailable."}])
        agent, _ = self.agent()
        response = agent.ask("Sales summary")
        self.assertEqual(response["agent_status"], "TOOL_REJECTED")
        self.assertEqual(response["tool_result"], self.core.evidence)
        self.assertIn("DATA_QUALITY_BLOCKER", response["explanation"]["text"])

    def test_returned_evidence_is_a_defensive_copy_with_digest(self):
        agent, _ = self.agent()
        before = deepcopy(self.core.evidence)
        response = agent.ask("Sales summary")
        self.assertEqual(response["tool_result"], before)
        digest = sha256(json.dumps(before, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()
        self.assertEqual(response["evidence_sha256"], digest)
        response["tool_result"]["records"]["used"] = -1
        self.assertEqual(self.core.evidence, before)


class AgentCoreIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core = FinancialCore(ROOT)
        cls.agent = FinancialAnalysisAgent(cls.core)

    def test_all_seventeen_routes_preserve_exact_direct_core_results(self):
        for question, name, options in QUESTIONS:
            with self.subTest(question=question):
                direct = self.core.query({"contract_version": "1.0", "query_name": name, "dataset": CONTRACTS[name].dataset, **options})
                response = self.agent.ask(question)
                self.assertEqual(response["agent_status"], "ANSWERED")
                self.assertEqual(response["tool_result"], direct)
                json.dumps(response, allow_nan=False)

    def test_partial_discount_placeholders_and_unknown_currency_remain_visible(self):
        response = self.agent.ask("Discount analysis")
        evidence = response["tool_result"]
        self.assertEqual(evidence["status"], "PARTIAL")
        self.assertEqual(evidence["result"]["unresolved_placeholder_count"], 53)
        self.assertEqual(evidence["result"]["measures"]["discounts"]["coverage"]["used"], 647)
        self.assertEqual(evidence["currency"]["status"], "UNKNOWN")
        self.assertIsNone(evidence["currency"]["code"])
        self.assertIn("UNKNOWN", response["explanation"]["text"])
        self.assertIn("9205248.27", response["explanation"]["text"])
        for warning in evidence["quality"]["warnings"]:
            self.assertIn(json.dumps(warning, ensure_ascii=False, sort_keys=True), response["explanation"]["text"])

    def test_department_exclusions_full_flags_and_source_lineage_survive(self):
        response = self.agent.ask("Amounts by department", parameters={"missing_dimension": "exclude", "quality_detail": "full"})
        evidence = response["tool_result"]
        self.assertEqual(evidence["records"]["excluded"], 26)
        self.assertEqual(evidence["status"], "PARTIAL")
        self.assertEqual(evidence["quality"]["detail"], "full")
        self.assertTrue(evidence["quality"]["flags"])
        self.assertTrue(evidence["metadata"]["snapshot"])
        self.assertIn('"excluded": 26', response["explanation"]["text"])

    def test_negative_profit_is_not_relabelled(self):
        response = self.agent.ask("Profit summary")
        self.assertEqual(response["tool_result"]["result"]["negative_count"], 58)
        self.assertEqual(response["tool_result"]["records"]["excluded"], 5)
        self.assertNotIn("fraud", response["explanation"]["text"].casefold())
        self.assertNotIn("anomaly", response["explanation"]["text"].casefold())

    def test_units_and_counts_have_no_currency(self):
        for question in ["Units sold summary", "Company Financials record count"]:
            response = self.agent.ask(question)
            self.assertIsNone(response["tool_result"]["currency"])
            self.assertNotIn("Currency status:", response["explanation"]["text"])

    def test_no_data_is_preserved_not_changed_to_success_or_zero_amount(self):
        response = self.agent.ask('Discount analysis where discount band="None"')
        self.assertEqual(response["agent_status"], "ANSWERED")
        self.assertEqual(response["tool_result"]["status"], "NO_DATA")
        self.assertIsNone(response["tool_result"]["result"]["measures"]["discounts"]["sum"])
        self.assertIn("NO_DATA", response["explanation"]["text"])

    def test_offline_actual_query_and_fake_provider(self):
        provider = FakeProvider(ToolIntent.create("company_financials_record_count"))
        agent = FinancialAnalysisAgent(self.core, provider)
        with patch("socket.socket", side_effect=AssertionError("Network forbidden")), \
             patch("socket.create_connection", side_effect=AssertionError("Network forbidden")):
            response = agent.ask("Company Financials record count")
        self.assertEqual(response["tool_result"]["result"]["record_count"], 700)

    def test_sql_shaped_filter_is_only_a_literal_in_real_core(self):
        database = ROOT / "data/database/financial_manager.db"
        before = sha256(database.read_bytes()).hexdigest()
        response = self.agent.ask('Sales where product="Paseo\'; DROP TABLE company_financial_record; --"')
        self.assertEqual(response["tool_result"]["status"], "NO_DATA")
        self.assertEqual(response["tool_result"]["records"]["candidates"], 0)
        self.assertEqual(sha256(database.read_bytes()).hexdigest(), before)


if __name__ == "__main__":
    unittest.main()
