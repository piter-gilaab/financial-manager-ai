"""FastAPI foundation, schema and safe serialization tests."""

from decimal import Decimal
from pathlib import Path
import asyncio
import tempfile
import unittest

import httpx

from src.api import create_app
from src.api.serialization import to_json_safe


class _AsgiClient:
    def __init__(self, app):
        self.app = app

    def request(self, method, path, **kwargs):
        async def send():
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=self.app, raise_app_exceptions=False),
                base_url="http://test",
            ) as client:
                return await asyncio.wait_for(client.request(method, path, **kwargs), timeout=2)
        return asyncio.run(send())

    def get(self, path, **kwargs):
        return self.request("GET", path, **kwargs)

    def post(self, path, **kwargs):
        return self.request("POST", path, **kwargs)

    def options(self, path, **kwargs):
        return self.request("OPTIONS", path, **kwargs)


class ApiFoundationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "onboarding"
        self.app = create_app(onboarding_root=self.root)
        self.client = _AsgiClient(self.app)

    def test_factory_has_versioned_health_and_no_hidden_singleton_state(self):
        other = create_app(onboarding_root=Path(self.temporary.name) / "other")
        self.assertIsNot(self.app.state.applications, other.state.applications)

        response = self.client.get("/api/v1/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "api_version": "1",
            "status": "SUCCESS",
            "data": {"status": "ok", "api_version": "1", "product_version": "V2"},
            "limitations": [],
            "errors": [],
        })
        self.assertNotIn(str(self.root), response.text)

    def test_capabilities_expose_exact_frozen_catalogs_without_execution(self):
        response = self.client.get("/api/v1/capabilities")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(len(data["financial_operations"]["SALES_RECORD"]), 9)
        self.assertEqual(len(data["financial_operations"]["PAYABLE"]), 6)
        self.assertEqual(len(data["financial_operations"]["RECEIVABLE"]), 6)
        self.assertEqual(len(data["financial_operations"]["CASH_TRANSACTION"]), 6)
        self.assertEqual(data["anomaly_operations"], [
            "SALES_ANOMALY_SCREEN", "PROFIT_ANOMALY_SCREEN",
        ])
        blocked = {item["identifier"]: item["status"] for item in data["capabilities"]}
        self.assertEqual(blocked["CASH_FLOW_FORECASTING"], "BLOCKED")
        self.assertEqual(blocked["DOCUMENT_RETRIEVAL"], "BLOCKED")

    def test_decimal_serializer_is_exact_and_rejects_non_finite_values(self):
        values = [
            Decimal("0.1"), Decimal("0.2"), Decimal("0.3"),
            Decimal("1234567890.12345678901234567890"), Decimal("-1.2300"), Decimal("0"),
        ]
        self.assertEqual(to_json_safe(values), [
            "0.1", "0.2", "0.3", "1234567890.12345678901234567890", "-1.2300", "0",
        ])
        for value in (Decimal("NaN"), Decimal("Infinity"), float("inf"), float("nan")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                to_json_safe(value)

    def test_transport_validation_and_unexpected_errors_use_safe_envelopes(self):
        malformed = self.client.post(
            "/api/v1/analysis",
            content="{broken",
            headers={"content-type": "application/json"},
        )
        self.assertEqual(malformed.status_code, 422)
        self.assertEqual(malformed.json()["status"], "INVALID_REQUEST")
        self.assertNotIn("Traceback", malformed.text)
        self.assertNotIn(str(self.root), malformed.text)

        injected = self.client.post("/api/v1/analysis", json={
            "dataset_id": "ds_0123456789abcdef0123",
            "operation": "SALES_SUMMARY; DROP TABLE records",
            "parameters": {},
        })
        self.assertEqual(injected.status_code, 422)
        self.assertEqual(injected.json()["status"], "INVALID_REQUEST")

    def test_openapi_is_valid_closed_and_has_no_deferred_or_frontend_routes(self):
        response = self.client.get("/openapi.json")
        self.assertEqual(response.status_code, 200)
        schema = response.json()
        self.assertEqual(schema["openapi"].split(".")[0], "3")
        operation_schema = schema["components"]["schemas"]["FinancialOperation"]
        self.assertEqual(len(operation_schema["enum"]), 27)
        self.assertIn("ErrorEnvelope", schema["components"]["schemas"])
        analysis_responses = schema["paths"]["/api/v1/analysis"]["post"]["responses"]
        for status_code in ("400", "404", "409", "422", "500"):
            reference = analysis_responses[status_code]["content"]["application/json"]["schema"]
            self.assertEqual(reference["$ref"], "#/components/schemas/ErrorEnvelope")
        components = schema["components"]["schemas"]
        self.assertEqual(
            components["DatasetProfileResponse"]["properties"]["columns"]["items"]["$ref"],
            "#/components/schemas/ColumnProfileResponse",
        )
        self.assertEqual(
            components["ReadinessResponse"]["properties"]["capabilities"]["items"]["$ref"],
            "#/components/schemas/CapabilityReadinessResponse",
        )
        self.assertEqual(
            components["SemanticMappingResponse"]["properties"]["proposals"]["items"]["$ref"],
            "#/components/schemas/SemanticProposalResponse",
        )
        paths = set(schema["paths"])
        self.assertFalse(any("forecast" in path or "rag" in path or "documents" in path
                             for path in paths))

    def test_cors_is_explicit_and_wildcards_are_rejected(self):
        configured = create_app(
            onboarding_root=self.root,
            cors_origins=("http://127.0.0.1:3000",),
        )
        response = _AsgiClient(configured).options(
            "/api/v1/health",
            headers={
                "Origin": "http://127.0.0.1:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        self.assertEqual(response.headers["access-control-allow-origin"],
                         "http://127.0.0.1:3000")
        with self.assertRaises(ValueError):
            create_app(onboarding_root=self.root, cors_origins=("*",))

    def test_programming_key_error_is_a_safe_500_not_a_false_404(self):
        class BrokenAnalysis:
            def capabilities(self, dataset_id=None):
                raise KeyError("private implementation key")

        broken = create_app(
            onboarding_root=self.root,
            analysis_application=BrokenAnalysis(),
        )
        response = _AsgiClient(broken).get("/api/v1/capabilities")
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["errors"][0]["code"], "internal_error")
        self.assertNotIn("private implementation key", response.text)


if __name__ == "__main__":
    unittest.main()
