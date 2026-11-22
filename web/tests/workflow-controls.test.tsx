import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ClarificationPrompt, nextOnboardingStep, OperationSelect } from "@/components/workflow-controls";

describe("workflow controls", () => {
  it("enables ready operations and exposes blocked operations with status", () => {
    render(<OperationSelect value="" onChange={() => undefined} options={[{ identifier: "PAYABLE_SUMMARY", state: "SUPPORTED" }, { identifier: "PAYABLE_AGING", state: "BLOCKED" }]} />);
    expect(screen.getByRole("option", { name: /Payable summary · SUPPORTED/ })).toBeEnabled();
    expect(screen.getByRole("option", { name: /Payable aging · BLOCKED/ })).toBeDisabled();
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
