"use client";

import { useMemo, useState } from "react";
import { Check } from "lucide-react";
import { humanize } from "@/lib/format";
import { SEMANTIC_ROLES } from "@/lib/operations";
import type { SemanticMapping } from "@/lib/types";
import { Button, Field, Input, Select } from "./ui";

export type MappingOptions = { valueMapping?: Record<string, string>; dateFormat?: string };

const VALUE_TARGETS: Record<string, string[]> = {
  STATUS: ["OPEN", "SETTLED", "CANCELLED"],
  CASH_DIRECTION: ["INFLOW", "OUTFLOW"],
  DEBIT_CREDIT_INDICATOR: ["DEBIT", "CREDIT"],
  ACTUAL_BUDGET_INDICATOR: ["ACTUAL", "BUDGET"],
};

export function MappingRow({ proposal, busy, onDecide }: { proposal: SemanticMapping["proposals"][number]; busy: boolean; onDecide: (proposal: SemanticMapping["proposals"][number], decision: "CONFIRM" | "CORRECT" | "REJECT", role?: string, options?: MappingOptions) => Promise<void> }) {
  const [role, setRole] = useState(proposal.proposed_role || "");
  const [valueMapping, setValueMapping] = useState<Record<string, string>>(() => Object.fromEntries(proposal.observed_values.map((value) => [value, ""])));
  const [dateFormat, setDateFormat] = useState("");
  const suggestion = useMemo(() => proposal.proposed_role ? humanize(proposal.proposed_role) : "No suggestion", [proposal.proposed_role]);
  const mappingTargets = role === "CURRENCY" ? null : VALUE_TARGETS[role];
  const needsMapping = role === "CURRENCY" || Boolean(mappingTargets);
  const needsDateFormat = ["TRANSACTION_DATE", "POSTING_DATE", "DUE_DATE"].includes(role);
  const mappingComplete = !needsMapping || (proposal.observed_values.length > 0 && proposal.observed_values.every((value) => valueMapping[value]));
  const decisionComplete = Boolean(role) && mappingComplete && (!needsDateFormat || Boolean(dateFormat));
  const options: MappingOptions = { valueMapping: needsMapping ? valueMapping : undefined, dateFormat: needsDateFormat ? dateFormat : undefined };

  return <tr className="semantic-card"><td data-label="Source column"><strong>{proposal.source_column}</strong><div className="micro">{proposal.structural_type}</div></td><td data-label="Suggested meaning">{suggestion}<div className="micro">{proposal.confidence} confidence</div></td><td data-label="Evidence"><span className="muted">{proposal.rationale}</span>{proposal.conflicts.map((conflict) => <div className="field-error" key={conflict}>{conflict}</div>)}</td><td data-label="Authority action" style={{ minWidth: 280 }}><div className="stack" style={{ gap: 7 }}>
    <Select aria-label={`Meaning for ${proposal.source_column}`} value={role} onChange={(event) => { setRole(event.target.value); setDateFormat(""); setValueMapping(Object.fromEntries(proposal.observed_values.map((value) => [value, ""]))); }}><option value="">Choose role</option>{SEMANTIC_ROLES.map((item) => <option key={item}>{item}</option>)}</Select>
    {needsDateFormat && <Field label="Approved source date format" htmlFor={`date-format-${proposal.column_id}`}><Select id={`date-format-${proposal.column_id}`} aria-label={`Date format for ${proposal.source_column}`} value={dateFormat} onChange={(event) => setDateFormat(event.target.value)}><option value="">Confirm format</option>{proposal.structural_type === "AMBIGUOUS_DATE" ? <><option value="DD/MM/YYYY">DD/MM/YYYY</option><option value="MM/DD/YYYY">MM/DD/YYYY</option></> : <option value="YYYY-MM-DD">YYYY-MM-DD</option>}</Select></Field>}
    {needsMapping && <div className="mapping-grid"><span className="micro">Explicit source value mapping</span>{proposal.observed_values.map((source, index) => { const id = `value-${proposal.column_id}-${index}`; return <Field key={source} label={source} htmlFor={id}>{role === "CURRENCY" ? <Input id={id} aria-label={`${source} mapping for ${proposal.source_column}`} value={valueMapping[source] || ""} maxLength={3} placeholder="ISO code" onChange={(event) => setValueMapping((current) => ({ ...current, [source]: event.target.value.toUpperCase() }))} /> : <Select id={id} aria-label={`${source} mapping for ${proposal.source_column}`} value={valueMapping[source] || ""} onChange={(event) => setValueMapping((current) => ({ ...current, [source]: event.target.value }))}><option value="">Select meaning</option>{mappingTargets?.map((target) => <option key={target}>{target}</option>)}</Select>}</Field>; })}</div>}
    <div className="mapping-actions"><Button type="button" disabled={busy || !decisionComplete || role !== proposal.proposed_role} onClick={() => onDecide(proposal, "CONFIRM", role, options)}><Check size={14} /> {needsMapping ? "Confirm role and save value mapping" : "Confirm semantic role"}</Button><Button type="button" variant="secondary" disabled={busy || !decisionComplete || role === proposal.proposed_role} onClick={() => onDecide(proposal, "CORRECT", role, options)}>{needsMapping ? "Save corrected role and value mapping" : "Save corrected semantic role"}</Button><Button type="button" variant="ghost" disabled={busy} onClick={() => onDecide(proposal, "REJECT")}>Reject semantic suggestion</Button></div>
  </div></td></tr>;
}
