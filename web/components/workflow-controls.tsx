import { Button, Select } from "./ui";
import { OPERATIONS, operationIsExecutable } from "@/lib/operations";
import { humanize } from "@/lib/format";

export interface OperationOption {
  identifier: string;
  state: string;
}

export function OperationSelect({ options, value, onChange }: { options: OperationOption[]; value: string; onChange: (value: string) => void }) {
  return <Select id="analysis-operation" value={value} onChange={(event) => onChange(event.target.value)}><option value="">Select available operation</option>{options.map((item) => <option key={item.identifier} value={item.identifier} disabled={!operationIsExecutable(item.state)}>{OPERATIONS[item.identifier]?.label || humanize(item.identifier)} · {item.state}</option>)}</Select>;
}

export function ClarificationPrompt({ value, onChange, onSubmit, choices = [], busy = false }: { value: string; onChange: (value: string) => void; onSubmit: () => void; choices?: string[]; busy?: boolean }) {
  return <div className="clarification"><h3>Clarification required</h3><p className="muted">Provide one of the bounded choices requested by the Financial Manager.</p>{choices.length ? <Select aria-label="Clarification answer" value={value} onChange={(event) => onChange(event.target.value)}><option value="">Select a choice</option>{choices.map((choice) => <option key={choice}>{choice}</option>)}</Select> : <input className="input" aria-label="Clarification answer" value={value} onChange={(event) => onChange(event.target.value)} />}<div style={{ marginTop: 8 }}><Button onClick={onSubmit} disabled={!value.trim() || busy}>Submit clarification</Button></div></div>;
}

export function nextOnboardingStep(step: 1 | 2 | 3 | 4): 2 | 3 | 4 | 5 {
  return (step + 1) as 2 | 3 | 4 | 5;
}
