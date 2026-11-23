import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ClarificationPrompt, DatasetSelect, nextOnboardingStep, OperationSelect } from "@/components/workflow-controls";
import type { DatasetSummary } from "@/lib/types";

describe("workflow controls", () => {
  it("enables ready operations and exposes blocked operations with status", () => {
    render(<OperationSelect value="" onChange={() => undefined} options={[{ identifier: "PAYABLE_SUMMARY", state: "SUPPORTED" }, { identifier: "PAYABLE_AGING", state: "BLOCKED" }]} />);
    expect(screen.getByRole("option", { name: /Payable summary · Ready/ })).toBeEnabled();
    expect(screen.getByRole("option", { name: /Payable aging · Blocked/ })).toBeDisabled();
  });

  it("keeps the exact dataset id as authority without turning metadata into a giant option label", () => {
    const dataset = {
      dataset_id: "ds_12345678901234567890", source_filename: "company_payables.csv", source_type: "CSV",
      row_count: 2, column_count: 2, lifecycle_state: "READY", readiness_state: "READY",
      approved_domain: "PAYABLE", currency_state: "CONFIRMED", supported_operations: [], limitations: [],
    } satisfies DatasetSummary;
    const onChange = vi.fn();
    render(<DatasetSelect id="dataset" datasets={[dataset]} value={dataset.dataset_id} onChange={onChange} />);
    const option = screen.getByRole("option", { name: /company_payables\.csv/ });
    expect(option).toHaveValue(dataset.dataset_id);
    expect(option).not.toHaveTextContent("Accounts payable");
    expect(screen.getByText("Accounts payable")).toBeVisible();
    expect(screen.getByText("Ready")).toBeVisible();
    expect(screen.getByText(dataset.dataset_id)).not.toBeVisible();
  });

  it("renders bounded clarification choices as interaction, not an error", () => {
    const onChange = vi.fn();
    render(<ClarificationPrompt value="" onChange={onChange} onSubmit={() => undefined} choices={["January", "February"]} />);
    expect(screen.getByText("Clarification required")).toBeVisible();
    fireEvent.change(screen.getByLabelText("Clarification answer"), { target: { value: "February" } });
    expect(onChange).toHaveBeenCalledWith("February");
  });

  it("advances onboarding only one explicit state at a time", () => {
    expect(nextOnboardingStep(1)).toBe(2);
    expect(nextOnboardingStep(2)).toBe(3);
    expect(nextOnboardingStep(3)).toBe(4);
    expect(nextOnboardingStep(4)).toBe(5);
  });
});
