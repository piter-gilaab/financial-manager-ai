import { withoutPrivatePaths } from "@/lib/evidence";
import { isRecord } from "@/lib/types";
import { SafeJson, StateMessage } from "./ui";

const MAX_INLINE_EVIDENCE_CHARACTERS = 50_000;

function structuralProjection(value: unknown): unknown {
  if (!isRecord(value)) return value;
  return Object.fromEntries(Object.entries(value).flatMap(([key, item]) => {
    if (item === null || ["string", "number", "boolean"].includes(typeof item)) return [[key, item]];
    if (Array.isArray(item) && item.every((entry) => entry === null || ["string", "number", "boolean"].includes(typeof entry))) {
      return [[key, item.slice(0, 20)]];
    }
    return [];
  }));
}

export function ChatEvidence({ value }: { value: unknown }) {
  const safe = withoutPrivatePaths(value);
  const serialized = JSON.stringify(safe);
  if (serialized.length <= MAX_INLINE_EVIDENCE_CHARACTERS) return <SafeJson value={safe} />;
  return <div className="stack" style={{ marginTop: 10, gap: 8 }}>
    <StateMessage title="Large structured evidence returned" message="A bounded structural projection is shown here to keep the conversation responsive. Use the Analysis workspace for complete tabular evidence." />
    <SafeJson value={structuralProjection(safe)} />
  </div>;
}
