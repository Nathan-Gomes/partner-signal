import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError, type OpportunitySummary, type PracticeKey } from "../api";
import { DueTag, ErrorState, Loading, PageHeader, PracticeTag, SignalStrip, useToast } from "../components/ui";
import { cadShort, PRACTICE_LABEL } from "../format";

const COLUMNS = ["Prospect", "Discovery", "Qualified", "Solutioning", "Proposal"];
const PRACTICES: PracticeKey[] = ["security", "cloud", "network", "ai", "lifecycle", "training"];

export function Pipeline() {
  const client = useQueryClient();
  const toast = useToast();
  const [practice, setPractice] = useState("");
  const [dragging, setDragging] = useState<number | null>(null);
  const [over, setOver] = useState<string | null>(null);
  const [blocked, setBlocked] = useState<{ title: string; message: string; todo: string[] } | null>(null);
  const query = useQuery({
    queryKey: ["opportunities"],
    queryFn: () => api.get<OpportunitySummary[]>("/api/opportunities"),
  });

  const move = useMutation({
    mutationFn: ({ id, stage }: { id: number; stage: string }) => api.post(`/api/opportunities/${id}/stage`, { stage }),
    onSuccess: (_, { stage }) => {
      client.invalidateQueries();
      toast(`Moved to ${stage}. Follow-up date reset for the new stage.`);
    },
    onError: (error, { id }) => {
      const opp = query.data?.find((o) => o.id === id);
      if (error instanceof ApiError && error.status === 409) {
        const detail = error.detail as { message: string; to_do: string[] };
        setBlocked({ title: opp?.title ?? "This opportunity", message: detail.message, todo: detail.to_do });
      } else {
        toast((error as Error).message, "warn");
      }
    },
  });

  if (query.isLoading) return <Loading label="Loading pipeline" />;
  if (query.error || !query.data) return <ErrorState error={query.error} />;
  const items = query.data.filter((o) => !practice || o.practice === practice);
  const open = items.filter((o) => COLUMNS.includes(o.stage));
  const won = items.filter((o) => o.stage === "Won");

  function drop(stage: string) {
    setOver(null);
    const opp = open.find((o) => o.id === dragging);
    setDragging(null);
    if (opp && opp.stage !== stage) move.mutate({ id: opp.id, stage });
  }

  return (
    <div className="page page-wide">
      <PageHeader
        title="Pipeline"
        lede={
          <>
            {open.length} open opportunities worth {cadShort(open.reduce((s, o) => s + o.value, 0))}, weighted to{" "}
            {cadShort(open.reduce((s, o) => s + o.weighted_value, 0))}. Drag a card to change its stage; stage gates
            check that the qualification evidence is there.
          </>
        }
        actions={
          <a className="button" href="/api/export/opportunities.csv">
            Export CSV
          </a>
        }
      />
      <div className="filters">
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
        <p className="muted small">
          Won in the last 180 days: {won.length} for {cadShort(won.reduce((s, o) => s + o.value, 0))}
        </p>
      </div>

      {blocked && (
        <div className="gate" role="alert">
          <div>
            <p className="gate-title">
              {blocked.title} can't move yet. {blocked.message}
            </p>
            <ul>
              {blocked.todo.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
          <button className="icon-button" onClick={() => setBlocked(null)} aria-label="Dismiss">
            ×
          </button>
        </div>
      )}

      <div className="board">
        {COLUMNS.map((stage) => {
          const cards = open.filter((o) => o.stage === stage).sort((a, b) => b.priority.score - a.priority.score);
          return (
            <section
              key={stage}
              className={`column ${over === stage ? "is-over" : ""}`}
              aria-label={stage}
              onDragOver={(e) => {
                e.preventDefault();
                setOver(stage);
              }}
              onDragLeave={() => setOver((s) => (s === stage ? null : s))}
              onDrop={() => drop(stage)}
            >
              <header className="column-head">
                <h2>{stage}</h2>
                <p className="tabular">
                  {cards.length} for {cadShort(cards.reduce((s, o) => s + o.value, 0))}
                </p>
              </header>
              {cards.length === 0 && <p className="column-empty">Nothing here yet.</p>}
              {cards.map((o) => (
                <article
                  key={o.id}
                  className={`card ${dragging === o.id ? "is-dragging" : ""}`}
                  draggable
                  onDragStart={() => setDragging(o.id)}
                  onDragEnd={() => setDragging(null)}
                >
                  <Link to={`/opportunities/${o.id}`} className="card-title">
                    {o.title}
                  </Link>
                  <p className="card-partner">{o.partner}</p>
                  <div className="card-meta">
                    <PracticeTag practice={o.practice} />
                    <span className="tabular">{cadShort(o.value)}</span>
                  </div>
                  <SignalStrip priority={o.priority} />
                  <div className="card-foot">
                    <DueTag due={o.next_step_due} />
                    {o.priority.flags.includes("stalled") && <span className="flag">Stalled {o.days_in_stage}d</span>}
                    {stage !== "Prospect" && stage !== "Discovery" && !o.specialist && (
                      <span className="flag">No specialist</span>
                    )}
                  </div>
                </article>
              ))}
            </section>
          );
        })}
      </div>
    </div>
  );
}
