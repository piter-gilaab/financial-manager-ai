import json
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from src.anomaly.dynamic import DynamicAnomalyRequest
from src.cli.dataset import render_dataset
from src.cli.main import main
from src.manager import FinancialManagerAgent
from src.onboarding import OnboardingManager

from tests.execution_support import onboard_sales
from tests.onboarding_support import write_csv


def anomaly_capability(report):
    return next(
        item for item in report["capabilities"]
        if item["identifier"] == "ANOMALY_DETECTION"
    )


def operation_states(report):
    return {
        item["identifier"]: item
        for item in anomaly_capability(report)["operations"]
    }


class DynamicAnomalyEndToEndTests(unittest.TestCase):
    def test_persisted_renamed_sales_and_profit_flow_preserves_exact_evidence(self):
        sales = [-100] + list(range(30)) + [100]
        profits = [-200] + list(range(-15, 15)) + [200]
        rows = ["WhenObserved,RevenueValue,NetOutcome"]
        rows.extend(
            f"2026-01-01,{sale},{profit}"
            for sale, profit in zip(sales, profits, strict=True)
        )
        rows.extend(("2026-01-01,,", "2026-01-01,DROP TABLE,__import__('os')"))

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            onboarding = OnboardingManager(root / "onboarding")
            source = write_csv(root / "renamed.csv", "\n".join(rows) + "\n")
            added = onboarding.add(source)
            dataset_id = added["dataset_id"]
            onboarding.confirm(
                dataset_id, "WhenObserved", "TRANSACTION_DATE", evidence="owner approval",
            )
            onboarding.confirm(
                dataset_id, "RevenueValue", "SALES", evidence="owner approval",
            )
            onboarding.confirm(
                dataset_id, "NetOutcome", "PROFIT", evidence="owner approval",
            )
            approved = onboarding.confirm_domain(
                dataset_id, "SALES_RECORD", evidence="owner domain approval",
            )
            readiness = onboarding.capabilities(dataset_id)
            manager = FinancialManagerAgent(onboarding_root=root / "onboarding")
            with patch("socket.socket", side_effect=AssertionError("network forbidden")), \
                 patch("socket.create_connection", side_effect=AssertionError("network forbidden")):
                sales_response = manager.execute_dataset_anomaly_request(
                    DynamicAnomalyRequest(dataset_id, "SALES_ANOMALY_SCREEN"),
                )
                profit_response = manager.execute_dataset_anomaly_request(
                    DynamicAnomalyRequest(dataset_id, "PROFIT_ANOMALY_SCREEN"),
                )

        self.assertEqual(added["lifecycle_state"], "NEEDS_CONFIRMATION")
        self.assertEqual(approved["lifecycle_state"], "READY")
        self.assertEqual(
            {item["state"] for item in operation_states(readiness).values()},
            {"SUPPORTED"},
        )
        expected = {
            "SALES": {
                "q1": "6.75", "q3": "22.25", "iqr": "15.50",
                "lower_fence": "-16.500", "upper_fence": "45.500",
                "candidates": {"-100", "100"}, "source_column": "RevenueValue",
            },
            "PROFIT": {
                "q1": "-8.25", "q3": "7.25", "iqr": "15.50",
                "lower_fence": "-31.500", "upper_fence": "30.500",
                "candidates": {"-200", "200"}, "source_column": "NetOutcome",
            },
        }
        for response in (sales_response, profit_response):
            evidence = response["delegated_result"]["result"]
            measure_expected = expected[evidence["measure"]]
            self.assertEqual(response["manager_version"], "1.1")
            self.assertEqual(response["execution_status"], "PARTIAL")
            self.assertEqual(evidence["scope"], "GLOBAL")
            self.assertEqual(evidence["policy"], {"name": "tukey_iqr", "version": "1.0"})
            for field in ("q1", "q3", "iqr", "lower_fence", "upper_fence"):
                self.assertEqual(evidence[field], measure_expected[field])
            self.assertEqual(evidence["counts"], {
                "population": 34,
                "usable": 32,
                "assessed": 32,
                "excluded": 2,
                "candidate": 2,
                "not_selected": 30,
                "not_assessed": 2,
            })
            self.assertEqual(set(evidence["not_assessed_reasons"].values()), {1})
            self.assertEqual(
                {item["observed_status"] for item in evidence["assessments"][-2:]},
                {"source_missing", "parsing_failed"},
            )
            self.assertEqual(
                {
                    item["observed_value"]
                    for item in evidence["assessments"]
                    if item["status"] == "CANDIDATE"
                },
                measure_expected["candidates"],
            )
            self.assertEqual(evidence["lineage"]["source_column"], measure_expected["source_column"])
            self.assertEqual(len(evidence["lineage"]["records"]), 34)
            self.assertEqual(len(evidence["candidate_references"]), 2)
            self.assertEqual(evidence["currency"]["status"], "UNKNOWN")
            self.assertFalse(evidence["conversion_applied"])
            self.assertNotIn(str(root), json.dumps(response))

    def test_mapping_revocation_blocks_manager_and_restoration_recovers_fresh(self):
        values = list(range(30)) + [100]
        rows = ["date,sales,profit"] + [
            f"2026-01-01,{value},{value}" for value in values
        ]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            onboarding, state = onboard_sales(
                root,
                "\n".join(rows) + "\n",
                mappings={"date": "TRANSACTION_DATE", "sales": "SALES", "profit": "PROFIT"},
            )
            dataset_id = state["dataset_id"]
            manager = FinancialManagerAgent(onboarding_root=root / "onboarding")
            supported = manager.execute_dataset_anomaly_request(DynamicAnomalyRequest(
                dataset_id, "PROFIT_ANOMALY_SCREEN",
            ))
            onboarding.reject(dataset_id, "profit", evidence="authority revoked")
            revoked = manager.execute_dataset_anomaly_request(DynamicAnomalyRequest(
                dataset_id, "PROFIT_ANOMALY_SCREEN",
            ))
            onboarding.confirm(
                dataset_id, "profit", "PROFIT", evidence="authority restored",
            )
            recovered = manager.execute_dataset_anomaly_request(DynamicAnomalyRequest(
                dataset_id, "PROFIT_ANOMALY_SCREEN",
            ))

        self.assertEqual(supported["execution_status"], "SUCCESS")
        self.assertEqual(revoked["execution_status"], "DATA_QUALITY_BLOCKER")
        self.assertEqual(revoked["errors"][0]["code"], "missing_confirmed_profit")
        self.assertIsNone(revoked["delegated_result"])
        self.assertEqual(recovered["execution_status"], "SUCCESS")
        self.assertEqual(
            recovered["delegated_result"]["result"]["candidate_references"],
            supported["delegated_result"]["result"]["candidate_references"],
        )

    def test_cli_capability_discovery_is_truthful_for_supported_partial_and_blocked(self):
        fixtures = (
            (range(30), range(30), {"SUPPORTED"}, "AVAILABLE_WITH_LIMITATIONS"),
            (range(30), None, {"SUPPORTED", "BLOCKED"}, "AVAILABLE_WITH_LIMITATIONS"),
            ([1] * 30, None, {"BLOCKED"}, "BLOCKED"),
        )
        for sales, profits, expected_states, expected_overall in fixtures:
            with self.subTest(overall=expected_overall), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                headers = "date,sales" + (",profit" if profits is not None else "")
                records = [headers]
                for index, sale in enumerate(sales):
                    row = f"2026-01-01,{sale}"
                    if profits is not None:
                        row += f",{list(profits)[index]}"
                    records.append(row)
                mappings = {"date": "TRANSACTION_DATE", "sales": "SALES"}
                if profits is not None:
                    mappings["profit"] = "PROFIT"
                onboarding, state = onboard_sales(
                    root, "\n".join(records) + "\n", mappings=mappings,
                )
                report = onboarding.capabilities(state["dataset_id"])
                human = render_dataset("capabilities", report)
                output = StringIO()
                code = main(
                    ["dataset", "capabilities", state["dataset_id"], "--json"],
                    onboarding=onboarding, stdout=output, stderr=StringIO(),
                )
                parsed = json.loads(output.getvalue())

                self.assertEqual(code, 0)
                self.assertIn(f"Anomaly Detection: {expected_overall}", human)
                self.assertEqual(anomaly_capability(parsed)["state"], expected_overall)
                self.assertEqual(
                    {item["state"] for item in anomaly_capability(parsed)["operations"]},
                    expected_states,
                )

    def test_sample_and_iqr_revocation_recover_only_after_fresh_semantic_state(self):
        records = ["date,good sales,sparse sales,flat sales"]
        for index in range(31):
            sparse = str(index) if index < 29 else ""
            records.append(f"2026-01-01,{index},{sparse},1")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            onboarding, state = onboard_sales(
                root,
                "\n".join(records) + "\n",
                mappings={"date": "TRANSACTION_DATE", "good sales": "SALES"},
            )
            dataset_id = state["dataset_id"]
            manager = FinancialManagerAgent(onboarding_root=root / "onboarding")
            request = DynamicAnomalyRequest(dataset_id, "SALES_ANOMALY_SCREEN")
            initial = manager.execute_dataset_anomaly_request(request)

            onboarding.reject(dataset_id, "good sales", evidence="switch to sparse")
            onboarding.confirm(
                dataset_id, "sparse sales", "SALES", evidence="approved sparse source",
            )
            insufficient = manager.execute_dataset_anomaly_request(request)

            onboarding.reject(dataset_id, "sparse sales", evidence="restore good source")
            onboarding.confirm(
                dataset_id, "good sales", "SALES", evidence="approved good source",
            )
            recovered_sample = manager.execute_dataset_anomaly_request(request)

            onboarding.reject(dataset_id, "good sales", evidence="switch to flat")
            onboarding.confirm(
                dataset_id, "flat sales", "SALES", evidence="approved flat source",
            )
            zero_iqr = manager.execute_dataset_anomaly_request(request)

            onboarding.reject(dataset_id, "flat sales", evidence="restore good source")
            onboarding.confirm(
                dataset_id, "good sales", "SALES", evidence="approved good source again",
            )
            recovered_iqr = manager.execute_dataset_anomaly_request(request)

        self.assertEqual(initial["execution_status"], "SUCCESS")
        self.assertEqual(insufficient["errors"][0]["code"], "insufficient_numeric_records")
        self.assertIsNone(insufficient["delegated_result"])
        self.assertEqual(recovered_sample["execution_status"], "SUCCESS")
        self.assertEqual(zero_iqr["errors"][0]["code"], "zero_iqr")
        self.assertIsNone(zero_iqr["delegated_result"])
        self.assertEqual(recovered_iqr["execution_status"], "SUCCESS")


if __name__ == "__main__":
    unittest.main()
