export const OPERATIONS: Record<string, { label: string; parameters?: ("granularity" | "missing_dimension" | "as_of_date")[] }> = {
  SALES_RECORD_COUNT: { label: "Sales record count" },
  SALES_SUMMARY: { label: "Sales summary" },
  SALES_BY_COUNTRY: { label: "Sales by country", parameters: ["missing_dimension"] },
  SALES_BY_PERIOD: { label: "Sales by period", parameters: ["granularity"] },
  SALES_BY_SEGMENT: { label: "Sales by segment", parameters: ["missing_dimension"] },
  SALES_BY_PRODUCT: { label: "Sales by product", parameters: ["missing_dimension"] },
  PROFIT_SUMMARY: { label: "Profit summary" },
  DISCOUNT_ANALYSIS: { label: "Discount analysis" },
  UNITS_SOLD_SUMMARY: { label: "Units sold summary" },
  PAYABLE_COUNT: { label: "Payable count" },
  PAYABLE_SUMMARY: { label: "Payable summary" },
  PAYABLE_BY_SUPPLIER: { label: "By supplier", parameters: ["missing_dimension"] },
  PAYABLE_BY_DUE_PERIOD: { label: "By due period", parameters: ["granularity", "missing_dimension"] },
  PAYABLE_AGING: { label: "Payable aging", parameters: ["as_of_date"] },
  OVERDUE_PAYABLE_SUMMARY: { label: "Overdue payable summary", parameters: ["as_of_date"] },
  RECEIVABLE_COUNT: { label: "Receivable count" },
  RECEIVABLE_SUMMARY: { label: "Receivable summary" },
  RECEIVABLE_BY_CUSTOMER: { label: "By customer", parameters: ["missing_dimension"] },
  RECEIVABLE_BY_DUE_PERIOD: { label: "By due period", parameters: ["granularity", "missing_dimension"] },
  RECEIVABLE_AGING: { label: "Receivable aging", parameters: ["as_of_date"] },
  OVERDUE_RECEIVABLE_SUMMARY: { label: "Overdue receivable summary", parameters: ["as_of_date"] },
  CASH_TRANSACTION_COUNT: { label: "Cash transaction count" },
  CASH_INFLOW_SUMMARY: { label: "Cash inflow summary" },
  CASH_OUTFLOW_SUMMARY: { label: "Cash outflow summary" },
  NET_CASH_BY_PERIOD: { label: "Net cash by period", parameters: ["granularity", "missing_dimension"] },
  CASH_BY_CATEGORY: { label: "Cash by category", parameters: ["missing_dimension"] },
  CASH_BY_ACCOUNT: { label: "Cash by account", parameters: ["missing_dimension"] },
};

export const EXECUTABLE_DOMAINS = ["SALES_RECORD", "PAYABLE", "RECEIVABLE", "CASH_TRANSACTION"] as const;
export const operationIsExecutable = (state: string) => state === "SUPPORTED" || state === "READY";
export const SEMANTIC_ROLES = [
  "TRANSACTION_DATE", "POSTING_DATE", "DUE_DATE", "AMOUNT", "CURRENCY", "DESCRIPTION", "ACCOUNT",
  "CATEGORY", "DEBIT_CREDIT_INDICATOR", "VOUCHER_TYPE", "DEPARTMENT", "ENTITY", "COUNTRY", "SEGMENT", "PRODUCT", "UNITS_SOLD", "SALES",
  "PROFIT", "DISCOUNT", "GROSS_SALES", "COGS", "SALE_PRICE", "MANUFACTURING_PRICE", "INVOICE_ID",
  "SUPPLIER", "STATUS", "ACTUAL_BUDGET_INDICATOR", "CASH_DIRECTION", "BALANCE", "CUSTOMER",
] as const;
