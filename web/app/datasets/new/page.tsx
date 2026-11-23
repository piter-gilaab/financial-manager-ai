"use client";

import { ChangeEvent, DragEvent, useEffect, useRef, useState } from "react";
import { ArrowRight, UploadCloud } from "lucide-react";
import { ApiClientError, api } from "@/lib/api-client";
import { operationIsExecutable } from "@/lib/operations";
import type { DatasetProfile, DatasetSummary, Readiness, SemanticMapping } from "@/lib/types";
import { displayCurrencyState, fileSize, humanize } from "@/lib/format";
import { displayReason } from "@/lib/presentation";
import { useWorkspace } from "@/components/workspace-provider";
import { nextOnboardingStep } from "@/components/workflow-controls";
import { MappingRow, type MappingOptions } from "@/components/semantic-mapping-row";
import { ApprovalReview, DomainConfirmation, EMPTY_DECISION_EVIDENCE } from "@/components/onboarding-approval";
import { Button, Field, Input, LinkButton, PageHeader, Panel, PanelHeader, Select, StateMessage, StatusBadge } from "@/components/ui";

type Step = 1 | 2 | 3 | 4 | 5 | 6;

const STEP_LABELS = ["Upload", "Profile", "Semantics", "Confirm", "Review", "Ready"];

export default function OnboardingPage() {
  const [step, setStep] = useState<Step>(1);
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sheetChoices, setSheetChoices] = useState<string[]>([]);
  const [selectedSheet, setSelectedSheet] = useState("");
  const [dataset, setDataset] = useState<DatasetSummary | null>(null);
  const [profile, setProfile] = useState<DatasetProfile | null>(null);
  const [mappings, setMappings] = useState<SemanticMapping | null>(null);
  const [readiness, setReadiness] = useState<Readiness | null>(null);
  const [evidence, setEvidence] = useState(EMPTY_DECISION_EVIDENCE);
  const [evidenceError, setEvidenceError] = useState<string | null>(null);
  const evidenceRef = useRef<HTMLInputElement>(null);
  const { refreshDatasets, selectDataset } = useWorkspace();

  const refreshCurrent = async (id: string) => {
    const [detail, profileResponse, mappingResponse, readinessResponse] = await Promise.all([
      api.dataset(id), api.profile(id), api.mappings(id), api.readiness(id),
    ]);
    setDataset(detail.data); setProfile(profileResponse.data); setMappings(mappingResponse.data); setReadiness(readinessResponse.data); selectDataset(detail.data);
  };

  const requireEvidence = () => {
    if (evidence.trim()) { setEvidenceError(null); return true; }
    setEvidenceError("Enter the source, owner record or policy that supports this financial decision.");
    window.requestAnimationFrame(() => evidenceRef.current?.focus());
    return false;
  };

  useEffect(() => {
    const existing = new URLSearchParams(window.location.search).get("dataset");
    if (existing) {
      setBusy(true);
      refreshCurrent(existing).then(() => setStep(3)).catch((reason) => setError(reason instanceof Error ? reason.message : "Dataset could not be resumed.")).finally(() => setBusy(false));
    }
  // The exact URL is only inspected once to resume a registered dataset.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const acceptFile = (candidate?: File) => {
    if (!candidate) return;
    if (!/\.(csv|xlsx)$/i.test(candidate.name)) { setError("Select a CSV or XLSX file."); return; }
    setFile(candidate); setError(null); setSheetChoices([]); setSelectedSheet("");
  };

  const onDrop = (event: DragEvent<HTMLLabelElement>) => {
    event.preventDefault(); setDragging(false); acceptFile(event.dataTransfer.files[0]);
  };

  const upload = async () => {
    if (!file) return;
    setBusy(true); setError(null);
    try {
      const response = await api.upload(file, selectedSheet || undefined, "Local web onboarding");
      setDataset(response.data.dataset); setProfile(response.data.profile); setMappings(response.data.mappings); selectDataset(response.data.dataset); setStep(2); await refreshDatasets();
    } catch (reason) {
      if (reason instanceof ApiClientError && reason.status === "CLARIFICATION_REQUIRED") {
        setSheetChoices(reason.body?.data?.choices || []);
        setError(null);
      } else setError(reason instanceof Error ? reason.message : "Upload could not be completed.");
    } finally { setBusy(false); }
  };

  const decide = async (proposal: SemanticMapping["proposals"][number], decision: "CONFIRM" | "CORRECT" | "REJECT", role?: string, options: MappingOptions = {}) => {
    if (!dataset || !requireEvidence()) return;
    setBusy(true); setError(null);
    try {
      await api.semanticDecision(dataset.dataset_id, {
        column: proposal.source_column, decision, role: decision === "REJECT" ? undefined : role,
        evidence, value_mapping: options.valueMapping, date_format: options.dateFormat,
      });
      await refreshCurrent(dataset.dataset_id);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Semantic decision was rejected."); }
    finally { setBusy(false); }
  };

  const confirmDomain = async (domain: string) => {
    if (!dataset || !requireEvidence()) return;
    setBusy(true); setError(null);
    try { await api.confirmDomain(dataset.dataset_id, domain, evidence); await refreshCurrent(dataset.dataset_id); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Domain could not be confirmed."); }
    finally { setBusy(false); }
  };

  const confirmQualifiers = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault(); if (!dataset || !requireEvidence()) return;
    const form = new FormData(event.currentTarget);
    const body = Object.fromEntries([...form.entries()].filter(([, value]) => value).map(([key, value]) => [key, String(value)]));
    setBusy(true); setError(null);
    try { await api.confirmQualifiers(dataset.dataset_id, { ...body, evidence }); await refreshCurrent(dataset.dataset_id); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Qualifiers could not be confirmed."); }
    finally { setBusy(false); }
  };

  const operations = readiness?.capabilities.flatMap((capability) => capability.operations) || [];
  const readyOperations = operations.filter((operation) => operationIsExecutable(operation.state));
  const suggestedDomain = mappings?.domain_suggestions[0];
  const evidenceControl = <Field label="Decision evidence" htmlFor="mapping-evidence" help="Describe the source, owner record or policy that supports the decision. This text is saved with each authority-changing action." error={evidenceError || undefined}><Input ref={evidenceRef} id="mapping-evidence" value={evidence} placeholder="Example: Accounts payable export specification approved 2026-11-22" onChange={(event) => { setEvidence(event.target.value); if (event.target.value.trim()) setEvidenceError(null); }} maxLength={1000} aria-invalid={Boolean(evidenceError)} aria-describedby={`mapping-evidence-help${evidenceError ? " mapping-evidence-error" : ""}`} /></Field>;

  return <>
    <PageHeader title="Dataset onboarding" description="Safe ingestion, deterministic profile and explicit financial meaning approval." eyebrow="Controlled workflow" />
    <div className="steps" aria-label="Onboarding progress">{STEP_LABELS.map((label, index) => <div key={label} className={`step ${step === index + 1 ? "active" : step > index + 1 ? "complete" : ""}`} aria-current={step === index + 1 ? "step" : undefined}><strong>0{index + 1}</strong>{label}</div>)}</div>
    {error && <div style={{ marginBottom: 16 }}><StateMessage kind="error" title="Request not completed" message={error} /></div>}
    {busy && <div className="progress" role="progressbar" aria-label="Processing onboarding request" />}

    {step === 1 && <Panel><PanelHeader title="Upload local source" subtitle="CSV or constrained XLSX · maximum 10 MB" /><div className="panel-body stack">
      <label className={`dropzone ${dragging ? "dragging" : ""}`} onDragOver={(event) => { event.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={onDrop}>
        <input type="file" accept=".csv,.xlsx" onChange={(event: ChangeEvent<HTMLInputElement>) => acceptFile(event.target.files?.[0])} />
        <span className="empty-icon"><UploadCloud size={22} /></span>
        <strong>{file ? file.name : "Drop a source file here"}</strong>
        <span className="muted">{file ? `${file.type || "Detected by extension"} · ${fileSize(file.size)}` : "or choose a file from this device"}</span>
      </label>
      {sheetChoices.length > 0 && <div className="clarification"><h3>Select workbook sheet</h3><p className="muted">The workbook contains multiple safe sheets. Choose one explicitly to continue.</p><Field label="Sheet" htmlFor="sheet"><Select id="sheet" value={selectedSheet} onChange={(event) => setSelectedSheet(event.target.value)}><option value="">Select a sheet</option>{sheetChoices.map((sheet) => <option key={sheet}>{sheet}</option>)}</Select></Field></div>}
      <div><Button onClick={upload} disabled={!file || busy || (sheetChoices.length > 0 && !selectedSheet)}><UploadCloud size={16} /> {sheetChoices.length ? "Upload selected sheet" : "Upload and profile"}</Button></div>
    </div></Panel>}

    {step === 2 && profile && <Panel><PanelHeader title="Deterministic profile" subtitle={`${profile.row_count} rows · ${profile.column_count} columns · profile ${profile.profile_version}`} /><div className="panel-body stack">
      <div className="meta-strip"><div className="meta-item"><span className="micro">Rows</span><span className="meta-value tabular">{profile.row_count}</span></div><div className="meta-item"><span className="micro">Columns</span><span className="meta-value tabular">{profile.column_count}</span></div><div className="meta-item"><span className="micro">Duplicate candidates</span><span className="meta-value tabular">{profile.duplicate_row_candidates}</span></div><div className="meta-item"><span className="micro">Currency state</span><span className="meta-value">{displayCurrencyState(profile.currency_state)}</span></div></div>
      <div className="table-wrap"><table className="table"><thead><tr><th>Source column</th><th>Structural type</th><th>Missing</th><th>Cardinality</th><th>Bounded examples</th></tr></thead><tbody>{profile.columns.map((column) => <tr key={column.column_id}><td><strong>{column.name}</strong></td><td>{column.structural_type}</td><td className="tabular">{column.missing_count} · {column.missing_percentage}%</td><td className="tabular">{column.categorical_cardinality}</td><td>{column.examples.join(" · ") || "—"}</td></tr>)}</tbody></table></div>
      <div><Button onClick={() => setStep(nextOnboardingStep(2))}>Review semantic suggestions <ArrowRight size={16} /></Button></div>
    </div></Panel>}

    {step === 3 && mappings && <div className="stack">
      <StateMessage title="Suggestions require explicit decisions" message="No proposed meaning becomes financial authority until you confirm, correct or reject it." />
      <Panel><PanelHeader title="Semantic mapping" subtitle={`Mapping version ${mappings.mapping_version}`} /><div className="panel-body stack">
        {evidenceControl}
        <div className="semantic-decisions"><table className="table"><thead><tr><th>Source column</th><th>Suggested meaning</th><th>Evidence</th><th>Authority action</th></tr></thead><tbody>{mappings.proposals.map((proposal) => <MappingRow key={proposal.column_id} proposal={proposal} busy={busy} onDecide={decide} />)}</tbody></table></div>
        <div><Button onClick={() => setStep(nextOnboardingStep(3))}>Review domain and qualifiers <ArrowRight size={16} /></Button></div>
      </div></Panel>
    </div>}

    {step === 4 && mappings && <div className="grid-2">
      <Panel><PanelHeader title="Domain confirmation" subtitle="Recognition does not imply executable support" /><div className="panel-body stack">
        {evidenceControl}
        <DomainConfirmation approvedDomain={mappings.approved_domain} suggestedDomain={suggestedDomain} busy={busy} onConfirm={confirmDomain} />
        <p className="field-help">Executable domains remain limited to Sales Record, Accounts Payable, Accounts Receivable and Cash Transactions.</p>
      </div></Panel>
      <Panel><PanelHeader title="Qualifiers and value policy" subtitle="Save only values supported by the same evidence" /><form className="panel-body stack" onSubmit={confirmQualifiers}>
        {(mappings.approved_domain === "PAYABLE" || mappings.approved_domain === "RECEIVABLE") && <>
          <Field label="Amount basis" htmlFor="amount-basis"><Select id="amount-basis" name="amount_basis" defaultValue={mappings.qualifiers.amount_basis || ""}><option value="">Not confirmed</option><option value="OUTSTANDING_BALANCE">Outstanding balance</option></Select></Field>
          <Field label="Dataset reference date" htmlFor="reference-date" help="Approved observation date for aging and overdue analysis. Today is never substituted silently."><Input id="reference-date" name="dataset_reference_date" type="date" defaultValue={mappings.qualifiers.dataset_reference_date || ""} /></Field>
        </>}
        {mappings.approved_domain === "CASH_TRANSACTION" && <Field label="Cash amount convention" htmlFor="cash-convention"><Select id="cash-convention" name="cash_amount_convention" defaultValue={mappings.qualifiers.cash_amount_convention || ""}><option value="">Not confirmed</option><option value="MAGNITUDE_WITH_DIRECTION">Magnitude with confirmed direction</option><option value="SIGNED_WITH_DIRECTION">Signed amount with confirmed direction</option></Select></Field>}
        {(mappings.approved_domain === "PAYABLE" || mappings.approved_domain === "RECEIVABLE" || mappings.approved_domain === "CASH_TRANSACTION") && <div><Button type="submit" disabled={busy}>Save qualifiers</Button></div>}
        <div><Button type="button" variant="secondary" disabled={!mappings.approved_domain || busy} onClick={async () => { if (dataset) await refreshCurrent(dataset.dataset_id); setStep(5); }}>Review saved decisions <ArrowRight size={16} /></Button></div>
      </form></Panel>
    </div>}

    {step === 5 && dataset && mappings && readiness && <ApprovalReview dataset={dataset} mappings={mappings} readiness={readiness} onContinue={() => setStep(6)} />}

    {step === 6 && dataset && readiness && <Panel><PanelHeader title="Operation-specific readiness" subtitle={`${readiness.canonical_domain || "Domain unconfirmed"} · ${displayCurrencyState(readiness.currency.state, readiness.currency.code)}`} /><div className="panel-body stack">
      {operations.length === 0 ? <StateMessage kind="warning" title="No applicable operations" message="Required financial meanings or domain approval remain incomplete." /> : operations.map((operation) => <div className="operation-row" key={operation.identifier}><div><strong>{humanize(operation.identifier)}</strong>{operation.reasons.map((reason) => <div className="reason" key={reason}>{displayReason(reason)}<details className="inline-technical"><summary>Technical code</summary><code>{reason}</code></details></div>)}</div><StatusBadge status={operation.state} /></div>)}
      <div>{readyOperations.length > 0 ? <LinkButton href={`/analysis?dataset=${dataset.dataset_id}`}>Analyze dataset <ArrowRight size={16} /></LinkButton> : <Button variant="secondary" onClick={() => setStep(3)}>Resolve semantic blockers</Button>}</div>
    </div></Panel>}
  </>;
}
