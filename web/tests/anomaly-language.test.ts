import { describe, expect, it } from "vitest";
import fs from "node:fs";
import path from "node:path";

describe("anomaly terminology", () => {
  it("uses candidate-only product language", () => {
    const source = fs.readFileSync(path.resolve("app/anomalies/page.tsx"), "utf8");
    expect(source).toContain("Statistical candidates for review");
    for (const forbidden of ["Fraud detected", "Fraud probability", "Likely fraud", "Risk score", "Suspicious transaction"]) expect(source).not.toContain(forbidden);
  });
});
