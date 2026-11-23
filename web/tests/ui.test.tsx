import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Field, Input, StateMessage, StatusBadge } from "@/components/ui";

describe("institutional UI states", () => {
  it("communicates status with text as well as color", () => {
    render(<><StatusBadge status="READY" /><StatusBadge status="BLOCKED" /><StatusBadge status="UNSUPPORTED" /></>);
    expect(screen.getByText("Ready")).toBeVisible();
    expect(screen.getByText("Blocked")).toBeVisible();
    expect(screen.getByText("Not supported")).toBeVisible();
  });

  it("renders a specific blocked reason", () => {
    render(<StateMessage kind="warning" title="Operation blocked" message="CUSTOMER is not confirmed." />);
    expect(screen.getByText("CUSTOMER is not confirmed.")).toBeVisible();
  });

  it("provides stable help and error ids for form-field associations", () => {
    render(<Field label="Evidence" htmlFor="evidence" help="Explain the source." error="Evidence is required."><Input id="evidence" aria-invalid="true" aria-describedby="evidence-help evidence-error" /></Field>);
    const input = screen.getByLabelText("Evidence");
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(input).toHaveAccessibleDescription("Explain the source. Evidence is required.");
  });
});
