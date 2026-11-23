"use client";

import { useId } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { displayCurrencyState, displayDecimal, displayMoney, humanize } from "@/lib/format";
import { displayLimitation, displayStatus } from "@/lib/presentation";
import { evidenceRoot, toChartData, withoutPrivatePaths } from "@/lib/evidence";
import { isRecord } from "@/lib/types";
import { SafeJson, StateMessage, StatusBadge, TechnicalDetails } from "./ui";

function ExactTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload?: { label?: string; exact?: string } }> }) {
  const item = payload?.[0]?.payload;
  if (!active || !item) return null;
  return <div className="panel-body panel"><strong>{item.label}</strong><div className="tabular">Exact: {item.exact}</div></div>;
}

function ExactTable({ rows, label = "Exact authoritative evidence" }: { rows: Record<string, unknown>[]; label?: string }) {
  if (!rows.length) return null;
  const flatten = (value: Record<string, unknown>, prefix = "", depth = 0): Record<string, unknown> => Object.fromEntries(Object.entries(value).flatMap(([key, item]) => {
    const path = prefix ? `${prefix}.${key}` : key;
    if (isRecord(item) && depth < 3) return Object.entries(flatten(item, path, depth + 1));
    return [[path, item]];
  }));
  const flattened = rows.map((row) => flatten(row));
  const columns = Array.from(new Set(flattened.flatMap((row) => Object.keys(row)))).slice(0, 12);
  return <div className="table-wrap"><table className="table" aria-label={label}><thead><tr>{columns.map((column) => <th key={column}>{humanize(column.replaceAll(".", " "))}</th>)}</tr></thead><tbody>{flattened.map((row, index) => <tr key={String(row.id || row.reference || index)}>{columns.map((column) => <td key={column} className={typeof row[column] === "number" || (typeof row[column] === "string" && /^-?\d/.test(row[column] as string)) ? "numeric" : ""}>{Array.isArray(row[column]) ? <code>{JSON.stringify(row[column])}</code> : displayDecimal(row[column] as string | number | null)}</td>)}</tr>)}</tbody></table></div>;
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

function evidenceFacts(value: Record<string, unknown>, prefix = "", depth = 0): Array<{ label: string; value: string }> {
  if (depth > 2) return [];
  return Object.entries(value).flatMap(([key, item]) => {
    if (/policy|digest|identifier|lineage/i.test(key)) return [];
    const label = prefix ? `${prefix} ${key}` : key;
    if (typeof item === "string" || typeof item === "number" || typeof item === "boolean") return [{ label, value: String(item) }];
    if (isRecord(item)) return evidenceFacts(item, label, depth + 1);
    return [];
  }).slice(0, 12);
}

function EvidenceFacts({ value }: { value: Record<string, unknown> }) {
  const facts = evidenceFacts(value);
  if (!facts.length) return <p className="muted">No separate coverage summary was returned.</p>;
  return <dl className="quality-facts">{facts.map((fact) => <div key={fact.label}><dt>{humanize(fact.label)}</dt><dd className="tabular">{fact.value}</dd></div>)}</dl>;
}

export function EvidenceRenderer({ status, evidence, limitations = [] }: { status: string; evidence: unknown; limitations?: string[] }) {
  const chartTitleId = useId();
  const chartDescriptionId = useId();
  const root = evidenceRoot(evidence);
  const result = isRecord(root.result) ? root.result : root;
  const currency = isRecord(root.currency) ? root.currency : null;
  const groupsValue = result.groups ?? result.buckets ?? result.candidates ?? root.candidates;
  const rows = Array.isArray(groupsValue) ? groupsValue.filter(isRecord) : [];
  const chartData = toChartData(rows);
  const measures = isRecord(result.measures) ? result.measures : null;
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

  return <div className="evidence-flow">
    <div className="result-header"><div><div className="eyebrow">Exact calculation result</div><h2 style={{ margin: "4px 0 0" }}>{typeof root.query_name === "string" ? humanize(root.query_name) : "Analysis result"}</h2></div><StatusBadge status={status} /></div>
    {currency && <div className="meta-strip"><div className="meta-item"><span className="micro">Currency context</span><span className="meta-value">{displayCurrencyState(String(currency.status || currency.state || "UNKNOWN"), typeof currency.code === "string" ? currency.code : null)}</span></div></div>}
    {status === "NO_DATA" && <StateMessage title="No data" message="The operation completed but returned no applicable evidence for the approved source." />}
    {measures && <section className="evidence-section" aria-labelledby="answer-heading"><div className="section-heading"><div><div className="eyebrow">Answer</div><h3 id="answer-heading">Key returned values</h3></div><span className="micro">Exact API strings</span></div><MeasureGrid measures={measures} currency={currency} /></section>}
    {chartData.length > 0 && <section className="evidence-section"><div className="section-heading"><div><div className="eyebrow">Primary evidence</div><h3 id={chartTitleId}>Presentation view</h3></div><span className="micro">Geometry only</span></div><div className="chart-figure" role="img" aria-labelledby={chartTitleId} aria-describedby={chartDescriptionId}><div className="chart" aria-hidden="true"><ResponsiveContainer width="100%" height="100%">{temporalOrAging ? <BarChart data={chartData} margin={{ left: 12, right: 16, top: 10, bottom: 36 }}><CartesianGrid stroke="#e1e5e1" vertical={false} /><XAxis dataKey="label" angle={-20} textAnchor="end" interval={0} height={60} tick={{ fontSize: 13 }} /><YAxis tick={{ fontSize: 13 }} /><Tooltip content={<ExactTooltip />} /><Bar dataKey="coordinate" fill="#24624d" maxBarSize={46} /></BarChart> : <BarChart data={chartData} layout="vertical" margin={{ left: 12, right: 24, top: 10, bottom: 10 }}><CartesianGrid stroke="#e1e5e1" horizontal={false} /><XAxis type="number" tick={{ fontSize: 13 }} /><YAxis type="category" dataKey="label" width={112} tick={{ fontSize: 13 }} /><Tooltip content={<ExactTooltip />} /><Bar dataKey="coordinate" fill="#24624d" maxBarSize={30} /></BarChart>}</ResponsiveContainer></div></div><p className="micro" id={chartDescriptionId}>Presentation of {chartData.length} returned groups. The exact values are available in the authoritative table below.</p></section>}
    {rows.length > 0 && <section className="evidence-section"><div className="section-heading"><div><div className="eyebrow">Primary evidence</div><h3>Exact evidence table</h3></div><span className="micro">{rows.length} rows returned</span></div><ExactTable rows={rows} /></section>}
    {!measures && rows.length === 0 && Object.keys(result).length > 0 && <section className="evidence-section"><h3>Returned evidence</h3><p className="muted">The structured response is available under technical details.</p></section>}
    <section className="quality-section" aria-labelledby="quality-heading"><div className="section-heading"><div><div className="eyebrow">Quality</div><h3 id="quality-heading">Coverage and limitations</h3></div></div><div className="grid-2"><div><h4>Coverage</h4>{coverage && Object.keys(coverage).length ? <EvidenceFacts value={coverage} /> : <p className="muted">No separate coverage object was returned.</p>}</div><div><h4>Limitations</h4>{allLimitations.length ? <ul className="notice-list">{allLimitations.map((item) => <li key={item}>{displayLimitation(item)}</li>)}</ul> : <p className="muted">No additional limitations were returned.</p>}</div></div></section>
    <TechnicalDetails><dl className="technical-summary"><div><dt>Raw status</dt><dd><code>{status}</code> — {displayStatus(status)}</dd></div><div><dt>Operation identifier</dt><dd><code>{queryName || "not supplied"}</code></dd></div></dl>{coverage && <><h4>Raw coverage</h4><SafeJson value={coverage} /></>}{allLimitations.length > 0 && <><h4>Raw limitation text</h4><SafeJson value={allLimitations} /></>}<h4>Raw structured evidence</h4><SafeJson value={withoutPrivatePaths(result)} /><h4>Lineage and reproducibility</h4>{metadata ? <SafeJson value={withoutPrivatePaths(metadata)} /> : <p className="muted">No separate metadata object was returned.</p>}</TechnicalDetails>
  </div>;
}
