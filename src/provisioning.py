"""Validate the local V1 environment and approved data without changing it."""

import argparse
import importlib
import json
from pathlib import Path
import shlex
import sqlite3
import sys
import unittest

from src.database.connection import connect
from src.database.loaders import APPROVAL_PATH, APPROVED_RUN_ID, read_approved_bundle
from src.database.validation import validate_database


SUPPORTED_PYTHON = (3, 14)
DEFAULT_DATABASE = Path("data/database/financial_manager.db")


def required_paths(project_root):
    """Return the approved inputs grouped by their provisioning role."""
    root = Path(project_root).resolve()
    approval = json.loads(APPROVAL_PATH.read_text(encoding="utf-8"))
    run_directory = Path("data/processed") / approval["run_id"]
    protected = sorted(approval["protected_inputs"])
    return {
        "raw_sources": [path for path in protected if path.startswith("data/raw/")],
        "processed_artifacts": sorted(
            str(run_directory / name) for name in approval["artifacts"]
        ),
        "pipeline_evidence": [path for path in protected if path.startswith("notebooks/")],
        "project_root": str(root),
    }


def _discover_tests(root):
    tests = root / "tests"
    if not tests.is_dir():
        return 0
    suite = unittest.defaultTestLoader.discover(str(tests))
    return suite.countTestCases()


def _environment_metadata(root):
    version_path = root / ".python-version"
    requirements_path = root / "requirements.txt"
    version = version_path.read_text(encoding="utf-8").strip()
    packages = [
        line.strip()
        for line in requirements_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    try:
        version_parts = tuple(int(part) for part in version.split("."))
    except ValueError:
        version_parts = ()
    minor_matches = version_parts[:2] == SUPPORTED_PYTHON
    return {
        "python_version_file": version,
        "python_minor_matches": minor_matches,
        "requirements_file": "requirements.txt",
        "third_party_packages": packages,
        "passed": minor_matches and not packages,
    }


def validate_environment(project_root, *, database_path=None):
    """Return a JSON-compatible report for the local, offline V1 setup."""
    root = Path(project_root).resolve()
    database = Path(database_path).resolve() if database_path else root / DEFAULT_DATABASE
    paths = required_paths(root)
    required = (paths["raw_sources"] + paths["processed_artifacts"]
                + paths["pipeline_evidence"])
    missing = [relative for relative in required if not (root / relative).is_file()]
    python_ok = sys.version_info[:2] == SUPPORTED_PYTHON
    errors = [f"Required provisioning file is missing: {path}" for path in missing]
    if not python_ok:
        errors.append(
            f"Python {SUPPORTED_PYTHON[0]}.{SUPPORTED_PYTHON[1]} is required; "
            f"running {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        )

    try:
        environment_metadata = _environment_metadata(root)
        if not environment_metadata["passed"]:
            errors.append("Environment metadata does not match the V1 runtime contract")
    except OSError as exc:
        environment_metadata = {
            "python_version_file": None,
            "python_minor_matches": False,
            "requirements_file": "requirements.txt",
            "third_party_packages": None,
            "passed": False,
        }
        errors.append(f"Environment metadata is missing: {exc.filename}")

    report = {
        "status": "FAIL",
        "python": {
            "required": ".".join(map(str, SUPPORTED_PYTHON)),
            "running": ".".join(map(str, sys.version_info[:3])),
            "passed": python_ok,
        },
        "dependencies": {
            "runtime": "Python standard library and repository source only",
            "passed": False,
        },
        "environment_metadata": environment_metadata,
        "data": {
            "approved_run_id": APPROVED_RUN_ID,
            "required": paths,
            "missing": missing,
            "approved_bundle": "BLOCKED" if missing else "NOT_CHECKED",
        },
        "database": {
            "path": str(database),
            "status": "BLOCKED" if missing else "NOT_CHECKED",
            "rebuild_command": (
                ".venv/bin/python -m src.database.initialize --database "
                + shlex.quote(str(database))
            ),
        },
        "cli": {"importable": False},
        "tests": {"discovered": 0, "passed": False},
        "network_required": False,
        "errors": errors,
    }

    try:
        importlib.import_module("src.cli.main")
        importlib.import_module("src.manager")
        report["cli"]["importable"] = True
        report["dependencies"]["passed"] = True
    except (ImportError, OSError) as exc:
        errors.append(f"Application imports failed: {exc}")

    try:
        discovered = _discover_tests(root)
        report["tests"] = {"discovered": discovered, "passed": discovered > 0}
        if discovered == 0:
            errors.append("No unittest tests were discovered")
    except (ImportError, OSError) as exc:
        errors.append(f"Unittest discovery failed: {exc}")

    if not missing:
        try:
            bundle = read_approved_bundle(root)
            report["data"]["approved_bundle"] = "VALID"
        except (OSError, ValueError) as exc:
            report["data"]["approved_bundle"] = "INVALID"
            report["database"]["status"] = "BLOCKED"
            errors.append(f"Approved data validation failed: {exc}")
        else:
            if not database.is_file():
                report["database"]["status"] = "READY_TO_BUILD"
            else:
                try:
                    with connect(database, readonly=True) as connection:
                        validate_database(connection, bundle)
                except (OSError, ValueError, sqlite3.Error) as exc:
                    report["database"]["status"] = "INVALID"
                    errors.append(f"Database validation failed: {exc}")
                else:
                    report["database"]["status"] = "VALID"

    checks = (
        report["python"]["passed"],
        report["environment_metadata"]["passed"],
        report["dependencies"]["passed"],
        report["data"]["approved_bundle"] == "VALID",
        report["database"]["status"] in {"VALID", "READY_TO_BUILD"},
        report["cli"]["importable"],
        report["tests"]["passed"],
    )
    report["status"] = "PASS" if all(checks) else "FAIL"
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path,
                        default=Path(__file__).resolve().parents[1])
    parser.add_argument("--database", type=Path)
    args = parser.parse_args(argv)
    report = validate_environment(args.project_root, database_path=args.database)
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
