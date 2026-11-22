"""Run an isolated real FastAPI slice with synthetic Phase 4 datasets."""

from pathlib import Path
from tempfile import TemporaryDirectory
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import uvicorn  # noqa: E402

from src.api import create_app  # noqa: E402
from src.onboarding import OnboardingManager  # noqa: E402
from tests.onboarding_support import write_csv, write_xlsx  # noqa: E402


def confirm(manager, dataset_id, column, role, *, value_mapping=None, date_format=None):
    manager.confirm(
        dataset_id, column, role, evidence="Synthetic Phase 4 E2E fixture",
        value_mapping=value_mapping, date_format=date_format,
    )


def seed(manager: OnboardingManager, sources: Path):
    sales_rows = ["Date,Sales,Profit,Country,Segment,Product,Units,Discount"]
    for index in range(30):
        sales_rows.append(f"2026-01-{(index % 28) + 1:02d},{index},{index - 5},BRL,Institutional,Product A,{index + 1},0.10")
    sales_rows.append("2026-02-01,1000,900,BRL,Institutional,Product B,2,0.20")
    sales_id = manager.add(write_csv(sources / "e2e_sales.csv", "\n".join(sales_rows) + "\n"))["dataset_id"]
    for column, role in (("Date", "TRANSACTION_DATE"), ("Sales", "SALES"), ("Profit", "PROFIT"), ("Country", "COUNTRY"), ("Segment", "SEGMENT"), ("Product", "PRODUCT"), ("Units", "UNITS_SOLD"), ("Discount", "DISCOUNT")):
        confirm(manager, sales_id, column, role, date_format="YYYY-MM-DD" if role == "TRANSACTION_DATE" else None)
    manager.confirm_domain(sales_id, "SALES_RECORD", evidence="Synthetic Phase 4 E2E fixture")

    payable_id = manager.add(write_csv(sources / "e2e_payables.csv", "Supplier,Amount,Due,Status\nVendor A,10.50,2026-10-01,open\nVendor B,20.00,2026-11-15,open\n"))["dataset_id"]
    confirm(manager, payable_id, "Supplier", "SUPPLIER")
    confirm(manager, payable_id, "Amount", "AMOUNT")
    confirm(manager, payable_id, "Due", "DUE_DATE", date_format="YYYY-MM-DD")
    confirm(manager, payable_id, "Status", "STATUS", value_mapping={"open": "OPEN"})
    manager.confirm_qualifiers(payable_id, evidence="Synthetic Phase 4 E2E fixture", amount_basis="OUTSTANDING_BALANCE", dataset_reference_date="2026-11-01")
    manager.confirm_domain(payable_id, "PAYABLE", evidence="Synthetic Phase 4 E2E fixture")

    receivable_id = manager.add(write_csv(sources / "e2e_receivables.csv", "Customer,Amount,Due,Status\nCustomer A,12.30,2026-10-15,open\nCustomer B,4.20,2026-12-01,open\n"))["dataset_id"]
    confirm(manager, receivable_id, "Customer", "CUSTOMER")
    confirm(manager, receivable_id, "Amount", "AMOUNT")
    confirm(manager, receivable_id, "Due", "DUE_DATE", date_format="YYYY-MM-DD")
    confirm(manager, receivable_id, "Status", "STATUS", value_mapping={"open": "OPEN"})
    manager.confirm_qualifiers(receivable_id, evidence="Synthetic Phase 4 E2E fixture", amount_basis="OUTSTANDING_BALANCE", dataset_reference_date="2026-11-01")
    manager.confirm_domain(receivable_id, "RECEIVABLE", evidence="Synthetic Phase 4 E2E fixture")

    cash_id = manager.add(write_csv(sources / "e2e_cash.csv", "Date,Amount,Direction,Category,Account\n2026-01-01,10.50,in,Operations,Main\n2026-02-01,2.25,out,Supplies,Main\n"))["dataset_id"]
    confirm(manager, cash_id, "Date", "TRANSACTION_DATE", date_format="YYYY-MM-DD")
    confirm(manager, cash_id, "Amount", "AMOUNT")
    confirm(manager, cash_id, "Direction", "CASH_DIRECTION", value_mapping={"in": "INFLOW", "out": "OUTFLOW"})
    confirm(manager, cash_id, "Category", "CATEGORY")
    confirm(manager, cash_id, "Account", "ACCOUNT")
    manager.confirm_qualifiers(cash_id, evidence="Synthetic Phase 4 E2E fixture", cash_amount_convention="MAGNITUDE_WITH_DIRECTION")
    manager.confirm_domain(cash_id, "CASH_TRANSACTION", evidence="Synthetic Phase 4 E2E fixture")


if __name__ == "__main__":
    fixture_root = Path("/tmp/financial-manager-phase4-e2e")
    fixture_root.mkdir(parents=True, exist_ok=True)
    write_xlsx(fixture_root / "multisheet.xlsx", sheets={
        "January": [["Date", "Sales"], ["2026-01-01", "10"]],
        "February": [["Date", "Sales"], ["2026-02-01", "20"]],
    })
    with TemporaryDirectory(prefix="financial-manager-phase4-api-") as temporary:
        base = Path(temporary)
        onboarding = base / "onboarding"
        seed(OnboardingManager(onboarding), base)
        uvicorn.run(
            create_app(onboarding_root=onboarding, cors_origins=("http://127.0.0.1:3000",)),
            host="127.0.0.1", port=8000,
        )
