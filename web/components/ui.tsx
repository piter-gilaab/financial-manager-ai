import Link from "next/link";
import { AlertCircle, Ban, CircleHelp, Database, LoaderCircle, TriangleAlert } from "lucide-react";
import type { ButtonHTMLAttributes, HTMLAttributes, InputHTMLAttributes, SelectHTMLAttributes } from "react";

export function Button({ variant = "primary", className = "", ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "ghost" }) {
  return <button className={`button button-${variant} ${className}`} {...props} />;
}

export function LinkButton({ href, children, variant = "primary" }: { href: string; children: React.ReactNode; variant?: "primary" | "secondary" | "ghost" }) {
  return <Link className={`button button-${variant}`} href={href}>{children}</Link>;
}

export function Badge({ children, tone }: { children: React.ReactNode; tone?: string }) {
  const normalized = (tone || String(children)).toLowerCase().replaceAll("_", "-");
  return <span className={`badge ${normalized}`}>{children}</span>;
}

export function StatusBadge({ status }: { status: string }) {
  const labels: Record<string, string> = {
    CLARIFICATION_REQUIRED: "Requires confirmation",
    DATA_QUALITY_BLOCKER: "Blocked",
    API_UNAVAILABLE: "API unavailable",
  };
  return <Badge tone={status}>{labels[status] || status.replaceAll("_", " ")}</Badge>;
}

export function Panel({ children, className = "", ...props }: HTMLAttributes<HTMLDivElement>) {
  return <section className={`panel ${className}`} {...props}>{children}</section>;
}

export function PanelHeader({ title, action, subtitle }: { title: string; action?: React.ReactNode; subtitle?: string }) {
  return <header className="panel-header"><div><h2>{title}</h2>{subtitle && <div className="micro">{subtitle}</div>}</div>{action}</header>;
}

export function SectionHeader({ title, description, action }: { title: string; description?: string; action?: React.ReactNode }) {
  return <div className="section-header"><div><h2>{title}</h2>{description && <p className="muted">{description}</p>}</div>{action}</div>;
}

export function PageHeader({ title, description, action, eyebrow }: { title: string; description: string; action?: React.ReactNode; eyebrow?: string }) {
  return <header className="page-header"><div>{eyebrow && <div className="eyebrow">{eyebrow}</div>}<h1>{title}</h1><p className="muted">{description}</p></div>{action}</header>;
}

export function Field({ label, htmlFor, help, error, children }: { label: string; htmlFor: string; help?: string; error?: string; children: React.ReactNode }) {
  return <div className="field"><label htmlFor={htmlFor}>{label}</label>{children}{help && <span className="field-help">{help}</span>}{error && <span className="field-error" id={`${htmlFor}-error`}>{error}</span>}</div>;
}

export function Input(props: InputHTMLAttributes<HTMLInputElement>) { return <input className="input" {...props} />; }
export function Select(props: SelectHTMLAttributes<HTMLSelectElement>) { return <select className="select" {...props} />; }

export function LoadingState({ label = "Loading workspace data" }: { label?: string }) {
  return <div className="panel panel-body stack" role="status" aria-live="polite"><div className="skeleton" style={{ width: "28%" }} /><div className="skeleton" /><div className="skeleton" style={{ width: "72%" }} /><span className="micro"><LoaderCircle size={12} aria-hidden /> {label}</span></div>;
}

export function StateMessage({ kind = "info", title, message, action }: { kind?: "info" | "warning" | "error"; title: string; message: string; action?: React.ReactNode }) {
  const Icon = kind === "error" ? AlertCircle : kind === "warning" ? TriangleAlert : CircleHelp;
  return <div className={`state ${kind}`} role={kind === "error" ? "alert" : "status"}><Icon size={20} aria-hidden /><div><h3>{title}</h3><p>{message}</p>{action && <div style={{ marginTop: 12 }}>{action}</div>}</div></div>;
}

export function EmptyState({ title, description, action, kind = "database" }: { title: string; description: string; action?: React.ReactNode; kind?: "database" | "blocked" }) {
  const Icon = kind === "blocked" ? Ban : Database;
  return <div className="empty-state"><span className="empty-icon"><Icon size={21} aria-hidden /></span><h2>{title}</h2><p className="muted" style={{ maxWidth: 480 }}>{description}</p>{action}</div>;
}

export function SafeJson({ value }: { value: unknown }) {
  return <pre className="code-grid">{JSON.stringify(value, null, 2)}</pre>;
}
