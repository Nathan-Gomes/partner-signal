import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api, type PracticeKey, type SignalItem, type WhitespaceCell } from "../api";
import { type ComposerTarget, OutreachComposer } from "../components/OutreachComposer";
import { ErrorState, Loading, PageHeader, PracticeTag, useToast } from "../components/ui";
import { cad, cadShort, daysFromToday, KIND_LABEL, pct, PRACTICE_LABEL, shortDate } from "../format";

const PRACTICES: PracticeKey[] = ["security", "cloud", "network", "ai", "lifecycle", "training"];

export function Signals() {
  const [params, setParams] = useSearchParams();
  const view = params.get("view") === "whitespace" ? "whitespace" : "feed";
  return (
    <div className="page">
      <PageHeader
        title="Signals"
        lede="Prospecting starts from evidence: renewals, end-of-support dates, purchase patterns and services partners have never attached."
      />
      <div className="tabs" role="tablist">
        <button role="tab" aria-selected={view === "feed"} onClick={() => setParams({})}>
          Signal feed
        </button>
        <button role="tab" aria-selected={view === "whitespace"} onClick={() => setParams({ view: "whitespace" })}>
          Whitespace map
        </button>
      </div>
      {view === "feed" ? <Feed /> : <Whitespace />}
    </div>
  );
}

function Feed() {
  const [practice, setPractice] = useState<string>("");
  const [status, setStatus] = useState<string>("new");
  const [composer, setComposer] = useState<ComposerTarget | null>(null);
  const client = useQueryClient();
  const toast = useToast();
  const navigate = useNavigate();
  const query = useQuery({
    queryKey: ["signals", status, practice],
    queryFn: () =>
      api.get<SignalItem[]>(`/api/signals?${new URLSearchParams({ ...(status && { status }), ...(practice && { practice }) })}`),
  });
  const dismiss = useMutation({
    mutationFn: (id: number) => api.post(`/api/signals/${id}/dismiss`),
    onSuccess: () => {
      client.invalidateQueries();
      toast("Signal dismissed. It will not appear in today's queue.");
    },
  });
  const convert = useMutation({
    mutationFn: (id: number) => api.post<{ opportunity_id: number }>(`/api/signals/${id}/convert`, {}),
    onSuccess: (data) => {
      client.invalidateQueries();
      navigate(`/opportunities/${data.opportunity_id}`);
    },
  });

  return (
    <>
      <div className="filters">
        <label>
          Status
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="new">Not yet worked</option>
            <option value="actioned">Actioned</option>
            <option value="dismissed">Dismissed</option>
            <option value="">All</option>
          </select>
        </label>
        <label>
          Practice
          <select value={practice} onChange={(e) => setPractice(e.target.value)}>
            <option value="">All practices</option>
            {PRACTICES.map((p) => (
              <option key={p} value={p}>
                {PRACTICE_LABEL[p]}
              </option>
            ))}
          </select>
        </label>
        {query.data && <p className="muted small">{query.data.length} signals</p>}
      </div>
      {query.isLoading && <Loading />}
      {query.error && <ErrorState error={query.error} />}
      {query.data && query.data.length === 0 && (
        <p className="empty-note">No signals match these filters. Try another practice or include actioned signals.</p>
      )}
      <div className="signal-list">
        {query.data?.map((s) => {
          const until = s.deadline ? daysFromToday(s.deadline) : null;
          return (
            <article key={s.id} className="signal-card">
              <div className="signal-top">
                <PracticeTag practice={s.practice} />
                <span className="signal-kind">{KIND_LABEL[s.kind] ?? s.kind}</span>
                <span className="muted small">
                  {s.source}, found {shortDate(s.detected_on)}
                </span>
                <span className="signal-score tabular" title="Signal score: strength, deadline and freshness">
                  {s.score}
                </span>
              </div>
              <h3>{s.title}</h3>
              <p className="signal-partner">
                <Link to={`/partners/${s.partner_id}`}>{s.partner}</Link>
              </p>
              <p className="signal-detail">{s.detail}</p>
              <dl className="signal-facts">
                <div>
                  <dt>Strength</dt>
                  <dd>
                    <span className="pips" aria-label={`${s.strength} of 5`}>
                      {[1, 2, 3, 4, 5].map((n) => (
                        <span key={n} className={n <= s.strength ? "on" : ""} />
                      ))}
                    </span>
                  </dd>
                </div>
                <div>
                  <dt>Suggested service</dt>
                  <dd>{s.service}</dd>
                </div>
                <div>
                  <dt>Typical value</dt>
                  <dd className="tabular">{cad(s.estimated_value)}</dd>
                </div>
                {until !== null && (
                  <div>
                    <dt>Customer deadline</dt>
                    <dd className={until <= 45 ? "text-alert" : ""}>
                      {shortDate(s.deadline!)} ({until} days)
                    </dd>
                  </div>
                )}
              </dl>
              {s.status === "new" && (
                <div className="signal-actions">
                  <button
                    className="button primary small"
                    onClick={() =>
                      setComposer({ partnerId: s.partner_id, partnerName: s.partner, signalId: s.id, heading: s.title })
                    }
                  >
                    Draft outreach
                  </button>
                  <button className="button small" onClick={() => convert.mutate(s.id)}>
                    Open as opportunity
                  </button>
                  <button className="link-button" onClick={() => dismiss.mutate(s.id)}>
                    Not relevant
                  </button>
                </div>
              )}
            </article>
          );
        })}
      </div>
      {composer && <OutreachComposer target={composer} onClose={() => setComposer(null)} />}
    </>
  );
}

interface Matrix {
  practices: PracticeKey[];
  rows: { partner_id: string; partner: string; tier: string; cells: Record<PracticeKey, WhitespaceCell> }[];
  totals: Record<PracticeKey, number>;
  benchmark: number;
}

function Whitespace() {
  const query = useQuery({ queryKey: ["whitespace"], queryFn: () => api.get<Matrix>("/api/whitespace") });
  if (query.isLoading) return <Loading />;
  if (query.error || !query.data) return <ErrorState error={query.error} />;
  const { rows, practices, totals, benchmark } = query.data;
  const max = Math.max(...rows.flatMap((r) => practices.map((p) => r.cells[p].potential)));
  const step = (value: number) => (value === 0 ? 0 : Math.max(1, Math.ceil((value / max) * 4)));

  return (
    <section>
      <p className="lede narrow">
        Each cell compares a partner's 12-month product revenue in a practice with the services they attach. A gap
        estimates the services revenue at a {pct(benchmark)} attach benchmark. Darker means a larger opportunity.
      </p>
      <div className="legend" aria-hidden>
        <span className="legend-item">
          <span className="ws-swatch ws-attached" />
          Services already attached
        </span>
        <span className="legend-item">
          <span className="ws-swatch ws-none" />
          Little product revenue
        </span>
        <span className="legend-item">
          Gap, by size
          {[1, 2, 3, 4].map((n) => (
            <span key={n} className={`ws-swatch ws-gap-${n}`} />
          ))}
        </span>
      </div>
      <div className="table-scroll">
        <table className="ws-table">
          <caption className="sr-only">Services whitespace by partner and practice</caption>
          <thead>
            <tr>
              <th scope="col">Partner</th>
              {practices.map((p) => (
                <th key={p} scope="col">
                  {PRACTICE_LABEL[p]}
                </th>
              ))}
              <th scope="col">Total gap</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const total = practices.reduce((sum, p) => sum + row.cells[p].potential, 0);
              return (
                <tr key={row.partner_id}>
                  <th scope="row">
                    <Link to={`/partners/${row.partner_id}`}>{row.partner}</Link>
                    <span className="muted small"> {row.tier}</span>
                  </th>
                  {practices.map((p) => {
                    const cell = row.cells[p];
                    const cls = cell.status === "gap" ? `ws-gap-${step(cell.potential)}` : `ws-${cell.status}`;
                    const text =
                      cell.status === "gap" ? cadShort(cell.potential) : cell.status === "attached" ? "Attached" : "–";
                    const title =
                      cell.status === "none"
                        ? `${PRACTICE_LABEL[p]}: ${pct(cell.share)} of product revenue`
                        : `${PRACTICE_LABEL[p]}: ${pct(cell.share)} of product revenue (${cad(cell.product_revenue)})`;
                    return (
                      <td key={p} className={`ws-cell ${cls}`} title={title}>
                        {text}
                      </td>
                    );
                  })}
                  <td className="tabular strong">{cadShort(total)}</td>
                </tr>
              );
            })}
          </tbody>
          <tfoot>
            <tr>
              <th scope="row">All partners</th>
              {practices.map((p) => (
                <td key={p} className="tabular strong">
                  {cadShort(totals[p])}
                </td>
              ))}
              <td className="tabular strong">{cadShort(Object.values(totals).reduce((a, b) => a + b, 0))}</td>
            </tr>
          </tfoot>
        </table>
      </div>
    </section>
  );
}
