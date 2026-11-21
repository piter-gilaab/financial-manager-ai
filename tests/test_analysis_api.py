"""Closed multi-domain Financial Analysis and anomaly HTTP tests."""

from pathlib import Path
import tempfile
import unittest

from src.anomaly.dynamic import DynamicAnomalyRequest
from src.api import create_app
from src.api.serialization import to_json_safe
from src.execution import DynamicQueryParameters, DynamicQueryRequest
from src.manager import FinancialManagerAgent
from src.onboarding import OnboardingManager

from tests.api_support import AsgiClient
from tests.onboarding_support import write_csv


class AnalysisApiTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.root = self.base / "onboarding"
        self.ids = self._onboard_domains()
        self.client = AsgiClient(create_app(onboarding_root=self.root), timeout=10)

    def _onboard(self, filename, text, domain, roles, *, mappings=None, qualifiers=None):
        onboarding = OnboardingManager(self.root)
        dataset_id = onboarding.add(write_csv(self.base / filename, text))["dataset_id"]
        for column, role in roles.items():
            onboarding.confirm(
                dataset_id, column, role, evidence="Synthetic HTTP approval",
                value_mapping=(mappings or {}).get(column),
            )
        if qualifiers:
            onboarding.confirm_qualifiers(
                dataset_id, evidence="Synthetic HTTP qualifiers", **qualifiers,
            )
        onboarding.confirm_domain(dataset_id, domain, evidence="Synthetic HTTP domain")
        return dataset_id

    def _onboard_domains(self):
        sales_rows = ["Date,Sales,Profit,Country,Segment,Product,Discount,Units"]
        for value in range(30):
            sales_rows.append(f"2026-01-01,{value},{value},CA,S1,P1,0.1,2")
        sales_rows.append("2026-01-01,100,200,BR,S2,P2,0.2,3")
        sales = self._onboard(
            "sales.csv", "\n".join(sales_rows) + "\n", "SALES_RECORD",
            {"Date": "TRANSACTION_DATE", "Sales": "SALES", "Profit": "PROFIT",
             "Country": "COUNTRY", "Segment": "SEGMENT", "Product": "PRODUCT",
             "Discount": "DISCOUNT", "Units": "UNITS_SOLD"},
        )
        payable = self._onboard(
            "payable.csv",
            "Amount,Due,Supplier,Status,Currency\n100.00,2026-10-01,A,open,USD\n"
            "20.25,2026-11-01,B,settled,USD\n",
            "PAYABLE", {"Amount": "AMOUNT", "Due": "DUE_DATE", "Supplier": "SUPPLIER",
                        "Status": "STATUS", "Currency": "CURRENCY"},
            mappings={"Status": {"open": "OPEN", "settled": "SETTLED"},
                      "Currency": {"USD": "USD"}},
            qualifiers={"amount_basis": "OUTSTANDING_BALANCE",
                        "dataset_reference_date": "2026-11-01"},
        )
        receivable = self._onboard(
            "receivable.csv",
            "Amount,Due,Customer,Status\n12.1,2026-10-01,Alice,open\n"
            "0.2,2026-11-01,Bob,open\n",
            "RECEIVABLE", {"Amount": "AMOUNT", "Due": "DUE_DATE",
                           "Customer": "CUSTOMER", "Status": "STATUS"},
            mappings={"Status": {"open": "OPEN"}},
            qualifiers={"amount_basis": "OUTSTANDING_BALANCE",
                        "dataset_reference_date": "2026-11-01"},
        )
        cash = self._onboard(
            "cash.csv",
            "Date,Amount,Direction,Category,Account\n"
            "2026-01-01,0.1,in,Sales,Bank\n2026-01-02,0.2,out,Fees,Bank\n"
            "2026-02-01,-0.3,out,Fees,Cash\n",
            "CASH_TRANSACTION", {"Date": "TRANSACTION_DATE", "Amount": "AMOUNT",
                                 "Direction": "CASH_DIRECTION", "Category": "CATEGORY",
                                 "Account": "ACCOUNT"},
            mappings={"Direction": {"in": "INFLOW", "out": "OUTFLOW"}},
            qualifiers={"cash_amount_convention": "SIGNED_WITH_DIRECTION"},
        )
        return {"sales": sales, "payable": payable, "receivable": receivable, "cash": cash}

    def analysis(self, key, operation, parameters=None):
        return self.client.post("/api/v1/analysis", json={
            "dataset_id": self.ids[key], "operation": operation,
            "parameters": parameters or {},
        })

    def test_all_18_phase2_operations_are_reachable_through_closed_http_contract(self):
        operations = {
            "payable": (
                ("PAYABLE_COUNT", {}), ("PAYABLE_SUMMARY", {}),
                ("PAYABLE_BY_SUPPLIER", {}),
                ("PAYABLE_BY_DUE_PERIOD", {"granularity": "MONTH"}),
                ("PAYABLE_AGING", {"as_of_date": "2026-11-01"}),
                ("OVERDUE_PAYABLE_SUMMARY", {"as_of_date": "2026-11-01"}),
            ),
            "receivable": (
                ("RECEIVABLE_COUNT", {}), ("RECEIVABLE_SUMMARY", {}),
                ("RECEIVABLE_BY_CUSTOMER", {}),
                ("RECEIVABLE_BY_DUE_PERIOD", {"granularity": "YEAR"}),
                ("RECEIVABLE_AGING", {"as_of_date": "2026-11-01"}),
                ("OVERDUE_RECEIVABLE_SUMMARY", {"as_of_date": "2026-11-01"}),
            ),
            "cash": (
                ("CASH_TRANSACTION_COUNT", {}), ("CASH_INFLOW_SUMMARY", {}),
                ("CASH_OUTFLOW_SUMMARY", {}),
                ("NET_CASH_BY_PERIOD", {"granularity": "MONTH"}),
                ("CASH_BY_CATEGORY", {}), ("CASH_BY_ACCOUNT", {}),
            ),
        }
        reached = []
        for key, requests in operations.items():
            for operation, parameters in requests:
                with self.subTest(operation=operation):
                    response = self.analysis(key, operation, parameters)
                    self.assertEqual(response.status_code, 200, response.text)
                    self.assertIn(response.json()["status"], {"SUCCESS", "PARTIAL", "NO_DATA"})
                    self.assertEqual(
                        response.json()["evidence"]["delegated_result"]["query_name"], operation,
                    )
                    reached.append(operation)
        self.assertEqual(len(reached), 18)

    def test_sales_analysis_anomalies_and_manager_evidence_are_preserved(self):
        sales = self.analysis("sales", "SALES_SUMMARY")
        self.assertEqual(sales.status_code, 200)
        self.assertEqual(sales.json()["evidence"]["delegated_result"]["result"]["measures"]["sales"]["sum"],
                         "535")

        manager = FinancialManagerAgent(onboarding_root=self.root)
        direct = manager.execute_dataset_request(DynamicQueryRequest(
            self.ids["payable"], "PAYABLE_AGING",
            DynamicQueryParameters(as_of_date="2026-11-01"),
        ))
        api = self.analysis("payable", "PAYABLE_AGING", {"as_of_date": "2026-11-01"})
        self.assertEqual(api.json()["evidence"], to_json_safe(direct))

        for operation in ("SALES_ANOMALY_SCREEN", "PROFIT_ANOMALY_SCREEN"):
            response = self.client.post("/api/v1/anomalies", json={
                "dataset_id": self.ids["sales"], "operation": operation,
            })
            self.assertEqual(response.status_code, 200, response.text)
            evidence = response.json()["evidence"]["delegated_result"]
            self.assertEqual(evidence["result"]["scope"], "GLOBAL")
            self.assertNotIn("fraud_probability", response.text)
            direct_anomaly = manager.execute_dataset_anomaly_request(
                DynamicAnomalyRequest(self.ids["sales"], operation),
            )
            self.assertEqual(response.json()["evidence"], to_json_safe(direct_anomaly))

    def test_decimal_currency_coverage_limitations_and_lineage_round_trip(self):
        payable = self.analysis("payable", "PAYABLE_SUMMARY").json()["evidence"]
        self.assertEqual(payable["delegated_result"]["currency"]["status"], "CONFIRMED")
        self.assertEqual(payable["delegated_result"]["currency"]["code"], "USD")
        self.assertEqual(payable["delegated_result"]["result"]["measures"]["amount"]["sum"], "120.25")
        self.assertIn(
            "coverage", payable["delegated_result"]["result"]["measures"]["amount"],
        )
        self.assertIn("lineage", payable["delegated_result"]["metadata"])

        receivable = self.analysis("receivable", "RECEIVABLE_SUMMARY").json()["evidence"]
        self.assertEqual(receivable["delegated_result"]["currency"]["status"], "UNKNOWN")
        self.assertEqual(receivable["delegated_result"]["result"]["measures"]["amount"]["sum"], "12.3")
        self.assertIsInstance(receivable["delegated_result"]["result"]["measures"]["amount"]["sum"], str)

        net = self.analysis("cash", "NET_CASH_BY_PERIOD", {"granularity": "MONTH"}).json()["evidence"]
        self.assertEqual(net["delegated_result"]["currency"]["status"], "UNKNOWN")
        self.assertEqual(net["delegated_result"]["result"]["groups"][0]["net_cash"], "0.1")
        self.assertEqual(net["delegated_result"]["result"]["groups"][1]["net_cash"], "-0.3")
        self.assertTrue(net["limitations"])

    def test_blocked_and_malicious_requests_are_controlled_not_server_errors(self):
        mismatch = self.analysis("payable", "PAYABLE_AGING", {"as_of_date": "2026-10-01"})
        self.assertEqual(mismatch.status_code, 409)
        self.assertEqual(mismatch.json()["status"], "DATA_QUALITY_BLOCKER")
        self.assertEqual(mismatch.json()["errors"][0]["code"], "REFERENCE_DATE_MISMATCH")

        for extra in (
            {"sql": "SELECT * FROM x"}, {"column": "Amount"}, {"adapter": "evil"},
            {"formula": "__import__('os')"}, {"group_by": "supplier"},
        ):
            response = self.client.post("/api/v1/analysis", json={
                "dataset_id": self.ids["payable"], "operation": "PAYABLE_SUMMARY",
                "parameters": {}, **extra,
            })
            self.assertEqual(response.status_code, 422)
            self.assertNotIn("Traceback", response.text)

    def test_confirmed_multiple_currency_is_preserved_and_blocks_monetary_execution(self):
        dataset_id = self._onboard(
            "multiple.csv",
            "Amount,Due,Currency\n1,2026-01-01,USD\n2,2026-01-02,EUR\n",
            "PAYABLE", {"Amount": "AMOUNT", "Due": "DUE_DATE", "Currency": "CURRENCY"},
            mappings={"Currency": {"USD": "USD", "EUR": "EUR"}},
        )
        readiness = self.client.get(f"/api/v1/datasets/{dataset_id}/readiness")
        self.assertEqual(readiness.json()["data"]["currency"]["state"], "CONFIRMED_MULTIPLE")
        blocked = self.client.post("/api/v1/analysis", json={
            "dataset_id": dataset_id, "operation": "PAYABLE_SUMMARY", "parameters": {},
        })
        self.assertEqual(blocked.status_code, 409)
        self.assertEqual(blocked.json()["status"], "DATA_QUALITY_BLOCKER")
        self.assertEqual(
            blocked.json()["evidence"]["dataset_capability"]["currency"]["state"],
            "CONFIRMED_MULTIPLE",
        )


if __name__ == "__main__":
    unittest.main()
