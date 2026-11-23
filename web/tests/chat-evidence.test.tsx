import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ChatEvidence } from "@/components/chat-evidence";

describe("bounded chat evidence", () => {
  it("keeps small authoritative values exact", () => {
    render(<ChatEvidence value={{ status: "SUCCESS", amount: "123456789.123456" }} />);
    expect(screen.getAllByText(/123456789\.123456/)[0]).toBeVisible();
  });

  it("projects exceptionally large results without rendering the full payload", () => {
    render(<ChatEvidence value={{ execution_status: "SUCCESS", records: Array.from({ length: 10_000 }, (_, index) => ({ index, value: "10.50" })) }} />);
    expect(screen.getByRole("heading", { name: "Large structured evidence returned" })).toBeVisible();
    expect(screen.getByText("Execution Status")).toBeVisible();
    expect(screen.getByText("SUCCESS")).toBeVisible();
    expect(screen.getByText("Technical details").closest("details")).not.toHaveAttribute("open");
    expect(screen.queryByText(/"records"/)).not.toBeInTheDocument();
  });
});
