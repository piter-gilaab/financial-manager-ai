"""Phase 17 Step 68: closed conversational dynamic anomaly execution."""

from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest
from unittest.mock import patch

from src.anomaly.dynamic import DynamicAnomalyRequest
from src.manager import FinancialManagerAgent, FinancialManagerSession
from src.mediation import ConversationMediator, InterpretationContext, MediationRejected, parse_intent
from src.mediation.grounding import locate
from src.mediation.models import DynamicDatasetOption
from src.mediation.presentation import deterministic_dynamic
from src.onboarding.models import OnboardingError

from tests.execution_support import onboard_sales
from tests.mediation_support import ScriptedLLM


MAPPINGS = {
    "date": "TRANSACTION_DATE", "sales": "SALES", "country": "COUNTRY",
    "segment": "SEGMENT", "product": "PRODUCT", "profit": "PROFIT",
    "discount": "DISCOUNT", "units": "UNITS_SOLD",
}


def anomaly_csv(*, sales_outlier="100", profit_outlier="200"):
    rows = ["date,sales,country,segment,product,profit,discount,units"]
    for value in range(30):
        rows.append(f"2026-01-01,{value},Canada,Government,Widget,{value},1,2")
    rows.append(
        f"2026-01-01,{sales_outlier},Brazil,Enterprise,Gadget,{profit_outlier},1,2"
    )
    return "\n".join(rows) + "\n"


class FixedClock:
    def __call__(self):
        return datetime(2026, 10, 14, 12, tzinfo=timezone.utc)


def dynamic_intent(operation, **overrides):
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


def grounded_response(packet):
    return {
        "message": "Authoritative statistical evidence is shown below.",
        "used_fact_ids": [packet["facts"][0]["id"]],
        "warning_fact_ids": [],
        "presentation_hint": packet["default_presentation"],
        "language": packet["language"],
    }


class ConversationalDynamicAnomalyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.onboarding, state = onboard_sales(
            self.base, anomaly_csv(), mappings=MAPPINGS,
        )
        self.dataset_id = state["dataset_id"]
        self.root = self.base / "onboarding"
        self.manager = FinancialManagerAgent(onboarding_root=self.root)
        self.session = FinancialManagerSession(
            manager=self.manager, clock=FixedClock(),
            session_id_factory=lambda: "dynamic-session",
            reference_id_factory=iter(f"dynamic-ref-{index}" for index in range(1, 30)).__next__,
        )

    def tearDown(self):
        self.temporary.cleanup()

    def mediator(self, intents, respond=grounded_response):
        llm = ScriptedLLM(intents, respond=respond)
        return ConversationMediator(self.session, llm.provider), llm

    def test_catalog_adds_only_bounded_anomaly_readiness_metadata(self):
        option = self.manager.dynamic_dataset_catalog()["datasets"][0]

        self.assertEqual(option["supported_anomaly_operations"], [
            "SALES_ANOMALY_SCREEN", "PROFIT_ANOMALY_SCREEN",
        ])
        self.assertEqual(option["anomaly_state"], "AVAILABLE_WITH_LIMITATIONS")
        self.assertNotIn("source_fingerprint", repr(option))
        self.assertNotIn("100", repr(option))

    def test_anomaly_projection_failure_does_not_remove_financially_eligible_dataset(self):
        with patch.object(
            self.manager._dynamic_onboarding, "anomaly_detection_readiness",
            side_effect=OnboardingError("invalid_anomaly_readiness"),
        ):
            option = self.manager.dynamic_dataset_catalog()["datasets"][0]

        self.assertEqual(option["dataset_id"], self.dataset_id)
        self.assertEqual(option["anomaly_state"], "BLOCKED")
        self.assertEqual(option["supported_anomaly_operations"], [])

    def test_session_executes_sales_and_profit_only_through_dynamic_manager(self):
        self.session.select_dynamic_dataset(self.dataset_id)

        for operation, expected in (
            ("SALES_ANOMALY_SCREEN", "100"),
            ("PROFIT_ANOMALY_SCREEN", "200"),
        ):
            with self.subTest(operation=operation):
                outcome = self.session.execute_dynamic_anomaly(operation)
                direct = self.manager.execute_dataset_anomaly_request(
                    DynamicAnomalyRequest(self.dataset_id, operation)
                )
                self.assertEqual(outcome["status"], "SUCCESS")
                self.assertEqual(outcome["result"], direct)
                self.assertEqual(
                    outcome["result"]["delegated_result"]["result"]["scope"], "GLOBAL",
                )
                self.assertIn(expected, repr(outcome["result"]["delegated_result"]))

    def test_no_selection_never_auto_selects_even_the_only_dataset(self):
        outcome = self.session.execute_dynamic_anomaly("SALES_ANOMALY_SCREEN")

        self.assertEqual(outcome["status"], "CLARIFICATION_REQUIRED")
        self.assertEqual(outcome["error"]["choices"], [self.dataset_id])
        self.assertIsNone(self.session.status()["dynamic_dataset"])

    def test_closed_intent_accepts_two_operations_and_rejects_arbitrary_algorithm(self):
        option = DynamicDatasetOption(
            self.dataset_id, "SALES_RECORD", "AVAILABLE_WITH_LIMITATIONS",
            ("SALES_RECORD_COUNT",), "AVAILABLE_WITH_LIMITATIONS",
            ("SALES_ANOMALY_SCREEN", "PROFIT_ANOMALY_SCREEN"),
        )
        context = InterpretationContext(
            dynamic_datasets=(option,), selected_dynamic_dataset=self.dataset_id,
        )

        for operation in ("SALES_ANOMALY_SCREEN", "PROFIT_ANOMALY_SCREEN"):
            accepted = parse_intent(json.dumps(dynamic_intent(
                "DYNAMIC_ANOMALY_SCREEN", capability_hint="ANOMALY_DETECTION",
                dynamic_operation=operation,
            )), context)
            self.assertEqual(accepted.dynamic_operation, operation)
        for operation in ("DISCOUNT_ANOMALY_SCREEN", "UNITS_ANOMALY_SCREEN", "ISOLATION_FOREST"):
            with self.subTest(operation=operation), self.assertRaises(MediationRejected):
                parse_intent(json.dumps(dynamic_intent(
                    "DYNAMIC_ANOMALY_SCREEN", capability_hint="ANOMALY_DETECTION",
                    dynamic_operation=operation,
                )), context)

    def test_current_schema_rejects_obsolete_deferral_while_version_11_stays_compatible(self):
        option = DynamicDatasetOption(
            self.dataset_id, "SALES_RECORD", "AVAILABLE_WITH_LIMITATIONS",
            ("SALES_RECORD_COUNT",), "AVAILABLE_WITH_LIMITATIONS",
            ("SALES_ANOMALY_SCREEN", "PROFIT_ANOMALY_SCREEN"),
        )
        context = InterpretationContext(
            dynamic_datasets=(option,), selected_dynamic_dataset=self.dataset_id,
        )
        current = dynamic_intent(
            "REQUEST_CLARIFICATION", clarification_kind="DYNAMIC_ANOMALY_DEFERRED",
        )
        legacy = dict(current, version="1.1")

        with self.assertRaises(MediationRejected):
            parse_intent(json.dumps(current), context)
        accepted = parse_intent(json.dumps(legacy), context)
        self.assertEqual(accepted.clarification_kind, "DYNAMIC_ANOMALY_DEFERRED")

    def test_selection_execution_labels_and_why_selected_are_grounded(self):
        select = f"Use dataset {self.dataset_id}."
        screen = "Are there unusual sales?"
        follow = "Why was A1 selected?"
        mediator, llm = self.mediator({
            select: dynamic_intent("SELECT_DYNAMIC_DATASET", dataset_id=self.dataset_id),
            screen: dynamic_intent(
                "DYNAMIC_ANOMALY_SCREEN", capability_hint="ANOMALY_DETECTION",
                dynamic_operation="SALES_ANOMALY_SCREEN",
            ),
            follow: dynamic_intent(
                "EVIDENCE_FOLLOWUP", evidence_reference="A1",
                follow_up_intent="why_selected",
            ),
        })

        mediator.handle(select)
        screened = mediator.handle(screen)
        explained = mediator.handle(follow)

        self.assertEqual(screened.outcome["status"], "SUCCESS")
        self.assertEqual([label for label, _handle in screened.labels], ["A1"])
        self.assertIn("CANDIDATE", screened.text)
        self.assertNotIn("fraudulent", screened.text.casefold())
        self.assertEqual(explained.outcome["status"], "SUCCESS")
        self.assertEqual(explained.outcome["result"]["observed_value"], "100")
        assessment = explained.outcome["result"]["assessments"]["global"]
        self.assertEqual(assessment["assessment"]["tail"], "upper")
        self.assertEqual(assessment["reference"]["upper_fence"], "45.00")
        self.assertIn("45.00", explained.text)
        self.assertEqual(llm.packets[-1]["subject"]["dataset"], self.dataset_id)

    def test_record_detail_is_same_bounded_fresh_evidence_view(self):
        self.session.select_dynamic_dataset(self.dataset_id)
        screened = self.session.execute_dynamic_anomaly("SALES_ANOMALY_SCREEN")
        handle = screened["references"][0]["handle"]

        detail = self.session.follow_up(reference=handle, intent="record_detail")

        self.assertEqual(detail["status"], "SUCCESS")
        self.assertEqual(set(detail["result"]), {
            "reference_type", "capability", "dataset", "measure", "operation",
            "snapshot", "result_digest", "lineage", "observed_value", "observed_raw",
            "observed_status", "peer_values", "assessments", "policy", "currency",
            "quality_warnings",
        })
        self.assertEqual(detail["result"]["lineage"]["source_row_number"], 32)
        self.assertNotIn("country", repr(detail["result"]).casefold())
        self.assertNotIn("product", repr(detail["result"]).casefold())

    def test_invented_cross_session_and_cross_dataset_references_fail_closed(self):
        self.session.select_dynamic_dataset(self.dataset_id)
        screened = self.session.execute_dynamic_anomaly("SALES_ANOMALY_SCREEN")
        handle = screened["references"][0]["handle"]
        other = FinancialManagerSession(manager=self.manager, clock=FixedClock())

        self.assertEqual(
            self.session.follow_up(reference="A1; DROP TABLE sales", intent="why_selected")["status"],
            "UNKNOWN_REFERENCE",
        )
        self.assertEqual(other.follow_up(reference=handle, intent="why_selected")["status"],
                         "NO_EVIDENCE_CONTEXT")

        _onboarding, second = onboard_sales(
            self.base, anomaly_csv(sales_outlier="101"), mappings=MAPPINGS,
        )
        self.session.select_dynamic_dataset(second["dataset_id"])
        self.assertEqual(self.session.follow_up(reference=handle, intent="why_selected")["status"],
                         "NO_EVIDENCE_CONTEXT")

    def test_source_invalidation_makes_candidate_reference_stale(self):
        self.session.select_dynamic_dataset(self.dataset_id)
        screened = self.session.execute_dynamic_anomaly("SALES_ANOMALY_SCREEN")
        handle = screened["references"][0]["handle"]
        source = next((self.root / "artifacts" / self.dataset_id / "source").iterdir())
        source.write_text(anomaly_csv(sales_outlier="101"), encoding="utf-8")

        stale = self.session.follow_up(reference=handle, intent="why_selected")

        self.assertEqual(stale["status"], "STALE_REFERENCE")
        self.assertIsNone(self.session.status()["dynamic_dataset"])

    def test_new_screen_reset_cancel_and_financial_request_invalidate_labels(self):
        self.session.select_dynamic_dataset(self.dataset_id)
        first = self.session.execute_dynamic_anomaly("SALES_ANOMALY_SCREEN")
        old = first["references"][0]["handle"]
        self.session.execute_dynamic_anomaly("PROFIT_ANOMALY_SCREEN")
        self.assertEqual(self.session.follow_up(reference=old, intent="why_selected")["status"],
                         "UNKNOWN_REFERENCE")

        self.session.reset()
        self.assertEqual(self.session.follow_up(reference=old, intent="why_selected")["status"],
                         "NO_EVIDENCE_CONTEXT")
        self.session.select_dynamic_dataset(self.dataset_id)
        latest = self.session.execute_dynamic_anomaly("SALES_ANOMALY_SCREEN")
        latest_handle = latest["references"][0]["handle"]
        self.session.cancel()
        self.assertEqual(self.session.follow_up(reference=latest_handle, intent="why_selected")["status"],
                         "NO_EVIDENCE_CONTEXT")

    def test_blocked_profit_is_not_substituted_with_sales(self):
        partial = "date,sales\n" + "\n".join(
            f"2026-01-01,{value}" for value in list(range(30)) + [100]
        ) + "\n"
        _onboarding, state = onboard_sales(
            self.base, partial, mappings={"date": "TRANSACTION_DATE", "sales": "SALES"},
        )
        manager = FinancialManagerAgent(onboarding_root=self.root)
        session = FinancialManagerSession(manager=manager, clock=FixedClock())
        session.select_dynamic_dataset(state["dataset_id"])

        outcome = session.execute_dynamic_anomaly("PROFIT_ANOMALY_SCREEN")

        self.assertEqual(outcome["status"], "DATA_QUALITY_BLOCKER")
        self.assertEqual(outcome["result"]["errors"][0]["code"], "missing_confirmed_profit")
        self.assertIsNone(outcome["result"]["delegated_result"])

        session.select_dynamic_dataset(state["dataset_id"])
        question = "Check Profit for anomalies."
        turn = ConversationMediator(session, ScriptedLLM({question: dynamic_intent(
            "DYNAMIC_ANOMALY_SCREEN", capability_hint="ANOMALY_DETECTION",
            dynamic_operation="PROFIT_ANOMALY_SCREEN",
        )}).provider).handle(question)
        self.assertIn("confirmed supplied Profit", turn.text)
        self.assertNotIn("Sales instead", turn.text)

    def test_exact_same_turn_target_executes_without_prior_selection(self):
        question = f"Check sales for anomalies in dataset {self.dataset_id}."
        mediator, _llm = self.mediator({question: dynamic_intent(
            "DYNAMIC_ANOMALY_SCREEN", capability_hint="ANOMALY_DETECTION",
            dataset_id=self.dataset_id, dynamic_operation="SALES_ANOMALY_SCREEN",
        )})

        turn = mediator.handle(question)

        self.assertEqual(turn.outcome["status"], "SUCCESS")
        self.assertEqual(
            turn.outcome["result"]["delegated_result"]["result"]["dataset_id"],
            self.dataset_id,
        )
        self.assertEqual(self.session.status()["dynamic_dataset"]["dataset_id"], self.dataset_id)

    def test_multiple_datasets_without_selection_require_clarification(self):
        _onboarding, second = onboard_sales(
            self.base, anomaly_csv(sales_outlier="101"), mappings=MAPPINGS,
        )
        outcome = self.session.execute_dynamic_anomaly("SALES_ANOMALY_SCREEN")

        self.assertEqual(outcome["status"], "CLARIFICATION_REQUIRED")
        self.assertCountEqual(outcome["error"]["choices"], [
            self.dataset_id, second["dataset_id"],
        ])
        self.assertIsNone(self.session.status()["dynamic_dataset"])

    def test_provider_malformed_or_unavailable_never_executes_dynamic_anomaly(self):
        self.session.select_dynamic_dataset(self.dataset_id)
        for provider_value in ("not json", RuntimeError("provider unavailable")):
            with self.subTest(provider=type(provider_value).__name__), patch.object(
                self.manager, "execute_dataset_anomaly_request",
                wraps=self.manager.execute_dataset_anomaly_request,
            ) as execute:
                llm = ScriptedLLM({"Find anomalies": provider_value})
                turn = ConversationMediator(self.session, llm.provider).handle("Find anomalies")

                self.assertIsNone(turn.outcome)
                self.assertIn("not executed", turn.text)
                execute.assert_not_called()

    def test_schema_valid_user_text_cannot_redirect_dynamic_anomaly_to_legacy(self):
        self.session.select_dynamic_dataset(self.dataset_id)
        question = "Are there unusual sales?"
        llm = ScriptedLLM({question: dynamic_intent(
            "NEW_REQUEST", intent="USER_TEXT",
        )})
        with patch.object(self.manager, "ask", wraps=self.manager.ask) as ask:
            turn = ConversationMediator(self.session, llm.provider).handle(question)

        self.assertIsNone(turn.outcome)
        self.assertIn("not executed", turn.text)
        ask.assert_not_called()

    def test_stale_dynamic_selection_cannot_redirect_to_legacy_request(self):
        self.session.select_dynamic_dataset(self.dataset_id)
        source = next((self.root / "artifacts" / self.dataset_id / "source").iterdir())
        source.write_text(anomaly_csv(sales_outlier="101"), encoding="utf-8")
        question = "Are there unusual sales?"
        llm = ScriptedLLM({question: dynamic_intent(
            "NEW_REQUEST", intent="SCREEN_CF_SALES", capability_hint="ANOMALY_DETECTION",
        )})
        with patch.object(self.manager, "ask", wraps=self.manager.ask) as ask:
            turn = ConversationMediator(self.session, llm.provider).handle(question)

        self.assertIsNone(turn.outcome)
        self.assertIn("no longer current", turn.text)
        self.assertIsNone(self.session.status()["dynamic_dataset"])
        ask.assert_not_called()

    def test_fraud_claim_from_response_provider_is_discarded_for_safe_fallback(self):
        question = f"Find fraudulent sales in dataset {self.dataset_id}."

        def unsafe(packet):
            return {
                "message": "1 fraudulent record was found.",
                "used_fact_ids": [packet["facts"][0]["id"]],
                "warning_fact_ids": [],
                "presentation_hint": packet["default_presentation"],
                "language": packet["language"],
            }

        mediator, _llm = self.mediator({question: dynamic_intent(
            "DYNAMIC_ANOMALY_SCREEN", capability_hint="ANOMALY_DETECTION",
            dataset_id=self.dataset_id, dynamic_operation="SALES_ANOMALY_SCREEN",
        )}, respond=unsafe)

        turn = mediator.handle(question)

        self.assertEqual(turn.outcome["status"], "SUCCESS")
        self.assertIsNotNone(turn.notice)
        self.assertNotIn("fraudulent record", turn.text.casefold())
        self.assertIn("it is not fraud", turn.text.casefold())
        self.assertIn("CANDIDATE", turn.text)

    def test_dynamic_followup_provider_failure_uses_code_rendered_fallback(self):
        select = f"Use dataset {self.dataset_id}."
        screen = "Check Sales for anomalies."
        follow = "Why was A1 selected?"

        def respond(packet):
            if packet["default_presentation"] == "LIST":
                raise RuntimeError("response provider unavailable")
            return grounded_response(packet)

        mediator, _llm = self.mediator({
            select: dynamic_intent("SELECT_DYNAMIC_DATASET", dataset_id=self.dataset_id),
            screen: dynamic_intent(
                "DYNAMIC_ANOMALY_SCREEN", capability_hint="ANOMALY_DETECTION",
                dynamic_operation="SALES_ANOMALY_SCREEN",
            ),
            follow: dynamic_intent(
                "EVIDENCE_FOLLOWUP", evidence_reference="A1",
                follow_up_intent="why_selected",
            ),
        }, respond=respond)
        mediator.handle(select)
        mediator.handle(screen)

        turn = mediator.handle(follow)

        self.assertEqual(turn.outcome["status"], "SUCCESS")
        self.assertIsNotNone(turn.notice)
        self.assertIsNotNone(turn.text)
        self.assertIn("45.00", turn.text)
        self.assertIn("CANDIDATE", turn.text)

    def test_readiness_blocks_insufficient_zero_iqr_and_multiple_currency(self):
        cases = (
            (
                "date,sales\n" + "\n".join(
                    f"2026-01-01,{value}" for value in range(29)
                ) + "\n",
                {"date": "TRANSACTION_DATE", "sales": "SALES"}, None,
                "insufficient_numeric_records",
            ),
            (
                "date,sales\n" + "\n".join("2026-01-01,1" for _ in range(30)) + "\n",
                {"date": "TRANSACTION_DATE", "sales": "SALES"}, None, "zero_iqr",
            ),
            (
                "date,sales,currency\n" + "\n".join(
                    f"2026-01-01,{value},{'USD' if value % 2 else 'BRL'}"
                    for value in list(range(30)) + [100]
                ) + "\n",
                {"date": "TRANSACTION_DATE", "sales": "SALES", "currency": "CURRENCY"},
                {"USD": "USD", "BRL": "BRL"}, "incompatible_currency",
            ),
        )
        for csv_text, mappings, currencies, reason in cases:
            with self.subTest(reason=reason):
                _onboarding, state = onboard_sales(
                    self.base, csv_text, mappings=mappings, currency_values=currencies,
                )
                session = FinancialManagerSession(
                    manager=FinancialManagerAgent(onboarding_root=self.root), clock=FixedClock(),
                )
                session.select_dynamic_dataset(state["dataset_id"])
                outcome = session.execute_dynamic_anomaly("SALES_ANOMALY_SCREEN")
                self.assertEqual(outcome["status"], "DATA_QUALITY_BLOCKER")
                self.assertEqual(outcome["result"]["errors"][0]["code"], reason)
                self.assertIsNone(outcome["result"]["delegated_result"])

    def test_confirmed_currency_is_copied_without_inference_or_conversion(self):
        rows = ["date,sales,currency"] + [
            f"2026-01-01,{value},USD" for value in list(range(30)) + [100]
        ]
        _onboarding, state = onboard_sales(
            self.base, "\n".join(rows) + "\n",
            mappings={"date": "TRANSACTION_DATE", "sales": "SALES", "currency": "CURRENCY"},
            currency_values={"USD": "USD"},
        )
        session = FinancialManagerSession(
            manager=FinancialManagerAgent(onboarding_root=self.root), clock=FixedClock(),
        )
        session.select_dynamic_dataset(state["dataset_id"])

        outcome = session.execute_dynamic_anomaly("SALES_ANOMALY_SCREEN")
        currency = outcome["result"]["delegated_result"]["currency"]

        self.assertEqual(currency["status"], "CONFIRMED")
        self.assertEqual(currency["code"], "USD")
        self.assertFalse(currency["conversion_applied"])

    def test_phase16_twenty_reference_bound_maps_to_existing_ten_label_bound(self):
        rows = ["date,sales"]
        rows.extend(f"2026-01-01,{value}" for value in range(100))
        rows.extend("2026-01-01,10000" for _ in range(30))
        _onboarding, state = onboard_sales(
            self.base, "\n".join(rows) + "\n",
            mappings={"date": "TRANSACTION_DATE", "sales": "SALES"},
        )
        session = FinancialManagerSession(
            manager=FinancialManagerAgent(onboarding_root=self.root), clock=FixedClock(),
        )
        session.select_dynamic_dataset(state["dataset_id"])

        outcome = session.execute_dynamic_anomaly("SALES_ANOMALY_SCREEN")

        evidence = outcome["result"]["delegated_result"]["result"]
        self.assertEqual(evidence["counts"]["candidate"], 30)
        self.assertEqual(len(evidence["candidate_references"]), 20)
        self.assertEqual(len(outcome["references"]), 10)
        self.assertEqual(session.status()["active_context"]["reference_count"], 10)
        rendered = deterministic_dynamic(locate(outcome), "en")
        self.assertIn("Showing 10 of 30 records flagged CANDIDATE", rendered)


if __name__ == "__main__":
    unittest.main()
