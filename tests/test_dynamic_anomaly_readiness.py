import json
import hashlib
import tempfile
import unittest
from io import StringIO
from pathlib import Path

from src.cli.dataset import render_dataset
from src.cli.main import main
from src.anomaly.dynamic import DynamicAnomalyAdapter, DynamicAnomalyOperation
from src.onboarding.readiness import CapabilityDiscovery
from src.onboarding.registry import DatasetRegistry

from tests.execution_support import onboard_sales


def rows(sales, profits=None, currencies=None):
    headers = ["date", "sales"]
    if profits is not None:
        headers.append("profit")
    if currencies is not None:
        headers.append("currency")
    output = [",".join(headers)]
    for index, sale in enumerate(sales):
        record = ["2026-01-01", str(sale)]
        if profits is not None:
            record.append(str(profits[index]))
        if currencies is not None:
            record.append(currencies[index])
        output.append(",".join(record))
    return "\n".join(output) + "\n"


def anomaly_capability(report):
    return next(
        item for item in report["capabilities"]
        if item["identifier"] == "ANOMALY_DETECTION"
    )


def operation_states(capability):
    return {item["identifier"]: item for item in capability["operations"]}


def seal(payload, field):
    payload[field] = ""
    payload[field] = hashlib.sha256(json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


class DynamicAnomalyReadinessTests(unittest.TestCase):
    def onboard(self, root, sales, profits=None, *, currencies=None,
                currency_values=None):
        mappings = {"date": "TRANSACTION_DATE", "sales": "SALES"}
        if profits is not None:
            mappings["profit"] = "PROFIT"
        if currencies is not None:
            mappings["currency"] = "CURRENCY"
        return onboard_sales(
            root,
            rows(sales, profits, currencies),
            mappings=mappings,
            currency_values=currency_values,
        )

    def test_sales_supported_profit_absent_is_partial_anomaly_availability(self):
        with tempfile.TemporaryDirectory() as temporary:
            manager, state = self.onboard(Path(temporary), range(30))
            anomaly = anomaly_capability(manager.capabilities(state["dataset_id"]))

        operations = operation_states(anomaly)
        self.assertEqual(anomaly["state"], "AVAILABLE_WITH_LIMITATIONS")
        self.assertEqual(operations["SALES_ANOMALY_SCREEN"]["state"], "SUPPORTED")
        self.assertEqual(operations["PROFIT_ANOMALY_SCREEN"]["state"], "BLOCKED")
        self.assertEqual(
            operations["PROFIT_ANOMALY_SCREEN"]["reasons"],
            ["missing_confirmed_profit"],
        )

    def test_profit_supported_independently_when_sales_reference_is_degenerate(self):
        with tempfile.TemporaryDirectory() as temporary:
            manager, state = self.onboard(Path(temporary), [1] * 30, range(30))
            anomaly = anomaly_capability(manager.capabilities(state["dataset_id"]))

        operations = operation_states(anomaly)
        self.assertEqual(anomaly["state"], "AVAILABLE_WITH_LIMITATIONS")
        self.assertEqual(operations["SALES_ANOMALY_SCREEN"]["state"], "BLOCKED")
        self.assertEqual(operations["SALES_ANOMALY_SCREEN"]["reasons"], ["zero_iqr"])
        self.assertEqual(operations["PROFIT_ANOMALY_SCREEN"]["state"], "SUPPORTED")

    def test_both_operations_supported_or_blocked_from_current_data(self):
        with tempfile.TemporaryDirectory() as temporary:
            manager, state = self.onboard(Path(temporary), range(30), range(100, 130))
            both = anomaly_capability(manager.capabilities(state["dataset_id"]))
        with tempfile.TemporaryDirectory() as temporary:
            manager, state = self.onboard(Path(temporary), [1] * 30, [2] * 30)
            blocked = anomaly_capability(manager.capabilities(state["dataset_id"]))

        self.assertEqual(
            {item["state"] for item in both["operations"]}, {"SUPPORTED"},
        )
        self.assertEqual(both["state"], "AVAILABLE_WITH_LIMITATIONS")
        self.assertEqual(blocked["state"], "BLOCKED")
        self.assertEqual(
            {tuple(item["reasons"]) for item in blocked["operations"]},
            {("zero_iqr",)},
        )

    def test_sample_size_and_arithmetic_feasibility_are_operation_specific(self):
        with tempfile.TemporaryDirectory() as temporary:
            manager, state = self.onboard(Path(temporary), range(29), range(29))
            insufficient = operation_states(anomaly_capability(
                manager.capabilities(state["dataset_id"])
            ))
        with tempfile.TemporaryDirectory() as temporary:
            manager, state = self.onboard(Path(temporary), range(30), range(30))
            exact = operation_states(anomaly_capability(
                manager.capabilities(state["dataset_id"])
            ))
        with tempfile.TemporaryDirectory() as temporary:
            huge = [str(value) for value in range(29)] + ["9" * 61]
            manager, state = self.onboard(Path(temporary), huge)
            infeasible = operation_states(anomaly_capability(
                manager.capabilities(state["dataset_id"])
            ))

        self.assertEqual(insufficient["SALES_ANOMALY_SCREEN"]["reasons"], ["insufficient_numeric_records"])
        self.assertEqual(insufficient["PROFIT_ANOMALY_SCREEN"]["reasons"], ["insufficient_numeric_records"])
        self.assertEqual(exact["SALES_ANOMALY_SCREEN"]["state"], "SUPPORTED")
        self.assertEqual(exact["PROFIT_ANOMALY_SCREEN"]["state"], "SUPPORTED")
        self.assertEqual(infeasible["SALES_ANOMALY_SCREEN"]["reasons"], ["exact_arithmetic_limit"])

    def test_currency_readiness_allows_unknown_and_confirmed_but_blocks_multiple(self):
        with tempfile.TemporaryDirectory() as temporary:
            manager, state = self.onboard(Path(temporary), range(30))
            unknown = operation_states(anomaly_capability(manager.capabilities(state["dataset_id"])))
        with tempfile.TemporaryDirectory() as temporary:
            manager, state = self.onboard(
                Path(temporary), range(30), currencies=["USD"] * 30,
                currency_values={"USD": "USD"},
            )
            confirmed = operation_states(anomaly_capability(manager.capabilities(state["dataset_id"])))
        with tempfile.TemporaryDirectory() as temporary:
            denominations = ["USD" if index % 2 else "BRL" for index in range(30)]
            manager, state = self.onboard(
                Path(temporary), range(30), currencies=denominations,
                currency_values={"USD": "USD", "BRL": "BRL"},
            )
            multiple = operation_states(anomaly_capability(manager.capabilities(state["dataset_id"])))

        self.assertEqual(unknown["SALES_ANOMALY_SCREEN"]["state"], "SUPPORTED")
        self.assertEqual(confirmed["SALES_ANOMALY_SCREEN"]["state"], "SUPPORTED")
        self.assertEqual(multiple["SALES_ANOMALY_SCREEN"]["state"], "BLOCKED")
        self.assertEqual(multiple["SALES_ANOMALY_SCREEN"]["reasons"], ["incompatible_currency"])

    def test_profit_mapping_revocation_and_restoration_are_fresh(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manager, state = self.onboard(root, range(30), range(30))
            dataset_id = state["dataset_id"]
            baseline = operation_states(anomaly_capability(manager.capabilities(dataset_id)))
            manager.reject(dataset_id, "profit", evidence="Profit authority revoked")
            revoked = operation_states(anomaly_capability(manager.capabilities(dataset_id)))
            manager.confirm(
                dataset_id, "profit", "PROFIT", evidence="Profit authority restored",
            )
            restored = operation_states(anomaly_capability(manager.capabilities(dataset_id)))

        self.assertEqual(baseline["PROFIT_ANOMALY_SCREEN"]["state"], "SUPPORTED")
        self.assertEqual(revoked["PROFIT_ANOMALY_SCREEN"]["state"], "BLOCKED")
        self.assertEqual(revoked["SALES_ANOMALY_SCREEN"]["state"], "SUPPORTED")
        self.assertEqual(restored["PROFIT_ANOMALY_SCREEN"]["state"], "SUPPORTED")

    def test_sales_mapping_revocation_blocks_domain_and_restoration_recovers(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manager, state = self.onboard(root, range(30), range(30))
            dataset_id = state["dataset_id"]
            manager.reject(dataset_id, "sales", evidence="Sales authority revoked")
            revoked = operation_states(anomaly_capability(manager.capabilities(dataset_id)))
            manager.confirm(
                dataset_id, "sales", "SALES", evidence="Sales authority restored",
            )
            restored = operation_states(anomaly_capability(manager.capabilities(dataset_id)))

        self.assertEqual({item["state"] for item in revoked.values()}, {"BLOCKED"})
        self.assertEqual(restored["SALES_ANOMALY_SCREEN"]["state"], "SUPPORTED")
        self.assertEqual(restored["PROFIT_ANOMALY_SCREEN"]["state"], "SUPPORTED")

    def test_source_change_revokes_and_exact_restoration_recovers(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manager, state = self.onboard(root, range(30))
            dataset_id = state["dataset_id"]
            source = root / "onboarding" / "artifacts" / dataset_id / "source" / "source.csv"
            original = source.read_bytes()
            source.write_text(rows(list(range(29)) + [999]), encoding="utf-8")
            revoked = operation_states(anomaly_capability(manager.capabilities(dataset_id)))
            source.write_bytes(original)
            recovered = operation_states(anomaly_capability(manager.capabilities(dataset_id)))

        self.assertEqual(revoked["SALES_ANOMALY_SCREEN"]["state"], "BLOCKED")
        self.assertEqual(recovered["SALES_ANOMALY_SCREEN"]["state"], "SUPPORTED")

    def test_unavailable_adapter_is_never_supported(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manager, state = self.onboard(root, range(30))
            registry = DatasetRegistry(root / "onboarding")
            entry = registry.get(state["dataset_id"])
            profile = registry.load_profile(state["dataset_id"], entry.profile_digest)
            mapping = registry.load_mapping(
                state["dataset_id"], entry.semantic_mapping_version,
                entry.semantic_mapping_digest,
            )
            report = CapabilityDiscovery(
                root / "onboarding", anomaly_adapter_factory=lambda _: None,
            ).evaluate(profile, mapping).to_dict()

        anomaly = anomaly_capability(report)
        self.assertEqual(anomaly["state"], "BLOCKED")
        self.assertEqual({item["state"] for item in anomaly["operations"]}, {"UNSUPPORTED"})

    def test_single_unavailable_operation_does_not_block_supported_sales(self):
        class SalesOnlyAdapter(DynamicAnomalyAdapter):
            @staticmethod
            def supported_operations():
                return (DynamicAnomalyOperation.SALES_ANOMALY_SCREEN,)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manager, state = self.onboard(root, range(30), range(30))
            registry = DatasetRegistry(root / "onboarding")
            entry = registry.get(state["dataset_id"])
            profile = registry.load_profile(state["dataset_id"], entry.profile_digest)
            mapping = registry.load_mapping(
                state["dataset_id"], entry.semantic_mapping_version,
                entry.semantic_mapping_digest,
            )
            report = CapabilityDiscovery(
                root / "onboarding", anomaly_adapter_factory=SalesOnlyAdapter,
            ).evaluate(profile, mapping).to_dict()

        anomaly = anomaly_capability(report)
        operations = operation_states(anomaly)
        self.assertEqual(anomaly["state"], "AVAILABLE_WITH_LIMITATIONS")
        self.assertEqual(operations["SALES_ANOMALY_SCREEN"]["state"], "SUPPORTED")
        self.assertEqual(operations["PROFIT_ANOMALY_SCREEN"]["state"], "UNSUPPORTED")

    def test_incompatible_policy_version_is_never_supported(self):
        class IncompatiblePolicyAdapter(DynamicAnomalyAdapter):
            policy_version = "2.0"

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manager, state = self.onboard(root, range(30))
            registry = DatasetRegistry(root / "onboarding")
            entry = registry.get(state["dataset_id"])
            profile = registry.load_profile(state["dataset_id"], entry.profile_digest)
            mapping = registry.load_mapping(
                state["dataset_id"], entry.semantic_mapping_version,
                entry.semantic_mapping_digest,
            )
            report = CapabilityDiscovery(
                root / "onboarding", anomaly_adapter_factory=IncompatiblePolicyAdapter,
            ).evaluate(profile, mapping).to_dict()

        anomaly = anomaly_capability(report)
        self.assertEqual(anomaly["state"], "BLOCKED")
        self.assertEqual({item["state"] for item in anomaly["operations"]}, {"UNSUPPORTED"})

    def test_corrupt_registry_revokes_readiness_without_stale_authorization(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manager, state = self.onboard(root, range(30))
            registry_path = (
                root / "onboarding" / "registry" / state["dataset_id"] / "current.json"
            )
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            registry["row_count"] = 999
            registry_path.write_text(json.dumps(registry), encoding="utf-8")
            anomaly = anomaly_capability(manager.capabilities(state["dataset_id"]))

        self.assertEqual(anomaly["state"], "BLOCKED")
        self.assertEqual({item["state"] for item in anomaly["operations"]}, {"BLOCKED"})
        self.assertTrue(all(
            "integrity" in " ".join(item["reasons"]).casefold()
            for item in anomaly["operations"]
        ))

    def test_stale_profile_revokes_dataset_capability_readiness(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manager, state = self.onboard(root, range(30))
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
            anomaly = anomaly_capability(manager.capabilities(state["dataset_id"]))

        self.assertEqual(anomaly["state"], "BLOCKED")
        self.assertEqual({item["state"] for item in anomaly["operations"]}, {"BLOCKED"})

    def test_cli_human_and_json_expose_typed_anomaly_operation_states(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manager, state = self.onboard(root, range(30))
            report = manager.capabilities(state["dataset_id"])
            human = render_dataset("capabilities", report)
            output = StringIO()
            code = main(
                ["dataset", "capabilities", state["dataset_id"], "--json"],
                onboarding=manager, stdout=output, stderr=StringIO(),
            )

        parsed = json.loads(output.getvalue())
        parsed_anomaly = anomaly_capability(parsed)
        self.assertEqual(code, 0)
        self.assertIn("Anomaly Detection: AVAILABLE_WITH_LIMITATIONS", human)
        self.assertIn("SALES_ANOMALY_SCREEN: SUPPORTED", human)
        self.assertIn("PROFIT_ANOMALY_SCREEN: BLOCKED", human)
        self.assertEqual(
            operation_states(parsed_anomaly)["PROFIT_ANOMALY_SCREEN"]["reasons"],
            ["missing_confirmed_profit"],
        )
        self.assertNotIn("candidate_references", json.dumps(parsed_anomaly))
        self.assertNotIn('"assessments"', json.dumps(parsed_anomaly))

    def test_forecasting_rag_and_financial_analysis_remain_unchanged(self):
        with tempfile.TemporaryDirectory() as temporary:
            manager, state = self.onboard(Path(temporary), range(30))
            report = manager.capabilities(state["dataset_id"])

        states = {item["identifier"]: item["state"] for item in report["capabilities"]}
        self.assertEqual(states["FINANCIAL_ANALYSIS"], "AVAILABLE_WITH_LIMITATIONS")
        self.assertEqual(states["ANOMALY_DETECTION"], "AVAILABLE_WITH_LIMITATIONS")
        self.assertEqual(states["CASH_FLOW_FORECASTING"], "BLOCKED")
        self.assertEqual(states["DOCUMENT_RETRIEVAL"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
