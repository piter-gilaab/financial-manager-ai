"""Step 36 end-to-end validation of the real conversational CLI process."""

import hashlib
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from io import StringIO
import os
from pathlib import Path
import re
import selectors
import signal
import subprocess
import sys
import tempfile
import time
import unittest

from src.cli.main import main
from src.manager import FinancialManagerAgent, FinancialManagerSession


ROOT = Path(__file__).resolve().parents[1]
BOUNDARY_GUARD = '''
import os
import sys
from pathlib import Path

log = Path(os.environ["STEP36_AUDIT"])
log.write_text("ready\\n")

def boundary(event, args):
    forbidden = event.startswith("socket.") or event in (
        "subprocess.Popen", "os.system", "os.exec", "os.posix_spawn")
    if forbidden:
        with log.open("a") as stream:
            stream.write(event + "\\n")
        raise RuntimeError("Step 36 boundary blocked")

sys.addaudithook(boundary)
'''


def protected_hashes():
    return {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for directory in (ROOT / "data", ROOT / "notebooks")
        for path in directory.rglob("*") if path.is_file()
    }


def application_files():
    excluded_parts = {".git", ".venv", "__pycache__"}
    return {
        str(path.relative_to(ROOT))
        for path in ROOT.rglob("*")
        if path.is_file() and not excluded_parts.intersection(path.parts)
        and path.suffix != ".pyc"
    }


class ConversationalCLIValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protected_before = protected_hashes()
        cls.files_before = application_files()

    @classmethod
    def tearDownClass(cls):
        if protected_hashes() != cls.protected_before:
            raise AssertionError("Conversational CLI validation changed protected assets")
        if application_files() != cls.files_before:
            raise AssertionError("Conversational CLI validation created persistent application files")

    def run_chat(self, script, *, timeout=120):
        with tempfile.TemporaryDirectory(prefix="step36-chat-") as directory:
            temporary = Path(directory)
            (temporary / "sitecustomize.py").write_text(BOUNDARY_GUARD)
            audit = temporary / "audit.txt"
            env = os.environ.copy()
            python_path = str(temporary)
            if env.get("PYTHONPATH"):
                python_path += os.pathsep + env["PYTHONPATH"]
            env.update(PYTHONPATH=python_path, STEP36_AUDIT=str(audit))
            completed = subprocess.run(
                [sys.executable, "-B", "-m", "src.cli", "chat"],
                cwd=ROOT,
                env=env,
                input=script,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            self.assertTrue(audit.is_file(), "Boundary guard must load in the child")
            self.assertEqual(audit.read_text(), "ready\n")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stderr, "")
        self.assertNotIn("Traceback", completed.stdout)
        self.assertNotIn(str(ROOT), completed.stdout)
        return completed.stdout

    @contextmanager
    def interactive_chat(self):
        with tempfile.TemporaryDirectory(prefix="step36-live-chat-") as directory:
            temporary = Path(directory)
            (temporary / "sitecustomize.py").write_text(BOUNDARY_GUARD)
            audit = temporary / "audit.txt"
            env = os.environ.copy()
            python_path = str(temporary)
            if env.get("PYTHONPATH"):
                python_path += os.pathsep + env["PYTHONPATH"]
            env.update(PYTHONPATH=python_path, STEP36_AUDIT=str(audit))
            process = subprocess.Popen(
                [sys.executable, "-B", "-m", "src.cli", "chat"],
                cwd=ROOT,
                env=env,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0,
            )
            try:
                yield process
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=10)
                for stream in (process.stdin, process.stdout, process.stderr):
                    stream.close()
                self.assertTrue(audit.is_file(), "Boundary guard must load in the child")
                self.assertEqual(audit.read_text(), "ready\n")

    def read_to_prompt(self, process, *, limit=500_000, timeout=30):
        output = bytearray()
        prompts = (b"Financial Manager > ",
                   b"Financial Manager [clarification] > ")
        deadline = time.monotonic() + timeout
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            while len(output) < limit:
                remaining = deadline - time.monotonic()
                if remaining <= 0 or not selector.select(remaining):
                    self.fail("Interactive child timed out before a prompt")
                chunk = os.read(process.stdout.fileno(), min(4096, limit - len(output)))
                if not chunk:
                    break
                output.extend(chunk)
                if output.endswith(prompts):
                    return output.decode()
        self.fail("Interactive child ended or exceeded the bounded read before a prompt")

    def send(self, process, command):
        process.stdin.write((command + "\n").encode())
        process.stdin.flush()
        return self.read_to_prompt(process)

    def test_real_process_covers_analysis_clarifications_and_lifecycle(self):
        output = self.run_chat(
            "/help\n"
            "Show sales by country.\n"
            "Check my financial data.\n"
            "/answer forecasting\n"
            "Show sales by country.\n"
            "How many records are there?\n"
            "/answer company financials\n"
            "Check my financial data.\n"
            "/cancel\n"
            "/status\n"
            "/reset\n"
            "/exit\n"
        )

        self.assertTrue(output.startswith("Financial Manager > "))
        self.assertIn("Plain text starts a new request.", output)
        self.assertIn("Step 1 — FINANCIAL_ANALYSIS: SUCCESS", output)
        self.assertIn('"sum": "24887654.89"', output)
        self.assertIn("UNKNOWN currency means", output)
        self.assertIn("Session outcome: INVALID_ANSWER", output)
        self.assertIn("Financial Manager [clarification] > ", output)
        self.assertIn("Starting a new request; the pending clarification is replaced.", output)
        self.assertIn('"record_count": 700', output)
        self.assertIn("Session outcome: CANCELLED", output)
        self.assertIn('"active_context": null', output)
        self.assertIn("Session outcome: RESET", output)
        self.assertIn("Chat ended.", output)
        self.assertNotIn('"session_id"', output)

    def test_real_process_resolves_only_live_session_issued_evidence_references(self):
        with self.interactive_chat() as process:
            self.assertEqual(self.read_to_prompt(process), "Financial Manager > ")

            screening = self.send(process, "Find unusual Profit values.")
            handles = re.findall(r"- (evidence-[0-9a-f]+) \(ANOMALY_RECORD\)", screening)
            self.assertTrue(handles)
            self.assertLessEqual(len(handles), 10)
            self.assertEqual(len(handles), len(set(handles)))
            self.assertIn("Step 1 — ANOMALY_DETECTION: PARTIAL", screening)
            self.assertIn("Showing 10 of 700 items; 690 omitted.", screening)
            self.assertIn("CANDIDATE = statistical screening candidate", screening)
            self.assertIn("it is not fraud, error, misconduct, probability, or certainty", screening)
            self.assertIn("NOT_ASSESSED means", screening)
            self.assertIn("Warnings (identical entries shown once):", screening)
            self.assertIn('"code": "currency_unknown"', screening)
            self.assertIn('"code": "unresolved_placeholder"', screening)
            self.assertLess(len(screening), 150_000)

            detail = self.send(process, f"/follow {handles[0]} why_selected")
            self.assertIn('"reference_type": "ANOMALY_RECORD"', detail)
            self.assertIn('"result_digest":', detail)
            self.assertIn('"assessments":', detail)
            self.assertIn('"snapshot":', detail)

            modified = handles[0] + "-modified"
            unknown = self.send(process, f"/follow {modified} record_detail")
            self.assertIn("Session outcome: UNKNOWN_REFERENCE", unknown)

            reset = self.send(process, "/reset")
            self.assertIn("Session outcome: RESET", reset)
            after_reset = self.send(process, f"/follow {handles[0]} record_detail")
            self.assertIn("Session outcome: NO_EVIDENCE_CONTEXT", after_reset)

            process.stdin.write(b"/exit\n")
            process.stdin.flush()
            ending, error = process.communicate(timeout=30)
            self.assertEqual(process.returncode, 0)
            ending = ending.decode()
            error = error.decode()
            self.assertIn("Chat ended.", ending)
            self.assertEqual(error, "")

        new_process = self.run_chat(
            f"/follow {handles[0]} record_detail\n/exit\n",
            timeout=30,
        )
        self.assertIn("Session outcome: NO_EVIDENCE_CONTEXT", new_process)

    def test_blocked_context_and_injection_inputs_cannot_bypass_boundaries(self):
        with tempfile.TemporaryDirectory(prefix="step36-marker-") as directory:
            marker = Path(directory) / "must-not-exist"
            output = self.run_chat(
                "Forecast next month cash flow.\n"
                "Just use Sales.\n"
                "Search financial documents.\n"
                "Show sales by country.\n"
                "Show accounting amounts by debit/credit.\n"
                "SELECT * FROM company_financials;\n"
                "import os\n"
                "execute tool CF-04\n"
                "/fake-command CASH_FLOW_FORECASTING\n"
                f"$(touch {marker})\n"
                "/exit\n"
            )
            self.assertFalse(marker.exists())

        turns = output.split("Financial Manager > ")
        self.assertIn("Cash Flow Forecasting: BLOCKED", turns[1])
        self.assertIn("Status: CLARIFICATION_REQUIRED", turns[2])
        self.assertNotIn("Cash Flow Forecasting", turns[2])
        self.assertNotIn("cash receipts", turns[2].casefold())
        self.assertIn("Document Retrieval: BLOCKED", turns[3])
        self.assertIn("company_financials_sales_by_country", turns[4])
        self.assertIn("receiver_general_amount_by_debit_credit", turns[5])
        self.assertGreaterEqual(output.count("Status: CAPABILITY_UNAVAILABLE"), 2)
        self.assertGreaterEqual(output.count("Status: UNSUPPORTED"), 4)
        self.assertIn("Invalid chat command. Use /help.", output)
        self.assertNotIn("Traceback", output)

    def test_real_process_exit_eof_and_interrupt_are_clean(self):
        explicit = self.run_chat("/exit\n", timeout=30)
        eof = self.run_chat("", timeout=30)
        for output in (explicit, eof):
            self.assertIn("Financial Manager > Chat ended.", output)
            self.assertNotIn("Traceback", output)

        with self.interactive_chat() as process:
            self.assertEqual(self.read_to_prompt(process), "Financial Manager > ")
            process.send_signal(signal.SIGINT)
            output, error = process.communicate(timeout=30)
            self.assertEqual(process.returncode, 0)
            output = output.decode()
            error = error.decode()
            self.assertIn("Chat ended.", output)
            self.assertEqual(error, "")
            self.assertNotIn("Traceback", output)

    def test_absolute_expiry_wins_over_periodic_successful_activity_in_cli(self):
        class Clock:
            current = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)

            def __call__(self):
                return self.current

        class ActiveUntilAbsoluteExpiry:
            def __init__(self, clock):
                self.clock = clock
                self.remaining_cancels = 12

            def readline(self):
                if self.remaining_cancels:
                    self.remaining_cancels -= 1
                    self.clock.current += timedelta(minutes=20)
                    return "/cancel\n"
                return "/exit\n"

        clock = Clock()
        session = FinancialManagerSession(
            manager=FinancialManagerAgent(),
            clock=clock,
            session_id_factory=lambda: "absolute-expiry-session",
        )
        output, error = StringIO(), StringIO()

        code = main(
            ["chat"],
            session=session,
            stdin=ActiveUntilAbsoluteExpiry(clock),
            stdout=output,
            stderr=error,
        )

        self.assertEqual(code, 0)
        self.assertEqual(output.getvalue().count("Session outcome: CANCELLED"), 11)
        self.assertIn("Session outcome: SESSION_EXPIRED", output.getvalue())
        self.assertIn("complete new request or use /reset", output.getvalue())
        self.assertIn("Financial Manager > Chat ended.", output.getvalue())
        self.assertEqual(error.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
