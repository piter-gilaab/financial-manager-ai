import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const apiMock = vi.hoisted(() => ({
  createSession: vi.fn(), session: vi.fn(), sessionTurn: vi.fn(), answer: vi.fn(), followUp: vi.fn(),
}));

vi.mock("@/lib/api-client", () => ({ api: apiMock, ApiClientError: class extends Error {} }));
vi.mock("@/components/workspace-provider", () => ({ useWorkspace: () => ({ datasets: [], selectedDataset: null, selectDataset: vi.fn() }) }));

import ChatPage from "@/app/chat/page";

const session = { session_id: "session-1", status: "ACTIVE", created_at: null, last_activity_at: null, inactivity_expires_at: null, absolute_expires_at: null, active_context: null, dynamic_dataset: null };

describe("chat session lifecycle UI", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMock.createSession.mockResolvedValue({ data: session });
  });

  it("creates a runtime session, sends a question and renders clarification", async () => {
    apiMock.sessionTurn.mockResolvedValue({ data: { status: "CLARIFICATION_REQUIRED", text: null, notice: "Select a dataset", outcome: null, labels: [], replaced_pending: false } });
    apiMock.session.mockResolvedValue({ data: { ...session, active_context: { reconstruction_descriptor: { kind: "DATASET_SELECTION" }, pending_clarification: { source: "manager", code: "dataset_required", field: "dataset_id", choices: ["ds_11111111111111111111"] } } } });
    const user = userEvent.setup();
    render(<ChatPage />);
    const input = await screen.findByLabelText("Financial question");
    await waitFor(() => expect(input).toBeEnabled());
    await user.type(input, "Show payables by supplier.");
    await user.click(screen.getByRole("button", { name: "Send financial question" }));
    expect(apiMock.sessionTurn).toHaveBeenCalledWith("session-1", "Show payables by supplier.");
    expect(await screen.findByText("Clarification required")).toBeVisible();
    expect(screen.getByRole("option", { name: "ds_11111111111111111111" })).toBeVisible();
  });

  it("executes only session-issued anomaly follow-up handles", async () => {
    apiMock.sessionTurn.mockResolvedValue({ data: { status: "SUCCESS", text: "Candidates returned", notice: null, outcome: { result: {}, error: null, references: [{ handle: "ref-1", kind: "ANOMALY_RECORD" }] }, labels: [], replaced_pending: false } });
    apiMock.session.mockResolvedValue({ data: session });
    apiMock.followUp.mockResolvedValue({ data: { status: "SUCCESS", outcome: { result: { reason: "upper fence exceeded" }, error: null, references: [] }, session } });
    const user = userEvent.setup();
    render(<ChatPage />);
    const input = await screen.findByLabelText("Financial question");
    await waitFor(() => expect(input).toBeEnabled());
    await user.type(input, "Screen unusual sales.");
    await user.click(screen.getByRole("button", { name: "Send financial question" }));
    await user.click(await screen.findByRole("button", { name: "Why selected" }));
    expect(apiMock.followUp).toHaveBeenCalledWith("session-1", "ref-1", "why_selected");
    expect(await screen.findByText("Why this candidate was selected")).toBeVisible();
  });

  it("shows a controlled provider failure and never fabricates an answer", async () => {
    apiMock.sessionTurn.mockRejectedValue(new Error("Provider unavailable"));
    const user = userEvent.setup();
    render(<ChatPage />);
    const input = await screen.findByLabelText("Financial question");
    await waitFor(() => expect(input).toBeEnabled());
    await user.type(input, "Show net cash by month.");
    await user.click(screen.getByRole("button", { name: "Send financial question" }));
    expect(await screen.findByText("Provider or API unavailable")).toBeVisible();
    expect(screen.queryByText(/invented total/i)).not.toBeInTheDocument();
  });
});
