"""Phase 2 persisted execution through onboarding, readiness and Manager."""

from pathlib import Path
import tempfile
import unittest

from src.execution import DynamicQueryParameters, DynamicQueryRequest
from src.manager import FinancialManagerAgent
from src.onboarding import OnboardingManager

from tests.onboarding_support import write_csv, write_xlsx


class MultiDomainExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.root = self.base / "onboarding"

    def onboard(self, name, text, domain, roles, *, value_mappings=None, qualifiers=None):
        manager = OnboardingManager(self.root)
        state = manager.add(write_csv(self.base / name, text))
        dataset_id = state["dataset_id"]
        for column, role in roles.items():
            manager.confirm(
                dataset_id, column, role, evidence="Synthetic Phase 2 approval",
                value_mapping=(value_mappings or {}).get(column),
            )
        if qualifiers:
            manager.confirm_qualifiers(
                dataset_id, evidence="Synthetic Phase 2 qualifier approval", **qualifiers,
            )
        return manager, manager.confirm_domain(
            dataset_id, domain, evidence="Synthetic Phase 2 domain approval",
        )

    def execute(self, dataset_id, operation, **parameters):
        return FinancialManagerAgent(onboarding_root=self.root).execute_dataset_request(
            DynamicQueryRequest(
                dataset_id, operation, DynamicQueryParameters(**parameters),
            )
        )

    def test_payable_all_six_operations_and_operation_specific_readiness(self):
        manager, state = self.onboard(
            "payables.csv",
            "Amount,Due,Supplier,Status,Currency\n"
            "100.00,2026-10-01,Alpha,open,USD\n"
            "50.00,2026-11-01,,open,USD\n"
            "25.00,2026-01-01,Beta,paid,USD\n"
            "-5.00,invalid,Gamma,cancelled,USD\n",
            "PAYABLE",
            {"Amount": "AMOUNT", "Due": "DUE_DATE", "Supplier": "SUPPLIER",
             "Status": "STATUS", "Currency": "CURRENCY"},
            value_mappings={
                "Status": {"open": "OPEN", "paid": "SETTLED", "cancelled": "CANCELLED"},
                "Currency": {"USD": "USD"},
            },
            qualifiers={
                "amount_basis": "OUTSTANDING_BALANCE",
                "dataset_reference_date": "2026-11-01",
            },
        )
        dataset_id = state["dataset_id"]
        readiness = manager.financial_analysis_readiness(dataset_id)
        self.assertEqual(
            {item["identifier"]: item["state"] for item in readiness["operations"]},
            {name: "SUPPORTED" for name in (
                "PAYABLE_COUNT", "PAYABLE_SUMMARY", "PAYABLE_BY_SUPPLIER",
                "PAYABLE_BY_DUE_PERIOD", "PAYABLE_AGING", "OVERDUE_PAYABLE_SUMMARY",
            )},
        )
        count = self.execute(dataset_id, "PAYABLE_COUNT")
        summary = self.execute(dataset_id, "PAYABLE_SUMMARY")
        supplier = self.execute(dataset_id, "PAYABLE_BY_SUPPLIER")
        period = self.execute(dataset_id, "PAYABLE_BY_DUE_PERIOD", granularity="MONTH")
        aging = self.execute(dataset_id, "PAYABLE_AGING", as_of_date="2026-11-01")
        overdue = self.execute(dataset_id, "OVERDUE_PAYABLE_SUMMARY", as_of_date="2026-11-01")

        self.assertEqual(count["delegated_result"]["result"]["record_count"], 4)
        self.assertEqual(summary["delegated_result"]["result"]["measures"]["amount"]["sum"], "170.00")
        self.assertIsNone(supplier["delegated_result"]["result"]["groups"][-1]["key"]["value"])
        self.assertEqual(period["delegated_result"]["result"]["groups"][-1]["key"]["kind"], "unavailable")
        self.assertEqual(aging["delegated_result"]["result"]["eligible_open_record_count"], 2)
        self.assertEqual(overdue["delegated_result"]["result"]["overdue_balance"]["sum"], "100.00")
        self.assertEqual(summary["delegated_result"]["currency"]["code"], "USD")

        mismatch = self.execute(dataset_id, "PAYABLE_AGING", as_of_date="2026-10-01")
        self.assertEqual(mismatch["execution_status"], "DATA_QUALITY_BLOCKER")
        self.assertEqual(mismatch["errors"][0]["code"], "REFERENCE_DATE_MISMATCH")

    def test_receivable_customer_is_distinct_and_all_six_execute(self):
        manager, state = self.onboard(
            "receivables.csv",
            "Value,DueDate,CustomerName,State\n"
            "20,2026-10-01,Alice,open\n"
            "30,2026-11-01,Bob,open\n",
            "RECEIVABLE",
            {"Value": "AMOUNT", "DueDate": "DUE_DATE", "CustomerName": "CUSTOMER",
             "State": "STATUS"},
            value_mappings={"State": {"open": "OPEN"}},
            qualifiers={"amount_basis": "OUTSTANDING_BALANCE",
                        "dataset_reference_date": "2026-11-01"},
        )
        dataset_id = state["dataset_id"]
        operations = (
            ("RECEIVABLE_COUNT", {}), ("RECEIVABLE_SUMMARY", {}),
            ("RECEIVABLE_BY_CUSTOMER", {}),
            ("RECEIVABLE_BY_DUE_PERIOD", {"granularity": "YEAR"}),
            ("RECEIVABLE_AGING", {"as_of_date": "2026-11-01"}),
            ("OVERDUE_RECEIVABLE_SUMMARY", {"as_of_date": "2026-11-01"}),
        )
        for operation, parameters in operations:
            with self.subTest(operation=operation):
                self.assertIn(self.execute(dataset_id, operation, **parameters)["execution_status"],
                              {"SUCCESS", "PARTIAL", "NO_DATA"})
        grouped = self.execute(dataset_id, "RECEIVABLE_BY_CUSTOMER")
        self.assertEqual([item["key"]["value"] for item in grouped["delegated_result"]["result"]["groups"]],
                         ["Alice", "Bob"])

    def test_cash_all_six_operations_signed_convention_and_no_sign_inference(self):
        manager, state = self.onboard(
            "cash.csv",
            "When,Value,Flow,Category,Account\n"
            "2026-01-01,100,in,Sales,Bank\n"
            "2026-01-02,-40,out,Fees,Bank\n"
            "2026-02-01,10,in,Sales,Cash\n",
            "CASH_TRANSACTION",
            {"When": "TRANSACTION_DATE", "Value": "AMOUNT", "Flow": "CASH_DIRECTION",
             "Category": "CATEGORY", "Account": "ACCOUNT"},
            value_mappings={"Flow": {"in": "INFLOW", "out": "OUTFLOW"}},
            qualifiers={"cash_amount_convention": "SIGNED_WITH_DIRECTION"},
        )
        dataset_id = state["dataset_id"]
        requests = (
            ("CASH_TRANSACTION_COUNT", {}), ("CASH_INFLOW_SUMMARY", {}),
            ("CASH_OUTFLOW_SUMMARY", {}),
            ("NET_CASH_BY_PERIOD", {"granularity": "MONTH"}),
            ("CASH_BY_CATEGORY", {}), ("CASH_BY_ACCOUNT", {}),
        )
        for operation, parameters in requests:
            with self.subTest(operation=operation):
                self.assertIn(self.execute(dataset_id, operation, **parameters)["execution_status"],
                              {"SUCCESS", "PARTIAL"})
        net = self.execute(dataset_id, "NET_CASH_BY_PERIOD", granularity="MONTH")
        self.assertEqual(
            [(item["key"]["value"], item["net_cash"])
             for item in net["delegated_result"]["result"]["groups"]],
            [("2026-01", "60"), ("2026-02", "10")],
        )
        for group in net["delegated_result"]["result"]["groups"]:
            self.assertIn("coverage", group)
            for measure in group["measures"].values():
                self.assertIn("coverage", measure)
        outflow = self.execute(dataset_id, "CASH_OUTFLOW_SUMMARY")
        self.assertEqual(outflow["delegated_result"]["result"]["measures"]["outflow"]["sum"], "40")
        cash_lineage = outflow["delegated_result"]["metadata"]["lineage"]["records"]
        self.assertEqual(cash_lineage[1]["source_amount"], "-40")
        self.assertEqual(cash_lineage[1]["mapped_cash_direction"], "OUTFLOW")

    def test_constrained_xlsx_reaches_each_new_domain_through_persisted_execution(self):
        fixtures = (
            ("PAYABLE", [["Amount", "Due"], ["10", "2026-01-01"]],
             {"Amount": "AMOUNT", "Due": "DUE_DATE"}, "PAYABLE_SUMMARY", {}),
            ("RECEIVABLE", [["Amount", "Due"], ["20", "2026-01-01"]],
             {"Amount": "AMOUNT", "Due": "DUE_DATE"}, "RECEIVABLE_SUMMARY", {}),
            ("CASH_TRANSACTION", [["Date", "Amount", "Direction"],
                                  ["2026-01-01", "30", "in"]],
             {"Date": "TRANSACTION_DATE", "Amount": "AMOUNT", "Direction": "CASH_DIRECTION"},
             "CASH_INFLOW_SUMMARY", {"Direction": {"in": "INFLOW"}}),
        )
        for index, (domain, rows, roles, operation, mappings) in enumerate(fixtures):
            with self.subTest(domain=domain):
                path = write_xlsx(self.base / f"domain-{index}.xlsx", sheets={"Data": rows})
                onboarding = OnboardingManager(self.root)
                dataset_id = onboarding.add(path)["dataset_id"]
                for column, role in roles.items():
                    onboarding.confirm(
                        dataset_id, column, role, evidence="Synthetic XLSX approval",
                        value_mapping=mappings.get(column),
                    )
                if domain == "CASH_TRANSACTION":
                    onboarding.confirm_qualifiers(
                        dataset_id, evidence="Synthetic XLSX qualifier",
                        cash_amount_convention="MAGNITUDE_WITH_DIRECTION",
                    )
                onboarding.confirm_domain(dataset_id, domain, evidence="Synthetic XLSX domain")
                self.assertIn(self.execute(dataset_id, operation)["execution_status"],
                              {"SUCCESS", "PARTIAL"})


if __name__ == "__main__":
    unittest.main()
