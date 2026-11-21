"""Phase 2 bounded conversational integration for the three new domains."""

from pathlib import Path
import tempfile
import unittest

from src.manager import FinancialManagerAgent, FinancialManagerSession
from src.mediation import ConversationMediator
from src.mediation.validation import validate_natural_response
from src.onboarding import OnboardingManager

from tests.mediation_support import ScriptedLLM
from tests.onboarding_support import write_csv


def phase2_intent(operation, **values):
    payload = {
        "version": "1.2", "operation": operation, "intent": None,
        "capability_hint": None, "clarification_answer": None,
        "clarification_kind": None, "evidence_reference": None,
        "follow_up_intent": None, "presentation_hint": None,
        "response_language": "en", "dataset_id": None,
        "dynamic_operation": None, "period_granularity": None,
        "missing_dimension": None, "as_of_date": None,
    }
    payload.update(values)
    return payload


def grounded(packet):
    return {
        "message": "The authoritative evidence is shown below.",
        "used_fact_ids": [packet["facts"][0]["id"]],
        "warning_fact_ids": [],
        "presentation_hint": packet["default_presentation"],
        "language": packet["language"],
    }


class ConversationalMultiDomainTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.root = self.base / "onboarding"

    def onboard(self, filename, text, domain, roles, mappings=None, qualifiers=None):
        onboarding = OnboardingManager(self.root)
        dataset_id = onboarding.add(write_csv(self.base / filename, text))["dataset_id"]
        for column, role in roles.items():
            onboarding.confirm(
                dataset_id, column, role, evidence="Synthetic conversation approval",
                value_mapping=(mappings or {}).get(column),
            )
        if qualifiers:
            onboarding.confirm_qualifiers(
                dataset_id, evidence="Synthetic conversation qualifiers", **qualifiers,
            )
        onboarding.confirm_domain(dataset_id, domain, evidence="Synthetic domain approval")
        return dataset_id

    def mediator(self, scripts):
        session = FinancialManagerSession(
            manager=FinancialManagerAgent(onboarding_root=self.root),
        )
        return ConversationMediator(session, ScriptedLLM(scripts, respond=grounded).provider)

    def test_payable_language_selection_grouping_aging_and_missing_date_clarification(self):
        dataset_id = self.onboard(
            "payable.csv", "Amount,Due,Supplier,Status\n10,2026-10-01,A,open\n",
            "PAYABLE", {"Amount": "AMOUNT", "Due": "DUE_DATE",
                        "Supplier": "SUPPLIER", "Status": "STATUS"},
            mappings={"Status": {"open": "OPEN"}},
            qualifiers={"amount_basis": "OUTSTANDING_BALANCE",
                        "dataset_reference_date": "2026-11-01"},
        )
        select = f"Use dataset {dataset_id}."
        scripts = {
            select: phase2_intent("SELECT_DYNAMIC_DATASET", dataset_id=dataset_id),
            "Show payables by supplier.": phase2_intent(
                "DYNAMIC_FINANCIAL_ANALYSIS", dynamic_operation="PAYABLE_BY_SUPPLIER",
                capability_hint="FINANCIAL_ANALYSIS",
            ),
            "Show payable aging as of 2026-11-01.": phase2_intent(
                "DYNAMIC_FINANCIAL_ANALYSIS", dynamic_operation="PAYABLE_AGING",
                as_of_date="2026-11-01", capability_hint="FINANCIAL_ANALYSIS",
            ),
            "Show overdue payables.": phase2_intent(
                "DYNAMIC_FINANCIAL_ANALYSIS", dynamic_operation="OVERDUE_PAYABLE_SUMMARY",
                capability_hint="FINANCIAL_ANALYSIS",
            ),
        }
        mediator = self.mediator(scripts)
        self.assertEqual(mediator.handle(select).outcome["status"], "DATASET_SELECTED")
        self.assertIn(mediator.handle("Show payables by supplier.").outcome["status"],
                      {"SUCCESS", "PARTIAL"})
        self.assertIn(mediator.handle("Show payable aging as of 2026-11-01.").outcome["status"],
                      {"SUCCESS", "PARTIAL"})
        missing = mediator.handle("Show overdue payables.")
        self.assertEqual(missing.outcome["status"], "CLARIFICATION_REQUIRED")
        self.assertEqual(missing.outcome["error"]["code"], "as_of_date_required")

    def test_receivable_and_cash_followups_stay_within_the_selected_domain(self):
        receivable_id = self.onboard(
            "receivable.csv", "Amount,Due,Customer,Status\n12,2026-10-01,Alice,open\n",
            "RECEIVABLE", {"Amount": "AMOUNT", "Due": "DUE_DATE",
                           "Customer": "CUSTOMER", "Status": "STATUS"},
            mappings={"Status": {"open": "OPEN"}},
            qualifiers={"amount_basis": "OUTSTANDING_BALANCE",
                        "dataset_reference_date": "2026-11-01"},
        )
        cash_id = self.onboard(
            "cash.csv", "Date,Amount,Direction,Category,Account\n"
            "2026-01-01,20,in,Sales,Bank\n2026-01-02,5,out,Fee,Bank\n",
            "CASH_TRANSACTION", {"Date": "TRANSACTION_DATE", "Amount": "AMOUNT",
                                 "Direction": "CASH_DIRECTION", "Category": "CATEGORY",
                                 "Account": "ACCOUNT"},
            mappings={"Direction": {"in": "INFLOW", "out": "OUTFLOW"}},
            qualifiers={"cash_amount_convention": "MAGNITUDE_WITH_DIRECTION"},
        )
        receivable_select = f"Use dataset {receivable_id}."
        receivable = self.mediator({
            receivable_select: phase2_intent("SELECT_DYNAMIC_DATASET", dataset_id=receivable_id),
            "Show receivables by customer.": phase2_intent(
                "DYNAMIC_FINANCIAL_ANALYSIS", dynamic_operation="RECEIVABLE_BY_CUSTOMER",
                capability_hint="FINANCIAL_ANALYSIS",
            ),
        })
        receivable.handle(receivable_select)
        self.assertIn(receivable.handle("Show receivables by customer.").outcome["status"],
                      {"SUCCESS", "PARTIAL"})

        cash_select = f"Use dataset {cash_id}."
        cash = self.mediator({
            cash_select: phase2_intent("SELECT_DYNAMIC_DATASET", dataset_id=cash_id),
            "Show net cash by month.": phase2_intent(
                "DYNAMIC_FINANCIAL_ANALYSIS", dynamic_operation="NET_CASH_BY_PERIOD",
                period_granularity="MONTH", capability_hint="FINANCIAL_ANALYSIS",
            ),
            "Now by account.": phase2_intent(
                "DYNAMIC_FINANCIAL_ANALYSIS", dynamic_operation="CASH_BY_ACCOUNT",
                capability_hint="FINANCIAL_ANALYSIS",
            ),
        })
        cash.handle(cash_select)
        net = cash.handle("Show net cash by month.")
        account = cash.handle("Now by account.")
        self.assertIn(net.outcome["status"], {"SUCCESS", "PARTIAL"})
        self.assertIn(account.outcome["status"], {"SUCCESS", "PARTIAL"})
        self.assertEqual(account.outcome["result"]["delegated_result"]["query_name"],
                         "CASH_BY_ACCOUNT")

    def test_grounding_allows_observed_cash_language_only_with_cash_facts(self):
        packet = {
            "facts": [{"id": "F1", "label": "net cash sum", "value": "15",
                       "semantic_type": "sum"}],
            "warnings": [], "allowed_presentations": ["TEXT"], "language": "en",
        }
        response = {
            "message": "Observed net cash is 15.", "used_fact_ids": ["F1"],
            "warning_fact_ids": [], "presentation_hint": "TEXT", "language": "en",
        }
        import json
        accepted = validate_natural_response(json.dumps(response), packet)
        self.assertEqual(accepted.message, "Observed net cash is 15.")


if __name__ == "__main__":
    unittest.main()
