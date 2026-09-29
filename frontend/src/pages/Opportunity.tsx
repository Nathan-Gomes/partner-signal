import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, ApiError, type Bant, type Meta, type OpportunityDetail } from "../api";
import { type ComposerTarget, OutreachComposer } from "../components/OutreachComposer";
import { DueTag, ErrorState, Loading, PracticeTag, PriorityBreakdown, useToast } from "../components/ui";
import { BANT_LABEL, cad, relativeTime, shortDate } from "../format";

const STAGES = ["Prospect", "Discovery", "Qualified", "Solutioning", "Proposal", "Won", "Lost"];
const BANT_FIELDS: { key: keyof Bant; label: string; hint: string }[] = [
  { key: "budget", label: "Budget", hint: "Is money set aside?" },
  { key: "authority", label: "Authority", hint: "Who approves the spend?" },
  { key: "need", label: "Need", hint: "How painful is the problem?" },
  { key: "timeline", label: "Timeline", hint: "What date drives it?" },
];

export function Opportunity() {
  const { id } = useParams();
  const client = useQueryClient();
  const toast = useToast();
  const [composer, setComposer] = useState<ComposerTarget | null>(null);
  const [gate, setGate] = useState<{ message: string; todo: string[] } | null>(null);
  const [closing, setClosing] = useState<string | null>(null);
  const [closeReason, setCloseReason] = useState("");
  const query = useQuery({
    queryKey: ["opportunity", id],
    queryFn: () => api.get<OpportunityDetail>(`/api/opportunities/${id}`),
  });
  const meta = useQuery({ queryKey: ["meta"], queryFn: () => api.get<Meta>("/api/meta"), staleTime: Infinity });

  const refresh = (data: OpportunityDetail) => {
    client.setQueryData(["opportunity", id], data);
    client.invalidateQueries({ predicate: (q) => q.queryKey[0] !== "opportunity" });
  };

  const stage = useMutation({
    mutationFn: (body: { stage: string; reason?: string }) =>
      api.post<OpportunityDetail>(`/api/opportunities/${id}/stage`, body),
    onSuccess: (data) => {
      setGate(null);
      refresh(data);
      toast(`Stage set to ${data.stage}.`);
    },
    onError: (error) => {
      if (error instanceof ApiError && error.status === 409) {
        const detail = error.detail as { message: string; to_do: string[] };
        setGate({ message: detail.message, todo: detail.to_do });
      } else toast((error as Error).message, "warn");
    },
  });
  const assign = useMutation({
    mutationFn: (specialist_id: string) =>
      api.post<OpportunityDetail>(`/api/opportunities/${id}/assign`, { specialist_id }),
    onSuccess: (data) => {
      refresh(data);
      toast(`Handoff brief sent to ${data.specialist}.`);
    },
  });

  if (query.isLoading) return <Loading label="Loading opportunity" />;
  if (query.error || !query.data) return <ErrorState error={query.error} />;
  const opp = query.data;
  const closed = opp.stage === "Won" || opp.stage === "Lost";

  function changeStage(next: string) {
    if (next === "Won" || next === "Lost") setClosing(next);
    else stage.mutate({ stage: next });
  }

  return (
    <div className="page">
      <nav className="crumbs" aria-label="Breadcrumb">
        <Link to="/pipeline">Pipeline</Link> / <Link to={`/partners/${opp.partner_id}`}>{opp.partner}</Link>
      </nav>
      <header className="opp-header">
        <div>
          <div className="queue-meta">
            <PracticeTag practice={opp.practice} />
            <DueTag due={opp.next_step_due} />
          </div>
          <h1>{opp.title}</h1>
          <p className="lede">
            {opp.end_customer}
            {opp.industry && `, ${opp.industry.toLowerCase()}`}. Through {opp.partner} ({opp.contact_name},{" "}
            {opp.contact_title}).
          </p>
        </div>
        <dl className="opp-facts">
          <div>
            <dt>Service</dt>
            <dd>{opp.service}</dd>
          </div>
          <div>
            <dt>Value</dt>
            <dd className="tabular">
              {cad(opp.value)} <span className="muted">({cad(opp.weighted_value)} weighted)</span>
            </dd>
          </div>
          <div>
            <dt>Stage</dt>
            <dd>
              <select
                aria-label="Stage"
                value={opp.stage}
                onChange={(e) => changeStage(e.target.value)}
                disabled={stage.isPending}
              >
                {STAGES.map((s) => (
                  <option key={s}>{s}</option>
                ))}
              </select>
              <span className="muted small"> {opp.days_in_stage}d in stage</span>
            </dd>
          </div>
        </dl>
      </header>

      {closing && (
        <form
          className="gate close-form"
          onSubmit={(e) => {
            e.preventDefault();
            stage.mutate({ stage: closing, reason: closeReason });
            setClosing(null);
            setCloseReason("");
          }}
        >
          <label className="field grow">
            Why is this {closing.toLowerCase()}? It is recorded on the timeline and in win/loss reporting.
            <input autoFocus value={closeReason} onChange={(e) => setCloseReason(e.target.value)} required minLength={3} />
          </label>
          <div className="close-actions">
            <button className="button primary" type="submit">
              Mark {closing}
            </button>
            <button className="button" type="button" onClick={() => setClosing(null)}>
              Cancel
            </button>
          </div>
        </form>
      )}
      {gate && (
        <div className="gate" role="alert">
          <div>
            <p className="gate-title">Not yet. {gate.message}</p>
            <ul>
              {gate.todo.map((t) => (
                <li key={t}>{t}</li>
              ))}
            </ul>
          </div>
          <button className="icon-button" onClick={() => setGate(null)} aria-label="Dismiss">
            ×
          </button>
        </div>
      )}
      {closed && opp.close_reason && (
        <p className="note">
          Closed {opp.stage.toLowerCase()}: {opp.close_reason}
        </p>
      )}

      <div className="two-col">
        <div className="stack">
          <section className="panel">
            <PriorityBreakdown priority={opp.priority} />
          </section>
          <Qualification opp={opp} meta={meta.data} onSaved={refresh} />
          <LogTouch opp={opp} onLogged={() => client.invalidateQueries()} />
          <section className="panel">
            <h2 className="panel-title">Timeline</h2>
            <ul className="timeline">
              {opp.activities.map((a) => (
                <li key={a.id}>
                  <span className={`tl-kind k-${a.kind}`}>{a.kind}</span>
                  <p>{a.summary}</p>
                  <p className="muted small">
                    {relativeTime(a.occurred_at)}
                    {a.outcome && `, ${a.outcome}`}
                  </p>
                </li>
              ))}
            </ul>
          </section>
        </div>

        <div className="stack">
          <section className="panel">
            <h2 className="panel-title">Specialist handoff</h2>
            {opp.specialist ? (
              <p>
                Routed to <strong>{opp.specialist}</strong>. The brief below is what they received.
              </p>
            ) : (
              <p className="muted">Pick who scopes this with the partner. The least-loaded specialist is suggested.</p>
            )}
            <ul className="specialists">
              {opp.specialists.map((s) => (
                <li key={s.id} className={s.id === opp.specialist_id ? "is-current" : ""}>
                  <div>
                    <p>
                      <strong>{s.name}</strong>
                      {s.recommended && !opp.specialist_id && <span className="suggested">Suggested</span>}
                    </p>
                    <p className="muted small">{s.title}</p>
                  </div>
                  <div className="load" title={`${s.load} of ${s.capacity} open opportunities`}>
                    <span className="load-bar">
                      <span style={{ width: `${Math.min(1, s.utilization) * 100}%` }} />
                    </span>
                    <span className="small tabular">
                      {s.load}/{s.capacity}
                    </span>
                  </div>
                  {s.id !== opp.specialist_id && !closed && (
                    <button className="button small" onClick={() => assign.mutate(s.id)} disabled={assign.isPending}>
                      Route
                    </button>
                  )}
                </li>
              ))}
            </ul>
            <details className="brief" open={!!opp.specialist}>
              <summary>Handoff brief</summary>
              <pre>{opp.handoff.text}</pre>
              <button
                className="link-button"
                onClick={async () => {
                  await navigator.clipboard?.writeText(opp.handoff.text);
                  toast("Brief copied.");
                }}
              >
                Copy brief
              </button>
            </details>
          </section>

          <section className="panel">
            <div className="panel-row">
              <h2 className="panel-title">Outreach</h2>
              {!closed && (
                <button
                  className="button primary small"
                  onClick={() =>
                    setComposer({
                      partnerId: opp.partner_id,
                      partnerName: opp.partner,
                      contactName: opp.contact_name,
                      opportunityId: opp.id,
                      heading: opp.title,
                      defaultGoal: opp.specialist ? "meeting" : opp.priority.flags.includes("stalled") ? "reengage" : "follow_up",
                    })
                  }
                >
                  Draft e-mail
                </button>
              )}
            </div>
            {opp.drafts.length === 0 ? (
              <p className="muted">No drafts yet. Drafts are reviewed and sent by you, then logged here.</p>
            ) : (
              <ul className="drafts">
                {opp.drafts.map((d) => (
                  <li key={d.id}>
                    <p>
                      <strong>{d.subject}</strong>
                    </p>
                    <p className="muted small">
                      {d.status === "approved" ? "Sent and logged" : "Draft"}, {d.engine === "claude" ? "Claude" : "rules engine"}
                      {d.edited && ", edited by you"}, {relativeTime(d.created_at)}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="panel">
            <h2 className="panel-title">Discovery questions</h2>
            <ol className="questions">
              {opp.playbook.questions.map((q) => (
                <li key={q}>{q}</li>
              ))}
            </ol>
            {opp.signal && (
              <p className="small muted">
                Opened from a {opp.signal.source.toLowerCase()} signal on {shortDate(opp.signal.detected_on)}:{" "}
                {opp.signal.title}.
              </p>
            )}
          </section>
        </div>
      </div>
      {composer && <OutreachComposer target={composer} onClose={() => setComposer(null)} />}
    </div>
  );
}

function Qualification({
  opp,
  meta,
  onSaved,
}: {
  opp: OpportunityDetail;
  meta?: Meta;
  onSaved: (d: OpportunityDetail) => void;
}) {
  const toast = useToast();
  const [bant, setBant] = useState<Bant>(opp.bant);
  const [challenge, setChallenge] = useState(opp.challenge);
  const [nextStep, setNextStep] = useState(opp.next_step);
  const [due, setDue] = useState(opp.next_step_due ?? "");
  useEffect(() => {
    setBant(opp.bant);
    setChallenge(opp.challenge);
    setNextStep(opp.next_step);
    setDue(opp.next_step_due ?? "");
  }, [opp]);
  const save = useMutation({
    mutationFn: () =>
      api.patch<OpportunityDetail>(`/api/opportunities/${opp.id}`, {
        ...bant,
        challenge,
        next_step: nextStep,
        next_step_due: due || null,
      }),
    onSuccess: (data) => {
      onSaved(data);
      toast(`Saved. Priority is now ${data.priority.score}.`);
    },
  });
  const dirty =
    JSON.stringify(bant) !== JSON.stringify(opp.bant) ||
    challenge !== opp.challenge ||
    nextStep !== opp.next_step ||
    due !== (opp.next_step_due ?? "");

  return (
    <section className="panel">
      <h2 className="panel-title">Qualification</h2>
      <div className="bant">
        {BANT_FIELDS.map((f) => (
          <fieldset key={f.key} className="bant-row">
            <legend>
              {f.label} <span className="muted small">{f.hint}</span>
            </legend>
            <div className="segmented">
              {(meta?.bant_levels[f.key] ?? [bant[f.key]]).map((level) => (
                <label key={level} className={bant[f.key] === level ? "is-on" : ""}>
                  <input
                    type="radio"
                    name={f.key}
                    value={level}
                    checked={bant[f.key] === level}
                    onChange={() => setBant({ ...bant, [f.key]: level })}
                  />
                  {BANT_LABEL[level]}
                </label>
              ))}
            </div>
          </fieldset>
        ))}
      </div>
      <label className="field">
        Customer challenge, in their words
        <textarea rows={3} value={challenge} onChange={(e) => setChallenge(e.target.value)} />
      </label>
      <div className="field-row">
        <label className="field grow">
          Next step
          <input value={nextStep} onChange={(e) => setNextStep(e.target.value)} />
        </label>
        <label className="field">
          Due
          <input type="date" value={due} onChange={(e) => setDue(e.target.value)} />
        </label>
      </div>
      <button className="button primary" disabled={!dirty || save.isPending} onClick={() => save.mutate()}>
        {save.isPending ? "Saving…" : "Save qualification"}
      </button>
    </section>
  );
}

function LogTouch({ opp, onLogged }: { opp: OpportunityDetail; onLogged: () => void }) {
  const toast = useToast();
  const [kind, setKind] = useState("call");
  const [outcome, setOutcome] = useState("connected");
  const [summary, setSummary] = useState("");
  const log = useMutation({
    mutationFn: () =>
      api.post("/api/activities", {
        partner_id: opp.partner_id,
        opportunity_id: opp.id,
        kind,
        outcome,
        summary,
      }),
    onSuccess: () => {
      setSummary("");
      onLogged();
      toast("Touch logged. The next follow-up date follows the stage cadence.");
    },
  });
  const outcomes: Record<string, string[]> = {
    call: ["connected", "voicemail", "no answer"],
    email: ["sent", "replied"],
    meeting: ["held", "rescheduled"],
    note: [""],
  };
  return (
    <section className="panel">
      <h2 className="panel-title">Log a touch</h2>
      <form
        className="log-form"
        onSubmit={(e) => {
          e.preventDefault();
          if (summary.trim().length >= 3) log.mutate();
        }}
      >
        <div className="field-row">
          <label className="field">
            Type
            <select
              value={kind}
              onChange={(e) => {
                setKind(e.target.value);
                setOutcome(outcomes[e.target.value][0]);
              }}
            >
              <option value="call">Call</option>
              <option value="email">E-mail</option>
              <option value="meeting">Meeting</option>
              <option value="note">Note</option>
            </select>
          </label>
          {kind !== "note" && (
            <label className="field">
              Outcome
              <select value={outcome} onChange={(e) => setOutcome(e.target.value)}>
                {outcomes[kind].map((o) => (
                  <option key={o}>{o}</option>
                ))}
              </select>
            </label>
          )}
        </div>
        <label className="field">
          What happened
          <textarea rows={2} value={summary} onChange={(e) => setSummary(e.target.value)} placeholder="Two lines are enough." />
        </label>
        <button className="button" type="submit" disabled={summary.trim().length < 3 || log.isPending}>
          Log touch
        </button>
      </form>
    </section>
  );
}
