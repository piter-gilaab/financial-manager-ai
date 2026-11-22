import { describe, expect, it } from "vitest";
import { displayDecimal, displayMoney } from "@/lib/format";

describe("authoritative decimal and currency display", () => {
  it.each(["0.1", "0.10", "10.50", "123456789.123456", "-1.25"])("preserves exact text %s", (value) => {
    expect(displayDecimal(value)).toBe(value);
  });

  it("uses confirmed codes and never infers an unknown symbol", () => {
    expect(displayMoney("10.50", { status: "CONFIRMED", code: "BRL" })).toBe("BRL 10.50");
    expect(displayMoney("10.50", { status: "UNKNOWN" })).toContain("unverified source denomination");
    expect(displayMoney("10.50", { status: "UNKNOWN" })).not.toContain("$");
  });

  it("states mixed currency without aggregating", () => {
    expect(displayMoney("10.50", { state: "CONFIRMED_MULTIPLE" })).toBe("10.50 · mixed confirmed currencies");
  });
});
