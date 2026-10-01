"""Step 35 interactive CLI behavior through the public CLI/session seams."""

from io import StringIO
from datetime import datetime, timedelta, timezone
import unittest

from src.cli.main import main
from src.manager import FinancialManagerAgent, FinancialManagerSession


class ConversationalCLITests(unittest.TestCase):
    def make_session(self):
        references = iter(f"chat-evidence-{index}" for index in range(1, 20))
        return FinancialManagerSession(
            manager=FinancialManagerAgent(),
            session_id_factory=lambda: "chat-session",
            reference_id_factory=lambda: next(references),
        )

    def run_chat(self, script, *, session=None):
        output, error = StringIO(), StringIO()
        code = main(
            ["chat"],
            session=self.make_session() if session is None else session,
            stdin=StringIO(script),
            stdout=output,
            stderr=error,
        )
        return code, output.getvalue(), error.getvalue()

    def test_plain_text_runs_an_independent_request_and_exit_is_clean(self):
        code, output, error = self.run_chat(
            "What were total sales by country?\n/exit\n"
        )

        self.assertEqual(code, 0)
        self.assertIn("Financial Manager > ", output)
        self.assertIn("Status: SUCCESS", output)
        self.assertIn("one-shot ask command with --full or --json", output)
        self.assertNotIn("Use --full for expanded human output.", output)
        self.assertIn("Chat ended.", output)
        self.assertEqual(error, "")

    def test_supported_clarification_requires_the_explicit_answer_command(self):
        code, output, error = self.run_chat(
            "Check my financial data.\n/answer anomaly screening\n/exit\n"
        )

        self.assertEqual(code, 0)
        self.assertIn("Clarification pending.", output)
        self.assertIn("/answer financial analysis", output)
        self.assertIn("/answer anomaly screening", output)
        self.assertIn("Financial Manager [clarification] > ", output)
        self.assertEqual(error, "")

    def test_plain_text_visibly_replaces_a_pending_clarification(self):
        code, output, error = self.run_chat(
            "Check my financial data.\nWhat were total sales by country?\n/exit\n"
        )

        self.assertEqual(code, 0)
        self.assertIn("Starting a new request; the pending clarification is replaced.", output)
        self.assertIn("Status: SUCCESS", output)
        self.assertEqual(error, "")

    def test_help_status_cancel_and_reset_use_the_bounded_lifecycle_surface(self):
        code, output, error = self.run_chat(
            "/help\nCheck my financial data.\n/status\n/cancel\n/reset\n/exit\n"
        )

        self.assertEqual(code, 0)
        self.assertIn("Plain text starts a new request.", output)
        self.assertIn("Session status:", output)
        self.assertIn('"status": "ACTIVE"', output)
        self.assertNotIn("chat-session", output)
        self.assertIn("Session outcome: CANCELLED", output)
        self.assertIn("Session outcome: RESET", output)
        self.assertEqual(error, "")

    def test_unknown_commands_and_empty_input_do_not_become_financial_requests(self):
        code, output, error = self.run_chat("\n/unknown Sales\n/status\n/exit\n")

        self.assertEqual(code, 0)
        self.assertIn("Invalid chat command. Use /help.", output)
        self.assertIn('"active_context": null', output)
        self.assertNotIn("Status: SUCCESS", output)
        self.assertEqual(error, "")

    def test_chat_rejects_one_shot_presentation_flags(self):
        for flag in ("--json", "--full"):
            with self.subTest(flag=flag):
                output, error = StringIO(), StringIO()
                code = main(
                    [flag, "chat"],
                    session=self.make_session(),
                    stdin=StringIO("/exit\n"),
                    stdout=output,
                    stderr=error,
                )

                self.assertEqual(code, 2)
                self.assertEqual(output.getvalue(), "")
                self.assertIn("Invalid CLI syntax", error.getvalue())

    def test_anomaly_references_are_displayed_and_followed_only_explicitly(self):
        code, output, error = self.run_chat(
            "Screen profit\n/follow chat-evidence-1 why_selected\n/exit\n"
        )

        self.assertEqual(code, 0)
        self.assertIn("Evidence references:", output)
        self.assertIn("chat-evidence-1 (ANOMALY_RECORD)", output)
        self.assertIn("/follow <reference> why_selected", output)
        self.assertIn('"reference_type": "ANOMALY_RECORD"', output)
        self.assertIn('"dataset": "company_financials"', output)
        self.assertEqual(error, "")

    def test_malformed_follow_command_is_rejected_without_losing_context(self):
        code, output, error = self.run_chat(
            "Screen profit\n/follow chat-evidence-1\n/status\n/exit\n"
        )

        self.assertEqual(code, 0)
        self.assertIn("Invalid chat command. Use /help.", output)
        self.assertIn('"kind": "ANOMALY_EVIDENCE"', output)
        self.assertEqual(error, "")

    def test_eof_and_ctrl_c_end_chat_cleanly(self):
        code, output, error = self.run_chat("")
        self.assertEqual(code, 0)
        self.assertIn("Chat ended.", output)
        self.assertEqual(error, "")

        class InterruptedInput:
            def readline(self):
                raise KeyboardInterrupt()

        output, error = StringIO(), StringIO()
        code = main(
            ["chat"], session=self.make_session(), stdin=InterruptedInput(),
            stdout=output, stderr=error,
        )
        self.assertEqual(code, 0)
        self.assertIn("Chat ended.", output.getvalue())
        self.assertEqual(error.getvalue(), "")

    def test_expired_clarification_is_not_silently_recreated(self):
        class Clock:
            current = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)

            def __call__(self):
                return self.current

        clock = Clock()
        session = FinancialManagerSession(
            manager=FinancialManagerAgent(), clock=clock,
            session_id_factory=lambda: "expiring-session",
        )

        class ExpiringInput:
            def __init__(self):
                self.lines = iter((
                    "Check my financial data.\n",
                    "/answer anomaly screening\n",
                    "/exit\n",
                ))
                self.index = 0

            def readline(self):
                self.index += 1
                if self.index == 2:
                    clock.current += timedelta(minutes=31)
                return next(self.lines, "")

        output, error = StringIO(), StringIO()
        code = main(
            ["chat"], session=session, stdin=ExpiringInput(),
            stdout=output, stderr=error,
        )

        self.assertEqual(code, 0)
        self.assertIn("Session outcome: SESSION_EXPIRED", output.getvalue())
        self.assertIn("start a new request", output.getvalue())
        self.assertIn("/reset", output.getvalue())
        self.assertEqual(error.getvalue(), "")

    def test_each_expired_continuation_command_shows_both_recovery_paths(self):
        class Clock:
            current = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)

            def __call__(self):
                return self.current

        for command in (
            "/answer anomaly screening",
            "/follow unavailable why_selected",
            "/cancel",
        ):
            with self.subTest(command=command):
                clock = Clock()
                session = FinancialManagerSession(
                    manager=FinancialManagerAgent(), clock=clock,
                    session_id_factory=lambda: "expired-session",
                )
                clock.current += timedelta(minutes=31)

                code, output, error = self.run_chat(
                    command + "\n/exit\n", session=session,
                )

                self.assertEqual(code, 0)
                self.assertIn("Session outcome: SESSION_EXPIRED", output)
                self.assertIn("complete new request", output)
                self.assertIn("/reset", output)
                self.assertEqual(error, "")

    def test_prompt_drops_stale_clarification_indicator_after_waiting_expiry(self):
        class Clock:
            current = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)

            def __call__(self):
                return self.current

        clock = Clock()
        session = FinancialManagerSession(
            manager=FinancialManagerAgent(), clock=clock,
            session_id_factory=lambda: "prompt-expiry-session",
        )
        session.new_request("Check my financial data.")

        class ExpiringHelpInput:
            def __init__(self):
                self.lines = iter(("/help\n", "/exit\n"))
                self.first = True

            def readline(self):
                if self.first:
                    self.first = False
                    clock.current += timedelta(minutes=31)
                return next(self.lines, "")

        output, error = StringIO(), StringIO()
        code = main(
            ["chat"], session=session, stdin=ExpiringHelpInput(),
            stdout=output, stderr=error,
        )

        self.assertEqual(code, 0)
        self.assertEqual(output.getvalue().count("Financial Manager [clarification] > "), 1)
        self.assertIn("Financial Manager > Chat ended.", output.getvalue())
        self.assertEqual(error.getvalue(), "")

    def test_unexpected_session_failure_uses_the_fixed_cli_diagnostic(self):
        class BrokenManager:
            def ask(self, question):
                raise RuntimeError("/private/data.db API_KEY=fixture-secret")

        session = FinancialManagerSession(
            manager=BrokenManager(),
            session_id_factory=lambda: "broken-session",
        )
        output, error = StringIO(), StringIO()

        code = main(
            ["chat"], session=session, stdin=StringIO("Sales\n"),
            stdout=output, stderr=error,
        )

        self.assertEqual(code, 1)
        self.assertNotIn("fixture-secret", output.getvalue() + error.getvalue())
        self.assertNotIn("Traceback", output.getvalue() + error.getvalue())
        self.assertIn("Unable to complete the command.", error.getvalue())


if __name__ == "__main__":
    unittest.main()
