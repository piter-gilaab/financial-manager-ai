"use client";

import { useEffect, useMemo, useState } from "react";
import { Play } from "lucide-react";
import { ApiClientError, api } from "@/lib/api-client";
import { OPERATIONS, operationIsExecutable } from "@/lib/operations";
import type { AnalysisParameters, ExecutionEnvelope, Readiness, SemanticMapping } from "@/lib/types";
import { humanize } from "@/lib/format";
import { displayReason, displayStatus } from "@/lib/presentation";
import { EvidenceRenderer } from "@/components/evidence-renderer";
import { DatasetSelect, OperationSelect } from "@/components/workflow-controls";
import { useWorkspace } from "@/components/workspace-provider";
import { Button, EmptyState, Field, Input, LinkButton, PageHeader, Panel, PanelHeader, Select, StateMessage, StatusBadge } from "@/components/ui";

export default function AnalysisPage() {
  const { datasets, loadingDatasets, selectedDataset, selectDataset } = useWorkspace();
  const [datasetId, setDatasetId] = useState("");
  const [readiness, setReadiness] = useState<Readiness | null>(null);
  const [mappings, setMappings] = useState<SemanticMapping | null>(null);
  const [operation, setOperation] = useState("");
  const [granularity, setGranularity] = useState<"MONTH" | "YEAR">("MONTH");
  const [missingDimension, setMissingDimension] = useState<"BUCKET" | "EXCLUDE">("BUCKET");
  const [asOfDate, setAsOfDate] = useState("");
  const [result, setResult] = useState<ExecutionEnvelope | null>(null);
  const [error, setError] = useState<ApiClientError | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const queryId = new URLSearchParams(window.location.search).get("dataset");
    const initial = queryId || selectedDataset?.dataset_id || "";
    if (initial) setDatasetId(initial);
  }, [selectedDataset?.dataset_id]);

  useEffect(() => {
    if (!datasetId) { setReadiness(null); setOperation(""); return; }
    const selected = datasets.find((dataset) => dataset.dataset_id === datasetId);
    if (selected) selectDataset(selected);
    Promise.all([api.readiness(datasetId), api.mappings(datasetId)]).then(([readinessResponse, mappingResponse]) => {
      setReadiness(readinessResponse.data); setMappings(mappingResponse.data); setError(null);
      const ready = readinessResponse.data.capabilities.flatMap((capability) => capability.operations).find((item) => operationIsExecutable(item.state));
      setOperation((current) => readinessResponse.data.capabilities.flatMap((capability) => capability.operations).some((item) => item.identifier === current && operationIsExecutable(item.state)) ? current : ready?.identifier || "");
    }).catch((reason) => {
      setReadiness(null); setMappings(null); setOperation("");
      setError(reason instanceof ApiClientError ? reason : new ApiClientError("Dataset readiness could not be loaded.", 0, null));
    });
  }, [datasetId, datasets, selectDataset]);

  const operationItems = readiness?.capabilities.flatMap((capability) => capability.operations) || [];
  const current = operationItems.find((item) => item.identifier === operation);
  const parameterNames = OPERATIONS[operation]?.parameters || [];
  const referenceDate = useMemo(() => mappings?.qualifiers.dataset_reference_date, [mappings]);

  const run = async () => {
    if (!datasetId || !operation) return;
    const parameters: AnalysisParameters = {};
    if (parameterNames.includes("granularity")) parameters.granularity = granularity;
    if (parameterNames.includes("missing_dimension")) parameters.missing_dimension = missingDimension;
    if (parameterNames.includes("as_of_date")) parameters.as_of_date = asOfDate;
    setBusy(true); setError(null); setResult(null);
    try { setResult(await api.analysis(datasetId, operation, parameters)); }
    catch (reason) { setError(reason instanceof ApiClientError ? reason : new ApiClientError("Analysis request failed.", 0, null)); }
    finally { setBusy(false); }
  };

  return <>
    <PageHeader title="Financial analysis" description="Run an approved operation and inspect its exact calculation evidence." />
    {loadingDatasets ? <Panel><div className="panel-body">Loading dataset catalog…</div></Panel> : datasets.length === 0 ? <Panel><EmptyState title="No datasets available" description="Onboard and approve a dataset before running financial analysis." action={<LinkButton href="/datasets/new">Add dataset</LinkButton>} /></Panel> : <div className="split-workspace">
      <Panel><PanelHeader title="Analysis controls" subtitle="Only API-approved options" /><div className="panel-body stack">
        <Field label="Registered dataset" htmlFor="analysis-dataset"><DatasetSelect id="analysis-dataset" datasets={datasets} value={datasetId} onChange={(value) => { setDatasetId(value); setResult(null); }} /></Field>
        <Field label="Operation" htmlFor="analysis-operation" help="Blocked operations remain visible with their exact reason."><OperationSelect options={operationItems} value={operation} onChange={(value) => { setOperation(value); setResult(null); }} /></Field>
        {current && !operationIsExecutable(current.state) && <StateMessage kind="warning" title="Operation blocked" message={current.reasons.map(displayReason).join(" ") || "This capability is not ready for the selected dataset."} />}
        {parameterNames.includes("granularity") && <Field label="Period granularity" htmlFor="granularity"><Select id="granularity" value={granularity} onChange={(event) => setGranularity(event.target.value as "MONTH" | "YEAR")}><option value="MONTH">Month</option><option value="YEAR">Year</option></Select></Field>}
        {parameterNames.includes("missing_dimension") && <Field label="Missing dimension policy" htmlFor="missing-dimension"><Select id="missing-dimension" value={missingDimension} onChange={(event) => setMissingDimension(event.target.value as "BUCKET" | "EXCLUDE")}><option value="BUCKET">Bucket</option><option value="EXCLUDE">Exclude</option></Select></Field>}
        {parameterNames.includes("as_of_date") && <Field label="As-of date" htmlFor="as-of-date" help={referenceDate ? `Approved dataset reference date: ${referenceDate}. The request must match it exactly.` : "Use the explicitly approved observation date; today is never substituted."}><Input id="as-of-date" type="date" value={asOfDate} onChange={(event) => setAsOfDate(event.target.value)} /></Field>}
        <Button onClick={run} disabled={busy || !datasetId || !operation || !current || !operationIsExecutable(current.state) || (parameterNames.includes("as_of_date") && !asOfDate)}><Play size={15} /> {busy ? "Running…" : "Run analysis"}</Button>
        {readiness && <div><div className="eyebrow">Operation readiness</div>{operationItems.map((item) => <div className="operation-row" key={item.identifier}><div><strong>{OPERATIONS[item.identifier]?.label || humanize(item.identifier)}</strong>{item.reasons.map((reason) => <div className="reason" key={reason}>{displayReason(reason)}<details className="inline-technical"><summary>Technical code</summary><code>{reason}</code></details></div>)}</div><StatusBadge status={item.state} /></div>)}</div>}
      </div></Panel>
      <div className="stack">
        {error && <StateMessage kind={error.status === "CLARIFICATION_REQUIRED" || error.status === "BLOCKED" || error.status === "DATA_QUALITY_BLOCKER" ? "warning" : "error"} title={displayStatus(error.status)} message={error.message} />}
        {result ? <EvidenceRenderer status={result.status} evidence={result.evidence} limitations={result.limitations} /> : <Panel><EmptyState title="No analysis result" description="Select an exact dataset and a ready operation. Results, coverage, limitations and lineage will appear here." /></Panel>}
      </div>
    </div>}
  </>;
}
