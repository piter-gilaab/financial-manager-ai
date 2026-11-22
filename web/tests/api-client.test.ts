import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "@/lib/api-client";

afterEach(() => vi.unstubAllGlobals());

describe("central API client", () => {
  it("serializes only closed analysis fields and preserves decimal strings", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({
      api_version: "1", status: "SUCCESS", evidence: { amount: "0.10" }, limitations: [], errors: [],
    }), { status: 200, headers: { "Content-Type": "application/json" } }));
    vi.stubGlobal("fetch", fetchMock);
    const result = await api.analysis("ds_12345678901234567890", "PAYABLE_AGING", { as_of_date: "2026-11-01" });
    expect(result.evidence).toEqual({ amount: "0.10" });
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ dataset_id: "ds_12345678901234567890", operation: "PAYABLE_AGING", parameters: { as_of_date: "2026-11-01" } });
  });

  it("keeps clarification choices distinct from generic failures", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ status: "CLARIFICATION_REQUIRED", data: { field: "sheet", choices: ["January", "February"] }, errors: [{ code: "sheet_selection_required", field: "sheet", message: "Select a sheet." }] }), { status: 409 })));
    await expect(api.upload(new File(["x"], "book.xlsx"))).rejects.toMatchObject({ httpStatus: 409, status: "CLARIFICATION_REQUIRED", body: { data: { choices: ["January", "February"] } } });
  });

  it("maps network failure to API unavailable without leaking details", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("private socket details")));
    await expect(api.health()).rejects.toMatchObject({ httpStatus: 0, status: "API_UNAVAILABLE", message: "Local Financial Manager API could not be reached." });
  });

  it.each([
    [404, "NOT_FOUND", "dataset_not_found", "The exact dataset was not found."],
    [422, "INVALID_REQUEST", "validation_error", "The closed request is invalid."],
    [500, "INTERNAL_ERROR", "internal_error", "The request failed safely."],
  ])("preserves safe structured HTTP %s failures", async (httpStatus, status, code, message) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({
      api_version: "1", status, data: null, limitations: [], errors: [{ code, field: null, message }],
    }), { status: httpStatus, headers: { "Content-Type": "application/json" } })));
    await expect(api.dataset("ds_12345678901234567890")).rejects.toMatchObject({
      httpStatus, status, message,
    });
    try { await api.dataset("ds_12345678901234567890"); }
    catch (error) { expect(String(error)).not.toMatch(/Traceback|private socket|stack/i); }
  });
});
