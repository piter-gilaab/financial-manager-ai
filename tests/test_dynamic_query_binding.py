import tempfile
import unittest
from pathlib import Path
import hashlib
import json

from src.execution import (
    AdapterExecutionRequest,
    BindingOutcome,
    DynamicQueryBinder,
    DynamicQueryParameters,
    DynamicQueryRequest,
    MissingDimensionPolicy,
    SalesRecordOperation,
    adapter_for,
)
from src.onboarding import OnboardingManager

from tests.execution_support import onboard_sales
from tests.onboarding_support import write_csv


def seal(payload, field):
    payload[field] = ""
    payload[field] = hashlib.sha256(json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


class DynamicQueryBindingTests(unittest.TestCase):
    def test_registered_sales_record_count_binds_to_typed_adapter_request(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                "date,sales\n2026-01-01,10.00\n",
            )

            result = DynamicQueryBinder(root / "onboarding").bind(DynamicQueryRequest(
                dataset_id=state["dataset_id"],
                operation="SALES_RECORD_COUNT",
            ))

            self.assertEqual(result.outcome, BindingOutcome.BOUND)
            self.assertTrue(result.bound)
            self.assertEqual(result.request.canonical_domain, "SALES_RECORD")
            self.assertEqual(result.request.registry_version, state["registry_version"])
            self.assertEqual(result.request.mapping_version, state["mapping_version"])
            self.assertIsInstance(result.request.adapter_request, AdapterExecutionRequest)
            self.assertIs(
                result.request.adapter_request.operation,
                SalesRecordOperation.SALES_RECORD_COUNT,
            )

    def test_sales_summary_requires_only_the_approved_sales_role(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                "SaleDate,Revenue\n2026-01-01,10.00\n",
                mappings={"SaleDate": "TRANSACTION_DATE", "Revenue": "SALES"},
            )

            result = DynamicQueryBinder(root / "onboarding").bind(DynamicQueryRequest(
                dataset_id=state["dataset_id"],
                operation="SALES_SUMMARY",
            ))

            self.assertEqual(result.outcome, BindingOutcome.BOUND)
            self.assertIs(
                result.request.adapter_request.operation,
                SalesRecordOperation.SALES_SUMMARY,
            )

    def test_sales_by_country_binds_only_allowlisted_missing_dimension_policies(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                "date,nation,sales\n2026-01-01,Brazil,10.00\n",
                mappings={
                    "date": "TRANSACTION_DATE",
                    "nation": "COUNTRY",
                    "sales": "SALES",
                },
            )
            binder = DynamicQueryBinder(root / "onboarding")

            for policy in ("BUCKET", "EXCLUDE"):
                with self.subTest(policy=policy):
                    result = binder.bind(DynamicQueryRequest(
                        dataset_id=state["dataset_id"],
                        operation="SALES_BY_COUNTRY",
                        parameters=DynamicQueryParameters(missing_dimension=policy),
                    ))

                    self.assertEqual(result.outcome, BindingOutcome.BOUND)
                    self.assertIs(
                        result.request.adapter_request.missing_dimension,
                        MissingDimensionPolicy(policy),
                    )

    def test_execute_reuses_existing_adapter_result_and_lineage(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                "date,sales\n2026-01-01,0.1\n2026-01-02,0.2\n",
            )
            request = DynamicQueryRequest(
                dataset_id=state["dataset_id"],
                operation="SALES_SUMMARY",
            )

            response = DynamicQueryBinder(root / "onboarding").execute(request)

            self.assertEqual(response["status"], "SUCCESS")
            self.assertEqual(response["result"]["measures"]["sales"]["sum"], "0.3")
            self.assertEqual(
                response["metadata"]["lineage"]["dataset_id"],
                state["dataset_id"],
            )
            self.assertEqual(
                response["metadata"]["lineage"]["semantic_mapping_digest"],
                state["mapping_digest"],
            )
            self.assertEqual(len(response["metadata"]["lineage"]["records"]), 2)

    def test_binding_rejects_required_role_with_incompatible_stable_column_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                "date,sales\n2026-01-01,10.00\n",
            )
            onboarding = root / "onboarding"
            workflow_path = onboarding / "workflows" / state["dataset_id"] / "current.json"
            workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
            mapping_path = (
                onboarding / "artifacts" / state["dataset_id"] / "mappings"
                / f'{workflow["mapping_version"]}-{workflow["mapping_digest"]}.json'
            )
            mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
            sales = next(
                item for item in mapping["proposals"]
                if item["proposed_role"] == "SALES"
            )
            sales["column_id"] = "col_0000000000000000"
            seal(mapping, "mapping_digest")
            replacement = mapping_path.with_name(
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

            result = DynamicQueryBinder(onboarding).bind(DynamicQueryRequest(
                dataset_id=state["dataset_id"],
                operation="SALES_SUMMARY",
            ))

            self.assertEqual(result.outcome, BindingOutcome.BINDING_BLOCKED)

    def test_mapping_profile_identity_mismatch_is_stale_before_adapter_resolution(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                "date,sales\n2026-01-01,10.00\n",
            )
            onboarding = root / "onboarding"
            workflow_path = onboarding / "workflows" / state["dataset_id"] / "current.json"
            workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
            mapping_path = (
                onboarding / "artifacts" / state["dataset_id"] / "mappings"
                / f'{workflow["mapping_version"]}-{workflow["mapping_digest"]}.json'
            )
            mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
            mapping["profile_digest"] = "0" * 64
            seal(mapping, "mapping_digest")
            mapping_path.with_name(
                f'{mapping["mapping_version"]}-{mapping["mapping_digest"]}.json'
            ).write_text(
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

            result = DynamicQueryBinder(onboarding).bind(DynamicQueryRequest(
                dataset_id=state["dataset_id"],
                operation="SALES_SUMMARY",
            ))

            self.assertEqual(result.outcome, BindingOutcome.STALE_MAPPING)

    def test_profile_source_identity_mismatch_is_stale_before_adapter_resolution(self):
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
            profile["source_sha256"] = "0" * 64
            seal(profile, "profile_digest")
            profile_path.with_name(f'{profile["profile_digest"]}.json').write_text(
                json.dumps(profile, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
                encoding="utf-8",
            )
            mapping_path = (
                onboarding / "artifacts" / state["dataset_id"] / "mappings"
                / f'{workflow["mapping_version"]}-{workflow["mapping_digest"]}.json'
            )
            mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
            mapping["profile_digest"] = profile["profile_digest"]
            seal(mapping, "mapping_digest")
            mapping_path.with_name(
                f'{mapping["mapping_version"]}-{mapping["mapping_digest"]}.json'
            ).write_text(
                json.dumps(mapping, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
                encoding="utf-8",
            )
            registry_path = onboarding / "registry" / state["dataset_id"] / "current.json"
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            registry["profile_digest"] = profile["profile_digest"]
            registry["semantic_mapping_digest"] = mapping["mapping_digest"]
            registry["capability_readiness"]["mapping_digest"] = mapping["mapping_digest"]
            seal(registry, "entry_digest")
            registry_path.write_text(
                json.dumps(registry, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
                encoding="utf-8",
            )
            workflow["profile_digest"] = profile["profile_digest"]
            workflow["mapping_digest"] = mapping["mapping_digest"]
            seal(workflow, "workflow_digest")
            workflow_path.write_text(
                json.dumps(workflow, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
                encoding="utf-8",
            )

            result = DynamicQueryBinder(onboarding).bind(DynamicQueryRequest(
                dataset_id=state["dataset_id"],
                operation="SALES_SUMMARY",
            ))

            self.assertEqual(result.outcome, BindingOutcome.STALE_MAPPING)

    def test_sales_by_country_rejects_unapproved_country_without_loading_an_alternative(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                "date,country,sales\n2026-01-01,Brazil,10.00\n",
            )

            result = DynamicQueryBinder(root / "onboarding").bind(DynamicQueryRequest(
                dataset_id=state["dataset_id"],
                operation="SALES_BY_COUNTRY",
            ))

            self.assertEqual(
                result.outcome,
                BindingOutcome.MISSING_REQUIRED_SEMANTICS,
            )
            self.assertIsNone(result.request)

    def test_revised_mapping_without_sales_blocks_summary_binding(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manager, state = onboard_sales(
                root,
                "date,sales\n2026-01-01,10.00\n",
            )
            manager.confirm(
                state["dataset_id"],
                "sales",
                "PROFIT",
                evidence="Synthetic correction removes SALES authority",
            )

            result = DynamicQueryBinder(root / "onboarding").bind(DynamicQueryRequest(
                dataset_id=state["dataset_id"],
                operation="SALES_SUMMARY",
            ))

            self.assertEqual(result.outcome, BindingOutcome.BINDING_BLOCKED)
            self.assertIsNone(result.request)

    def test_unknown_registered_identifier_returns_controlled_not_found(self):
        with tempfile.TemporaryDirectory() as temporary:
            request = DynamicQueryRequest(
                dataset_id="ds_00000000000000000000",
                operation="SALES_RECORD_COUNT",
            )
            binder = DynamicQueryBinder(Path(temporary) / "onboarding")

            result = binder.bind(request)
            response = binder.execute(request)

            self.assertEqual(result.outcome, BindingOutcome.DATASET_NOT_FOUND)
            self.assertEqual(response["status"], "INVALID_REQUEST")
            self.assertEqual(response["errors"][0]["code"], "DATASET_NOT_FOUND")
            self.assertNotIn(str(temporary), response["errors"][0]["message"])

    def test_recognized_accounting_domain_is_not_coerced_to_sales_record(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = write_csv(
                root / "accounting.csv",
                "date,amount\n2026-01-01,10.00\n",
            )
            manager = OnboardingManager(root / "onboarding")
            state = manager.add(source)
            manager.confirm(
                state["dataset_id"], "date", "POSTING_DATE",
                evidence="Synthetic posting-date approval",
            )
            manager.confirm(
                state["dataset_id"], "amount", "AMOUNT",
                evidence="Synthetic accounting-amount approval",
            )
            state = manager.confirm_domain(
                state["dataset_id"], "ACCOUNTING_TRANSACTION",
                evidence="Synthetic accounting-domain approval",
            )

            result = DynamicQueryBinder(root / "onboarding").bind(DynamicQueryRequest(
                dataset_id=state["dataset_id"],
                operation="SALES_RECORD_COUNT",
            ))

            self.assertEqual(result.outcome, BindingOutcome.UNSUPPORTED_DOMAIN)
            self.assertIsNone(result.request)

    def test_invalid_policy_and_policy_on_ungrouped_operation_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                "date,country,sales\n2026-01-01,Brazil,10.00\n",
                mappings={
                    "date": "TRANSACTION_DATE",
                    "country": "COUNTRY",
                    "sales": "SALES",
                },
            )
            binder = DynamicQueryBinder(root / "onboarding")

            sql_shaped = binder.bind(DynamicQueryRequest(
                dataset_id=state["dataset_id"],
                operation="SALES_BY_COUNTRY",
                parameters=DynamicQueryParameters(missing_dimension="DROP TABLE datasets"),
            ))
            irrelevant = binder.bind(DynamicQueryRequest(
                dataset_id=state["dataset_id"],
                operation="SALES_SUMMARY",
                parameters=DynamicQueryParameters(missing_dimension="EXCLUDE"),
            ))

            self.assertEqual(sql_shaped.outcome, BindingOutcome.INVALID_PARAMETER)
            self.assertEqual(irrelevant.outcome, BindingOutcome.INVALID_PARAMETER)

    def test_malicious_operation_and_dataset_identifiers_are_inert_data(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                "date,sales\n2026-01-01,10.00\n",
            )
            resolver_calls = []

            def resolver(domain, root):
                resolver_calls.append((domain, root))
                raise AssertionError("Invalid input must not reach adapter resolution.")

            binder = DynamicQueryBinder(
                root / "onboarding",
                adapter_resolver=resolver,
            )
            operation = binder.bind(DynamicQueryRequest(
                dataset_id=state["dataset_id"],
                operation="__import__('os').system('rm -rf /')",
            ))
            unknown = binder.bind(DynamicQueryRequest(
                dataset_id="ds_00000000000000000000",
                operation="__import__('os').system('rm -rf /')",
            ))
            dataset = binder.bind(DynamicQueryRequest(
                dataset_id="../../etc/passwd",
                operation="SALES_RECORD_COUNT",
            ))

            self.assertEqual(operation.outcome, BindingOutcome.UNSUPPORTED_OPERATION)
            self.assertEqual(unknown.outcome, BindingOutcome.DATASET_NOT_FOUND)
            self.assertEqual(dataset.outcome, BindingOutcome.INVALID_REQUEST)
            self.assertEqual(resolver_calls, [])

    def test_stale_workflow_mapping_pointer_is_rejected_before_adapter_resolution(self):
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
            resolver_calls = []

            result = DynamicQueryBinder(
                onboarding,
                adapter_resolver=lambda domain, root: resolver_calls.append((domain, root)),
            ).bind(DynamicQueryRequest(
                dataset_id=state["dataset_id"],
                operation="SALES_SUMMARY",
            ))

            self.assertEqual(result.outcome, BindingOutcome.STALE_MAPPING)
            self.assertEqual(resolver_calls, [])

    def test_static_registry_unavailability_is_a_controlled_binding_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                "date,sales\n2026-01-01,10.00\n",
            )

            result = DynamicQueryBinder(
                root / "onboarding",
                adapter_resolver=lambda domain, onboarding_root: None,
            ).bind(DynamicQueryRequest(
                dataset_id=state["dataset_id"],
                operation="SALES_SUMMARY",
            ))

            self.assertEqual(result.outcome, BindingOutcome.ADAPTER_UNAVAILABLE)
            self.assertIsNone(result.request)

    def test_binding_and_execution_match_step54_dataset_capability(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manager, state = onboard_sales(
                root,
                "date,sales\n2026-01-01,10.00\n",
            )
            binder = DynamicQueryBinder(root / "onboarding")

            response = binder.execute(DynamicQueryRequest(
                dataset_id=state["dataset_id"],
                operation="SALES_SUMMARY",
            ))
            financial = next(
                item for item in manager.capabilities(state["dataset_id"])["capabilities"]
                if item["identifier"] == "FINANCIAL_ANALYSIS"
            )

            self.assertEqual(response["status"], "SUCCESS")
            self.assertEqual(financial["state"], "AVAILABLE_WITH_LIMITATIONS")
            self.assertEqual(financial["execution_readiness"], "READY")

    def test_execute_rechecks_adapter_compatibility_after_binding(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, state = onboard_sales(
                root,
                "date,sales\n2026-01-01,10.00\n",
            )
            calls = 0

            class WrongDomainAdapter:
                domain = "ACCOUNTING_TRANSACTION"
                adapter_version = "1.0"
                canonical_model_version = "1.0"

                @staticmethod
                def execute(request):
                    raise AssertionError("An incompatible adapter must not execute.")

            def changing_resolver(domain, onboarding_root):
                nonlocal calls
                calls += 1
                if calls == 1:
                    return adapter_for(domain, onboarding_root)
                return WrongDomainAdapter()

            response = DynamicQueryBinder(
                root / "onboarding",
                adapter_resolver=changing_resolver,
            ).execute(DynamicQueryRequest(
                dataset_id=state["dataset_id"],
                operation="SALES_SUMMARY",
            ))

            self.assertEqual(response["status"], "DATA_QUALITY_BLOCKER")
            self.assertEqual(response["errors"][0]["code"], "ADAPTER_UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()
