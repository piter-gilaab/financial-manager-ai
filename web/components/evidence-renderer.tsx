"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { displayCurrencyState, displayDecimal, displayMoney, humanize } from "@/lib/format";
import { evidenceRoot, toChartData, withoutPrivatePaths } from "@/lib/evidence";
import { isRecord } from "@/lib/types";
import { Panel, PanelHeader, SafeJson, StateMessage, StatusBadge } from "./ui";

function ExactTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload?: { label?: string; exact?: string } }> }) {
  const item = payload?.[0]?.payload;
  if (!active || !item) return null;
  return <div className="panel-body panel"><strong>{item.label}</strong><div className="tabular">Exact: {item.exact}</div></div>;
}

function ExactTable({ rows }: { rows: Record<string, unknown>[] }) {
  if (!rows.length) return null;
  const columns = Array.from(new Set(rows.flatMap((row) => Object.keys(row)))).slice(0, 12);
  return <div className="table-wrap"><table className="table"><thead><tr>{columns.map((column) => <th key={column}>{humanize(column)}</th>)}</tr></thead><tbody>{rows.map((row, index) => <tr key={String(row.id || row.reference || index)}>{columns.map((column) => <td key={column} className={typeof row[column] === "number" || (typeof row[column] === "string" && /^-?\d/.test(row[column] as string)) ? "numeric" : ""}>{isRecord(row[column]) || Array.isArray(row[column]) ? <code>{JSON.stringify(row[column])}</code> : displayDecimal(row[column] as string | number | null)}</td>)}</tr>)}</tbody></table></div>;
}

function MeasureGrid({ measures, currency }: { measures: Record<string, unknown>; currency: Record<string, unknown> | null }) {
  const values = Object.entries(measures).flatMap(([measure, detail]) => {
    if (!isRecord(detail)) return [{ label: measure, value: detail }];
    return Object.entries(detail).filter(([key, value]) => !["coverage", "lineage", "limitations"].includes(key) && (typeof value === "string" || typeof value === "number")).map(([key, value]) => ({ label: `${measure} ${key}`, value }));
  });
  return <div className="evidence-grid">{values.map(({ label, value }) => {
    const monetary = !/(unit|count|status|code)$/i.test(label) && /(amount|sales|profit|cash|sum|average|median|balance|total)/i.test(label);
    return <div className="evidence-value" key={label}><span className="micro">{humanize(label)}</span><strong>{monetary && typeof value === "string" ? displayMoney(value, currency as { status?: string; code?: string | null }) : displayDecimal(value as string | number)}</strong></div>;
  })}</div>;
}

export function EvidenceRenderer({ status, evidence, limitations = [] }: { status: string; evidence: unknown; limitations?: string[] }) {
  const root = evidenceRoot(evidence);
  const result = isRecord(root.result) ? root.result : root;
  const currency = isRecord(root.currency) ? root.currency : null;
  const groupsValue = result.groups ?? result.buckets ?? result.candidates ?? root.candidates;
  const rows = Array.isArray(groupsValue) ? groupsValue.filter(isRecord) : [];
  const chartData = toChartData(rows);
  const measures = isRecord(result.measures) ? result.measures : null;
  const measureRows = measures ? Object.entries(measures).map(([measure, value]) => ({
    measure,
    ...(isRecord(value)
      ? Object.fromEntries(Object.entries(value).filter(([, item]) => typeof item === "string" || typeof item === "number" || item === null))
      : { value }),
  })) : [];
  const metadata = isRecord(root.metadata) ? root.metadata : null;
  const groupedCoverage = {
    ...(isRecord(result.dimension_coverage) ? { dimension_coverage: result.dimension_coverage } : {}),
    ...(isRecord(result.measure_coverage) ? { measure_coverage: result.measure_coverage } : {}),
  };
  const coverage = measures
    ? Object.fromEntries(Object.entries(measures).flatMap(([key, value]) => isRecord(value) && isRecord(value.coverage) ? [[key, value.coverage]] : []))
    : (Object.keys(groupedCoverage).length ? groupedCoverage : isRecord(result.coverage) ? result.coverage : null);
  const rootLimitations = Array.isArray(root.limitations) ? root.limitations.filter((item): item is string => typeof item === "string") : [];
  const allLimitations = Array.from(new Set([...limitations, ...rootLimitations]));
  const queryName = typeof root.query_name === "string" ? root.query_name : "";
  const temporalOrAging = /PERIOD|AGING/.test(queryName);

  return <div className="stack">
    <div className="result-header"><div><div className="eyebrow">Authoritative backend evidence</div><h2 style={{ margin: "4px 0 0" }}>{typeof root.query_name === "string" ? humanize(root.query_name) : "Analysis result"}</h2></div><StatusBadge status={status} /></div>
    {currency && <div className="meta-strip"><div className="meta-item"><span className="micro">Currency context</span><span className="meta-value">{displayCurrencyState(String(currency.status || currency.state || "UNKNOWN"), typeof currency.code === "string" ? currency.code : null)}</span></div></div>}
    {status === "NO_DATA" && <StateMessage title="No data" message="The operation completed but returned no applicable evidence for the approved source." />}
    {measures && <Panel><PanelHeader title="Primary evidence" subtitle="Exact API values" /><div className="panel-body"><MeasureGrid measures={measures} currency={currency} /></div></Panel>}
    {measureRows.length > 0 && <Panel><PanelHeader title="Exact evidence table" subtitle="Authoritative text and count fields" /><ExactTable rows={measureRows} /></Panel>}
    {chartData.length > 0 && <Panel><PanelHeader title="Presentation view" subtitle="Geometry only; exact values remain in tooltip and table" /><div className="panel-body"><div className="chart" aria-label="Presentation-only chart"><ResponsiveContainer width="100%" height="100%">{temporalOrAging ? <BarChart data={chartData} margin={{ left: 12, right: 16, top: 10, bottom: 36 }}><CartesianGrid stroke="#e1e5e1" vertical={false} /><XAxis dataKey="label" angle={-20} textAnchor="end" interval={0} height={60} tick={{ fontSize: 11 }} /><YAxis tick={{ fontSize: 11 }} /><Tooltip content={<ExactTooltip />} /><Bar dataKey="coordinate" fill="#24624d" maxBarSize={46} /></BarChart> : <BarChart data={chartData} layout="vertical" margin={{ left: 12, right: 24, top: 10, bottom: 10 }}><CartesianGrid stroke="#e1e5e1" horizontal={false} /><XAxis type="number" tick={{ fontSize: 11 }} /><YAxis type="category" dataKey="label" width={112} tick={{ fontSize: 11 }} /><Tooltip content={<ExactTooltip />} /><Bar dataKey="coordinate" fill="#24624d" maxBarSize={30} /></BarChart>}</ResponsiveContainer></div></div></Panel>}
    {rows.length > 0 && <Panel><PanelHeader title="Exact evidence table" subtitle={`${rows.length} evidence rows returned`} /><ExactTable rows={rows} /></Panel>}
    {!measures && rows.length === 0 && Object.keys(result).length > 0 && <Panel><PanelHeader title="Exact evidence" subtitle="Bounded structured response" /><div className="panel-body"><SafeJson value={withoutPrivatePaths(result)} /></div></Panel>}
    <div className="grid-2">
      <Panel><PanelHeader title="Coverage" subtitle="Population, exclusions and parsing quality" /><div className="panel-body">{coverage && Object.keys(coverage).length ? <SafeJson value={coverage} /> : <p className="muted">No separate coverage object was returned for this evidence shape.</p>}</div></Panel>
      <Panel><PanelHeader title="Limitations" subtitle="Backend-authored constraints" /><div className="panel-body">{allLimitations.length ? <ul className="notice-list">{allLimitations.map((item) => <li key={item}>{item}</li>)}</ul> : <p className="muted">No additional limitations were returned.</p>}</div></Panel>
    </div>
    <Panel><div className="panel-body lineage"><details><summary>Technical lineage and reproducibility</summary>{metadata ? <SafeJson value={withoutPrivatePaths(metadata)} /> : <p className="muted" style={{ marginTop: 10 }}>No separate metadata object was returned.</p>}</details></div></Panel>
  </div>;
}
