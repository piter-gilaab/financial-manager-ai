"use client";

import { useEffect, useMemo, useState } from "react";
import { ArrowRight, Check } from "lucide-react";
import { displayCurrencyState, humanize } from "@/lib/format";
import { EXECUTABLE_DOMAINS } from "@/lib/operations";
import { displayDomain, displayReason } from "@/lib/presentation";
import type { DatasetSummary, Readiness, SemanticMapping } from "@/lib/types";
import { Button, Field, Select, StateMessage, StatusBadge } from "./ui";

export const EMPTY_DECISION_EVIDENCE = "";

export function DomainConfirmation({
  approvedDomain,
  suggestedDomain,
  busy,
  onConfirm,
}: {
  approvedDomain: string | null;
  suggestedDomain?: string | null;
  busy: boolean;
  onConfirm: (domain: string) => Promise<void>;
}) {
  const [pendingDomain, setPendingDomain] = useState(approvedDomain || "");

  useEffect(() => setPendingDomain(approvedDomain || ""), [approvedDomain]);

  const changed = Boolean(pendingDomain && pendingDomain !== approvedDomain);

  return <div className="stack">
    <div><span className="micro">Suggested domain</span><h2>{suggestedDomain ? displayDomain(suggestedDomain) : "No executable domain suggested"}</h2></div>
    <Field label="Proposed domain" htmlFor="domain" help="Selecting a domain keeps it pending in this browser. It is not saved until you confirm it.">
      <Select id="domain" value={pendingDomain} onChange={(event) => setPendingDomain(event.target.value)} disabled={busy}>
        <option value="">Select a domain</option>
        {EXECUTABLE_DOMAINS.map((domain) => <option key={domain} value={domain}>{displayDomain(domain)}</option>)}
      </Select>
    </Field>
    {changed && <StateMessage title="Pending domain" message={`${displayDomain(pendingDomain)} is selected for review and has not been saved.`} />}
    {approvedDomain && !changed && <StateMessage title="Saved domain" message={displayDomain(approvedDomain)} />}
    <div><Button type="button" disabled={busy || !changed} onClick={() => onConfirm(pendingDomain)}><Check size={16} /> Confirm domain</Button></div>
  </div>;
}

type SemanticDecision = Extract<SemanticMapping["decisions"][number], { source_column: string }>;

function isSemanticDecision(decision: SemanticMapping["decisions"][number]): decision is SemanticDecision {
  return "source_column" in decision;
}

function currentSemanticDecisions(mappings: SemanticMapping): SemanticDecision[] {
  const byColumn = new Map<string, SemanticDecision>();
  for (const decision of mappings.decisions) {
    if (isSemanticDecision(decision)) byColumn.set(decision.source_column, decision);
  }
  return [...byColumn.values()];
}

export function ApprovalReview({
  dataset,
  mappings,
  readiness,
  onContinue,
}: {
  dataset: DatasetSummary;
  mappings: SemanticMapping;
  readiness: Readiness;
  onContinue: () => void;
}) {
  const semanticDecisions = useMemo(() => currentSemanticDecisions(mappings), [mappings]);
  const operations = readiness.capabilities.flatMap((capability) => capability.operations);

  return <section aria-labelledby="approval-review-title" className="review-summary">
    <header className="review-summary-head">
      <div><div className="eyebrow">Read-only approval summary</div><h2 id="approval-review-title">Review saved decisions</h2><p className="muted">This page does not save or calculate authority. Operation readiness below comes from the registered system decision.</p></div>
      <StatusBadge status={dataset.readiness_state} />
    </header>

    <dl className="review-facts">
      <div><dt>Dataset</dt><dd>{dataset.source_filename}<span className="micro truncate-id" title={dataset.dataset_id}>{dataset.dataset_id}</span></dd></div>
      <div><dt>Domain</dt><dd>{displayDomain(mappings.approved_domain)}</dd></div>
      <div><dt>Currency</dt><dd>{displayCurrencyState(readiness.currency.state, readiness.currency.code)}</dd></div>
      <div><dt>Mapping version</dt><dd>{mappings.mapping_version}</dd></div>
    </dl>

    <div className="review-section">
      <h3>Semantic mappings</h3>
      {semanticDecisions.length ? <div className="review-list">{semanticDecisions.map((decision) => <div className="review-row" key={decision.source_column}>
        <div><strong>{decision.source_column}</strong><span>{decision.decision === "REJECT" || !decision.approved_role ? "Suggestion rejected" : humanize(decision.approved_role)}</span></div>
        {decision.value_mapping && Object.keys(decision.value_mapping).length > 0 && <div className="review-values">{Object.entries(decision.value_mapping).map(([source, target]) => <span key={source}>{source} → {humanize(target)}</span>)}</div>}
      </div>)}</div> : <p className="muted">No semantic decisions are saved.</p>}
    </div>

    <div className="review-section">
      <h3>Saved qualifiers</h3>
      {Object.keys(mappings.qualifiers).length ? <dl className="review-qualifiers">{Object.entries(mappings.qualifiers).map(([key, value]) => <div key={key}><dt>{humanize(key)}</dt><dd>{humanize(value)}</dd></div>)}</dl> : <p className="muted">No domain-specific qualifiers are required or saved.</p>}
    </div>

    <div className="review-section">
      <h3>Operation readiness</h3>
      <div className="review-list">{operations.map((operation) => <div className="review-operation" key={operation.identifier}><div><strong>{humanize(operation.identifier)}</strong>{operation.reasons.length > 0 && <span>{operation.reasons.map(displayReason).join(" ")}</span>}</div><StatusBadge status={operation.state} /></div>)}</div>
    </div>

    <div><Button type="button" onClick={onContinue}>Open operation readiness <ArrowRight size={16} /></Button></div>
  </section>;
}
