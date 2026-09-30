"""Step 23 environment and data provisioning behavior."""

from hashlib import sha256
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from src.provisioning import required_paths, validate_environment


ROOT = Path(__file__).resolve().parents[1]


class ProvisioningTests(unittest.TestCase):
    def test_required_paths_identify_approved_inputs_and_derivatives(self):
        paths = required_paths(ROOT)

        self.assertEqual(paths["raw_sources"], [
            "data/raw/Company Financials Dataset/Financials.csv",
            "data/raw/Receiver General Accounting Transactions/tcrg-rgat.csv",
        ])
        self.assertEqual(paths["processed_artifacts"], [
            "data/processed/20260928T190320706702Z_0a18cf5b/cleaning_manifest.json",
            "data/processed/20260928T190320706702Z_0a18cf5b/cleaning_review_flags.csv",
            "data/processed/20260928T190320706702Z_0a18cf5b/cleaning_validation_report.json",
            "data/processed/20260928T190320706702Z_0a18cf5b/company_financials_standardized.csv",
            "data/processed/20260928T190320706702Z_0a18cf5b/receiver_general_standardized.csv",
        ])
        self.assertEqual(len(paths["pipeline_evidence"]), 5)

    def test_missing_required_data_fails_with_each_relative_path(self):
        with tempfile.TemporaryDirectory() as directory:
            report = validate_environment(Path(directory))

        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["data"]["approved_bundle"], "BLOCKED")
        self.assertEqual(report["database"]["status"], "BLOCKED")
        self.assertIn(
            "data/raw/Company Financials Dataset/Financials.csv",
            report["data"]["missing"],
        )
        self.assertIn(
            "data/processed/20260928T190320706702Z_0a18cf5b/cleaning_manifest.json",
            report["data"]["missing"],
        )
        self.assertTrue(any("Required provisioning file is missing" in error
                            for error in report["errors"]))

    def test_environment_metadata_matches_validator_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            report = validate_environment(
                ROOT, database_path=Path(directory) / "rebuilt.db"
            )

        self.assertEqual((ROOT / ".python-version").read_text(encoding="utf-8"),
                         "3.14.7\n")
        requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
        install_lines = [line for line in requirements.splitlines()
                         if line.strip() and not line.lstrip().startswith("#")]
        self.assertEqual(install_lines, [])
        self.assertEqual(report["environment_metadata"], {
            "python_version_file": "3.14.7",
            "python_minor_matches": True,
            "requirements_file": "requirements.txt",
            "third_party_packages": [],
            "passed": True,
        })

    def test_validation_is_offline_read_only_and_reports_rebuild_readiness(self):
        raw_paths = [ROOT / path for path in required_paths(ROOT)["raw_sources"]]
        before = {path: sha256(path.read_bytes()).hexdigest() for path in raw_paths}

        with tempfile.TemporaryDirectory() as directory:
            absent_database = Path(directory) / "rebuilt.db"
            with patch.object(socket, "socket", side_effect=AssertionError("network attempted")):
                report = validate_environment(ROOT, database_path=absent_database)

        after = {path: sha256(path.read_bytes()).hexdigest() for path in raw_paths}
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["data"]["approved_bundle"], "VALID")
        self.assertEqual(report["database"]["status"], "READY_TO_BUILD")
        self.assertEqual(report["database"]["rebuild_command"],
                         ".venv/bin/python -m src.database.initialize --database "
                         + str(absent_database.resolve()))
        self.assertTrue(report["cli"]["importable"])
        self.assertGreaterEqual(report["tests"]["discovered"], 294)
        self.assertFalse(report["network_required"])
        self.assertEqual(after, before)

    def test_invalid_database_does_not_misreport_approved_data(self):
        with tempfile.TemporaryDirectory() as directory:
            invalid_database = Path(directory) / "invalid.db"
            invalid_database.write_bytes(b"not a sqlite database")
            report = validate_environment(ROOT, database_path=invalid_database)

        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["data"]["approved_bundle"], "VALID")
        self.assertEqual(report["database"]["status"], "INVALID")
        self.assertTrue(any("Database validation failed" in error
                            for error in report["errors"]))

    def test_test_discovery_rejects_import_failures(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tests = root / "tests"
            tests.mkdir()
            (tests / "test_broken_step24.py").write_text(
                "import module_that_does_not_exist_for_step24\n",
                encoding="utf-8",
            )

            report = validate_environment(root)

        self.assertEqual(report["tests"]["discovered"], 1)
        self.assertFalse(report["tests"]["passed"])
        self.assertTrue(any("Unittest discovery failed" in error
                            for error in report["errors"]))


if __name__ == "__main__":
    unittest.main()
