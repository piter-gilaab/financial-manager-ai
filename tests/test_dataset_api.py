"""Dataset/onboarding HTTP behavior through the existing safe ingestion path."""

from io import BytesIO
from pathlib import Path
import tempfile
import unittest
from zipfile import ZIP_DEFLATED, ZipFile

from src.api import create_app

from tests.api_support import AsgiClient
from tests.onboarding_support import write_xlsx


class DatasetApiTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.root = self.base / "onboarding"
        self.client = AsgiClient(create_app(onboarding_root=self.root))

    def upload(self, name="sales.csv", content=b"Date,Sales\n2026-01-01,10.50\n"):
        return self.client.post(
            "/api/v1/onboarding",
            files={"file": (name, content, "application/octet-stream")},
            data={"provenance_note": "Synthetic API test"},
        )

    def test_csv_upload_list_detail_profile_and_mappings_are_safe(self):
        uploaded = self.upload()
        self.assertEqual(uploaded.status_code, 201)
        payload = uploaded.json()["data"]
        dataset_id = payload["dataset"]["dataset_id"]
        self.assertEqual(payload["profile"]["row_count"], 1)
        self.assertEqual(payload["mappings"]["status"], "NEEDS_CONFIRMATION")

        listed = self.client.get("/api/v1/datasets")
        self.assertEqual([item["dataset_id"] for item in listed.json()["data"]], [dataset_id])
        detail = self.client.get(f"/api/v1/datasets/{dataset_id}")
        profile = self.client.get(f"/api/v1/datasets/{dataset_id}/profile")
        mappings = self.client.get(f"/api/v1/datasets/{dataset_id}/mappings")
        self.assertEqual(detail.json()["data"]["dataset_id"], dataset_id)
        self.assertEqual(profile.json()["data"]["columns"][1]["name"], "Sales")
        self.assertLessEqual(len(profile.json()["data"]["columns"][1]["examples"]), 5)
        self.assertEqual(mappings.json()["data"]["dataset_id"], dataset_id)
        for response in (uploaded, listed, detail, profile, mappings):
            self.assertNotIn(str(self.root), response.text)

    def test_explicit_semantic_domain_qualifier_and_readiness_flow(self):
        uploaded = self.upload(
            "payables.csv",
            b"Amount,Due,Status\n100.00,2026-10-01,open\n",
        )
        dataset_id = uploaded.json()["data"]["dataset"]["dataset_id"]
        decisions = (
            {"column": "Amount", "decision": "CONFIRM", "role": "AMOUNT",
             "evidence": "owner"},
            {"column": "Due", "decision": "CORRECT", "role": "DUE_DATE",
             "evidence": "owner", "date_format": "YYYY-MM-DD"},
            {"column": "Status", "decision": "CONFIRM", "role": "STATUS",
             "evidence": "owner", "value_mapping": {"open": "OPEN"}},
        )
        for decision in decisions:
            response = self.client.post(
                f"/api/v1/datasets/{dataset_id}/mappings/decisions", json=decision,
            )
            self.assertEqual(response.status_code, 200, response.text)

        qualifier = self.client.post(
            f"/api/v1/datasets/{dataset_id}/qualifiers",
            json={
                "evidence": "owner",
                "amount_basis": "OUTSTANDING_BALANCE",
                "dataset_reference_date": "2026-11-01",
            },
        )
        self.assertEqual(qualifier.status_code, 200, qualifier.text)
        domain = self.client.post(
            f"/api/v1/datasets/{dataset_id}/domain-confirmation",
            json={"domain": "PAYABLE", "evidence": "owner"},
        )
        self.assertEqual(domain.status_code, 200, domain.text)

        mappings = self.client.get(f"/api/v1/datasets/{dataset_id}/mappings")
        self.assertEqual(mappings.status_code, 200, mappings.text)
        self.assertEqual(
            [item["decision"] for item in mappings.json()["data"]["decisions"][-2:]],
            ["CONFIRM_QUALIFIERS", "APPROVE_DOMAIN"],
        )

        readiness = self.client.get(f"/api/v1/datasets/{dataset_id}/readiness")
        self.assertEqual(readiness.status_code, 200)
        analysis = next(item for item in readiness.json()["data"]["capabilities"]
                        if item["identifier"] == "FINANCIAL_ANALYSIS")
        self.assertEqual(analysis["state"], "AVAILABLE_WITH_LIMITATIONS")
        self.assertEqual(len(analysis["operations"]), 6)
        executed = self.client.post("/api/v1/analysis", json={
            "dataset_id": dataset_id, "operation": "PAYABLE_AGING",
            "parameters": {"as_of_date": "2026-11-01"},
        })
        self.assertEqual(executed.status_code, 200, executed.text)
        self.assertEqual(executed.json()["evidence"]["delegated_result"]["query_name"],
                         "PAYABLE_AGING")

    def test_xlsx_upload_uses_existing_formula_macro_external_link_protections(self):
        valid = write_xlsx(
            self.base / "valid.xlsx",
            sheets={"Data": [["Date", "Sales"], ["2026-01-01", "10"]]},
        )
        response = self.upload("valid.xlsx", valid.read_bytes())
        self.assertEqual(response.status_code, 201, response.text)

        for flag, code in (("formula", "formula_not_allowed"),
                           ("macro", "macro_not_allowed"),
                           ("external_link", "external_link_not_allowed")):
            path = write_xlsx(
                self.base / f"{flag}.xlsx",
                sheets={"Data": [["Date", "Sales"], ["2026-01-01", "10"]]},
                **{flag: True},
            )
            rejected = self.upload(f"{flag}.xlsx", path.read_bytes())
            self.assertEqual(rejected.status_code, 400)
            self.assertEqual(rejected.json()["errors"][0]["code"], code)
            self.assertNotIn(str(self.base), rejected.text)

    def test_multi_sheet_xlsx_requires_explicit_safe_sheet_selection(self):
        workbook = write_xlsx(
            self.base / "multi.xlsx",
            sheets={
                "January": [["Date", "Sales"], ["2026-01-01", "10"]],
                "February": [["Date", "Sales"], ["2026-02-01", "20"]],
            },
        )
        required = self.upload("multi.xlsx", workbook.read_bytes())
        self.assertEqual(required.status_code, 409, required.text)
        self.assertEqual(required.json()["status"], "CLARIFICATION_REQUIRED")
        self.assertEqual(required.json()["data"], {
            "field": "sheet", "choices": ["January", "February"],
        })

        selected = self.client.post(
            "/api/v1/onboarding",
            files={"file": ("multi.xlsx", workbook.read_bytes(), "application/octet-stream")},
            data={"sheet": "February", "provenance_note": "Synthetic API test"},
        )
        self.assertEqual(selected.status_code, 201, selected.text)
        self.assertEqual(selected.json()["data"]["profile"]["row_count"], 1)

    def test_unsafe_uploads_fail_without_path_or_content_disclosure(self):
        cases = (
            ("../escape.csv", b"A\n1\n", "unsupported_format"),
            ("fake.csv", b"PK\x03\x04not-a-csv", "format_mismatch"),
            ("bad.csv", b'"unterminated\n', "malformed_csv"),
            ("bad.xlsx", b"not-a-zip", "malformed_xlsx"),
            ("unsupported.txt", b"A\n1\n", "unsupported_format"),
        )
        for name, content, code in cases:
            with self.subTest(name=name):
                response = self.upload(name, content)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["errors"][0]["code"], code)
                self.assertNotIn(content.decode("latin-1"), response.text)

        oversized = self.upload("large.csv", b"A\n" + b"1" * (10 * 1024 * 1024 + 1))
        self.assertIn(oversized.status_code, {400, 413})
        self.assertIn(oversized.json()["errors"][0]["code"], {"file_too_large", "request_too_large"})

    def test_zip_traversal_and_duplicate_names_are_rejected_by_existing_ingestion(self):
        archive = BytesIO()
        with ZipFile(archive, "w", ZIP_DEFLATED) as workbook:
            workbook.writestr("../escape", "x")
            workbook.writestr("xl/workbook.xml", "<workbook/>")
        traversal = self.upload("traversal.xlsx", archive.getvalue())
        self.assertEqual(traversal.status_code, 400)
        self.assertEqual(traversal.json()["errors"][0]["code"], "unsafe_archive_path")

        first = self.upload("same.csv", b"A\n1\n")
        second = self.upload("same.csv", b"A\n2\n")
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertNotEqual(
            first.json()["data"]["dataset"]["dataset_id"],
            second.json()["data"]["dataset"]["dataset_id"],
        )

    def test_no_filesystem_path_endpoint_and_exact_dataset_ids_only(self):
        response = self.client.post("/api/v1/onboarding/path", json={"path": "/etc/passwd"})
        self.assertEqual(response.status_code, 404)
        malicious = self.client.get("/api/v1/datasets/..%2F..%2Fetc%2Fpasswd")
        self.assertIn(malicious.status_code, {404, 422})
        self.assertNotIn("/etc/passwd", malicious.text)


if __name__ == "__main__":
    unittest.main()
