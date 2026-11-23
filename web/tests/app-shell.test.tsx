import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AppShell } from "@/components/app-shell";

vi.mock("next/navigation", () => ({ usePathname: () => "/overview" }));
vi.mock("@/components/workspace-provider", () => ({
  useWorkspace: () => ({ health: "healthy", selectedDataset: null }),
}));

describe("application shell accessibility", () => {
  beforeEach(() => {
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: vi.fn().mockImplementation(() => ({
        matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn(),
      })),
    });
  });

  it("places a keyboard-focusable skip link before workspace navigation", async () => {
    const user = userEvent.setup();
    render(<AppShell><h1>Overview</h1></AppShell>);
    const skip = screen.getByRole("link", { name: "Skip to main content" });
    expect(skip).toHaveAttribute("href", "#main-content");
    await user.tab();
    expect(skip).toHaveFocus();
    expect(document.querySelector("main#main-content")).toBeInTheDocument();
  });
});
