"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { Activity, BarChart3, Database, LayoutDashboard, Menu, MessageSquareText, ShieldCheck, X } from "lucide-react";
import { useWorkspace } from "./workspace-provider";

const NAV = [
  { href: "/overview", label: "Overview", icon: LayoutDashboard },
  { href: "/datasets", label: "Datasets", icon: Database },
  { href: "/analysis", label: "Analysis", icon: BarChart3 },
  { href: "/anomalies", label: "Anomalies", icon: Activity },
  { href: "/chat", label: "Ask Financial Manager", icon: MessageSquareText },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const menuButton = useRef<HTMLButtonElement>(null);
  const sidebar = useRef<HTMLElement>(null);
  const { health, selectedDataset } = useWorkspace();

  useEffect(() => {
    const query = window.matchMedia("(max-width: 767px)");
    const update = () => { setIsMobile(query.matches); if (!query.matches) setOpen(false); };
    update(); query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);

  const closeNavigation = useCallback(() => {
    setOpen(false);
    window.setTimeout(() => menuButton.current?.focus(), 0);
  }, []);

  useEffect(() => {
    if (!open || !isMobile) return;
    const drawer = sidebar.current;
    const focusable = drawer?.querySelectorAll<HTMLElement>("a[href], button:not([disabled])");
    focusable?.[0]?.focus();
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") closeNavigation();
      if (event.key === "Tab" && focusable?.length) {
        const first = focusable[0]; const last = focusable[focusable.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
      }
    };
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [open, isMobile, closeNavigation]);

  return <div className="app-shell">
    {open && <button className="nav-backdrop" aria-label="Close navigation" tabIndex={-1} onClick={closeNavigation} />}
    <aside ref={sidebar} className={`sidebar ${open ? "open" : ""}`} aria-label="Workspace navigation" aria-hidden={isMobile && !open ? true : undefined} inert={isMobile && !open ? true : undefined} role={isMobile ? "dialog" : undefined} aria-modal={isMobile && open ? true : undefined}>
      <div className="brand"><span className="brand-mark"><ShieldCheck size={15} /></span><span>Financial Manager AI</span></div>
      <div className="nav-label">Workspace</div>
      <nav className="nav-list" aria-label="Primary navigation">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || (href !== "/overview" && pathname.startsWith(`${href}/`));
          return <Link key={href} href={href} className={`nav-link ${active ? "active" : ""}`} aria-current={active ? "page" : undefined} onClick={() => isMobile ? closeNavigation() : undefined} title={label}><Icon size={17} aria-hidden /><span>{label}</span></Link>;
        })}
      </nav>
      <div className="sidebar-foot">Local workspace<br />V2 · API v1</div>
    </aside>
    <header className="topbar" inert={isMobile && open ? true : undefined}>
      <div className="topbar-context">
        <button ref={menuButton} className="button button-ghost icon-button mobile-trigger" onClick={() => setOpen((value) => !value)} aria-label={open ? "Close navigation" : "Open navigation"} aria-expanded={open}>{open ? <X size={18} /> : <Menu size={18} />}</button>
        <div><span className="micro">Dataset context</span><div className="context-dataset" title={selectedDataset?.dataset_id}>{selectedDataset ? selectedDataset.source_filename : "No dataset selected"}</div></div>
        {selectedDataset?.approved_domain && <span className="badge">{selectedDataset.approved_domain}</span>}
      </div>
      <div className="api-health" role="status" aria-live="polite"><span className={`health-dot ${health}`} />API {health === "checking" ? "checking" : health === "healthy" ? "Healthy" : "unavailable"}</div>
    </header>
    <main className="workspace" id="main-content" inert={isMobile && open ? true : undefined}><div className="workspace-inner">{children}</div></main>
  </div>;
}
