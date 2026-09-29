import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, type PartnerDetail as Detail, type PartnerSummary, type PracticeKey } from "../api";
import { type ComposerTarget, OutreachComposer } from "../components/OutreachComposer";
import { DueTag, ErrorState, Loading, PageHeader, PracticeTag, SignalStrip } from "../components/ui";
import { cad, cadShort, pct, PRACTICE_LABEL, relativeTime } from "../format";

type SortKey = "name" | "whitespace_potential" | "open_pipeline" | "days_since_touch" | "attach_rate";

export function Partners() {
  const query = useQuery({ queryKey: ["partners"], queryFn: () => api.get<PartnerSummary[]>("/api/partners") });
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<SortKey>("whitespace_potential");
  if (query.isLoading) return <Loading label="Loading partners" />;
  if (query.error || !query.data) return <ErrorState error={query.error} />;
  const term = search.toLowerCase();
  const rows = query.data
    .filter((p) => !term || `${p.name} ${p.city} ${p.contact_name} ${p.verticals.join(" ")}`.toLowerCase().includes(term))
    .sort((a, b) => {
      if (sort === "name") return a.name.localeCompare(b.name);
      if (sort === "attach_rate") return a.attach_rate - b.attach_rate;
      return (Number(b[sort]) || 0) - (Number(a[sort]) || 0);
    });

  return (
    <div className="page">
      <PageHeader title="Partners" lede={`${query.data.length} reseller partners across Canada. Sort by whitespace to see who to call about services they have never attached.`} />
      <div className="filters">
        <label className="grow">
          Search
          <input type="search" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Name, city, contact or vertical" />
        </label>
        <label>
          Sort by
          <select value={sort} onChange={(e) => setSort(e.target.value as SortKey)}>
            <option value="whitespace_potential">Largest services gap</option>
            <option value="open_pipeline">Open pipeline</option>
            <option value="attach_rate">Lowest attach rate</option>
            <option value="days_since_touch">Longest since last touch</option>
            <option value="name">Name</option>
          </select>
        </label>
      </div>
      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th scope="col">Partner</th>
              <th scope="col">Contact</th>
              <th scope="col" className="num">Attach rate</th>
              <th scope="col" className="num">Services gap</th>
              <th scope="col" className="num">Open pipeline</th>
              <th scope="col" className="num">Signals</th>
              <th scope="col">Last touch</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((p) => (
              <tr key={p.id}>
                <th scope="row">
                  <Link to={`/partners/${p.id}`}>{p.name}</Link>
                  <span className="muted small block">
                    {p.partner_type}, {p.city} {p.province}, {p.tier}
                  </span>
                </th>
                <td>
                  {p.contact_name}
                  <span className="muted small block">{p.contact_title}</span>
                </td>
                <td className="num tabular">{pct(p.attach_rate)}</td>
                <td className="num tabular">{cadShort(p.whitespace_potential)}</td>
                <td className="num tabular">
                  {cadShort(p.open_pipeline)}
                  <span className="muted small block">{p.open_opportunities} open</span>
                </td>
                <td className="num tabular">{p.new_signals || "–"}</td>
                <td className={p.days_since_touch !== null && p.days_since_touch > 14 ? "text-alert" : ""}>
                  {p.days_since_touch === null ? "Never" : p.days_since_touch === 0 ? "Today" : `${p.days_since_touch}d ago`}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const PRACTICES: PracticeKey[] = ["security", "cloud", "network", "ai", "lifecycle", "training"];

export function PartnerDetail() {
  const { id } = useParams();
  const query = useQuery({ queryKey: ["partner", id], queryFn: () => api.get<Detail>(`/api/partners/${id}`) });
  const [composer, setComposer] = useState<ComposerTarget | null>(null);
  if (query.isLoading) return <Loading label="Loading partner" />;
  if (query.error || !query.data) return <ErrorState error={query.error} />;
  const p = query.data;

  return (
    <div className="page">
      <nav className="crumbs" aria-label="Breadcrumb">
        <Link to="/partners">Partners</Link>
      </nav>
      <PageHeader
        title={p.name}
        lede={p.about}
        actions={
          <button
            className="button primary"
            onClick={() => setComposer({ partnerId: p.id, partnerName: p.name, contactName: p.contact_name, heading: p.name, defaultGoal: "intro" })}
          >
            Draft e-mail to {p.contact_name.split(" ")[0]}
          </button>
        }
      />
      <dl className="profile-facts">
        <div>
          <dt>Primary contact</dt>
          <dd>
            {p.contact_name}, {p.contact_title}
            <span className="muted small block">{p.contact_email}</span>
          </dd>
        </div>
        <div>
          <dt>Profile</dt>
          <dd>
            {p.partner_type}, {p.tier} tier
            <span className="muted small block">
              {p.city} {p.province}. Serves {p.verticals.join(", ").toLowerCase()}
            </span>
          </dd>
        </div>
        <div>
          <dt>12-month revenue</dt>
          <dd className="tabular">
            {cad(p.trailing_revenue)} product
            <span className="muted small block">
              {cad(p.services_revenue)} services, {pct(p.attach_rate)} attach
            </span>
          </dd>
        </div>
        <div>
          <dt>Vendors</dt>
          <dd>{p.vendors.join(", ")}</dd>
        </div>
      </dl>

      <section className="panel">
        <h2 className="panel-title">Services whitespace</h2>
        <div className="ws-bars">
          {PRACTICES.map((key) => {
            const cell = p.whitespace[key];
            return (
              <div key={key} className="ws-bar-row">
                <span className="ws-bar-label">{PRACTICE_LABEL[key]}</span>
                <span className="ws-bar-track" title={`${pct(cell.share)} of product revenue`}>
                  <span className={`ws-bar-fill p-${key}`} style={{ width: `${Math.min(1, cell.share / 0.8) * 100}%` }} />
                </span>
                <span className="ws-bar-value small">
                  {cell.status === "attached" ? "Services attached" : cell.status === "gap" ? `Gap ${cadShort(cell.potential)}` : "–"}
                </span>
              </div>
            );
          })}
        </div>
        <p className="muted small">Bars show each practice's share of product revenue.</p>
      </section>

      <div className="two-col even">
        <section className="panel">
          <h2 className="panel-title">Opportunities</h2>
          {p.opportunities.length === 0 && <p className="muted">None yet. Start from one of the signals.</p>}
          <ul className="opp-list">
            {p.opportunities.map((o) => (
              <li key={o.id}>
                <div>
                  <Link to={`/opportunities/${o.id}`}>{o.title}</Link>
                  <p className="muted small">
                    {o.stage}, {cad(o.value)}
                  </p>
                </div>
                {!["Won", "Lost"].includes(o.stage) && (
                  <div className="opp-list-side">
                    <SignalStrip priority={o.priority} />
                    <DueTag due={o.next_step_due} />
                  </div>
                )}
              </li>
            ))}
          </ul>
        </section>
        <section className="panel">
          <h2 className="panel-title">Signals</h2>
          <ul className="plain-list">
            {p.signals.map((s) => (
              <li key={s.id}>
                <PracticeTag practice={s.practice} /> <strong>{s.title}</strong>
                <span className="muted small block">
                  {s.source}, {s.status === "new" ? "not yet worked" : s.status}
                </span>
              </li>
            ))}
          </ul>
        </section>
      </div>

      <section className="panel">
        <h2 className="panel-title">Activity</h2>
        <ul className="timeline">
          {p.activities.map((a) => (
            <li key={a.id}>
              <span className={`tl-kind k-${a.kind}`}>{a.kind}</span>
              <p>{a.summary}</p>
              <p className="muted small">{relativeTime(a.occurred_at)}</p>
            </li>
          ))}
        </ul>
      </section>
      {composer && <OutreachComposer target={composer} onClose={() => setComposer(null)} />}
    </div>
  );
}
