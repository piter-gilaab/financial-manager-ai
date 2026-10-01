"""Phase 10 bounded in-memory conversation session behavior."""

from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import patch

from src.manager import FinancialManagerAgent, FinancialManagerSession


class FakeClock:
    def __init__(self):
        self.current = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)

    def __call__(self):
        return self.current

    def advance(self, **values):
        self.current += timedelta(**values)


class RecordingManager:
    def __init__(self):
        self.manager = FinancialManagerAgent()
        self.questions = []

    def ask(self, question):
        self.questions.append(question)
        return self.manager.ask(question)


class FailOnSecondQuestion(RecordingManager):
    def ask(self, question):
        if self.questions:
            raise RuntimeError("test-only manager failure")
        return super().ask(question)


class ConversationSessionTests(unittest.TestCase):
    def test_session_creation_and_status_are_bounded_and_inspectable(self):
        clock = FakeClock()
        session = FinancialManagerSession(clock=clock, session_id_factory=lambda: "session-a")

        status = session.status()

        self.assertEqual(status["conversation_version"], "1.0")
        self.assertEqual(status["session_id"], "session-a")
        self.assertEqual(status["status"], "ACTIVE")
        self.assertEqual(status["created_at"], "2026-10-01T12:00:00+00:00")
        self.assertEqual(status["last_activity_at"], status["created_at"])
        self.assertEqual(status["inactivity_expires_at"], "2026-10-01T12:30:00+00:00")
        self.assertEqual(status["absolute_expires_at"], "2026-10-01T16:00:00+00:00")
        self.assertIsNone(status["active_context"])

    def test_new_request_stores_only_supported_capability_choice(self):
        session = FinancialManagerSession(
            manager=FinancialManagerAgent(), clock=FakeClock(),
            session_id_factory=lambda: "session-a",
        )

        outcome = session.new_request("Check my financial data.")

        self.assertEqual(outcome["operation"], "new_request")
        self.assertEqual(outcome["status"], "CLARIFICATION_REQUIRED")
        self.assertEqual(outcome["result"]["execution_status"], "CLARIFICATION_REQUIRED")
        context = session.status()["active_context"]
        self.assertEqual(context["reconstruction_descriptor"], {"kind": "CAPABILITY_CHOICE"})
        self.assertEqual(context["pending_clarification"], {
            "source": "STEP_18_ROUTER",
            "code": "capability_required",
            "field": "capability",
            "choices": ["FINANCIAL_ANALYSIS", "ANOMALY_DETECTION"],
        })
        self.assertNotIn("Check my financial data", repr(context))

    def test_capability_answer_reconstructs_and_routes_a_fresh_request(self):
        manager = RecordingManager()
        session = FinancialManagerSession(
            manager=manager, clock=FakeClock(), session_id_factory=lambda: "session-a",
        )
        session.new_request("Check my financial data.")

        outcome = session.answer("Anomaly screening")

        self.assertEqual(manager.questions, [
            "Check my financial data.",
            "Screen financial data for anomalies.",
        ])
        self.assertEqual(outcome["operation"], "answer")
        self.assertEqual(outcome["status"], "CLARIFICATION_REQUIRED")
        self.assertEqual(outcome["result"]["routing"]["reason_code"], "screening_scope_required")
        self.assertIsNone(session.status()["active_context"])

    def test_invalid_capability_answer_neither_executes_nor_mutates_or_extends_state(self):
        clock, manager = FakeClock(), RecordingManager()
        session = FinancialManagerSession(
            manager=manager, clock=clock, session_id_factory=lambda: "session-a",
        )
        session.new_request("Check my financial data.")
        before = session.status()
        clock.advance(minutes=5)

        outcome = session.answer("CASH_FLOW_FORECASTING")

        self.assertEqual(outcome["status"], "INVALID_ANSWER")
        self.assertEqual(outcome["result"], None)
        self.assertEqual(manager.questions, ["Check my financial data."])
        self.assertEqual(session.status(), before)

    def test_record_count_clarification_and_dataset_answer_use_canonical_fresh_request(self):
        manager = RecordingManager()
        session = FinancialManagerSession(
            manager=manager, clock=FakeClock(), session_id_factory=lambda: "session-a",
        )

        first = session.new_request("How many records are there?")

        self.assertEqual(first["status"], "CLARIFICATION_REQUIRED")
        self.assertEqual(session.status()["active_context"], {
            "reconstruction_descriptor": {"kind": "FINANCIAL_RECORD_COUNT"},
            "pending_clarification": {
                "source": "FINANCIAL_ANALYSIS_AGENT",
                "code": "dataset_required",
                "field": "dataset",
                "choices": ["receiver_general", "company_financials"],
            },
        })

        outcome = session.answer("Company Financials")

        self.assertEqual(manager.questions[-1], "Company Financials record count")
        self.assertEqual(outcome["status"], "SUCCESS")
        evidence = outcome["result"]["results"][0]["response"]["delegated_result"]["tool_result"]
        self.assertEqual(evidence["result"]["record_count"], 700)
        self.assertIsNone(session.status()["active_context"])

    def test_invalid_record_count_dataset_answer_does_not_execute(self):
        manager = RecordingManager()
        session = FinancialManagerSession(
            manager=manager, clock=FakeClock(), session_id_factory=lambda: "session-a",
        )
        session.new_request("How many records are there?")
        before = session.status()

        outcome = session.answer("forecasting")

        self.assertEqual(outcome["status"], "INVALID_ANSWER")
        self.assertEqual(manager.questions, ["How many records are there?"])
        self.assertEqual(session.status(), before)

    def test_inactivity_expiry_clears_context_and_rejects_answer(self):
        clock, manager = FakeClock(), RecordingManager()
        session = FinancialManagerSession(
            manager=manager, clock=clock, session_id_factory=lambda: "session-a",
        )
        session.new_request("Check my financial data.")
        clock.advance(minutes=30)

        status = session.status()
        outcome = session.answer("Anomaly screening")

        self.assertEqual(status["status"], "EXPIRED")
        self.assertIsNone(status["active_context"])
        self.assertEqual(outcome["status"], "SESSION_EXPIRED")
        self.assertEqual(manager.questions, ["Check my financial data."])

    def test_absolute_expiry_wins_even_when_valid_activity_refreshes_inactivity(self):
        clock = FakeClock()
        session = FinancialManagerSession(
            manager=FinancialManagerAgent(), clock=clock,
            session_id_factory=lambda: "session-a",
        )
        for _ in range(8):
            clock.advance(minutes=29)
            session.new_request("Forecast cash flow.")
        clock.advance(minutes=8)

        self.assertEqual(session.status()["status"], "EXPIRED")
        self.assertIsNone(session.status()["active_context"])

    def test_cancel_reset_and_new_request_have_distinct_state_transitions(self):
        ids = iter(("session-a", "session-b"))
        session = FinancialManagerSession(
            manager=FinancialManagerAgent(), clock=FakeClock(),
            session_id_factory=lambda: next(ids),
        )
        session.new_request("Check my financial data.")

        cancelled = session.cancel()

        self.assertEqual(cancelled["status"], "CANCELLED")
        self.assertIsNone(session.status()["active_context"])
        session.new_request("How many records are there?")
        blocked = session.new_request("Forecast cash flow.")
        self.assertEqual(blocked["status"], "CAPABILITY_UNAVAILABLE")
        self.assertIsNone(session.status()["active_context"])

        reset = session.reset()

        self.assertEqual(reset["status"], "RESET")
        self.assertEqual(session.status()["session_id"], "session-b")
        self.assertIsNone(session.status()["active_context"])

    def test_sessions_are_isolated_and_state_never_accumulates_chat_history(self):
        first = FinancialManagerSession(
            manager=FinancialManagerAgent(), clock=FakeClock(),
            session_id_factory=lambda: "session-a",
        )
        second = FinancialManagerSession(
            manager=FinancialManagerAgent(), clock=FakeClock(),
            session_id_factory=lambda: "session-b",
        )
        first.new_request("Check my financial data.")

        self.assertIsNotNone(first.status()["active_context"])
        self.assertIsNone(second.status()["active_context"])
        self.assertEqual(second.answer("Anomaly screening")["status"], "NO_PENDING_CLARIFICATION")
        self.assertNotIn("Check my financial data", repr(first.status()))
        self.assertNotIn("history", first.status())

    def test_step31_operations_remain_offline_and_blocked_capabilities_stay_blocked(self):
        session = FinancialManagerSession(
            manager=FinancialManagerAgent(), clock=FakeClock(),
            session_id_factory=lambda: "session-a",
        )
        with patch("socket.socket", side_effect=AssertionError("No network")), \
             patch("socket.create_connection", side_effect=AssertionError("No network")):
            forecast = session.new_request("Forecast cash flow.")
            retrieval = session.new_request("Search financial documents.")

        self.assertEqual(forecast["status"], "CAPABILITY_UNAVAILABLE")
        self.assertEqual(retrieval["status"], "CAPABILITY_UNAVAILABLE")
        self.assertIsNone(session.status()["active_context"])

    def test_session_configuration_cannot_create_non_data_or_ambiguous_state(self):
        for identifier in (object(), "", "x" * 129, "line\nbreak"):
            with self.subTest(identifier=identifier):
                with self.assertRaises(ValueError):
                    FinancialManagerSession(
                        clock=FakeClock(), session_id_factory=lambda value=identifier: value,
                    )
        with self.assertRaises(ValueError):
            FinancialManagerSession(
                clock=lambda: datetime(2026, 10, 1, 12, 0),
                session_id_factory=lambda: "session-a",
            )

    def test_status_is_a_defensive_copy_and_arbitrary_answer_objects_do_not_execute(self):
        manager = RecordingManager()
        session = FinancialManagerSession(
            manager=manager, clock=FakeClock(), session_id_factory=lambda: "session-a",
        )
        session.new_request("Check my financial data.")
        public = session.status()
        public["active_context"]["pending_clarification"]["choices"].clear()

        outcome = session.answer(object())

        self.assertEqual(outcome["status"], "INVALID_ANSWER")
        self.assertEqual(manager.questions, ["Check my financial data."])
        self.assertEqual(session.status()["active_context"]["pending_clarification"]["choices"],
                         ["FINANCIAL_ANALYSIS", "ANOMALY_DETECTION"])

    def test_unapproved_clarification_types_are_not_retained(self):
        session = FinancialManagerSession(
            manager=FinancialManagerAgent(), clock=FakeClock(),
            session_id_factory=lambda: "session-a",
        )

        outcome = session.new_request("Show extreme amounts")

        self.assertEqual(outcome["status"], "CLARIFICATION_REQUIRED")
        self.assertIsNone(session.status()["active_context"])

    def test_failed_reconstructed_execution_leaves_pending_state_unchanged(self):
        clock, manager = FakeClock(), FailOnSecondQuestion()
        session = FinancialManagerSession(
            manager=manager, clock=clock, session_id_factory=lambda: "session-a",
        )
        session.new_request("Check my financial data.")
        before = session.status()
        clock.advance(minutes=2)

        with self.assertRaisesRegex(RuntimeError, "test-only"):
            session.answer("Anomaly screening")

        self.assertEqual(session.status(), before)

    def test_non_string_new_request_cannot_invoke_custom_object_methods(self):
        class ExecutableQuestion:
            def strip(self):
                raise AssertionError("Custom string hook must not run")

        session = FinancialManagerSession(
            manager=FinancialManagerAgent(), clock=FakeClock(),
            session_id_factory=lambda: "session-a",
        )

        outcome = session.new_request(ExecutableQuestion())

        self.assertEqual(outcome["status"], "INVALID_REQUEST")
        self.assertIsNone(session.status()["active_context"])

    def test_clock_rollback_is_rejected_before_lifecycle_state_can_change(self):
        clock = FakeClock()
        session = FinancialManagerSession(
            manager=FinancialManagerAgent(), clock=clock,
            session_id_factory=lambda: "session-a",
        )
        clock.advance(minutes=5)
        session.cancel()
        before = session.status()
        clock.advance(minutes=-1)

        with self.assertRaisesRegex(ValueError, "must not move backward"):
            session.status()

        clock.advance(minutes=1)
        self.assertEqual(session.status(), before)


if __name__ == "__main__":
    unittest.main()
