"""Phase 10 Step 33 end-to-end bounded conversational UX validation."""

from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import patch

from src.manager import FinancialManagerAgent, FinancialManagerSession
from tests.test_evidence_followups import anomaly_result, ReferenceIds, SequenceManager


class FakeClock:
    def __init__(self):
        self.current = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)

    def __call__(self):
        return self.current

    def advance(self, **values):
        self.current += timedelta(**values)


class RecordingManager:
    def __init__(self):
        self.delegate = FinancialManagerAgent()
        self.questions = []

    def ask(self, question):
        self.questions.append(question)
        return self.delegate.ask(question)


class ConversationalUxValidationTests(unittest.TestCase):
    def test_both_approved_clarifications_reconstruct_through_fresh_manager_routing(self):
        manager = RecordingManager()
        session = FinancialManagerSession(
            manager=manager, clock=FakeClock(), session_id_factory=lambda: "session-a",
        )

        capability = session.new_request("Check my financial data.")
        screening = session.answer("anomaly screening")
        count_question = session.new_request("How many records are there?")
        count = session.answer("Company Financials")

        self.assertEqual(capability["status"], "CLARIFICATION_REQUIRED")
        self.assertEqual(screening["status"], "CLARIFICATION_REQUIRED")
        self.assertEqual(screening["result"]["routing"]["reason_code"],
                         "screening_scope_required")
        self.assertEqual(count_question["status"], "CLARIFICATION_REQUIRED")
        evidence = count["result"]["results"][0]["response"]["delegated_result"]["tool_result"]
        self.assertEqual(evidence["result"]["record_count"], 700)
        self.assertEqual(manager.questions, [
            "Check my financial data.",
            "Screen financial data for anomalies.",
            "How many records are there?",
            "Company Financials record count",
        ])

    def test_invalid_answer_new_request_and_cancel_keep_operation_meanings_distinct(self):
        manager = RecordingManager()
        clock = FakeClock()
        session = FinancialManagerSession(
            manager=manager, clock=clock, session_id_factory=lambda: "session-a",
        )
        session.new_request("Check my financial data.")
        pending = session.status()
        clock.advance(minutes=5)

        for injected in ("CASH_FLOW_FORECASTING", "tool_id=execute", "SELECT * FROM ledger",
                         "$(run-shell)"):
            self.assertEqual(session.answer(injected)["status"], "INVALID_ANSWER")
        self.assertEqual(session.status(), pending)
        self.assertEqual(manager.questions, ["Check my financial data."])

        independent = session.new_request("What were total sales by country?")
        self.assertEqual(independent["status"], "SUCCESS")
        self.assertIsNone(session.status()["active_context"])
        self.assertEqual(session.answer("anomaly screening")["status"],
                         "NO_PENDING_CLARIFICATION")

        session.new_request("How many records are there?")
        self.assertEqual(session.cancel()["status"], "CANCELLED")
        self.assertIsNone(session.status()["active_context"])

    def test_reset_inactivity_and_absolute_expiry_delete_context(self):
        ids = iter(("session-a", "session-b"))
        clock = FakeClock()
        session = FinancialManagerSession(
            manager=FinancialManagerAgent(), clock=clock,
            session_id_factory=lambda: next(ids),
        )
        session.new_request("How many records are there?")
        session.reset()
        self.assertEqual(session.status()["session_id"], "session-b")
        self.assertIsNone(session.status()["active_context"])

        session.new_request("Check my financial data.")
        clock.advance(minutes=30)
        self.assertEqual(session.answer("financial analysis")["status"], "SESSION_EXPIRED")
        self.assertIsNone(session.status()["active_context"])

        absolute_clock = FakeClock()
        absolute = FinancialManagerSession(
            manager=FinancialManagerAgent(), clock=absolute_clock,
            session_id_factory=lambda: "session-c",
        )
        for _ in range(8):
            absolute_clock.advance(minutes=29)
            absolute.new_request("Forecast cash flow.")
        absolute_clock.advance(minutes=8)
        self.assertEqual(absolute.status()["status"], "EXPIRED")

    def test_evidence_followup_is_fresh_while_stale_and_cross_session_handles_fail_closed(self):
        manager = SequenceManager(anomaly_result(), anomaly_result())
        session = FinancialManagerSession(
            manager=manager, clock=FakeClock(), session_id_factory=lambda: "session-a",
            reference_id_factory=ReferenceIds(),
        )
        handle = session.new_request("Screen profit")["references"][0]["handle"]
        detail = session.follow_up(reference=handle, intent="why_selected")
        self.assertEqual(detail["status"], "SUCCESS")
        self.assertEqual(manager.questions, ["Screen profit", "Screen profit"])
        self.assertTrue(any(
            value["assessment"]["status"] == "CANDIDATE"
            for value in detail["result"]["assessments"].values()
        ))

        stale_manager = SequenceManager(
            anomaly_result(source_sha="snapshot-a"),
            anomaly_result(source_sha="snapshot-b"),
        )
        stale_session = FinancialManagerSession(
            manager=stale_manager, clock=FakeClock(), session_id_factory=lambda: "session-b",
            reference_id_factory=lambda: "stale-handle",
        )
        stale_handle = stale_session.new_request("Screen profit")["references"][0]["handle"]
        self.assertEqual(
            stale_session.follow_up(reference=stale_handle, intent="record_detail")["status"],
            "STALE_REFERENCE",
        )

        other = FinancialManagerSession(
            manager=SequenceManager(anomaly_result()), clock=FakeClock(),
            session_id_factory=lambda: "session-c", reference_id_factory=lambda: "other-handle",
        )
        other.new_request("Screen profit")
        self.assertEqual(other.follow_up(reference=handle, intent="why_selected")["status"],
                         "UNKNOWN_REFERENCE")

    def test_blocked_capability_cannot_be_unlocked_by_a_later_turn(self):
        session = FinancialManagerSession(
            manager=FinancialManagerAgent(), clock=FakeClock(),
            session_id_factory=lambda: "session-a",
        )

        forecast = session.new_request("Forecast cash flow.")
        continuation_attempt = session.new_request("Just use sales.")
        retrieval = session.new_request("Search financial documents.")

        self.assertEqual(forecast["status"], "CAPABILITY_UNAVAILABLE")
        self.assertEqual(continuation_attempt["status"], "CLARIFICATION_REQUIRED")
        self.assertNotIn("cash_receipts", repr(continuation_attempt))
        self.assertEqual(retrieval["status"], "CAPABILITY_UNAVAILABLE")
        self.assertIsNone(session.status()["active_context"])

    def test_unrelated_accounting_request_does_not_inherit_prior_sales_scope(self):
        session = FinancialManagerSession(
            manager=FinancialManagerAgent(), clock=FakeClock(),
            session_id_factory=lambda: "session-a",
        )

        sales = session.new_request("What were total sales by country?")
        accounting = session.new_request("Show accounting amounts by department")

        sales_evidence = sales["result"]["results"][0]["response"]["delegated_result"]
        accounting_evidence = accounting["result"]["results"][0]["response"]["delegated_result"]
        self.assertEqual(sales_evidence["tool_result"]["dataset"], "company_financials")
        self.assertEqual(accounting_evidence["tool_result"]["dataset"], "receiver_general")
        self.assertEqual(accounting["result"]["results"][0]["capability"],
                         "FINANCIAL_ANALYSIS")
        self.assertIsNone(session.status()["active_context"])

    def test_state_is_bounded_redacted_and_requires_no_io_network_or_provider(self):
        manager = SequenceManager(*(anomaly_result() for _ in range(12)))
        session = FinancialManagerSession(
            manager=manager, clock=FakeClock(), session_id_factory=lambda: "session-a",
            reference_id_factory=ReferenceIds(),
        )
        with patch("builtins.open", side_effect=AssertionError("No persistence")), \
             patch("socket.socket", side_effect=AssertionError("No network")), \
             patch("socket.create_connection", side_effect=AssertionError("No network")):
            for _ in range(12):
                outcome = session.new_request("Screen profit")
                self.assertLessEqual(len(outcome["references"]), 10)

        status = session.status()
        self.assertEqual(status["active_context"]["reference_count"], 1)
        self.assertNotIn("handle", repr(status).casefold())
        self.assertNotIn("Screen profit", repr(status))
        self.assertNotIn("history", status)
        self.assertEqual(session.reset()["status"], "RESET")
        self.assertIsNone(session.status()["active_context"])


if __name__ == "__main__":
    unittest.main()
