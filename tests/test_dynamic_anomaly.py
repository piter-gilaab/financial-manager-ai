import tempfile
import unittest
from copy import deepcopy
from decimal import localcontext
import hashlib
import json
from pathlib import Path

from src.anomaly.baseline import screen as legacy_screen
from src.anomaly.dynamic import (
    DynamicAnomalyAdapter,
    DynamicAnomalyOperation,
    DynamicAnomalyRequest,
)
from src.financial.contracts import CF

from tests.execution_support import onboard_sales
from tests.test_anomaly import fixture_rows


def seal(payload, field):
    payload[field] = ""
    payload[field] = hashlib.sha256(json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


def anomaly_csv(*, header="sales", values):
    return "date," + header + "\n" + "\n".join(
        f"2026-01-01,{value}" for value in values
    ) + "\n"


class DynamicAnomalyAdapterTests(unittest.TestCase):
    def execute(self, values, *, operation="SALES_ANOMALY_SCREEN", header="sales",
                role="SALES"):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        mappings = {"date": "TRANSACTION_DATE", header: role}
        csv_text = anomaly_csv(header=header, values=values)
        if role == "PROFIT":
            csv_text = "date,sales," + header + "\n" + "\n".join(
                f"2026-01-01,1.00,{value}" for value in values
            ) + "\n"
            mappings["sales"] = "SALES"
        _, state = onboard_sales(
            root,
            csv_text,
            mappings=mappings,
        )
        adapter = DynamicAnomalyAdapter(root / "onboarding")
        return adapter.execute(DynamicAnomalyRequest(state["dataset_id"], operation))

    def test_sales_screen_uses_closed_global_tukey_policy(self):
        result = self.execute(list(range(30)) + [100])

        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(result["query_name"], "SALES_ANOMALY_SCREEN")
        self.assertEqual(result["result"]["scope"], "GLOBAL")
        self.assertNotIn("dataset_capability_state", result["result"])
        self.assertEqual(result["result"]["policy"], {"name": "tukey_iqr", "version": "1.0"})
        self.assertEqual(result["result"]["counts"], {
            "population": 31,
            "usable": 31,
            "assessed": 31,
            "excluded": 0,
            "candidate": 1,
            "not_selected": 30,
            "not_assessed": 0,
        })
        self.assertEqual(result["result"]["assessments"][-1]["status"], "CANDIDATE")
        self.assertEqual(result["result"]["assessments"][-1]["tail"], "upper")

    def test_exactly_thirty_values_are_executable(self):
        result = self.execute(list(range(29)) + [100])

        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(result["result"]["counts"]["usable"], 30)

    def test_twenty_nine_values_fail_closed(self):
        result = self.execute(range(29))

        self.assertEqual(result["status"], "DATA_QUALITY_BLOCKER")
        self.assertIsNone(result["result"])
        self.assertEqual(result["errors"][0]["code"], "insufficient_numeric_records")

    def test_zero_iqr_fails_closed(self):
        result = self.execute(["10.00"] * 30)

        self.assertEqual(result["status"], "DATA_QUALITY_BLOCKER")
        self.assertIsNone(result["result"])
        self.assertEqual(result["errors"][0]["code"], "zero_iqr")

    def test_arbitrary_measure_and_peer_request_are_rejected(self):
        values = list(range(30))
        arbitrary = self.execute(values, operation="DISCOUNT_ANOMALY_SCREEN")
        peer = self.execute(values, operation="SALES_ANOMALY_SCREEN:COUNTRY")

        self.assertEqual(arbitrary["status"], "UNSUPPORTED")
        self.assertEqual(peer["status"], "UNSUPPORTED")
        self.assertEqual(
            [item.value for item in DynamicAnomalyOperation],
            ["SALES_ANOMALY_SCREEN", "PROFIT_ANOMALY_SCREEN"],
        )

    def test_profit_screen_uses_supplied_profit_and_preserves_negative_values(self):
        result = self.execute(
            [-100] + list(range(-15, 15)),
            operation="PROFIT_ANOMALY_SCREEN",
            header="net result",
            role="PROFIT",
        )

        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(result["result"]["measure"], "PROFIT")
        self.assertEqual(result["result"]["assessments"][0]["status"], "CANDIDATE")
        self.assertEqual(result["result"]["assessments"][0]["tail"], "lower")
        self.assertEqual(result["result"]["assessments"][1]["observed_value"], "-15")

    def test_negative_sales_participate_and_only_fences_select_them(self):
        result = self.execute([-100] + list(range(-15, 15)))

        self.assertEqual(result["result"]["assessments"][0]["status"], "CANDIDATE")
        self.assertEqual(result["result"]["assessments"][1]["status"], "NOT_SELECTED")
        self.assertEqual(result["result"]["assessments"][1]["observed_value"], "-15")

    def test_strict_fences_do_not_select_exact_equality(self):
        lower = self.execute([-6] + [0] * 14 + [4] * 16)
        upper = self.execute([0] * 15 + [4] * 15 + [10])

        self.assertEqual(lower["result"]["lower_fence"], "-6.0")
        self.assertEqual(lower["result"]["assessments"][0]["status"], "NOT_SELECTED")
        self.assertEqual(upper["result"]["upper_fence"], "10.0")
        self.assertEqual(upper["result"]["assessments"][-1]["status"], "NOT_SELECTED")

    def test_missing_and_parse_failed_values_are_distinct_not_assessed_records(self):
        result = self.execute(list(range(30)) + ["", "DROP TABLE values"])

        self.assertEqual(result["status"], "PARTIAL")
        self.assertEqual(result["result"]["counts"]["not_assessed"], 2)
        self.assertEqual(result["result"]["not_assessed_reasons"], {
            "measure:sales:parsing_failed": 1,
            "measure:sales:source_missing": 1,
        })
        self.assertEqual(
            [item["status"] for item in result["result"]["assessments"][-2:]],
            ["NOT_ASSESSED", "NOT_ASSESSED"],
        )
        self.assertEqual(
            [item["observed_status"] for item in result["result"]["assessments"][-2:]],
            ["source_missing", "parsing_failed"],
        )

    def test_unknown_and_confirmed_currency_are_disclosed_without_conversion(self):
        unknown = self.execute(list(range(30)))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            rows = "\n".join(f"2026-01-01,{value},USD" for value in range(30))
            _, state = onboard_sales(
                root,
                "date,revenue,currency\n" + rows + "\n",
                mappings={
                    "date": "TRANSACTION_DATE",
                    "revenue": "SALES",
                    "currency": "CURRENCY",
                },
                currency_values={"USD": "USD"},
            )
            confirmed = DynamicAnomalyAdapter(root / "onboarding").execute(
                DynamicAnomalyRequest(state["dataset_id"], "SALES_ANOMALY_SCREEN")
            )

        self.assertEqual(unknown["currency"]["status"], "UNKNOWN")
        self.assertFalse(unknown["currency"]["conversion_applied"])
        self.assertEqual(confirmed["currency"]["status"], "CONFIRMED")
        self.assertEqual(confirmed["currency"]["code"], "USD")
        self.assertFalse(confirmed["currency"]["conversion_applied"])

    def test_executable_looking_header_is_inert_under_explicit_mapping(self):
        header = "__import__('os').system('id')"
        result = self.execute(list(range(30)) + [100], header=header)

        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(result["result"]["lineage"]["source_column"], header)
        self.assertEqual(result["result"]["counts"]["candidate"], 1)

    def test_confirmed_multiple_currencies_block_without_assessments(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            rows = "\n".join(
                f"2026-01-01,{value},{'USD' if value % 2 else 'BRL'}"
                for value in range(30)
            )
            _, state = onboard_sales(
                root,
                "date,sales,currency\n" + rows + "\n",
                mappings={
                    "date": "TRANSACTION_DATE",
                    "sales": "SALES",
                    "currency": "CURRENCY",
                },
                currency_values={"USD": "USD", "BRL": "BRL"},
            )
            result = DynamicAnomalyAdapter(root / "onboarding").execute(
                DynamicAnomalyRequest(state["dataset_id"], "SALES_ANOMALY_SCREEN")
            )

        self.assertEqual(result["status"], "DATA_QUALITY_BLOCKER")
        self.assertEqual(result["errors"][0]["code"], "incompatible_currency")
        self.assertIsNone(result["result"])
        self.assertEqual(result["currency"]["status"], "CONFIRMED_MULTIPLE")

    def test_exact_decimal_context_and_arithmetic_failure_are_fail_closed(self):
        values = [f"{index}.1" for index in range(30)] + ["100.1"]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(root, anomaly_csv(values=values))
            adapter = DynamicAnomalyAdapter(root / "onboarding")
            request = DynamicAnomalyRequest(state["dataset_id"], "SALES_ANOMALY_SCREEN")
            expected = adapter.execute(request)
            with localcontext() as context:
                context.prec = 2
                context.rounding = "ROUND_DOWN"
                actual = adapter.execute(request)
        overflow = self.execute(list(range(30)) + ["9" * 61])

        self.assertEqual(actual["result"]["q1"], expected["result"]["q1"])
        self.assertEqual(actual["result"]["upper_fence"], expected["result"]["upper_fence"])
        self.assertEqual(overflow["status"], "DATA_QUALITY_BLOCKER")
        self.assertEqual(overflow["errors"][0]["code"], "exact_arithmetic_limit")
        self.assertIsNone(overflow["result"])

    def test_high_scale_plain_decimal_remains_exact_canonical_text(self):
        values = ["0.0000000000000000001"] + [f"{index}.0000000000000000001" for index in range(1, 30)]
        result = self.execute(values)

        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(
            result["result"]["assessments"][0]["observed_value"],
            "0.0000000000000000001",
        )

    def test_order_lineage_candidate_references_and_source_privacy_are_deterministic(self):
        first = self.execute(list(range(30)) + [100])
        second = self.execute(list(range(30)) + [100])

        self.assertEqual(
            [item["source_row_number"] for item in first["result"]["assessments"]],
            list(range(2, 33)),
        )
        self.assertEqual(first["result"]["assessments"], second["result"]["assessments"])
        self.assertEqual(len(first["metadata"]["lineage"]["records"]), 31)
        self.assertEqual(first["result"]["lineage"]["confirmed_measure"], "SALES")
        self.assertEqual(first["result"]["lineage"]["source_column"], "sales")
        self.assertTrue(first["result"]["lineage"]["column_id"].startswith("col_"))
        self.assertEqual(first["result"]["reference"]["numeric_size"], 31)
        self.assertEqual(first["result"]["assessments"][0]["reference_id"], "global")
        self.assertEqual(first["result"]["assessments"][0]["observed_raw"], "0")
        self.assertLessEqual(len(first["result"]["candidate_references"]), 20)
        self.assertNotIn(tempfile.gettempdir(), json.dumps(first))

    def test_stale_mapping_stale_profile_and_changed_source_fail_closed(self):
        def onboard(root):
            return onboard_sales(root, anomaly_csv(values=list(range(30))))[1]

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state = onboard(root)
            onboarding = root / "onboarding"
            mapping_files = sorted(
                (onboarding / "artifacts" / state["dataset_id"] / "mappings").glob("*.json")
            )
            old_mapping = json.loads(mapping_files[0].read_text(encoding="utf-8"))
            workflow_path = onboarding / "workflows" / state["dataset_id"] / "current.json"
            workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
            workflow["mapping_version"] = old_mapping["mapping_version"]
            workflow["mapping_digest"] = old_mapping["mapping_digest"]
            seal(workflow, "workflow_digest")
            workflow_path.write_text(json.dumps(workflow), encoding="utf-8")
            stale_mapping = DynamicAnomalyAdapter(onboarding).execute(
                DynamicAnomalyRequest(state["dataset_id"], "SALES_ANOMALY_SCREEN")
            )

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state = onboard(root)
            onboarding = root / "onboarding"
            workflow_path = onboarding / "workflows" / state["dataset_id"] / "current.json"
            workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
            profile_path = (
                onboarding / "artifacts" / state["dataset_id"] / "profiles"
                / f'{workflow["profile_digest"]}.json'
            )
            profile = json.loads(profile_path.read_text(encoding="utf-8"))
            profile["bounds"]["max_examples"] += 1
            seal(profile, "profile_digest")
            profile_path.with_name(f'{profile["profile_digest"]}.json').write_text(
                json.dumps(profile), encoding="utf-8",
            )
            workflow["profile_digest"] = profile["profile_digest"]
            seal(workflow, "workflow_digest")
            workflow_path.write_text(json.dumps(workflow), encoding="utf-8")
            stale_profile = DynamicAnomalyAdapter(onboarding).execute(
                DynamicAnomalyRequest(state["dataset_id"], "SALES_ANOMALY_SCREEN")
            )

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state = onboard(root)
            onboarding = root / "onboarding"
            source = onboarding / "artifacts" / state["dataset_id"] / "source" / "source.csv"
            source.write_text(anomaly_csv(values=list(range(29)) + [999]), encoding="utf-8")
            changed_source = DynamicAnomalyAdapter(onboarding).execute(
                DynamicAnomalyRequest(state["dataset_id"], "SALES_ANOMALY_SCREEN")
            )

        self.assertEqual(stale_mapping["errors"][0]["code"], "stale_mapping")
        self.assertEqual(stale_profile["errors"][0]["code"], "stale_mapping")
        self.assertEqual(changed_source["errors"][0]["code"], "invalid_registry")
        self.assertIsNone(stale_mapping["result"])
        self.assertIsNone(stale_profile["result"])
        self.assertIsNone(changed_source["result"])

    def test_dynamic_sales_and_profit_match_legacy_global_policy_semantics(self):
        for measure, operation, header, role in (
            ("sales", "SALES_ANOMALY_SCREEN", "revenue", "SALES"),
            ("profit", "PROFIT_ANOMALY_SCREEN", "net result", "PROFIT"),
        ):
            with self.subTest(measure=measure):
                values = [f"{value}.00" for value in range(30)] + ["100.00"]
                dynamic = self.execute(values, operation=operation, header=header, role=role)
                rows = fixture_rows(values, CF, measure)
                before = deepcopy(rows)
                legacy = legacy_screen(rows, CF, measure)
                legacy_statuses = [
                    item["assessments"]["global"]["status"]
                    for item in legacy["items"]
                ]
                self.assertEqual(
                    [item["status"] for item in dynamic["result"]["assessments"]],
                    legacy_statuses,
                )
                self.assertEqual(rows, before)


if __name__ == "__main__":
    unittest.main()
