"""Phase 17 Step 69: persisted end-to-end conversational dynamic execution."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.anomaly.dynamic import DynamicAnomalyRequest
from src.execution import DynamicQueryParameters, DynamicQueryRequest
from src.manager import FinancialManagerAgent, FinancialManagerSession
from src.mediation import ConversationMediator

from tests.execution_support import onboard_sales
from tests.mediation_support import ScriptedLLM


MAPPINGS = {
    "date": "TRANSACTION_DATE", "sales": "SALES", "country": "COUNTRY",
    "segment": "SEGMENT", "product": "PRODUCT", "profit": "PROFIT",
    "discount": "DISCOUNT", "units": "UNITS_SOLD",
}


def persisted_csv(outlier=100):
    rows = ["date,sales,country,segment,product,profit,discount,units"]
    for value in range(30):
        rows.append(
            f"2026-{value % 2 + 1:02d}-01,{value},Canada,Government,Widget,"
            f"{value},1,2"
        )
    rows.append(f"2026-02-01,{outlier},Brazil,Enterprise,Gadget,200,2,4")
    return "\n".join(rows) + "\n"


def intent(operation, **overrides):
    value = {
        "version": "1.2", "operation": operation, "intent": None,
        "capability_hint": None, "clarification_answer": None,
        "clarification_kind": None, "evidence_reference": None,
        "follow_up_intent": None, "presentation_hint": None,
        "response_language": "en", "dataset_id": None,
        "dynamic_operation": None, "period_granularity": None,
        "missing_dimension": None,
    }
    value.update(overrides)
    return value


def grounded(packet):
    return {
        "message": "The authoritative result is presented below.",
        "used_fact_ids": [packet["facts"][0]["id"]],
        "warning_fact_ids": [],
        "presentation_hint": packet["default_presentation"],
        "language": packet["language"],
    }


class MutableClock:
    def __init__(self):
        self.value = datetime(2026, 10, 14, 12, tzinfo=timezone.utc)

    def __call__(self):
        return self.value

    def advance(self, **values):
        self.value += timedelta(**values)


class ConversationalDynamicExecutionEndToEndTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.onboarding, state = onboard_sales(
            self.base, persisted_csv(), mappings=MAPPINGS,
        )
        self.dataset_id = state["dataset_id"]
        self.root = self.base / "onboarding"
        self.manager = FinancialManagerAgent(onboarding_root=self.root)
        self.clock = MutableClock()
        self.references = iter(f"e2e-ref-{index}" for index in range(1, 50))
        self.session = FinancialManagerSession(
            manager=self.manager, clock=self.clock,
            session_id_factory=lambda: "phase17-e2e",
            reference_id_factory=self.references.__next__,
        )

    def tearDown(self):
        self.temporary.cleanup()

    def test_primary_persisted_flow_all_nine_financial_operations_and_anomalies(self):
        select = f"Use dataset {self.dataset_id}."
        requests = {
            "How many sales records are there?": ("SALES_RECORD_COUNT", None),
            "Show total sales.": ("SALES_SUMMARY", None),
            "Show sales by country.": ("SALES_BY_COUNTRY", None),
            "Show sales by month.": ("SALES_BY_PERIOD", "MONTH"),
            "Show sales by year.": ("SALES_BY_PERIOD", "YEAR"),
            "Show sales by segment.": ("SALES_BY_SEGMENT", None),
            "Now by product.": ("SALES_BY_PRODUCT", None),
            "Summarize Profit.": ("PROFIT_SUMMARY", None),
            "Analyze discounts.": ("DISCOUNT_ANALYSIS", None),
            "Summarize units sold.": ("UNITS_SOLD_SUMMARY", None),
        }
        scripts = {
            select: intent("SELECT_DYNAMIC_DATASET", dataset_id=self.dataset_id),
            **{
                question: intent(
                    "DYNAMIC_FINANCIAL_ANALYSIS", capability_hint="FINANCIAL_ANALYSIS",
                    dynamic_operation=operation, period_granularity=granularity,
                )
                for question, (operation, granularity) in requests.items()
            },
            "Check Sales for anomalies.": intent(
                "DYNAMIC_ANOMALY_SCREEN", capability_hint="ANOMALY_DETECTION",
                dynamic_operation="SALES_ANOMALY_SCREEN",
            ),
            "Why was A1 selected?": intent(
                "EVIDENCE_FOLLOWUP", evidence_reference="A1",
                follow_up_intent="why_selected",
            ),
            "Check Profit for anomalies.": intent(
                "DYNAMIC_ANOMALY_SCREEN", capability_hint="ANOMALY_DETECTION",
                dynamic_operation="PROFIT_ANOMALY_SCREEN",
            ),
        }
        llm = ScriptedLLM(scripts, respond=grounded)
        mediator = ConversationMediator(self.session, llm.provider)

        self.assertEqual(mediator.handle(select).outcome["status"], "DATASET_SELECTED")
        observed = []
        for question, (operation, granularity) in requests.items():
            turn = mediator.handle(question)
            self.assertEqual(turn.outcome["status"], "SUCCESS", question)
            evidence = turn.outcome["result"]["delegated_result"]
            observed.append(evidence["query_name"])
            self.assertEqual(evidence["dataset"], self.dataset_id)
            if granularity is not None:
                periods = [group["key"]["value"] for group in evidence["result"]["groups"]]
                self.assertTrue(all(len(period) == (7 if granularity == "MONTH" else 4)
                                    for period in periods))
        self.assertEqual(set(observed), {
            "SALES_RECORD_COUNT", "SALES_SUMMARY", "SALES_BY_COUNTRY", "SALES_BY_PERIOD",
            "SALES_BY_SEGMENT", "SALES_BY_PRODUCT", "PROFIT_SUMMARY",
            "DISCOUNT_ANALYSIS", "UNITS_SOLD_SUMMARY",
        })

        sales = mediator.handle("Check Sales for anomalies.")
        self.assertEqual(sales.outcome["status"], "SUCCESS")
        self.assertEqual([label for label, _handle in sales.labels], ["A1"])
        why = mediator.handle("Why was A1 selected?")
        self.assertEqual(why.outcome["status"], "SUCCESS")
        self.assertEqual(why.outcome["result"]["observed_value"], "100")
        self.assertEqual(
            why.outcome["result"]["assessments"]["global"]["assessment"]["tail"], "upper",
        )
        profit = mediator.handle("Check Profit for anomalies.")
        self.assertEqual(profit.outcome["status"], "SUCCESS")
        self.assertEqual(
            profit.outcome["result"]["delegated_result"]["result"]["operation"],
            "PROFIT_ANOMALY_SCREEN",
        )

    def test_same_turn_target_and_ambiguity_never_auto_select(self):
        same_turn = f"Show sales by product for dataset {self.dataset_id}."
        llm = ScriptedLLM({same_turn: intent(
            "DYNAMIC_FINANCIAL_ANALYSIS", capability_hint="FINANCIAL_ANALYSIS",
            dataset_id=self.dataset_id, dynamic_operation="SALES_BY_PRODUCT",
        )}, respond=grounded)
        turn = ConversationMediator(self.session, llm.provider).handle(same_turn)
        self.assertEqual(turn.outcome["status"], "SUCCESS")

        _onboarding, second = onboard_sales(
            self.base, persisted_csv(outlier=101), mappings=MAPPINGS,
        )
        session = FinancialManagerSession(
            manager=FinancialManagerAgent(onboarding_root=self.root), clock=MutableClock(),
        )
        question = "Show sales by country."
        ambiguous = ConversationMediator(session, ScriptedLLM({question: intent(
            "REQUEST_CLARIFICATION", clarification_kind="DYNAMIC_DATASET",
        )}).provider).handle(question)
        self.assertIsNone(ambiguous.outcome)
        self.assertIn(self.dataset_id, ambiguous.text)
        self.assertIn(second["dataset_id"], ambiguous.text)
        self.assertIsNone(session.status()["dynamic_dataset"])

    def test_reference_lifecycle_cancel_reset_expiry_and_new_result(self):
        self.session.select_dynamic_dataset(self.dataset_id)
        first = self.session.execute_dynamic_anomaly("SALES_ANOMALY_SCREEN")
        old = first["references"][0]["handle"]
        self.session.execute_dynamic_anomaly("PROFIT_ANOMALY_SCREEN")
        self.assertEqual(self.session.follow_up(reference=old, intent="why_selected")["status"],
                         "UNKNOWN_REFERENCE")

        current = self.session.status()["active_context"]
        self.assertEqual(current["operation"], "PROFIT_ANOMALY_SCREEN")
        current_handle = self.session.execute_dynamic_anomaly(
            "SALES_ANOMALY_SCREEN",
        )["references"][0]["handle"]
        self.session.cancel()
        self.assertEqual(self.session.follow_up(
            reference=current_handle, intent="record_detail",
        )["status"], "NO_EVIDENCE_CONTEXT")

        self.session.select_dynamic_dataset(self.dataset_id)
        reset_handle = self.session.execute_dynamic_anomaly(
            "SALES_ANOMALY_SCREEN",
        )["references"][0]["handle"]
        self.session.reset()
        self.assertEqual(self.session.follow_up(
            reference=reset_handle, intent="why_selected",
        )["status"], "NO_EVIDENCE_CONTEXT")

        self.session.select_dynamic_dataset(self.dataset_id)
        expired_handle = self.session.execute_dynamic_anomaly(
            "SALES_ANOMALY_SCREEN",
        )["references"][0]["handle"]
        self.clock.advance(minutes=30)
        self.assertEqual(self.session.follow_up(
            reference=expired_handle, intent="why_selected",
        )["status"], "SESSION_EXPIRED")

    def test_grounding_rejects_invented_numbers_and_preserves_exact_evidence(self):
        question = f"Check Sales for anomalies in dataset {self.dataset_id}."

        def fabricated(packet):
            return {
                "message": "999 records were selected and values doubled.",
                "used_fact_ids": [packet["facts"][0]["id"]],
                "warning_fact_ids": [], "presentation_hint": packet["default_presentation"],
                "language": packet["language"],
            }

        llm = ScriptedLLM({question: intent(
            "DYNAMIC_ANOMALY_SCREEN", capability_hint="ANOMALY_DETECTION",
            dataset_id=self.dataset_id, dynamic_operation="SALES_ANOMALY_SCREEN",
        )}, respond=fabricated)
        turn = ConversationMediator(self.session, llm.provider).handle(question)

        self.assertEqual(turn.outcome["status"], "SUCCESS")
        self.assertIsNotNone(turn.notice)
        self.assertNotIn("999", turn.text)
        self.assertIn("100", turn.text)
        self.assertIn("CANDIDATE", turn.text)

    def test_conversation_matches_unchanged_direct_manager_apis(self):
        self.session.select_dynamic_dataset(self.dataset_id)
        financial = self.session.execute_dynamic_financial_analysis("SALES_SUMMARY")
        anomaly = self.session.execute_dynamic_anomaly("SALES_ANOMALY_SCREEN")

        self.assertEqual(financial["result"], self.manager.execute_dataset_request(
            DynamicQueryRequest(
                self.dataset_id, "SALES_SUMMARY", DynamicQueryParameters(),
            )
        ))
        self.assertEqual(anomaly["result"], self.manager.execute_dataset_anomaly_request(
            DynamicAnomalyRequest(self.dataset_id, "SALES_ANOMALY_SCREEN")
        ))


if __name__ == "__main__":
    unittest.main()
