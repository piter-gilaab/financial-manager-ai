"""Step 28 validation of the public CLI presentation contract."""

import json
from pathlib import Path
import subprocess
import sys
import unittest

from src.manager import FinancialManagerAgent


ROOT = Path(__file__).resolve().parents[1]
# Step 25's smallest problematic large response was about 708 KB. This generous
# bound catches a return to full evidence dumping without optimizing wording to a
# narrow byte target.
CONCISE_REGRESSION_BOUND = 500_000


class PresentationValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manager = FinancialManagerAgent()

    def cli(self, question, *options, exit_code=0):
        completed = subprocess.run(
            [sys.executable, "-B", "-m", "src.cli", "ask", question, *options],
            cwd=ROOT, capture_output=True, text=True, timeout=60, check=False,
        )
        self.assertEqual(completed.returncode, exit_code, completed.stderr)
        if exit_code == 0:
            self.assertEqual(completed.stderr, "")
        return completed

    def json_response(self, question):
        def reject_float(token):
            self.fail("Presentation JSON must not contain a floating-point token: " + token)

        output = self.cli(question, "--json").stdout
        return json.loads(output, parse_float=reject_float, parse_constant=reject_float)

    def test_representative_human_workflows_are_concise_and_understandable(self):
        scenarios = (
            ("Sales summary", "SUCCESS", ("Structured evidence:", "UNKNOWN currency means")),
            ("Sales by country", "SUCCESS", ('"groups":', '"country"')),
            ("Discount analysis", "PARTIAL", ("unresolved_placeholder", "Coverage and exclusions")),
            ("Screen profit", "PARTIAL", ("CANDIDATE = statistical screening", "NOT_ASSESSED means")),
            ("Forecast cash flow next month", "CAPABILITY_UNAVAILABLE", ("Cash Flow Forecasting: BLOCKED",)),
            ("What does invoice 123 say?", "CAPABILITY_UNAVAILABLE", ("Document Retrieval: BLOCKED",)),
            ("Check my financial data", "CLARIFICATION_REQUIRED", ("Clarification required:",)),
            ("What is the fraud probability?", "UNSUPPORTED", ("unverified_claim",)),
            ("Summarize sales and identify unusual sales records.", "SUCCESS",
             ("Step 1 — FINANCIAL_ANALYSIS", "Step 2 — ANOMALY_DETECTION")),
        )

        for question, status, markers in scenarios:
            with self.subTest(question=question):
                output = self.cli(question).stdout
                self.assertTrue(output.startswith("Status: " + status + "\n"))
                self.assertLess(len(output.encode()), CONCISE_REGRESSION_BOUND)
                for marker in markers:
                    self.assertIn(marker, output)
                self.assertNotIn("Traceback", output)
                self.assertNotIn(str(ROOT), output)

    def test_preview_order_and_omission_accounting_are_deterministic(self):
        question = "Screen profit"
        first = self.cli(question).stdout
        second = self.cli(question).stdout
        evidence = self.manager.ask(question)["results"][0]["response"]["delegated_result"]
        items = evidence["result"]["items"]

        self.assertEqual(first, second)
        self.assertIn("Showing 10 of 700 items; 690 omitted.", first)
        self.assertIn('"returned_item_count": 10', first)
        self.assertIn('"total_item_count": 700', first)
        self.assertIn('"omitted_item_count": 690', first)
        positions = [first.index(item["lineage"]["record_id"]) for item in items[:10]]
        self.assertEqual(positions, sorted(positions))
        self.assertNotIn(items[10]["lineage"]["record_id"], first)

    def test_json_is_authoritative_exact_and_unchanged_across_workflows(self):
        questions = (
            "Discount analysis",
            "Screen profit",
            "Summarize sales and identify unusual sales records.",
        )
        for question in questions:
            with self.subTest(question=question):
                self.assertEqual(self.json_response(question), self.manager.ask(question))

    def test_full_expands_evidence_and_mode_flags_remain_exclusive(self):
        question = "Screen profit"
        evidence = self.manager.ask(question)["results"][0]["response"]["delegated_result"]
        last_record_id = evidence["result"]["items"][-1]["lineage"]["record_id"]
        concise = self.cli(question).stdout
        full = self.cli(question, "--full").stdout

        self.assertLess(len(concise), len(full))
        self.assertNotIn(last_record_id, concise)
        self.assertIn(last_record_id, full)
        self.assertIn("Use --json for complete structured evidence.", concise)
        self.assertNotIn("Use --json for complete structured evidence.", full)

        invalid = self.cli(question, "--json", "--full", exit_code=2)
        self.assertEqual(invalid.stdout, "")
        self.assertIn("Invalid CLI syntax", invalid.stderr)

    def test_real_warnings_are_deduplicated_without_losing_distinct_entries(self):
        question = "Discount analysis"
        response = self.manager.ask(question)
        warnings = response["results"][0]["response"]["delegated_result"]["tool_result"]["quality"]["warnings"]
        output = self.cli(question).stdout
        warning_section = output.split("Warnings (identical entries shown once):", 1)[1].split("Terminology:", 1)[0]

        self.assertEqual(output.count("Warnings (identical entries shown once):"), 1)
        self.assertIn('"applies_to_steps": [', warning_section)
        for warning in warnings:
            self.assertIn(warning["code"], warning_section)
            self.assertEqual(warning_section.count(warning["message"]), 1)


if __name__ == "__main__":
    unittest.main()
