import { isRecord } from "./types";

export interface ChartDatum {
  label: string;
  coordinate: number;
  exact: string;
}

const LABEL_KEYS = ["period", "supplier", "customer", "country", "product", "segment", "category", "account", "bucket", "label", "name"];
const VALUE_KEYS = ["net_cash", "sum", "amount", "sales", "profit", "value", "count", "total"];

function exactCoordinate(item: Record<string, unknown>): string | undefined {
  for (const key of [...VALUE_KEYS, "balance_sum", "record_count", "open_balance_sum"]) {
    const candidate = item[key];
    if (typeof candidate === "string" && /^-?\d+(\.\d+)?$/.test(candidate)) return candidate;
    if (typeof candidate === "number") return String(candidate);
  }
  if (isRecord(item.measures)) {
    for (const measure of Object.values(item.measures)) {
      if (!isRecord(measure)) continue;
      const nested = measure.sum ?? measure.value ?? measure.count ?? measure.average;
      if (typeof nested === "string" || typeof nested === "number") return String(nested);
    }
  }
  return undefined;
}

/** Presentation-only adapter. Never aggregates or returns authoritative display values. */
export function toChartData(groups: unknown): ChartDatum[] {
  if (!Array.isArray(groups)) return [];
  return groups.flatMap((item, index) => {
    if (!isRecord(item)) return [];
    const key = isRecord(item.key) ? item.key : null;
    const directLabel = LABEL_KEYS.map((labelKey) => item[labelKey]).find((value) => typeof value === "string" || typeof value === "number");
    const labelValue = key ? (key.value ?? (key.kind === "unavailable" ? "Unavailable" : undefined)) : directLabel;
    const exactValue = exactCoordinate(item);
    if (exactValue === undefined) return [];
    const coordinate = Number(exactValue);
    if (!Number.isFinite(coordinate)) return [];
    return [{ label: String(labelValue ?? `Group ${index + 1}`), coordinate, exact: exactValue }];
  });
}

export function withoutPrivatePaths(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(withoutPrivatePaths);
  if (!isRecord(value)) return value;
  return Object.fromEntries(Object.entries(value)
    .filter(([key]) => !/(^|_)(path|filesystem|artifact_path)$/i.test(key))
    .map(([key, item]) => [key, withoutPrivatePaths(item)]));
}

export function evidenceRoot(evidence: unknown): Record<string, unknown> {
  if (!isRecord(evidence)) return {};
  return isRecord(evidence.delegated_result) ? evidence.delegated_result : evidence;
}
