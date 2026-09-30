import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { useTour } from "./Tour";
import { CASE_STUDY } from "./Welcome";
import { api, type Health, type TodayView } from "../api";
import { useToast } from "./ui";

const NAV = [
  { to: "/", label: "Today", end: true },
  { to: "/signals", label: "Signals" },
  { to: "/pipeline", label: "Pipeline" },
  { to: "/partners", label: "Partners" },
  { to: "/capture", label: "Capture a call" },
  { to: "/reports", label: "Reports" },
  { to: "/playbook", label: "Playbook" },
];

export function Layout() {
  const [open, setOpen] = useState(false);
  const location = useLocation();
  const client = useQueryClient();
  const toast = useToast();
  const tour = useTour();
  const health = useQuery({ queryKey: ["health"], queryFn: () => api.get<Health>("/api/health") });
  const today = useQuery({ queryKey: ["today"], queryFn: () => api.get<TodayView>("/api/today") });
  const due = today.data ? today.data.kpis.due_today + today.data.kpis.overdue : null;

  async function reset() {
    await api.post("/api/reset");
    await client.invalidateQueries();
    toast("Demo data restored.");
  }

  return (
    <div className="shell">
      <a className="skip" href="#main">
        Skip to content
      </a>
      <aside className={`sidebar ${open ? "is-open" : ""}`}>
        <div className="brand">
          <svg width="26" height="26" viewBox="0 0 32 32" aria-hidden>
            <rect width="32" height="32" rx="7" fill="currentColor" />
            <rect x="7" y="18" width="4" height="7" rx="1" fill="#2a78d6" />
            <rect x="13" y="13" width="4" height="12" rx="1" fill="#1baf7a" />
            <rect x="19" y="8" width="4" height="17" rx="1" fill="#eb6834" />
          </svg>
          <div>
            <p className="brand-name">PartnerSignal</p>
            <p className="brand-sub">Professional services desk</p>
          </div>
          <button className="menu-toggle" aria-expanded={open} aria-controls="nav" onClick={() => setOpen(!open)}>
            {open ? "Close" : "Menu"}
          </button>
        </div>
        <nav id="nav" aria-label="Main">
          {NAV.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end} onClick={() => setOpen(false)}>
              {item.label}
              {item.to === "/" && due ? <span className="nav-count">{due}</span> : null}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-foot">
          <p className="engine-status">
            <span className={`pulse ${health.data?.ai.live_model_available ? "on" : ""}`} aria-hidden />
            {health.data
              ? health.data.ai.live_model_available
                ? `AI drafting: Claude (${health.data.ai.model})`
                : "AI drafting: built-in rules engine"
              : "Connecting…"}
          </p>
          <p className="fine">Fictional demo data. Drafts are never sent automatically.</p>
          <button
            className="side-tour"
            onClick={() => {
              setOpen(false);
              tour.start();
            }}
          >
            Take the 2-minute tour
          </button>
          <a className="side-link" href={CASE_STUDY} target="_blank" rel="noreferrer">
            About this project
          </a>
          <Link className="side-link" to="/?intro=1" onClick={() => setOpen(false)}>
            Show the intro
          </Link>
          <button className="link-button" onClick={reset}>
            Reset demo data
          </button>
        </div>
      </aside>
      <main id="main" key={location.pathname}>
        <Outlet />
      </main>
    </div>
  );
}
