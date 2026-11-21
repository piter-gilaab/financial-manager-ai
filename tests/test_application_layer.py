"""Transport-neutral Phase 3 application seam tests."""

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import tempfile
import unittest

from src.application import (
    AnalysisApplication,
    AnalysisCommand,
    ConversationApplication,
    DatasetApplication,
    DatasetUpload,
    FinancialOperation,
    ResourceNotFound,
)
from src.manager import FinancialManagerAgent, FinancialManagerSession
from src.onboarding import OnboardingManager

from tests.onboarding_support import write_csv


FIXED_TIME = datetime(2026, 11, 21, 12, 0, tzinfo=timezone.utc)


class _AnalysisDelegate:
    def __init__(self, response):
        self.response = response
        self.requests = []

    def list_capabilities(self):
        return ()

    def execute_dataset_request(self, request):
        self.requests.append(request)
        return self.response


class ApplicationLayerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.root = self.base / "onboarding"

    def test_dataset_application_delegates_upload_and_lists_safe_projection(self):
        application = DatasetApplication(OnboardingManager(self.root, clock=lambda: FIXED_TIME))
        uploaded = application.upload(DatasetUpload(
            filename="sales.csv",
            content=b"Date,Sales\n2026-01-01,10.50\n",
            provenance_note="Synthetic application test",
        ))

        self.assertRegex(uploaded.dataset_id, r"^ds_[0-9a-f]{20}$")
        listed = application.list_datasets()
        self.assertEqual([item.dataset_id for item in listed], [uploaded.dataset_id])
        self.assertEqual(listed[0].lifecycle_state, "NEEDS_CONFIRMATION")
        self.assertNotIn(str(self.root), repr(listed[0]))
        self.assertEqual(application.profile(uploaded.dataset_id).row_count, 1)
        self.assertEqual(application.mappings(uploaded.dataset_id).dataset_id, uploaded.dataset_id)

    def test_analysis_application_preserves_authoritative_evidence_without_arithmetic(self):
        authoritative = {
            "manager_version": "1.1",
            "execution_status": "PARTIAL",
            "delegated_result": {
                "status": "PARTIAL",
                "result": {"sum": Decimal("0.1000000000000000001")},
                "currency": {"state": "CONFIRMED", "code": "USD"},
                "quality": {"coverage": {"included": 1}},
                "metadata": {"lineage": {"source": "sha256"}},
            },
            "limitations": ["bounded"],
            "warnings": [],
            "errors": [],
        }
        delegate = _AnalysisDelegate(authoritative)
        application = AnalysisApplication(delegate)

        result = application.execute(AnalysisCommand(
            dataset_id="ds_0123456789abcdef0123",
            operation=FinancialOperation.SALES_SUMMARY,
        ))

        self.assertIs(result.payload, authoritative)
        self.assertEqual(
            result.payload["delegated_result"]["result"]["sum"],
            Decimal("0.1000000000000000001"),
        )
        self.assertEqual(result.status, "PARTIAL")
        self.assertEqual(result.limitations, ("bounded",))
        self.assertEqual(delegate.requests[0].operation.value, "SALES_SUMMARY")

    def test_analysis_application_preserves_blocked_and_unsupported_results(self):
        for status in ("DATA_QUALITY_BLOCKER", "UNSUPPORTED"):
            with self.subTest(status=status):
                payload = {
                    "execution_status": status,
                    "delegated_result": None,
                    "limitations": [],
                    "warnings": [],
                    "errors": [{"code": status.lower()}],
                }
                result = AnalysisApplication(_AnalysisDelegate(payload)).execute(
                    AnalysisCommand(
                        dataset_id="ds_0123456789abcdef0123",
                        operation=FinancialOperation.PAYABLE_SUMMARY,
                    )
                )
                self.assertEqual(result.status, status)
                self.assertIs(result.payload, payload)

    def test_conversation_application_preserves_session_lifecycle_and_isolation(self):
        ids = iter(("session-a", "session-b", "session-c"))

        def session_factory():
            return FinancialManagerSession(
                manager=FinancialManagerAgent(onboarding_root=self.root),
                clock=lambda: FIXED_TIME,
                session_id_factory=lambda: next(ids),
            )

        application = ConversationApplication(session_factory=session_factory)
        first = application.create_session()
        second = application.create_session()
        self.assertNotEqual(first.session_id, second.session_id)
        self.assertEqual(application.status(first.session_id).status, "ACTIVE")

        reset = application.reset(first.session_id)
        self.assertEqual(reset.status, "RESET")
        self.assertEqual(reset.session.session_id, "session-c")
        self.assertEqual(application.status(second.session_id).session_id, "session-b")
        with self.assertRaises(ResourceNotFound):
            application.status(first.session_id)

        cancelled = application.cancel(second.session_id)
        self.assertEqual(cancelled.status, "CANCELLED")
        application.delete(second.session_id)
        with self.assertRaises(ResourceNotFound):
            application.status(second.session_id)


if __name__ == "__main__":
    unittest.main()
