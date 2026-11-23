import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { MappingRow } from "@/components/semantic-mapping-row";
import type { SemanticMapping } from "@/lib/types";

function proposal(overrides: Partial<SemanticMapping["proposals"][number]>): SemanticMapping["proposals"][number] {
  return {
    source_column: "Direction", column_id: "col-direction", proposed_role: null,
    status: "SUGGESTED", confidence: "LOW", rationale: "Requires owner confirmation.",
    confirmation_required: true, conflicts: [], alternatives: [], authority_source: null,
    structural_type: "CATEGORICAL", observed_values: ["in", "out"], approved_format: null,
    ...overrides,
  };
}

describe("explicit semantic confirmation controls", () => {
  it("requires every cash direction value to receive a closed canonical meaning", async () => {
    const user = userEvent.setup(); const onDecide = vi.fn().mockResolvedValue(undefined);
    render(<table><tbody><MappingRow proposal={proposal({})} busy={false} onDecide={onDecide} /></tbody></table>);
    await user.selectOptions(screen.getByLabelText("Meaning for Direction"), "CASH_DIRECTION");
    const correct = screen.getByRole("button", { name: "Save corrected role and value mapping" });
    expect(correct).toBeDisabled();
    await user.selectOptions(screen.getByLabelText("in mapping for Direction"), "INFLOW");
    await user.selectOptions(screen.getByLabelText("out mapping for Direction"), "OUTFLOW");
    await user.click(correct);
    expect(onDecide).toHaveBeenCalledWith(expect.anything(), "CORRECT", "CASH_DIRECTION", { valueMapping: { in: "INFLOW", out: "OUTFLOW" }, dateFormat: undefined });
  });

  it("requires an explicit ambiguous source date format", async () => {
    const user = userEvent.setup(); const onDecide = vi.fn().mockResolvedValue(undefined);
    render(<table><tbody><MappingRow proposal={proposal({ source_column: "Date", column_id: "col-date", proposed_role: "TRANSACTION_DATE", structural_type: "AMBIGUOUS_DATE", observed_values: ["01/02/2026"] })} busy={false} onDecide={onDecide} /></tbody></table>);
    const confirm = screen.getByRole("button", { name: "Confirm semantic role" });
    expect(confirm).toBeDisabled();
    await user.selectOptions(screen.getByLabelText("Date format for Date"), "DD/MM/YYYY");
    await user.click(confirm);
    expect(onDecide).toHaveBeenCalledWith(expect.anything(), "CONFIRM", "TRANSACTION_DATE", { valueMapping: undefined, dateFormat: "DD/MM/YYYY" });
  });

  it("uses explicit authority-changing labels", () => {
    render(<table><tbody><MappingRow proposal={proposal({ proposed_role: "SALES", observed_values: [] })} busy={false} onDecide={vi.fn()} /></tbody></table>);
    expect(screen.getByRole("button", { name: "Confirm semantic role" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Save corrected semantic role" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Reject semantic suggestion" })).toBeVisible();
  });
});
