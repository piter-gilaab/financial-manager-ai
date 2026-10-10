"""Synthetic Phase 13 fixtures used through the public onboarding interface."""

from pathlib import Path

from src.onboarding import OnboardingManager

from tests.onboarding_support import write_csv


def onboard_sales(root: Path, csv_text: str, *, mappings: dict[str, str] | None = None,
                  currency_values: dict[str, str] | None = None):
    source = write_csv(root / "sales.csv", csv_text)
    manager = OnboardingManager(root / "onboarding")
    state = manager.add(source)
    dataset_id = state["dataset_id"]
    roles = mappings or {"date": "TRANSACTION_DATE", "sales": "SALES"}
    for column, role in roles.items():
        options = {}
        if role == "CURRENCY":
            options["value_mapping"] = currency_values
        manager.confirm(
            dataset_id, column, role, evidence="Synthetic fixture approval", **options,
        )
    final = manager.confirm_domain(
        dataset_id, "SALES_RECORD", evidence="Synthetic fixture domain approval",
    )
    return manager, final
