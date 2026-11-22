import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StateMessage, StatusBadge } from "@/components/ui";

describe("institutional UI states", () => {
  it("communicates status with text as well as color", () => {
    render(<><StatusBadge status="READY" /><StatusBadge status="BLOCKED" /><StatusBadge status="UNSUPPORTED" /></>);
    expect(screen.getByText("READY")).toBeVisible();
    expect(screen.getByText("BLOCKED")).toBeVisible();
    expect(screen.getByText("UNSUPPORTED")).toBeVisible();
  });

  it("renders a specific blocked reason", () => {
    render(<StateMessage kind="warning" title="Operation blocked" message="CUSTOMER is not confirmed." />);
    expect(screen.getByText("CUSTOMER is not confirmed.")).toBeVisible();
  });
});
