import { humanize } from "./format";

const DOMAIN_LABELS: Record<string, string> = {
  SALES_RECORD: "Sales records",
  PAYABLE: "Accounts payable",
  RECEIVABLE: "Accounts receivable",
  CASH_TRANSACTION: "Cash transactions",
  UNCONFIRMED: "Not confirmed",
};

const REASON_LABELS: Record<string, string> = {
  MISSING_REQUIRED_SEMANTICS: "Required financial meaning is not confirmed.",
  "Binding validation returned MISSING_REQUIRED_SEMANTICS.": "Required financial meaning is not confirmed.",
  BINDING_VALIDATION_RETURNED_MISSING_REQUIRED_SEMANTICS: "Required financial meaning is not confirmed.",
  binding_validation_returned_missing_required_semantics: "Required financial meaning is not confirmed.",
  missing_confirmed_profit: "Profit meaning is not confirmed.",
  insufficient_numeric_records: "There are not enough usable numeric records.",
  missing_dataset_reference_date: "The dataset reference date is not confirmed.",
  missing_amount_basis: "The amount basis is not confirmed.",
  missing_cash_amount_convention: "The cash amount convention is not confirmed.",
  BLOCKED_NOT_IMPLEMENTED: "This capability is outside the implemented catalog.",
};

const LIMITATION_LABELS: Record<string, string> = {
  "The Step 13 agent supports a bounded question grammar and 17 approved contracts.": "This result follows the approved operation contract for the selected dataset.",
  "Source currency, grain and provenance limitations remain in the tool evidence.": "Source currency, data grain and provenance limitations remain applicable.",
  "Only GLOBAL screening under tukey_iqr v1.0 is supported.": "Screening uses one global statistical range across the selected measure.",
  "IQR screening supports RG accounting amount and CF Sales/Profit with the existing fixed peer policies.": "Range screening is limited to the approved accounting-amount and Sales/Profit measures.",
  "CANDIDATE means a screening candidate requiring investigation; NOT_SELECTED is not a validity finding.": "A review candidate requires investigation; records not selected by the screen are not validated.",
  "NOT_ASSESSED remains an abstention. Currency and comparability remain unresolved.": "Unassessed records remain outside the screening result. Currency and comparability may remain unresolved.",
};

const STATUS_LABELS: Record<string, string> = {
  SUPPORTED: "Ready",
  READY: "Ready",
  SUCCESS: "Complete",
  PARTIAL: "Complete with limitations",
  BLOCKED: "Blocked",
  NEEDS_CONFIRMATION: "Needs confirmation",
  CLARIFICATION_REQUIRED: "Needs confirmation",
  DATA_QUALITY_BLOCKER: "Blocked by data quality",
  NO_DATA: "No applicable data",
  UNSUPPORTED: "Not supported",
  CANDIDATE: "Review candidate",
};

export function displayDomain(value?: string | null): string {
  return DOMAIN_LABELS[value || "UNCONFIRMED"] || humanize(value || "UNCONFIRMED");
}

export function displayReason(value: string): string {
  return REASON_LABELS[value] || `${humanize(value)}.`;
}

export function displayLimitation(value: string): string {
  return LIMITATION_LABELS[value] || value;
}

export function displayStatus(value: string): string {
  return STATUS_LABELS[value] || humanize(value);
}

export function shortDatasetId(value: string): string {
  if (value.length <= 14) return value;
  return `${value.slice(0, 6)}…${value.slice(-6)}`;
}
