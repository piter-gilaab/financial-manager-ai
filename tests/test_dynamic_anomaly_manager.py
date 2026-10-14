import tempfile
import unittest
import json
from pathlib import Path

from src.anomaly.dynamic import DynamicAnomalyAdapter, DynamicAnomalyRequest
from src.manager import FinancialManagerAgent

from tests.execution_support import onboard_sales


def anomaly_csv(sales, profits):
    rows = ["when,revenue value,net outcome"]
    rows.extend(
        f"2026-01-01,{sale},{profit}"
        for sale, profit in zip(sales, profits, strict=True)
    )
    return "\n".join(rows) + "\n"


def operation_states(response):
    return {
        item["identifier"]: item
        for item in response["dataset_capability"]["operations"]
    }


class DynamicAnomalyManagerTests(unittest.TestCase):
    def test_manager_executes_sales_and_preserves_authoritative_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                anomaly_csv(list(range(30)) + [100], list(range(30)) + [-100]),
                mappings={
                    "when": "TRANSACTION_DATE",
                    "revenue value": "SALES",
                    "net outcome": "PROFIT",
                },
            )
            request = DynamicAnomalyRequest(
                state["dataset_id"], "SALES_ANOMALY_SCREEN",
            )
            expected = DynamicAnomalyAdapter(root / "onboarding").execute(request)

            response = FinancialManagerAgent(
                onboarding_root=root / "onboarding",
            ).execute_dataset_anomaly_request(request)

        self.assertEqual(response["manager_version"], "1.1")
        self.assertEqual(response["capability"], "ANOMALY_DETECTION")
        self.assertEqual(response["execution_status"], "SUCCESS")
        self.assertEqual(response["delegated_result"], expected)
        operations = {
            item["identifier"]: item
            for item in response["dataset_capability"]["operations"]
        }
        self.assertEqual(operations["SALES_ANOMALY_SCREEN"]["state"], "SUPPORTED")
        self.assertEqual(response["delegated_result"]["result"]["counts"]["candidate"], 1)

    def test_manager_executes_supplied_profit_without_derivation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                anomaly_csv([1] * 31, [-100] + list(range(-15, 15))),
                mappings={
                    "when": "TRANSACTION_DATE",
                    "revenue value": "SALES",
                    "net outcome": "PROFIT",
                },
            )
            request = DynamicAnomalyRequest(
                state["dataset_id"], "PROFIT_ANOMALY_SCREEN",
            )

            response = FinancialManagerAgent(
                onboarding_root=root / "onboarding",
            ).execute_dataset_anomaly_request(request)

        evidence = response["delegated_result"]["result"]
        self.assertEqual(response["execution_status"], "SUCCESS")
        self.assertEqual(evidence["measure"], "PROFIT")
        self.assertEqual(evidence["assessments"][0]["observed_value"], "-100")
        self.assertEqual(evidence["assessments"][0]["status"], "CANDIDATE")

    def test_manager_blocks_operation_from_current_readiness_without_screening_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                anomaly_csv(range(30), [""] * 30),
                mappings={
                    "when": "TRANSACTION_DATE",
                    "revenue value": "SALES",
                },
            )

            response = FinancialManagerAgent(
                onboarding_root=root / "onboarding",
            ).execute_dataset_anomaly_request(DynamicAnomalyRequest(
                state["dataset_id"], "PROFIT_ANOMALY_SCREEN",
            ))

        self.assertEqual(response["execution_status"], "DATA_QUALITY_BLOCKER")
        self.assertIsNone(response["delegated_result"])
        self.assertEqual(response["errors"][0]["code"], "missing_confirmed_profit")
        operations = {
            item["identifier"]: item
            for item in response["dataset_capability"]["operations"]
        }
        self.assertEqual(operations["SALES_ANOMALY_SCREEN"]["state"], "SUPPORTED")
        self.assertEqual(operations["PROFIT_ANOMALY_SCREEN"]["state"], "BLOCKED")

    def test_manager_enforces_sample_iqr_and_arithmetic_readiness(self):
        cases = (
            (list(range(29)), "insufficient_numeric_records"),
            ([1] * 30, "zero_iqr"),
            (list(range(29)) + ["9" * 61], "exact_arithmetic_limit"),
        )
        for values, expected_code in cases:
            with self.subTest(expected_code=expected_code), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                _, state = onboard_sales(
                    root,
                    anomaly_csv(values, [1] * len(values)),
                    mappings={
                        "when": "TRANSACTION_DATE",
                        "revenue value": "SALES",
                    },
                )

                response = FinancialManagerAgent(
                    onboarding_root=root / "onboarding",
                ).execute_dataset_anomaly_request(DynamicAnomalyRequest(
                    state["dataset_id"], "SALES_ANOMALY_SCREEN",
                ))

                self.assertEqual(response["execution_status"], "DATA_QUALITY_BLOCKER")
                self.assertEqual(response["errors"][0]["code"], expected_code)
                self.assertIsNone(response["delegated_result"])

    def test_manager_preserves_unknown_and_confirmed_currency_and_blocks_multiple(self):
        cases = (
            (None, None, "UNKNOWN", "SUCCESS"),
            (["USD"] * 31, {"USD": "USD"}, "CONFIRMED", "SUCCESS"),
            (
                ["USD" if index % 2 else "BRL" for index in range(31)],
                {"USD": "USD", "BRL": "BRL"},
                "CONFIRMED_MULTIPLE",
                "DATA_QUALITY_BLOCKER",
            ),
        )
        for currencies, currency_values, expected_currency, expected_status in cases:
            with self.subTest(currency=expected_currency), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                rows = ["when,revenue,currency"] if currencies else ["when,revenue"]
                for index, sale in enumerate(list(range(30)) + [100]):
                    row = ["2026-01-01", str(sale)]
                    if currencies:
                        row.append(currencies[index])
                    rows.append(",".join(row))
                mappings = {"when": "TRANSACTION_DATE", "revenue": "SALES"}
                if currencies:
                    mappings["currency"] = "CURRENCY"
                _, state = onboard_sales(
                    root, "\n".join(rows) + "\n", mappings=mappings,
                    currency_values=currency_values,
                )

                response = FinancialManagerAgent(
                    onboarding_root=root / "onboarding",
                ).execute_dataset_anomaly_request(DynamicAnomalyRequest(
                    state["dataset_id"], "SALES_ANOMALY_SCREEN",
                ))

                self.assertEqual(response["execution_status"], expected_status)
                self.assertEqual(response["dataset_capability"]["currency"]["state"], expected_currency)
                if expected_status == "SUCCESS":
                    evidence_currency = response["delegated_result"]["currency"]
                    self.assertEqual(evidence_currency["status"], expected_currency)
                    self.assertFalse(evidence_currency["conversion_applied"])
                else:
                    self.assertEqual(response["errors"][0]["code"], "incompatible_currency")
                    self.assertIsNone(response["delegated_result"])

    def test_manager_rejects_malformed_targets_and_malicious_operations(self):
        protocol_calls = []

        class ExecutableOperation:
            def __hash__(self):
                protocol_calls.append("executed")
                return 0

        class ExecutableString(str):
            def __hash__(self):
                protocol_calls.append("string_executed")
                return super().__hash__()

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                anomaly_csv(range(30), range(30)),
                mappings={
                    "when": "TRANSACTION_DATE",
                    "revenue value": "SALES",
                    "net outcome": "PROFIT",
                },
            )
            manager = FinancialManagerAgent(onboarding_root=root / "onboarding")

            malformed = manager.execute_dataset_anomaly_request(object())
            traversal = manager.execute_dataset_anomaly_request(DynamicAnomalyRequest(
                "../../etc/passwd", "SALES_ANOMALY_SCREEN",
            ))
            unknown = manager.execute_dataset_anomaly_request(DynamicAnomalyRequest(
                "ds_00000000000000000000", "SALES_ANOMALY_SCREEN",
            ))
            malicious = manager.execute_dataset_anomaly_request(DynamicAnomalyRequest(
                state["dataset_id"], "__import__('os').system('rm -rf /')",
            ))
            executable = manager.execute_dataset_anomaly_request(DynamicAnomalyRequest(
                state["dataset_id"], ExecutableOperation(),
            ))
            executable_string = manager.execute_dataset_anomaly_request(DynamicAnomalyRequest(
                state["dataset_id"], ExecutableString("SALES_ANOMALY_SCREEN"),
            ))

        self.assertEqual(malformed["execution_status"], "INVALID_REQUEST")
        self.assertEqual(traversal["errors"][0]["code"], "invalid_dataset_id")
        self.assertEqual(unknown["errors"][0]["code"], "dataset_not_found")
        self.assertEqual(malicious["execution_status"], "UNSUPPORTED")
        self.assertEqual(malicious["errors"][0]["code"], "unsupported_operation")
        self.assertEqual(executable["execution_status"], "UNSUPPORTED")
        self.assertEqual(executable_string["execution_status"], "UNSUPPORTED")
        self.assertEqual(protocol_calls, [])
        for response in (
            malformed, traversal, unknown, malicious, executable, executable_string,
        ):
            self.assertNotIn(str(root), json.dumps(response))

    def test_source_change_revokes_manager_execution_and_exact_restoration_recovers(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                anomaly_csv(list(range(30)) + [100], list(range(31))),
                mappings={
                    "when": "TRANSACTION_DATE",
                    "revenue value": "SALES",
                    "net outcome": "PROFIT",
                },
            )
            source = (
                root / "onboarding" / "artifacts" / state["dataset_id"]
                / "source" / "source.csv"
            )
            original = source.read_bytes()
            source.write_text(
                anomaly_csv(list(range(30)) + [999], list(range(31))),
                encoding="utf-8",
            )
            manager = FinancialManagerAgent(onboarding_root=root / "onboarding")
            revoked = manager.execute_dataset_anomaly_request(DynamicAnomalyRequest(
                state["dataset_id"], "SALES_ANOMALY_SCREEN",
            ))
            source.write_bytes(original)
            recovered = manager.execute_dataset_anomaly_request(DynamicAnomalyRequest(
                state["dataset_id"], "SALES_ANOMALY_SCREEN",
            ))

        self.assertEqual(revoked["execution_status"], "DATA_QUALITY_BLOCKER")
        self.assertIsNone(revoked["delegated_result"])
        self.assertEqual(recovered["execution_status"], "SUCCESS")

    def test_adapter_reauthenticates_if_source_changes_after_readiness(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                anomaly_csv(list(range(30)) + [100], list(range(31))),
                mappings={
                    "when": "TRANSACTION_DATE",
                    "revenue value": "SALES",
                    "net outcome": "PROFIT",
                },
            )
            source = (
                root / "onboarding" / "artifacts" / state["dataset_id"]
                / "source" / "source.csv"
            )

            class SourceChangingAdapter(DynamicAnomalyAdapter):
                def execute(self, request):
                    source.write_text(
                        anomaly_csv(list(range(30)) + [999], list(range(31))),
                        encoding="utf-8",
                    )
                    return super().execute(request)

            response = FinancialManagerAgent(
                onboarding_root=root / "onboarding",
                dynamic_anomaly=SourceChangingAdapter(root / "onboarding"),
            ).execute_dataset_anomaly_request(DynamicAnomalyRequest(
                state["dataset_id"], "SALES_ANOMALY_SCREEN",
            ))

        self.assertEqual(response["execution_status"], "DATA_QUALITY_BLOCKER")
        self.assertEqual(response["delegated_result"]["errors"][0]["code"], "invalid_registry")
        self.assertIsNone(response["delegated_result"]["result"])

    def test_candidate_references_are_bounded_candidate_only_and_deterministic(self):
        values = list(range(100)) + [10000 + index for index in range(25)]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                anomaly_csv(values, values),
                mappings={
                    "when": "TRANSACTION_DATE",
                    "revenue value": "SALES",
                    "net outcome": "PROFIT",
                },
            )
            manager = FinancialManagerAgent(onboarding_root=root / "onboarding")
            request = DynamicAnomalyRequest(state["dataset_id"], "SALES_ANOMALY_SCREEN")
            first = manager.execute_dataset_anomaly_request(request)
            second = manager.execute_dataset_anomaly_request(request)

        evidence = first["delegated_result"]["result"]
        references = evidence["candidate_references"]
        candidate_ids = {
            item["canonical_record_id"]
            for item in evidence["assessments"] if item["status"] == "CANDIDATE"
        }
        self.assertLessEqual(len(references), 20)
        self.assertTrue(references)
        self.assertTrue(all(item["dataset_id"] == state["dataset_id"] for item in references))
        self.assertTrue(all(item["canonical_record_id"] in candidate_ids for item in references))
        self.assertEqual(
            references,
            second["delegated_result"]["result"]["candidate_references"],
        )

    def test_manager_presentation_is_statistical_and_does_not_reinterpret_candidates(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                anomaly_csv(list(range(30)) + [100], list(range(31))),
                mappings={
                    "when": "TRANSACTION_DATE",
                    "revenue value": "SALES",
                    "net outcome": "PROFIT",
                },
            )
            response = FinancialManagerAgent(
                onboarding_root=root / "onboarding",
            ).execute_dataset_anomaly_request(DynamicAnomalyRequest(
                state["dataset_id"], "SALES_ANOMALY_SCREEN",
            ))

        self.assertEqual(
            response["summary"],
            "1 record met the statistical screening rule. This record is a candidate "
            "for review under the Tukey-IQR policy.",
        )
        for prohibited in (
            "suspicious transaction", "probably fraudulent", "erroneous sale",
            "likely wrongdoing",
        ):
            self.assertNotIn(prohibited, response["summary"].casefold())

    def test_manager_only_refusals_do_not_claim_adapter_delegation(self):
        response = FinancialManagerAgent().execute_dataset_anomaly_request(object())

        self.assertEqual(response["execution_status"], "INVALID_REQUEST")
        self.assertIsNone(response["delegated_status"])
        self.assertIsNone(response["delegated_result"])


if __name__ == "__main__":
    unittest.main()
