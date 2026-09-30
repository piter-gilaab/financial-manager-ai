"""Closed registry of the seventeen approved version-1.0 contracts."""

from dataclasses import dataclass


RG = "receiver_general"
CF = "company_financials"
FIELDS = {
    RG: {
        "effective_date": "accounting_effective_date", "fiscal_year": "fiscal_year",
        "fiscal_month": "fiscal_month", "debit_credit": "credit_debit_code",
        "voucher_type": "journal_voucher_type_code", "department": "department_number",
        "general_ledger_account": "general_ledger_account_code",
        "subledger_account": "subledger_account_identifier",
        "financial_coding_block": "financial_coding_block", "control_data_type": "control_data_type",
        "accounting_amount": "journal_voucher_item_amount",
    },
    CF: {name: name for name in (
        "country", "segment", "product", "discount_band", "gross_sales", "discounts",
        "sales", "cogs", "profit", "units_sold") } | {"period": "period_date"},
}
FILTERS = {
    RG: tuple(k for k in FIELDS[RG] if k not in ("effective_date", "accounting_amount")),
    CF: ("country", "segment", "product", "discount_band"),
}
DATES = {RG: "effective_date", CF: "period"}
SALES_MEASURES = ("gross_sales", "discounts", "sales", "cogs", "profit")
STATS = ("count", "sum", "mean", "median", "min", "max")
DIMENSIONS = ("general_ledger_account", "subledger_account", "financial_coding_block", "control_data_type")


@dataclass(frozen=True)
class Contract:
    dataset: str
    kind: str
    measures: tuple = ()
    group: str | None = None
    options: tuple = ()


CONTRACTS = {
    "receiver_general_record_count": Contract(RG, "count"),
    "receiver_general_amount_summary": Contract(RG, "summary", ("accounting_amount",), options=("statistics",)),
    "receiver_general_amount_by_debit_credit": Contract(RG, "group", ("accounting_amount",), "debit_credit", ("missing_dimension",)),
    "receiver_general_amount_by_voucher_type": Contract(RG, "group", ("accounting_amount",), "voucher_type", ("missing_dimension",)),
    "receiver_general_amount_by_department": Contract(RG, "group", ("accounting_amount",), "department", ("missing_dimension",)),
    "receiver_general_amount_by_period": Contract(RG, "group", ("accounting_amount",), "effective_date", ("missing_dimension", "granularity")),
    "receiver_general_accounting_dimension_summary": Contract(RG, "group", ("accounting_amount",), options=("missing_dimension", "group_by")),
    "receiver_general_extreme_amount_records": Contract(RG, "extreme", ("accounting_amount",), options=("direction", "limit")),
    "company_financials_record_count": Contract(CF, "count"),
    "company_financials_sales_summary": Contract(CF, "summary", options=("measures", "statistics")),
    "company_financials_sales_by_period": Contract(CF, "group", group="period", options=("measures", "granularity", "missing_dimension")),
    "company_financials_sales_by_country": Contract(CF, "group", group="country", options=("measures", "missing_dimension")),
    "company_financials_sales_by_segment": Contract(CF, "group", group="segment", options=("measures", "missing_dimension")),
    "company_financials_sales_by_product": Contract(CF, "group", group="product", options=("measures", "missing_dimension")),
    "company_financials_profit_summary": Contract(CF, "profit", ("profit",)),
    "company_financials_discount_analysis": Contract(CF, "discount", ("discounts",), options=("group_by", "missing_dimension")),
    "company_financials_units_sold_summary": Contract(CF, "summary", ("units_sold",), options=("statistics",)),
}
