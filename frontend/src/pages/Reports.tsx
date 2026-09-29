import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api, type Reports as ReportData } from "../api";
import { ErrorState, Loading, PageHeader } from "../components/ui";
import { cad, cadShort, pct, shortDate } from "../format";

export function Reports() {
  const query = useQuery({ queryKey: ["reports"], queryFn: () => api.get<ReportData>("/api/reports") });
  if (query.isLoading) return <Loading label="Building reports" />;
  if (query.error || !query.data) return <ErrorState error={query.error} />;
  const r = query.data;

  return (
    <div className="page">
      <PageHeader
        title="Reports"
        lede="The numbers a professional-services lead asks for in a weekly one-on-one: pipeline health, follow-through, and what converts."
        actions={
          <a className="button" href="/api/export/opportunities.csv">
            Export pipeline CSV
          </a>
        }
      />
      <dl className="report-stats">
        <div>
          <dt>Open pipeline</dt>
          <dd className="tabular">{cadShort(r.open_pipeline)}</dd>
          <p>{cadShort(r.weighted_pipeline)} weighted by stage</p>
        </div>
        <div>
          <dt>Win rate, last 180 days</dt>
          <dd className="tabular">{r.win_rate === null ? "–" : pct(r.win_rate)}</dd>
          <p>
            {r.won_count} won of {r.closed_count} closed
          </p>
        </div>
        <div>
          <dt>Won value</dt>
          <dd className="tabular">{cadShort(r.won_value)}</dd>
          <p>Average {r.avg_cycle_days ?? "–"} days from first touch</p>
        </div>
        <div>
          <dt>Stalled</dt>
          <dd className="tabular">{r.stalled}</dd>
          <p>open opportunities past their stage threshold</p>
        </div>
      </dl>

      <div className="two-col even">
        <section className="panel">
          <h2 className="panel-title">Funnel by stage</h2>
          <Funnel data={r.funnel} />
        </section>
        <section className="panel">
          <h2 className="panel-title">Open pipeline by practice</h2>
          <PracticeBars data={r.by_practice} />
        </section>
      </div>
      <section className="panel">
        <h2 className="panel-title">Partner touches per week</h2>
        <ActivityChart data={r.activity_weeks} />
      </section>
      <section className="panel">
        <h2 className="panel-title">Which signals turn into conversations</h2>
        <table className="data-table">
          <thead>
            <tr>
              <th scope="col">Source</th>
              <th scope="col" className="num">Signals</th>
              <th scope="col" className="num">Actioned</th>
              <th scope="col" className="num">Rate</th>
            </tr>
          </thead>
          <tbody>
            {r.signal_sources.map((s) => (
              <tr key={s.source}>
                <th scope="row">{s.source}</th>
                <td className="num tabular">{s.total}</td>
                <td className="num tabular">{s.actioned}</td>
                <td className="num tabular">{pct(s.actioned / s.total)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

function Funnel({ data }: { data: ReportData["funnel"] }) {
  const max = Math.max(...data.map((d) => d.value), 1);
  return (
    <ul className="hbars" aria-label="Opportunity value by stage">
      {data.map((d, i) => (
        <li key={d.stage} title={`${d.stage}: ${d.count} opportunities, ${cad(d.value)}`}>
          <span className="hbar-label">{d.stage}</span>
          <span className="hbar-track">
            <span className={`hbar-fill ord-${i}`} style={{ width: `${(d.value / max) * 100}%` }} />
          </span>
          <span className="hbar-value tabular">
            {cadShort(d.value)} <span className="muted">({d.count})</span>
          </span>
        </li>
      ))}
    </ul>
  );
}

function PracticeBars({ data }: { data: ReportData["by_practice"] }) {
  const max = Math.max(...data.map((d) => d.open_value), 1);
  return (
    <>
      <ul className="hbars" aria-label="Open and weighted pipeline by practice">
        {data.map((d) => (
          <li key={d.practice} title={`${d.label}: ${cad(d.open_value)} open, ${cad(d.weighted_value)} weighted`}>
            <span className="hbar-label">{d.label}</span>
            <span className="hbar-track">
              <span className={`hbar-fill p-${d.practice} is-faint`} style={{ width: `${(d.open_value / max) * 100}%` }} />
              <span className={`hbar-fill p-${d.practice} is-over`} style={{ width: `${(d.weighted_value / max) * 100}%` }} />
            </span>
            <span className="hbar-value tabular">{cadShort(d.open_value)}</span>
          </li>
        ))}
      </ul>
      <p className="muted small">Solid segment is the stage-weighted value; the lighter bar is the full open value.</p>
    </>
  );
}

const SERIES = [
  { key: "call", label: "Calls" },
  { key: "email", label: "E-mails" },
  { key: "meeting", label: "Meetings" },
] as const;

function ActivityChart({ data }: { data: ReportData["activity_weeks"] }) {
  const [hover, setHover] = useState<number | null>(null);
  const totals = data.map((d) => d.call + d.email + d.meeting);
  const max = Math.max(...totals, 1);
  const top = Math.max(10, Math.ceil(max / 10) * 10);
  const h = 180;
  return (
    <div className="vchart">
      <div className="legend">
        {SERIES.map((s, i) => (
          <span key={s.key} className="legend-item">
            <span className={`swatch s-${i}`} />
            {s.label}
          </span>
        ))}
      </div>
      <div className="vchart-plot" style={{ height: h }}>
        {[0, 0.5, 1].map((t) => (
          <span key={t} className="gridline" style={{ bottom: `${t * 100}%` }}>
            <span className="tabular">{Math.round(top * t)}</span>
          </span>
        ))}
        {data.map((d, i) => (
          <div
            key={d.week}
            className="vbar"
            onMouseEnter={() => setHover(i)}
            onMouseLeave={() => setHover(null)}
            onFocus={() => setHover(i)}
            onBlur={() => setHover(null)}
            tabIndex={0}
            aria-label={`Week of ${shortDate(d.week)}: ${d.call} calls, ${d.email} e-mails, ${d.meeting} meetings`}
          >
            <div className="vbar-stack" style={{ height: `${(totals[i] / top) * 100}%` }}>
              {SERIES.map((s, j) =>
                d[s.key] ? <span key={s.key} className={`s-${j}`} style={{ flexGrow: d[s.key] }} /> : null,
              )}
            </div>
            {hover === i && (
              <div className="tooltip" role="tooltip">
                <strong>Week of {shortDate(d.week)}</strong>
                {SERIES.map((s) => (
                  <span key={s.key}>
                    {s.label}: {d[s.key]}
                  </span>
                ))}
              </div>
            )}
            <span className="vbar-label">{shortDate(d.week)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
