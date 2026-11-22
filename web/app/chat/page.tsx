"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { MessageSquareText, Send } from "lucide-react";
import { ApiClientError, api } from "@/lib/api-client";
import type { SessionProjection } from "@/lib/types";
import { useWorkspace } from "@/components/workspace-provider";
import { ClarificationPrompt } from "@/components/workflow-controls";
import { ChatEvidence } from "@/components/chat-evidence";
import { Button, EmptyState, Field, Input, PageHeader, Panel, PanelHeader, Select, StateMessage, StatusBadge } from "@/components/ui";

interface Message {
  id: number;
  role: "user" | "manager";
  text: string;
  status?: string;
  evidence?: unknown;
  references?: { handle: string; kind: string }[];
}

export default function ChatPage() {
  const { datasets, selectDataset } = useWorkspace();
  const [session, setSession] = useState<SessionProjection | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [clarification, setClarification] = useState("");
  const nextId = useRef(1);
  const messagesRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.createSession().then((response) => setSession(response.data)).catch((reason) => setError(reason instanceof Error ? reason.message : "Session could not be created."));
  }, []);
  useEffect(() => {
    const container = messagesRef.current;
    if (container) container.scrollTop = container.scrollHeight;
  }, [messages]);

  const append = (entry: Omit<Message, "id">) => setMessages((current) => [...current, { ...entry, id: nextId.current++ }]);

  const refreshSession = async (sessionId: string) => {
    const projection = await api.session(sessionId);
    setSession(projection.data);
    const confirmedId = projection.data.dynamic_dataset?.dataset_id;
    const confirmed = datasets.find((item) => item.dataset_id === confirmedId);
    if (confirmed) selectDataset(confirmed);
    return projection.data;
  };

  const applyTurn = (data: { status: string; text: string | null; notice: string | null; outcome: { result?: unknown; error?: unknown; references?: { handle: string; kind: string }[] } | null }) => {
    const outcome = data.outcome;
    append({ role: "manager", text: data.text || data.notice || data.status.replaceAll("_", " "), status: data.status, evidence: outcome?.result || outcome?.error, references: outcome?.references || [] });
  };

  const send = async (event: FormEvent) => {
    event.preventDefault(); if (!session || !message.trim()) return;
    const value = message.trim(); setMessage(""); append({ role: "user", text: value }); setBusy(true); setError(null);
    try { const response = await api.sessionTurn(session.session_id, value); applyTurn(response.data); await refreshSession(session.session_id); }
    catch (reason) { setError(reason instanceof ApiClientError ? reason.message : "The local provider could not complete this turn."); }
    finally { setBusy(false); }
  };

  const chooseDataset = async (datasetId: string) => {
    if (!session || !datasetId) return;
    const dataset = datasets.find((item) => item.dataset_id === datasetId);
    if (!dataset) return;
    setBusy(true); setError(null);
    const instruction = `Use dataset ${dataset.dataset_id}.`;
    append({ role: "user", text: `Set active dataset to ${dataset.source_filename}.` });
    try { const response = await api.sessionTurn(session.session_id, instruction); applyTurn(response.data); await refreshSession(session.session_id); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Dataset context could not be selected."); }
    finally { setBusy(false); }
  };

  const answerClarification = async () => {
    if (!session || !clarification.trim()) return;
    const value = clarification.trim(); setClarification(""); append({ role: "user", text: value }); setBusy(true);
    try {
      const response = await api.answer(session.session_id, value);
      append({ role: "manager", text: response.data.status.replaceAll("_", " "), status: response.data.status, evidence: response.data.outcome.result || response.data.outcome.error, references: response.data.outcome.references });
      setSession(response.data.session);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Clarification could not be submitted."); }
    finally { setBusy(false); }
  };

  const followUp = async (reference: string, intent: "why_selected" | "record_detail") => {
    if (!session) return;
    setBusy(true);
    try {
      const response = await api.followUp(session.session_id, reference, intent);
      append({ role: "manager", text: intent === "why_selected" ? "Why this candidate was selected" : "Bounded record detail", status: response.data.status, evidence: response.data.outcome.result || response.data.outcome.error });
      setSession(response.data.session);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Follow-up could not be completed."); }
    finally { setBusy(false); }
  };

  const clarificationContext = session?.active_context && "pending_clarification" in session.active_context ? session.active_context.pending_clarification : null;
  const sessionDatasetId = session?.dynamic_dataset?.dataset_id || "";
  const sessionDataset = datasets.find((item) => item.dataset_id === sessionDatasetId) || null;

  return <>
    <PageHeader title="Ask Financial Manager" description="Process-local conversation grounded in approved dataset context and backend evidence." />
    <div className="chat-layout">
      <Panel className="conversation"><PanelHeader title="Conversation" subtitle={session ? "Runtime-only session · not authentication" : "Creating local session"} />
        <div className="messages" aria-live="polite" ref={messagesRef}>
          {messages.length === 0 && <EmptyState title="No conversation yet" description="Choose an active dataset, then ask a supported financial question. The transcript remains only in runtime memory and is not persisted." />}
          {messages.map((item) => <article className={`message ${item.role}`} key={item.id}><div className="message-meta">{item.role === "user" ? "You" : "Financial Manager"} {item.status && <>· <StatusBadge status={item.status} /></>}</div><p>{item.text}</p>{item.evidence !== undefined && item.evidence !== null && <ChatEvidence value={item.evidence} />}{item.references && item.references.length > 0 && <div style={{ display: "flex", gap: 7, marginTop: 10, flexWrap: "wrap" }}>{item.references.map((reference) => <span key={reference.handle} style={{ display: "contents" }}><Button variant="secondary" onClick={() => followUp(reference.handle, "why_selected")}>Why selected</Button><Button variant="ghost" onClick={() => followUp(reference.handle, "record_detail")}>Record detail</Button></span>)}</div>}</article>)}
          {clarificationContext && <ClarificationPrompt value={clarification} onChange={setClarification} onSubmit={answerClarification} choices={clarificationContext.choices} busy={busy} />}
          {error && <StateMessage kind="error" title="Provider or API unavailable" message={error} />}
        </div>
        <form className="composer" onSubmit={send}><Input aria-label="Financial question" placeholder="Show payables by supplier." value={message} onChange={(event) => setMessage(event.target.value)} maxLength={2000} disabled={!session || busy} /><Button type="submit" disabled={!session || !message.trim() || busy} aria-label="Send financial question"><Send size={16} /> Send</Button></form>
      </Panel>
      <aside className="chat-context"><Panel><PanelHeader title="Active context" subtitle="Explicit session selection" /><div className="panel-body stack">
        <Field label="Dataset" htmlFor="chat-dataset"><Select id="chat-dataset" value={sessionDatasetId} onChange={(event) => void chooseDataset(event.target.value)} disabled={!session || busy}><option value="">No dataset selected</option>{datasets.map((dataset) => <option key={dataset.dataset_id} value={dataset.dataset_id}>{dataset.source_filename} · {dataset.dataset_id} · {dataset.approved_domain || "UNCONFIRMED"} · {dataset.readiness_state}</option>)}</Select></Field>
        {sessionDataset ? <><div className="operation-row"><span>Domain</span><strong>{sessionDataset.approved_domain || "UNCONFIRMED"}</strong></div><div className="operation-row"><span>Readiness</span><StatusBadge status={sessionDataset.readiness_state} /></div><div><div className="eyebrow">Available capabilities</div>{sessionDataset.supported_operations.length ? sessionDataset.supported_operations.map((operation) => <div className="reason" key={operation}>{operation.replaceAll("_", " ")}</div>) : <p className="muted">No ready operations.</p>}</div></> : <StateMessage title="No active dataset" message="Choose an exact registered dataset. The selection is sent explicitly to the session and shown only after backend confirmation." />}
        <div className="micro"><MessageSquareText size={12} aria-hidden /> Refreshing may create a new process-local session. No transcript is stored in browser persistence.</div>
      </div></Panel></aside>
    </div>
  </>;
}
