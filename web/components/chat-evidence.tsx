import { withoutPrivatePaths } from "@/lib/evidence";
import { isRecord } from "@/lib/types";
import { humanize } from "@/lib/format";
import { LinkButton, SafeJson, StateMessage, TechnicalDetails } from "./ui";

const MAX_INLINE_EVIDENCE_CHARACTERS = 12_000;

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
  const projection = structuralProjection(safe);
  const facts = isRecord(projection) ? Object.entries(projection).filter(([, item]) => item === null || ["string", "number", "boolean"].includes(typeof item)) : [];
  const large = serialized.length > MAX_INLINE_EVIDENCE_CHARACTERS;
  return <div className="chat-evidence-card">
    <div><strong>Key evidence</strong>{facts.length ? <dl className="chat-evidence-facts">{facts.map(([key, item]) => <div key={key}><dt>{humanize(key)}</dt><dd>{String(item ?? "—")}</dd></div>)}</dl> : <p className="muted">Structured evidence was returned with this answer.</p>}</div>
    {large && <StateMessage title="Large structured evidence returned" message="A bounded projection is kept here. Open Analysis for complete tabular evidence." />}
    <div className="chat-evidence-actions"><LinkButton href="/analysis" variant="secondary">Open in Analysis</LinkButton></div>
    <TechnicalDetails>{large ? <SafeJson value={projection} /> : <SafeJson value={safe} />}</TechnicalDetails>
  </div>;
}
