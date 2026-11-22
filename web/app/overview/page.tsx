"use client";

import Link from "next/link";
import { ArrowRight, Database, FilePlus2 } from "lucide-react";
import { useWorkspace } from "@/components/workspace-provider";
import { EmptyState, LinkButton, LoadingState, PageHeader, Panel, PanelHeader, StateMessage, StatusBadge } from "@/components/ui";

export default function OverviewPage() {
  const { datasets, loadingDatasets, datasetError, selectedDataset, health, selectDataset } = useWorkspace();
  if (loadingDatasets) return <><PageHeader title="Overview" description="Current local data portfolio and execution readiness." /><LoadingState /></>;
  if (datasetError && datasets.length === 0) return <><PageHeader title="Overview" description="Current local data portfolio and execution readiness." /><StateMessage kind="error" title="API unavailable" message={datasetError} /></>;

  const domainCounts = datasets.reduce<Record<string, number>>((counts, dataset) => {
    const key = dataset.approved_domain || "UNCONFIRMED";
    counts[key] = (counts[key] || 0) + 1;
    return counts;
  }, {});

  return <>
    <PageHeader title="Overview" description="Dataset-aware operational context without assumed financial KPIs." action={<LinkButton href="/datasets/new"><FilePlus2 size={16} /> Add dataset</LinkButton>} eyebrow="Institutional Financial Workspace" />
    {datasets.length === 0 ? <Panel><EmptyState title="No datasets registered" description="Add a bounded CSV or XLSX source, inspect its deterministic profile, then explicitly approve semantics before analysis." action={<LinkButton href="/datasets/new">Add dataset</LinkButton>} /></Panel> : <div className="stack">
      <div className="meta-strip" aria-label="Workspace metadata">
        <div className="meta-item"><span className="micro">Registered datasets</span><span className="meta-value tabular">{datasets.length}</span></div>
        <div className="meta-item"><span className="micro">Approved domains</span><span className="meta-value tabular">{Object.keys(domainCounts).filter((domain) => domain !== "UNCONFIRMED").length}</span></div>
        <div className="meta-item"><span className="micro">API status</span><span className="meta-value">{health === "healthy" ? "Local API healthy" : "Local API unavailable"}</span></div>
        <div className="meta-item"><span className="micro">Current context</span><span className="meta-value" title={selectedDataset?.dataset_id}>{selectedDataset?.source_filename || "Not selected"}</span></div>
      </div>
      <div className="grid-2">
        <Panel><PanelHeader title="Dataset portfolio" subtitle="Safe metadata only" /><div className="panel-body stack">
          {Object.entries(domainCounts).sort().map(([domain, count]) => <div className="operation-row" key={domain}><div><strong>{domain.replaceAll("_", " ")}</strong><div className="reason">Current approved domain classification</div></div><span className="tabular">{count}</span></div>)}
          <Link className="button button-secondary" href="/datasets">Open datasets <ArrowRight size={15} /></Link>
        </div></Panel>
        <Panel><PanelHeader title={selectedDataset ? "Selected dataset" : "Choose a dataset"} subtitle="Runtime workspace context" /><div className="panel-body">
          {selectedDataset ? <div className="stack">
            <div><div className="eyebrow">{selectedDataset.approved_domain || "Domain unconfirmed"}</div><h2 style={{ marginTop: 5 }}>{selectedDataset.source_filename}</h2><span className="truncate-id" title={selectedDataset.dataset_id}>{selectedDataset.dataset_id}</span></div>
            <div className="operation-row"><span>Readiness</span><StatusBadge status={selectedDataset.readiness_state} /></div>
            <div className="operation-row"><span>Available capabilities</span><strong className="tabular">{selectedDataset.supported_operations.length}</strong></div>
            {selectedDataset.limitations.length > 0 && <div><div className="eyebrow">Limitations</div><ul className="notice-list">{selectedDataset.limitations.map((item) => <li key={item}>{item}</li>)}</ul></div>}
            <LinkButton href={`/datasets/${selectedDataset.dataset_id}`} variant="secondary">Open dataset workspace</LinkButton>
          </div> : <div className="stack"><p className="muted">Select an exact registered dataset to establish local workspace context.</p>{datasets.slice(0, 4).map((dataset) => <button className="button button-secondary" key={dataset.dataset_id} onClick={() => selectDataset(dataset)}><Database size={15} /> {dataset.source_filename}</button>)}</div>}
        </div></Panel>
      </div>
    </div>}
  </>;
}
