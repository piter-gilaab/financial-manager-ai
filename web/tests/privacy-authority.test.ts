import { describe, expect, it } from "vitest";
import fs from "node:fs";
import path from "node:path";

function allSource() {
  const roots = ["app", "components", "lib"];
  const files: string[] = [];
  const walk = (directory: string) => fs.readdirSync(directory, { withFileTypes: true }).forEach((entry) => {
    const full = path.join(directory, entry.name);
    if (entry.isDirectory()) walk(full);
    else if (/\.(ts|tsx)$/.test(entry.name) && entry.name !== "api-schema.ts") files.push(full);
  });
  roots.forEach(walk);
  return files.map((file) => fs.readFileSync(file, "utf8")).join("\n");
}

describe("frontend authority and privacy boundary", () => {
  it("does not persist transcripts or use unsafe HTML", () => {
    const source = allSource();
    expect(source).not.toContain("localStorage");
    expect(source).not.toContain("indexedDB");
    expect(source).not.toContain("dangerouslySetInnerHTML");
  });

  it("contains no financial aggregation algorithm", () => {
    const source = allSource();
    expect(source).not.toMatch(/\.reduce\([^\n]*(amount|sales|profit|cash|receivable|payable)/i);
    expect(source).not.toMatch(/quartile|calculateAging|calculateOverdue|sumFinancial|averageFinancial/i);
  });
});
