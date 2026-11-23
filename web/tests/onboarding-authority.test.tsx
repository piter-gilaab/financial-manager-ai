import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ApprovalReview, DomainConfirmation, EMPTY_DECISION_EVIDENCE } from "@/components/onboarding-approval";
import type { DatasetSummary, Readiness, SemanticMapping } from "@/lib/types";

describe("onboarding authority boundaries", () => {
  it("starts with empty evidence and never fabricates owner confirmation", () => {
    expect(EMPTY_DECISION_EVIDENCE).toBe("");
    expect(EMPTY_DECISION_EVIDENCE).not.toMatch(/owner|confirmed|approved/i);
  });

  it("keeps domain changes local until Confirm domain is pressed", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn().mockResolvedValue(undefined);
    render(<DomainConfirmation approvedDomain={null} suggestedDomain="PAYABLE" busy={false} onConfirm={onConfirm} />);

    const domain = screen.getByLabelText("Proposed domain");
    await user.selectOptions(domain, "PAYABLE");
    await user.selectOptions(domain, "RECEIVABLE");
    expect(onConfirm).not.toHaveBeenCalled();
    expect(screen.getByText(/Accounts receivable is selected for review/)).toBeVisible();

    await user.click(screen.getByRole("button", { name: "Confirm domain" }));
    expect(onConfirm).toHaveBeenCalledTimes(1);
    expect(onConfirm).toHaveBeenCalledWith("RECEIVABLE");
  });

  it("renders saved decisions and backend-provided readiness without inventing capabilities", () => {
    const dataset = {
      dataset_id: "ds_12345678901234567890", source_filename: "company_payables.csv",
      source_type: "CSV", row_count: 2, column_count: 2, lifecycle_state: "READY",
      readiness_state: "READY", approved_domain: "PAYABLE", currency_state: "CONFIRMED",
      supported_operations: ["PAYABLE_COUNT"], limitations: [],
    } satisfies DatasetSummary;
    const mappings = {
      dataset_id: dataset.dataset_id, status: "READY", mapping_version: 4, mapping_digest: "digest",
      approved_domain: "PAYABLE", domain_suggestions: ["PAYABLE"], currency_state: "CONFIRMED",
      confirmed_currency: "BRL", unresolved_requirements: [], qualifiers: { amount_basis: "OUTSTANDING_BALANCE" },
      proposals: [], decisions: [{ source_column: "Amount", column_id: "amount", approved_role: "AMOUNT",
        authority_source: "USER", date_format: null, decision: "CONFIRM", evidence: "Signed source contract",
        mapping_version: 2, previous_proposal: null, timestamp: "2026-11-22T00:00:00Z", value_mapping: null }],
    } satisfies SemanticMapping;
    const readiness = {
      version: "1", dataset_id: dataset.dataset_id, canonical_domain: "PAYABLE", mapping_digest: "digest",
      currency: { state: "CONFIRMED", code: "BRL" }, capabilities: [{ identifier: "PAYABLE", state: "AVAILABLE_WITH_LIMITATIONS",
        semantic_readiness: "READY", policy_readiness: "READY", execution_readiness: "READY", reasons: [], limitations: [],
        operations: [{ identifier: "PAYABLE_COUNT", state: "SUPPORTED", required_semantics: ["AMOUNT"], reasons: [] },
          { identifier: "PAYABLE_AGING", state: "BLOCKED", required_semantics: ["DUE_DATE"], reasons: ["MISSING_REQUIRED_SEMANTICS"] }] }],
    } satisfies Readiness;

    render(<ApprovalReview dataset={dataset} mappings={mappings} readiness={readiness} onContinue={() => undefined} />);
    expect(screen.getByRole("heading", { name: "Review saved decisions" })).toBeVisible();
    expect(screen.getAllByText("Amount")).toHaveLength(2);
    expect(screen.getByText("Payable Count")).toBeVisible();
    expect(screen.getByText("Payable Aging")).toBeVisible();
    expect(screen.getByText("Blocked")).toBeVisible();
    expect(screen.queryByText("Payable Summary")).not.toBeInTheDocument();
  });
});
