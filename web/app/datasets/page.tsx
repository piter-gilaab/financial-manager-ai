"use client";

import Link from "next/link";
import { ArrowRight, FilePlus2 } from "lucide-react";
import { useWorkspace } from "@/components/workspace-provider";
import { EmptyState, LinkButton, LoadingState, PageHeader, Panel, StateMessage, StatusBadge } from "@/components/ui";
import { displayCurrencyState } from "@/lib/format";
import { displayDomain } from "@/lib/presentation";

export default function DatasetsPage() {
  const { datasets, loadingDatasets, datasetError, selectDataset } = useWorkspace();
  return <>
    <PageHeader title="Datasets" description="Registered local sources, approved financial meaning and current operation readiness." action={<LinkButton href="/datasets/new"><FilePlus2 size={16} /> Add dataset</LinkButton>} />
    {loadingDatasets ? <LoadingState label="Loading registered datasets" /> : datasetError && datasets.length === 0 ? <StateMessage kind="error" title="Datasets unavailable" message={datasetError} /> : datasets.length === 0 ? <Panel><EmptyState title="No datasets registered" description="Onboard a CSV or constrained XLSX source to begin explicit semantic approval." action={<LinkButton href="/datasets/new">Add dataset</LinkButton>} /></Panel> : <Panel><div className="table-wrap"><table className="table"><thead><tr><th>Dataset</th><th>Domain</th><th>Lifecycle</th><th>Readiness</th><th>Capabilities</th><th>Currency</th><th><span className="sr-only">Actions</span></th></tr></thead><tbody>{datasets.map((dataset) => <tr key={dataset.dataset_id}>
      <td><strong>{dataset.source_filename}</strong><div className="micro truncate-id" title={dataset.dataset_id}>{dataset.dataset_id}</div></td>
      <td>{dataset.approved_domain ? displayDomain(dataset.approved_domain) : <span className="muted">Not confirmed</span>}</td>
      <td><StatusBadge status={dataset.lifecycle_state} /></td>
      <td><StatusBadge status={dataset.readiness_state} /></td>
      <td className="tabular">{dataset.supported_operations.length}</td>
      <td>{displayCurrencyState(dataset.currency_state)}</td>
      <td><Link href={`/datasets/${dataset.dataset_id}`} className="button button-ghost" onClick={() => selectDataset(dataset)}>Open <ArrowRight size={14} /></Link></td>
    </tr>)}</tbody></table></div></Panel>}
  </>;
}
