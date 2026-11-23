import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { EvidenceRenderer } from "@/components/evidence-renderer";
import { toChartData, withoutPrivatePaths } from "@/lib/evidence";

describe("analysis evidence renderer", () => {
  it("keeps chart conversion presentation-only and exact values alongside it", () => {
    expect(toChartData([{ period: "2026-01", net_cash: "0.10" }])).toEqual([{ label: "2026-01", coordinate: 0.1, exact: "0.10" }]);
    expect(toChartData([{ key: { value: "Vendor A", kind: "source_value" }, measures: { amount: { sum: "10.50" } } }])).toEqual([{ label: "Vendor A", coordinate: 10.5, exact: "10.50" }]);
    expect(toChartData([{ bucket: "31–60", balance_sum: "123456789.123456" }])).toEqual([{ label: "31–60", coordinate: 123456789.123456, exact: "123456789.123456" }]);
  });

  it("renders grouped dimension and measure coverage returned by the backend", () => {
    render(<EvidenceRenderer status="SUCCESS" evidence={{ delegated_result: { query_name: "PAYABLE_BY_SUPPLIER", currency: { status: "CONFIRMED", code: "BRL" }, result: { groups: [{ key: { value: "Vendor A", kind: "source_value" }, measures: { amount: { sum: "10.50" } } }], dimension_coverage: { population: 2, unavailable: 0 }, measure_coverage: { amount: { population: 2, used: 2 } } } } }} />);
    expect(screen.getByRole("img", { name: "Presentation view" })).toBeVisible();
    expect(screen.getByRole("table", { name: "Exact authoritative evidence" })).toBeVisible();
    expect(screen.getByText("BRL")).toBeVisible();
    expect(screen.getByText("Dimension Coverage Population")).toBeVisible();
    expect(screen.getByRole("cell", { name: /10\.50/ })).toBeVisible();
  });

  it("preserves mixed confirmed currency context without aggregating grouped values", () => {
    render(<EvidenceRenderer status="BLOCKED" evidence={{ delegated_result: { query_name: "SALES_BY_PERIOD", currency: { status: "CONFIRMED_MULTIPLE", code: null }, result: { groups: [] } } }} />);
    expect(screen.getByText("Mixed confirmed currencies")).toBeVisible();
  });

  it("renders exact measures, coverage, limitations and lineage", () => {
    render(<EvidenceRenderer status="PARTIAL" limitations={["Currency unverified"]} evidence={{ delegated_result: { query_name: "PAYABLE_SUMMARY", currency: { status: "UNKNOWN", code: null }, result: { measures: { amount: { sum: "10.50", coverage: { population: 3, used: 2, excluded: 1 } } } }, metadata: { lineage: { dataset_id: "ds_123" }, artifact_path: "/private/path" } } }} />);
    expect(screen.getByText(/10.50 · unverified source denomination/)).toBeVisible();
    expect(screen.getByText("Currency unverified")).toBeVisible();
    const technicalDetails = screen.getByText("Technical details").closest("details");
    expect(technicalDetails).not.toHaveAttribute("open");
    expect(screen.getByText("Lineage and reproducibility")).not.toBeVisible();
  });

  it("removes private filesystem path fields from technical evidence", () => {
    expect(withoutPrivatePaths({ dataset: "ds_1", source_path: "/private", nested: { artifact_path: "/secret" } })).toEqual({ dataset: "ds_1", nested: {} });
  });
});
