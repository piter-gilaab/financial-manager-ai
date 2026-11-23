import { Button, Select } from "./ui";
import { OPERATIONS, operationIsExecutable } from "@/lib/operations";
import { humanize } from "@/lib/format";
import type { DatasetSummary } from "@/lib/types";
import { displayDomain, displayStatus, shortDatasetId } from "@/lib/presentation";

export interface OperationOption {
  identifier: string;
  state: string;
}

export function OperationSelect({ options, value, onChange }: { options: OperationOption[]; value: string; onChange: (value: string) => void }) {
  return <Select id="analysis-operation" value={value} onChange={(event) => onChange(event.target.value)}><option value="">Select available operation</option>{options.map((item) => <option key={item.identifier} value={item.identifier} disabled={!operationIsExecutable(item.state)}>{OPERATIONS[item.identifier]?.label || humanize(item.identifier)} · {displayStatus(item.state)}</option>)}</Select>;
}

export function DatasetSelect({ id, datasets, value, onChange, disabled = false }: { id: string; datasets: DatasetSummary[]; value: string; onChange: (value: string) => void; disabled?: boolean }) {
  const selected = datasets.find((dataset) => dataset.dataset_id === value) || null;
  return <>
    <Select id={id} value={value} onChange={(event) => onChange(event.target.value)} disabled={disabled}>
      <option value="">Select dataset</option>
      {datasets.map((dataset) => <option key={dataset.dataset_id} value={dataset.dataset_id}>{dataset.source_filename} · {shortDatasetId(dataset.dataset_id)}</option>)}
    </Select>
    {selected && <dl className="dataset-selection" aria-label="Selected dataset details">
      <div><dt>Domain</dt><dd>{displayDomain(selected.approved_domain)}</dd></div>
      <div><dt>Readiness</dt><dd>{displayStatus(selected.readiness_state)}</dd></div>
      <div><dt>Dataset ID</dt><dd><details><summary>{shortDatasetId(selected.dataset_id)}</summary><code>{selected.dataset_id}</code></details></dd></div>
    </dl>}
  </>;
}

export function ClarificationPrompt({ value, onChange, onSubmit, choices = [], busy = false }: { value: string; onChange: (value: string) => void; onSubmit: () => void; choices?: string[]; busy?: boolean }) {
  return <div className="clarification"><h3>Clarification required</h3><p className="muted">Provide one of the bounded choices requested by the Financial Manager.</p>{choices.length ? <Select aria-label="Clarification answer" value={value} onChange={(event) => onChange(event.target.value)}><option value="">Select a choice</option>{choices.map((choice) => <option key={choice}>{choice}</option>)}</Select> : <input className="input" aria-label="Clarification answer" value={value} onChange={(event) => onChange(event.target.value)} />}<div style={{ marginTop: 8 }}><Button onClick={onSubmit} disabled={!value.trim() || busy}>Submit clarification</Button></div></div>;
}

export function nextOnboardingStep(step: 1 | 2 | 3 | 4): 2 | 3 | 4 | 5 {
  return (step + 1) as 2 | 3 | 4 | 5;
}
