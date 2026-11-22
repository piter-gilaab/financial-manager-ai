"use client";

import { useEffect, useMemo, useState } from "react";
import { ScanSearch } from "lucide-react";
import { ApiClientError, api } from "@/lib/api-client";
import { evidenceRoot, withoutPrivatePaths } from "@/lib/evidence";
import type { ExecutionEnvelope, Readiness } from "@/lib/types";
import { isRecord } from "@/lib/types";
import { displayDecimal, displayMoney } from "@/lib/format";
import { useWorkspace } from "@/components/workspace-provider";
import { Button, EmptyState, Field, PageHeader, Panel, PanelHeader, SafeJson, Select, StateMessage, StatusBadge } from "@/components/ui";

export default function AnomaliesPage() {
  const { datasets, selectDataset } = useWorkspace();
  const eligible = datasets.filter((dataset) => dataset.approved_domain === "SALES_RECORD");
  const [datasetId, setDatasetId] = useState("");
  const [operation, setOperation] = useState("");
  const [readiness, setReadiness] = useState<Readiness | null>(null);
  const [result, setResult] = useState<ExecutionEnvelope | null>(null);
  const [error, setError] = useState<ApiClientError | null>(null);
  const [busy, setBusy] = useState(false);
  const [selectedCandidate, setSelectedCandidate] = useState<Record<string, unknown> | null>(null);
  const [detailMode, setDetailMode] = useState<"why_selected" | "record_detail">("why_selected");

  useEffect(() => {
    if (!datasetId) { setReadiness(null); setOperation(""); return; }
    api.readiness(datasetId).then((response) => {
      setReadiness(response.data);
      const anomaly = response.data.capabilities.find((capability) => capability.identifier === "ANOMALY_DETECTION");
      const firstReady = anomaly?.operations.find((item) => item.state === "SUPPORTED" || item.state === "READY");
      setOperation((current) => anomaly?.operations.some((item) => item.identifier === current && (item.state === "SUPPORTED" || item.state === "READY")) ? current : firstReady?.identifier || "");
      setError(null);
    }).catch((reason) => setError(reason instanceof ApiClientError ? reason : new ApiClientError("Anomaly readiness could not be loaded.", 0, null)));
  }, [datasetId]);

  const screening = useMemo(() => result ? evidenceRoot(result.evidence) : {}, [result]);
  const body = isRecord(screening.result) ? screening.result : {};
  const assessments = Array.isArray(body.assessments) ? body.assessments.filter(isRecord) : [];
  const candidates = assessments.filter((item) => item.status === "CANDIDATE");
  const currency = isRecord(body.currency) ? body.currency : null;
  const anomalyCapability = readiness?.capabilities.find((capability) => capability.identifier === "ANOMALY_DETECTION");
  const operationItems = anomalyCapability?.operations || [];
  const currentOperation = operationItems.find((item) => item.identifier === operation);
  const operationReady = currentOperation?.state === "SUPPORTED" || currentOperation?.state === "READY";

  const run = async () => {
    if (!datasetId) return;
    setBusy(true); setError(null); setResult(null); setSelectedCandidate(null);
    try { setResult(await api.anomaly(datasetId, operation)); }
    catch (reason) { setError(reason instanceof ApiClientError ? reason : new ApiClientError("Anomaly screen failed.", 0, null)); }
    finally { setBusy(false); }
  };

  return <>
    <PageHeader title="Anomalies" description="Statistical candidates for review — never fraud, error, suspicion or risk classification." />
    {eligible.length === 0 ? <Panel><EmptyState title="No eligible Sales Record dataset" description="Sales and Profit anomaly screening is available only for approved SALES_RECORD datasets with operation-specific readiness." kind="blocked" /></Panel> : <div className="stack">
      <Panel><PanelHeader title="Screen controls" subtitle="GLOBAL Tukey-IQR policy from backend authority" /><div className="panel-body form-row">
        <Field label="Sales Record dataset" htmlFor="anomaly-dataset"><Select id="anomaly-dataset" value={datasetId} onChange={(event) => { const id = event.target.value; setDatasetId(id); setResult(null); const dataset = eligible.find((item) => item.dataset_id === id); if (dataset) selectDataset(dataset); }}><option value="">Select exact dataset</option>{eligible.map((dataset) => <option key={dataset.dataset_id} value={dataset.dataset_id}>{dataset.source_filename} · {dataset.dataset_id} · {dataset.readiness_state}</option>)}</Select></Field>
        <Field label="Measure" htmlFor="anomaly-operation"><Select id="anomaly-operation" value={operation} onChange={(event) => setOperation(event.target.value)}><option value="">Select ready screen</option>{operationItems.map((item) => <option key={item.identifier} value={item.identifier} disabled={item.state !== "SUPPORTED" && item.state !== "READY"}>{item.identifier === "SALES_ANOMALY_SCREEN" ? "Sales" : "Profit"} · {item.state}</option>)}</Select></Field>
        <div><Button onClick={run} disabled={!datasetId || !operation || !operationReady || busy}><ScanSearch size={16} /> {busy ? "Screening…" : "Screen candidates"}</Button></div>
      </div></Panel>
      {anomalyCapability && anomalyCapability.state !== "AVAILABLE_WITH_LIMITATIONS" && anomalyCapability.state !== "AVAILABLE" && <StateMessage kind="warning" title="Anomaly screening blocked" message={anomalyCapability.reasons.join(" ") || "The backend did not approve anomaly screening for this dataset."} />}
      {error && <StateMessage kind={error.status.includes("BLOCK") ? "warning" : "error"} title={error.status.replaceAll("_", " ")} message={error.message} />}
      {result && <>
        <div className="meta-strip"><div className="meta-item"><span className="micro">Status</span><span className="meta-value"><StatusBadge status={result.status} /></span></div><div className="meta-item"><span className="micro">Measure</span><span className="meta-value">{String(body.measure || "—")}</span></div><div className="meta-item"><span className="micro">Candidates</span><span className="meta-value tabular">{candidates.length}</span></div><div className="meta-item"><span className="micro">Policy</span><span className="meta-value">{isRecord(body.policy) ? `${body.policy.name} v${body.policy.version}` : "—"}</span></div></div>
        <Panel><PanelHeader title="Methodology evidence" subtitle="Fences are returned by the backend; the browser does not recompute them" /><div className="panel-body evidence-grid">{["q1", "q3", "iqr", "lower_fence", "upper_fence"].map((key) => <div className="evidence-value" key={key}><span className="micro">{key.replaceAll("_", " ")}</span><strong>{displayDecimal(body[key] as string)}</strong></div>)}</div></Panel>
        {candidates.length === 0 ? <Panel><EmptyState title="No statistical candidates" description="The authoritative screen completed without selecting a candidate under the identified policy." /></Panel> : <div className="candidate-layout">
          <Panel><PanelHeader title="Candidate table" subtitle="Statistical candidates for review" /><div className="table-wrap"><table className="table"><thead><tr><th>Candidate reference</th><th>Observed value</th><th>Tail</th><th>Status</th><th></th></tr></thead><tbody>{candidates.map((candidate) => <tr key={String(candidate.canonical_record_id)}><td><span className="truncate-id" title={String(candidate.canonical_record_id)}>{String(candidate.canonical_record_id)}</span><div className="micro">Source row {String(candidate.source_row_number)}</div></td><td className="numeric">{displayMoney(String(candidate.observed_value), currency as { status?: string; code?: string | null })}</td><td>{String(candidate.tail || "—")}</td><td><StatusBadge status="CANDIDATE" /></td><td><Button variant="ghost" onClick={() => setSelectedCandidate(candidate)}>Inspect</Button></td></tr>)}</tbody></table></div></Panel>
          <Panel><PanelHeader title="Candidate detail" subtitle="Evidence only; no causal inference" /><div className="panel-body">{selectedCandidate ? <div className="stack"><div><span className="micro">Observed value</span><h2 className="tabular">{displayMoney(String(selectedCandidate.observed_value), currency as { status?: string; code?: string | null })}</h2></div><div className="operation-row"><span>Status</span><StatusBadge status={String(selectedCandidate.status)} /></div><div className="operation-row"><span>Reference tail</span><strong>{String(selectedCandidate.tail || "—")}</strong></div><div style={{ display: "flex", gap: 7 }}><Button variant={detailMode === "why_selected" ? "primary" : "secondary"} onClick={() => setDetailMode("why_selected")}>Why selected</Button><Button variant={detailMode === "record_detail" ? "primary" : "secondary"} onClick={() => setDetailMode("record_detail")}>Record detail</Button></div>{detailMode === "why_selected" ? <SafeJson value={withoutPrivatePaths({ observed_value: selectedCandidate.observed_value, tail: selectedCandidate.tail, policy: body.policy, reference: body.reference })} /> : <SafeJson value={withoutPrivatePaths({ canonical_record_id: selectedCandidate.canonical_record_id, source_sheet: selectedCandidate.source_sheet, source_row_number: selectedCandidate.source_row_number, observed_raw: selectedCandidate.observed_raw, observed_status: selectedCandidate.observed_status, quality_warning_indices: selectedCandidate.quality_warning_indices })} />}</div> : <p className="muted">Choose a candidate to inspect its bounded record projection and policy evidence.</p>}</div></Panel>
        </div>}
        <div className="grid-2"><Panel><PanelHeader title="Coverage" subtitle="Assessed and excluded population" /><div className="panel-body"><SafeJson value={body.counts || body.quality || {}} /></div></Panel><Panel><PanelHeader title="Policy and limitations" subtitle="Candidate-only framing" /><div className="panel-body"><ul className="notice-list">{[...(Array.isArray(body.limitations) ? body.limitations : []), ...result.limitations].map((item) => <li key={String(item)}>{String(item)}</li>)}</ul></div></Panel></div>
      </>}
    </div>}
  </>;
}
