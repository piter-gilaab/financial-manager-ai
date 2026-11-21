"""Phase 2 readiness, currency, catalog and security boundaries."""

from pathlib import Path
import tempfile
import unittest

from src.dynamic_anomaly import DYNAMIC_ANOMALY_OPERATIONS
from src.dynamic_financial import DYNAMIC_FINANCIAL_OPERATIONS
from src.execution import DynamicQueryParameters, DynamicQueryRequest, dynamic_operation_bindings
from src.manager import FinancialManagerAgent
from src.multidomain_financial import DOMAIN_OPERATIONS, MULTIDOMAIN_FINANCIAL_OPERATIONS
from src.onboarding import OnboardingManager
from src.onboarding.models import OnboardingError

from tests.onboarding_support import write_csv


class MultiDomainBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.root = self.base / "onboarding"

    def onboard(self, text, domain, roles, *, mappings=None, qualifiers=None):
        manager = OnboardingManager(self.root)
        dataset_id = manager.add(write_csv(self.base / f"{domain}.csv", text))["dataset_id"]
        for column, role in roles.items():
            manager.confirm(dataset_id, column, role, evidence="Synthetic boundary approval",
                            value_mapping=(mappings or {}).get(column))
        if qualifiers:
            manager.confirm_qualifiers(dataset_id, evidence="Synthetic qualifier approval",
                                       **qualifiers)
        manager.confirm_domain(dataset_id, domain, evidence="Synthetic domain approval")
        return manager, dataset_id

    def execute(self, dataset_id, operation, **parameters):
        return FinancialManagerAgent(onboarding_root=self.root).execute_dataset_request(
            DynamicQueryRequest(dataset_id, operation, DynamicQueryParameters(**parameters))
        )

    def test_catalogs_are_exact_and_new_anomaly_catalog_is_absent(self):
        self.assertEqual(len(DYNAMIC_FINANCIAL_OPERATIONS), 9)
        self.assertEqual(len(MULTIDOMAIN_FINANCIAL_OPERATIONS), 18)
        self.assertEqual({key: len(value) for key, value in DOMAIN_OPERATIONS.items()}, {
            "PAYABLE": 6, "RECEIVABLE": 6, "CASH_TRANSACTION": 6,
        })
        self.assertEqual(len(DYNAMIC_ANOMALY_OPERATIONS), 2)
        self.assertEqual(len(dynamic_operation_bindings("SALES_RECORD")), 9)
        for domain in DOMAIN_OPERATIONS:
            self.assertEqual(len(dynamic_operation_bindings(domain)), 6)

    def test_unknown_currency_is_qualified_and_multiple_currency_blocks_only_money(self):
        _manager, unknown_id = self.onboard(
            "Amount,Due\n10,2026-01-01\n", "PAYABLE",
            {"Amount": "AMOUNT", "Due": "DUE_DATE"},
        )
        unknown = self.execute(unknown_id, "PAYABLE_SUMMARY")
        self.assertEqual(unknown["execution_status"], "SUCCESS")
        self.assertEqual(unknown["delegated_result"]["currency"]["status"], "UNKNOWN")
        self.assertFalse(unknown["delegated_result"]["currency"]["conversion_applied"])

        manager, multiple_id = self.onboard(
            "Amount,Due,Currency\n10,2026-01-01,USD\n20,2026-01-02,EUR\n", "PAYABLE",
            {"Amount": "AMOUNT", "Due": "DUE_DATE", "Currency": "CURRENCY"},
            mappings={"Currency": {"USD": "USD", "EUR": "EUR"}},
        )
        states = {item["identifier"]: item["state"]
                  for item in manager.financial_analysis_readiness(multiple_id)["operations"]}
        self.assertEqual(states["PAYABLE_COUNT"], "SUPPORTED")
        self.assertEqual(states["PAYABLE_SUMMARY"], "BLOCKED")
        self.assertEqual(self.execute(multiple_id, "PAYABLE_COUNT")["execution_status"], "SUCCESS")
        self.assertEqual(self.execute(multiple_id, "PAYABLE_SUMMARY")["execution_status"],
                         "DATA_QUALITY_BLOCKER")

    def test_incomplete_status_mapping_fails_and_sign_never_supplies_direction(self):
        manager = OnboardingManager(self.root)
        dataset_id = manager.add(write_csv(
            self.base / "status.csv",
            "Amount,Due,Status\n10,2026-01-01,open\n20,2026-01-02,paid\n",
        ))["dataset_id"]
        manager.confirm(dataset_id, "Amount", "AMOUNT", evidence="owner")
        manager.confirm(dataset_id, "Due", "DUE_DATE", evidence="owner")
        with self.assertRaises(OnboardingError) as raised:
            manager.confirm(dataset_id, "Status", "STATUS", evidence="owner",
                            value_mapping={"open": "OPEN"})
        self.assertEqual(raised.exception.code, "incomplete_value_mapping")

        cash, cash_id = self.onboard(
            "Date,Amount,Direction\n2026-01-01,5,out\n", "CASH_TRANSACTION",
            {"Date": "TRANSACTION_DATE", "Amount": "AMOUNT", "Direction": "CASH_DIRECTION"},
            mappings={"Direction": {"out": "OUTFLOW"}},
            qualifiers={"cash_amount_convention": "SIGNED_WITH_DIRECTION"},
        )
        states = {item["identifier"]: item["state"]
                  for item in cash.financial_analysis_readiness(cash_id)["operations"]}
        self.assertEqual(states["CASH_TRANSACTION_COUNT"], "SUPPORTED")
        self.assertEqual(states["CASH_OUTFLOW_SUMMARY"], "BLOCKED")
        self.assertEqual(self.execute(cash_id, "CASH_OUTFLOW_SUMMARY")["execution_status"],
                         "DATA_QUALITY_BLOCKER")
        evidence = self.execute(cash_id, "CASH_OUTFLOW_SUMMARY")["delegated_result"]
        self.assertEqual(evidence["errors"][0]["code"], "QUALITY_BLOCKER")

    def test_operation_readiness_revokes_and_recovers_without_affecting_summary(self):
        manager, dataset_id = self.onboard(
            "Amount,Due,Supplier\n10,2026-01-01,Alpha\n", "PAYABLE",
            {"Amount": "AMOUNT", "Due": "DUE_DATE", "Supplier": "SUPPLIER"},
        )
        manager.reject(dataset_id, "Supplier", evidence="Supplier mapping revoked")
        states = {item["identifier"]: item["state"]
                  for item in manager.financial_analysis_readiness(dataset_id)["operations"]}
        self.assertEqual(states["PAYABLE_SUMMARY"], "SUPPORTED")
        self.assertEqual(states["PAYABLE_BY_SUPPLIER"], "BLOCKED")
        manager.confirm(dataset_id, "Supplier", "SUPPLIER", evidence="Supplier mapping restored")
        restored = {item["identifier"]: item["state"]
                    for item in manager.financial_analysis_readiness(dataset_id)["operations"]}
        self.assertEqual(restored["PAYABLE_BY_SUPPLIER"], "SUPPORTED")

    def test_required_anchor_revocation_keeps_each_domain_catalog_and_recovers(self):
        fixtures = (
            ("PAYABLE", "Amount,Due\n10,2026-01-01\n",
             {"Amount": "AMOUNT", "Due": "DUE_DATE"}, "Amount", "PAYABLE_COUNT", {}, {}),
            ("RECEIVABLE", "Amount,Due\n10,2026-01-01\n",
             {"Amount": "AMOUNT", "Due": "DUE_DATE"}, "Due", "RECEIVABLE_COUNT", {}, {}),
            ("CASH_TRANSACTION", "Date,Amount,Direction\n2026-01-01,10,in\n",
             {"Date": "TRANSACTION_DATE", "Amount": "AMOUNT", "Direction": "CASH_DIRECTION"},
             "Date", "CASH_TRANSACTION_COUNT", {"Direction": {"in": "INFLOW"}},
             {"cash_amount_convention": "MAGNITUDE_WITH_DIRECTION"}),
        )
        for domain, text, roles, revoked_column, count_operation, mappings, qualifiers in fixtures:
            with self.subTest(domain=domain):
                manager, dataset_id = self.onboard(
                    text, domain, roles, mappings=mappings, qualifiers=qualifiers,
                )
                manager.reject(dataset_id, revoked_column, evidence="Anchor revoked")
                blocked = manager.financial_analysis_readiness(dataset_id)["operations"]
                self.assertEqual(len(blocked), 6)
                self.assertEqual({item["identifier"] for item in blocked},
                                 {item.value for item in DOMAIN_OPERATIONS[domain]})
                self.assertTrue(all(item["state"] == "BLOCKED" for item in blocked))
                manager.confirm(dataset_id, revoked_column, roles[revoked_column],
                                evidence="Anchor restored",
                                value_mapping=mappings.get(revoked_column))
                restored = {item["identifier"]: item["state"]
                            for item in manager.financial_analysis_readiness(dataset_id)["operations"]}
                self.assertEqual(restored[count_operation], "SUPPORTED")

    def test_missing_status_blocks_authoritative_aging_for_the_whole_dataset(self):
        manager, dataset_id = self.onboard(
            "Amount,Due,Status\n10,2026-01-01,open\n20,2026-01-02,\n", "PAYABLE",
            {"Amount": "AMOUNT", "Due": "DUE_DATE", "Status": "STATUS"},
            mappings={"Status": {"open": "OPEN"}},
            qualifiers={"amount_basis": "OUTSTANDING_BALANCE",
                        "dataset_reference_date": "2026-11-01"},
        )
        states = {item["identifier"]: item["state"]
                  for item in manager.financial_analysis_readiness(dataset_id)["operations"]}
        self.assertEqual(states["PAYABLE_SUMMARY"], "SUPPORTED")
        self.assertEqual(states["PAYABLE_AGING"], "BLOCKED")
        result = self.execute(dataset_id, "PAYABLE_AGING", as_of_date="2026-11-01")
        self.assertEqual(result["execution_status"], "DATA_QUALITY_BLOCKER")

    def test_malicious_labels_are_inert_and_arbitrary_operations_parameters_fail_closed(self):
        _manager, dataset_id = self.onboard(
            "Amount,Due,Supplier\n10,2026-01-01,'); DROP TABLE x; --\n"
            "20,2026-01-02,import os; os.system('rm -rf /')\n", "PAYABLE",
            {"Amount": "AMOUNT", "Due": "DUE_DATE", "Supplier": "SUPPLIER"},
        )
        grouped = self.execute(dataset_id, "PAYABLE_BY_SUPPLIER")["delegated_result"]
        self.assertEqual([item["key"]["value"] for item in grouped["result"]["groups"]],
                         ["'); DROP TABLE x; --", "import os; os.system('rm -rf /')"])
        unknown = self.execute(dataset_id, "SELECT * FROM payables")
        self.assertEqual(unknown["execution_status"], "UNSUPPORTED")
        misplaced = self.execute(dataset_id, "PAYABLE_SUMMARY", granularity="YEAR")
        self.assertEqual(misplaced["execution_status"], "INVALID_REQUEST")


if __name__ == "__main__":
    unittest.main()
