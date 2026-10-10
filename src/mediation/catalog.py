"""Closed, code-owned request catalog. The LLM selects a key; it never writes a request."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CatalogRequest:
    identifier: str
    capability: str
    text: str
    description: str


USER_TEXT = "USER_TEXT"
CAPABILITY_CLARIFICATION_REQUEST = "Check my financial data."

FA = "FINANCIAL_ANALYSIS"
AD = "ANOMALY_DETECTION"
FC = "CASH_FLOW_FORECASTING"
DR = "DOCUMENT_RETRIEVAL"

# Every text below is accepted by the existing English grammar and still passes
# fresh Step 18 routing, the registry and Step 13/anomaly validation.
REQUESTS = {entry.identifier: entry for entry in (
    CatalogRequest("RG_RECORD_COUNT", FA, "Receiver General record count",
                   "Number of Receiver General accounting records"),
    CatalogRequest("RG_AMOUNT_SUMMARY", FA, "Receiver General amount summary",
                   "Total, minimum and maximum of Receiver General accounting amounts"),
    CatalogRequest("RG_AMOUNT_BY_DEBIT_CREDIT", FA, "Receiver General amounts by debit/credit",
                   "Accounting amounts grouped by debit/credit code"),
    CatalogRequest("RG_AMOUNT_BY_VOUCHER_TYPE", FA, "Receiver General amounts by voucher type",
                   "Accounting amounts grouped by voucher type"),
    CatalogRequest("RG_AMOUNT_BY_DEPARTMENT", FA, "Receiver General amounts by department",
                   "Accounting amounts grouped by department"),
    CatalogRequest("RG_AMOUNT_BY_MONTH", FA, "Receiver General amounts by month",
                   "Accounting amounts grouped by calendar month of effective date"),
    CatalogRequest("RG_AMOUNT_BY_GENERAL_LEDGER_ACCOUNT", FA,
                   "Receiver General amounts by general ledger account",
                   "Accounting amounts grouped by general ledger account"),
    CatalogRequest("RG_HIGHEST_AMOUNTS", FA, "Receiver General highest amounts",
                   "The ten highest individual accounting amount records"),
    CatalogRequest("RG_LOWEST_AMOUNTS", FA, "Receiver General lowest amounts",
                   "The ten lowest individual accounting amount records"),
    CatalogRequest("CF_RECORD_COUNT", FA, "Company Financials record count",
                   "Number of Company Financials sales records"),
    CatalogRequest("CF_SALES_SUMMARY", FA, "Sales summary",
                   "Overall Sales summary for Company Financials"),
    CatalogRequest("CF_SALES_BY_COUNTRY", FA, "Total sales by country",
                   "Sales totals per country"),
    CatalogRequest("CF_SALES_BY_SEGMENT", FA, "Total sales by segment",
                   "Sales totals per segment"),
    CatalogRequest("CF_SALES_BY_PRODUCT", FA, "Total sales by product",
                   "Sales totals per product"),
    CatalogRequest("CF_SALES_BY_MONTH", FA, "Total sales by month",
                   "Sales totals per monthly label"),
    CatalogRequest("CF_PROFIT_SUMMARY", FA, "Profit summary",
                   "Profit total plus counts of negative, zero and positive Profit records"),
    CatalogRequest("CF_PROFIT_BY_COUNTRY", FA, "Profit by country",
                   "Profit totals per country"),
    CatalogRequest("CF_DISCOUNT_ANALYSIS", FA, "Discount analysis",
                   "Discount totals and coverage"),
    CatalogRequest("CF_DISCOUNTS_BY_BAND", FA, "Discounts by discount band",
                   "Discounts grouped by discount band"),
    CatalogRequest("CF_UNITS_SOLD_SUMMARY", FA, "Units sold summary",
                   "Summary of the Units Sold quantity"),
    CatalogRequest("SCREEN_RG_ACCOUNTING_AMOUNTS", AD, "Screen accounting amounts",
                   "Statistical screening of unusual Receiver General accounting amounts"),
    CatalogRequest("SCREEN_CF_SALES", AD, "Screen sales",
                   "Statistical screening of unusual Sales values"),
    CatalogRequest("SCREEN_CF_PROFIT", AD, "Screen profit",
                   "Statistical screening of unusual or strange Profit values"),
    CatalogRequest("CASH_FLOW_FORECAST", FC, "Forecast cash flow next month",
                   "Any forecast/prediction of cash, cash flow or future values, or treating sales as cash"),
    CatalogRequest("DOCUMENT_QUESTION", DR, "What does the invoice say?",
                   "Any question about invoices, contracts, statements or other documents"),
)}
