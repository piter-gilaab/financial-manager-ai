import tempfile
import unittest
from pathlib import Path
import hashlib
import json

from src.execution import (
    AdapterExecutionRequest,
    AdapterOutcome,
    SalesRecordOperation,
    adapter_for,
)

from tests.execution_support import onboard_sales


def seal(payload, field):
    payload[field] = ""
    payload[field] = hashlib.sha256(json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


class ExecutionAdapterContractTests(unittest.TestCase):
    def test_static_registry_does_not_resolve_data_as_an_implementation_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            adapter = adapter_for("SALES_RECORD", root)
            self.assertEqual(adapter.domain, "SALES_RECORD")
            self.assertEqual(adapter.adapter_version, "1.0")
            self.assertEqual(adapter.canonical_model_version, "1.0")
            self.assertEqual(adapter.supported_operations(), tuple(SalesRecordOperation))
            self.assertIsNone(adapter_for("SALES_RECORD.__class__", root))
            self.assertIsNone(adapter_for("src.execution.sales_record", root))
            self.assertIsNone(adapter_for("__import__('os').system('id')", root))

    def test_unsupported_operation_is_a_controlled_result(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                "date,sales\n2026-01-01,10.00\n",
            )
            adapter = adapter_for("SALES_RECORD", root / "onboarding")
            request = AdapterExecutionRequest(
                dataset_id=state["dataset_id"],
                operation="__import__('os').system('id')",
            )

            response = adapter.execute(request)

            self.assertEqual(response["status"], "UNSUPPORTED")
            self.assertEqual(response["errors"][0]["code"], "UNSUPPORTED_OPERATION")
            self.assertIsNone(response["result"])

    def test_non_typed_request_is_rejected_without_object_dispatch(self):
        with tempfile.TemporaryDirectory() as temporary:
            adapter = adapter_for("SALES_RECORD", Path(temporary))

            response = adapter.execute({"operation": "SALES_RECORD_COUNT"})

            self.assertEqual(response["status"], "UNSUPPORTED")
            self.assertEqual(response["errors"][0]["code"], "UNSUPPORTED_OPERATION")

    def test_grouping_requires_confirmed_country_semantics(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                "date,country,sales\n2026-01-01,Brazil,10.00\n",
            )
            adapter = adapter_for("SALES_RECORD", root / "onboarding")
            request = AdapterExecutionRequest(
                dataset_id=state["dataset_id"],
                operation=SalesRecordOperation.SALES_BY_COUNTRY,
            )

            checked = adapter.validate(request)
            response = adapter.execute(request)

            self.assertEqual(checked.outcome, AdapterOutcome.UNRESOLVED_SEMANTICS)
            self.assertEqual(response["status"], "DATA_QUALITY_BLOCKER")
            self.assertEqual(response["errors"][0]["code"], "UNRESOLVED_SEMANTICS")
            self.assertIsNone(response["result"])

    def test_invalid_unused_measure_does_not_block_operation_scoped_view(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                "date,sales,profit\n2026-01-01,10.00,not-money\n",
                mappings={
                    "date": "TRANSACTION_DATE",
                    "sales": "SALES",
                    "profit": "PROFIT",
                },
            )
            adapter = adapter_for("SALES_RECORD", root / "onboarding")

            count = adapter.execute(AdapterExecutionRequest(
                dataset_id=state["dataset_id"],
                operation=SalesRecordOperation.SALES_RECORD_COUNT,
            ))
            summary = adapter.execute(AdapterExecutionRequest(
                dataset_id=state["dataset_id"],
                operation=SalesRecordOperation.SALES_SUMMARY,
            ))

            self.assertEqual(count["status"], "SUCCESS")
            self.assertEqual(summary["status"], "SUCCESS")
            self.assertEqual(summary["result"]["measures"]["sales"]["sum"], "10.00")

    def test_dataset_with_no_valid_sales_is_not_execution_ready(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                "date,sales\n2026-01-01,not-money\n",
            )
            response = adapter_for("SALES_RECORD", root / "onboarding").execute(
                AdapterExecutionRequest(
                    dataset_id=state["dataset_id"],
                    operation=SalesRecordOperation.SALES_SUMMARY,
                )
            )

            self.assertEqual(response["status"], "DATA_QUALITY_BLOCKER")
            self.assertEqual(response["errors"][0]["code"], "QUALITY_BLOCKER")
            self.assertIsNone(response["result"])

    def test_revision_that_unresolves_sales_blocks_execution(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manager, state = onboard_sales(
                root,
                "date,sales\n2026-01-01,10.00\n",
            )
            manager.confirm(
                state["dataset_id"], "sales", "PROFIT",
                evidence="Synthetic correction removes SALES authority",
            )
            adapter = adapter_for("SALES_RECORD", root / "onboarding")
            request = AdapterExecutionRequest(
                dataset_id=state["dataset_id"],
                operation=SalesRecordOperation.SALES_SUMMARY,
            )

            checked = adapter.validate(request)
            response = adapter.execute(request)

            self.assertEqual(checked.outcome, AdapterOutcome.UNRESOLVED_SEMANTICS)
            self.assertEqual(response["errors"][0]["code"], "UNRESOLVED_SEMANTICS")

    def test_stale_workflow_mapping_digest_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                "date,sales\n2026-01-01,10.00\n",
            )
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
            workflow_path.write_text(
                json.dumps(workflow, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
                encoding="utf-8",
            )
            adapter = adapter_for("SALES_RECORD", onboarding)

            checked = adapter.validate(AdapterExecutionRequest(
                dataset_id=state["dataset_id"],
                operation=SalesRecordOperation.SALES_SUMMARY,
            ))

            self.assertEqual(checked.outcome, AdapterOutcome.STALE_MAPPING)

    def test_stale_workflow_profile_digest_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                "date,sales\n2026-01-01,10.00\n",
            )
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
            stale_profile_path = profile_path.with_name(f'{profile["profile_digest"]}.json')
            stale_profile_path.write_text(
                json.dumps(profile, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
                encoding="utf-8",
            )
            workflow["profile_digest"] = profile["profile_digest"]
            seal(workflow, "workflow_digest")
            workflow_path.write_text(
                json.dumps(workflow, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
                encoding="utf-8",
            )

            checked = adapter_for("SALES_RECORD", onboarding).validate(AdapterExecutionRequest(
                dataset_id=state["dataset_id"],
                operation=SalesRecordOperation.SALES_SUMMARY,
            ))

            self.assertEqual(checked.outcome, AdapterOutcome.STALE_MAPPING)

    def test_mapping_with_incompatible_stable_column_identity_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                "date,sales\n2026-01-01,10.00\n",
            )
            onboarding = root / "onboarding"
            workflow_path = onboarding / "workflows" / state["dataset_id"] / "current.json"
            workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
            current_mapping_path = (
                onboarding / "artifacts" / state["dataset_id"] / "mappings"
                / f'{workflow["mapping_version"]}-{workflow["mapping_digest"]}.json'
            )
            mapping = json.loads(current_mapping_path.read_text(encoding="utf-8"))
            sales = next(item for item in mapping["proposals"] if item["proposed_role"] == "SALES")
            sales["column_id"] = "col_0000000000000000"
            seal(mapping, "mapping_digest")
            replacement = current_mapping_path.with_name(
                f'{mapping["mapping_version"]}-{mapping["mapping_digest"]}.json'
            )
            replacement.write_text(
                json.dumps(mapping, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
                encoding="utf-8",
            )

            registry_path = onboarding / "registry" / state["dataset_id"] / "current.json"
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            registry["semantic_mapping_digest"] = mapping["mapping_digest"]
            registry["capability_readiness"]["mapping_digest"] = mapping["mapping_digest"]
            seal(registry, "entry_digest")
            registry_path.write_text(
                json.dumps(registry, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
                encoding="utf-8",
            )
            workflow["mapping_digest"] = mapping["mapping_digest"]
            seal(workflow, "workflow_digest")
            workflow_path.write_text(
                json.dumps(workflow, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
                encoding="utf-8",
            )

            checked = adapter_for("SALES_RECORD", onboarding).validate(AdapterExecutionRequest(
                dataset_id=state["dataset_id"],
                operation=SalesRecordOperation.SALES_SUMMARY,
            ))

            self.assertEqual(checked.outcome, AdapterOutcome.SCHEMA_MISMATCH)

    def test_registry_digest_tampering_is_rejected_without_raw_error_text(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                "date,sales\n2026-01-01,10.00\n",
            )
            onboarding = root / "onboarding"
            registry_path = onboarding / "registry" / state["dataset_id"] / "current.json"
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            registry["row_count"] = 999
            registry_path.write_text(json.dumps(registry), encoding="utf-8")

            response = adapter_for("SALES_RECORD", onboarding).execute(AdapterExecutionRequest(
                dataset_id=state["dataset_id"],
                operation=SalesRecordOperation.SALES_RECORD_COUNT,
            ))

            self.assertEqual(response["errors"][0]["code"], "INVALID_REGISTRY")
            self.assertNotIn(str(onboarding), response["errors"][0]["message"])

    def test_changed_preserved_source_fingerprint_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                "date,sales\n2026-01-01,10.00\n",
            )
            onboarding = root / "onboarding"
            source = onboarding / "artifacts" / state["dataset_id"] / "source" / "source.csv"
            source.write_text("date,sales\n2026-01-01,999.00\n", encoding="utf-8")

            response = adapter_for("SALES_RECORD", onboarding).execute(AdapterExecutionRequest(
                dataset_id=state["dataset_id"],
                operation=SalesRecordOperation.SALES_SUMMARY,
            ))

            self.assertEqual(response["errors"][0]["code"], "INVALID_REGISTRY")
            self.assertIsNone(response["result"])

    def test_direct_execution_and_step54_readiness_use_the_same_adapter_authority(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manager, state = onboard_sales(
                root,
                "date,sales\n2026-01-01,10.00\n",
            )
            response = adapter_for("SALES_RECORD", root / "onboarding").execute(
                AdapterExecutionRequest(
                    dataset_id=state["dataset_id"],
                    operation=SalesRecordOperation.SALES_SUMMARY,
                )
            )
            readiness = manager.capabilities(state["dataset_id"])
            financial = next(
                item for item in readiness["capabilities"]
                if item["identifier"] == "FINANCIAL_ANALYSIS"
            )

            self.assertEqual(response["status"], "SUCCESS")
            self.assertEqual(financial["state"], "AVAILABLE_WITH_LIMITATIONS")
            self.assertEqual(financial["execution_readiness"], "READY")


if __name__ == "__main__":
    unittest.main()
