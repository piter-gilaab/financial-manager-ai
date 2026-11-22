"use client";

import { use, useEffect, useState } from "react";
import { BarChart3 } from "lucide-react";
import { api } from "@/lib/api-client";
import type { DatasetProfile, DatasetSummary, Readiness, SemanticMapping } from "@/lib/types";
import { displayCurrencyState, humanize } from "@/lib/format";
import { operationIsExecutable } from "@/lib/operations";
import { useWorkspace } from "@/components/workspace-provider";
import { LinkButton, LoadingState, PageHeader, Panel, PanelHeader, SafeJson, SectionHeader, StateMessage, StatusBadge } from "@/components/ui";

export default function DatasetDetailPage({ params }: { params: Promise<{ datasetId: string }> }) {
  const { datasetId } = use(params);
  const [dataset, setDataset] = useState<DatasetSummary | null>(null);
  const [profile, setProfile] = useState<DatasetProfile | null>(null);
  const [mappings, setMappings] = useState<SemanticMapping | null>(null);
  const [readiness, setReadiness] = useState<Readiness | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { selectDataset } = useWorkspace();

  useEffect(() => {
    Promise.all([api.dataset(datasetId), api.profile(datasetId), api.mappings(datasetId), api.readiness(datasetId)])
      .then(([detail, profileResponse, mappingResponse, readinessResponse]) => {
        setDataset(detail.data); setProfile(profileResponse.data); setMappings(mappingResponse.data); setReadiness(readinessResponse.data); selectDataset(detail.data);
      }).catch((reason) => setError(reason instanceof Error ? reason.message : "Dataset could not be loaded."));
  }, [datasetId, selectDataset]);

  if (error) return <><PageHeader title="Dataset workspace" description="Exact registered dataset context." /><StateMessage kind="error" title="Dataset unavailable" message={error} /></>;
  if (!dataset || !profile || !mappings || !readiness) return <><PageHeader title="Dataset workspace" description="Exact registered dataset context." /><LoadingState /></>;
  const operations = readiness.capabilities.flatMap((capability) => capability.operations);
  const ready = operations.filter((operation) => operationIsExecutable(operation.state));

  return <>
    <PageHeader title={dataset.source_filename} description={`Exact dataset ID: ${dataset.dataset_id}`} eyebrow={dataset.approved_domain || "Domain requires confirmation"} action={ready.length > 0 ? <LinkButton href={`/analysis?dataset=${dataset.dataset_id}`}><BarChart3 size={16} /> Analyze dataset</LinkButton> : <LinkButton href={`/datasets/new?dataset=${dataset.dataset_id}`} variant="secondary">Continue onboarding</LinkButton>} />
    <div className="meta-strip">
      <div className="meta-item"><span className="micro">Rows</span><span className="meta-value tabular">{dataset.row_count}</span></div>
      <div className="meta-item"><span className="micro">Columns</span><span className="meta-value tabular">{dataset.column_count}</span></div>
      <div className="meta-item"><span className="micro">Readiness</span><span className="meta-value"><StatusBadge status={dataset.readiness_state} /></span></div>
      <div className="meta-item"><span className="micro">Currency</span><span className="meta-value">{displayCurrencyState(readiness.currency.state, readiness.currency.code)}</span></div>
    </div>
    <SectionHeader title="Operation-specific readiness" description="Projected by the backend for the current mapping and artifacts." />
    <Panel><div className="panel-body">{operations.length === 0 ? <StateMessage kind="warning" title="No available operations" message="Complete explicit semantic and domain confirmation to establish execution readiness." /> : operations.map((operation) => <div className="operation-row" key={operation.identifier}><div><strong>{humanize(operation.identifier)}</strong>{operation.reasons.map((reason) => <div className="reason" key={reason}>{reason}</div>)}</div><StatusBadge status={operation.state} /></div>)}</div></Panel>
    <div className="grid-2">
      <div><SectionHeader title="Profile" description="Bounded deterministic structural evidence." /><Panel><PanelHeader title={`${profile.column_count} source columns`} subtitle={`${profile.duplicate_row_candidates} duplicate row candidates`} /><div className="table-wrap"><table className="table"><thead><tr><th>Column</th><th>Type</th><th>Missing</th><th>Unique</th></tr></thead><tbody>{profile.columns.map((column) => <tr key={column.column_id}><td><strong>{column.name}</strong><div className="micro">{column.examples.slice(0, 2).join(" · ") || "No examples"}</div></td><td>{column.structural_type}</td><td className="tabular">{column.missing_percentage}%</td><td className="tabular">{column.unique_count}</td></tr>)}</tbody></table></div></Panel></div>
      <div><SectionHeader title="Semantic mapping" description="Explicit decisions only; suggestions are not authority." /><Panel><PanelHeader title={`Mapping version ${mappings.mapping_version}`} subtitle={mappings.mapping_digest} /><div className="panel-body">{mappings.decisions.length === 0 ? <p className="muted">No semantic decisions have been approved.</p> : mappings.decisions.map((decision) => {
        const title = "source_column" in decision ? decision.source_column : "approved_domain" in decision ? "Domain approval" : "Qualifier confirmation";
        const detail = "approved_role" in decision ? decision.approved_role || "Rejected" : "approved_domain" in decision ? decision.approved_domain : Object.entries(decision.qualifiers).map(([key, value]) => `${key}=${value}`).join(" · ");
        return <div className="operation-row" key={`${decision.decision}-${decision.mapping_version}`}><div><strong>{title}</strong><div className="reason">{detail} · {decision.authority_source}</div></div><StatusBadge status={decision.decision} /></div>;
      })}{mappings.unresolved_requirements.length > 0 && <><div className="eyebrow" style={{ marginTop: 16 }}>Unresolved requirements</div><ul className="notice-list">{mappings.unresolved_requirements.map((item) => <li key={item}>{item}</li>)}</ul></>}</div></Panel></div>
    </div>
    <SectionHeader title="Limitations and safe lineage" description="No server filesystem paths are exposed." />
    <Panel><div className="panel-body grid-2"><div><h3>Limitations</h3>{dataset.limitations.length ? <ul className="notice-list">{dataset.limitations.map((item) => <li key={item}>{item}</li>)}</ul> : <p className="muted">No dataset-level limitations were returned.</p>}</div><div><h3>Safe identifiers</h3><SafeJson value={{ dataset_id: dataset.dataset_id, profile_version: profile.profile_version, profile_digest: profile.profile_digest, mapping_digest: mappings.mapping_digest }} /></div></div></Panel>
  </>;
}
