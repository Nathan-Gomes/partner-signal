import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { api, type QueueItem, type TodayView } from "../api";
import { type ComposerTarget, OutreachComposer } from "../components/OutreachComposer";
import { BandTag, DueTag, ErrorState, Loading, PageHeader, PracticeTag } from "../components/ui";
import { Welcome } from "../components/Welcome";
import { cadShort, parseDay, relativeTime } from "../format";

const KIND_HINT: Record<QueueItem["kind"], string> = {
  follow_up: "Follow-up",
  route: "Needs a specialist",
  reengage: "Stalled",
  prospect: "New signal",
};

export function Today() {
  const { data, error, isLoading } = useQuery({ queryKey: ["today"], queryFn: () => api.get<TodayView>("/api/today") });
  const [composer, setComposer] = useState<ComposerTarget | null>(null);
  if (isLoading) return <Loading label="Building today's queue" />;
  if (error || !data) return <ErrorState error={error} />;

  const { kpis } = data;
  const date = parseDay(data.date).toLocaleDateString("en-CA", { weekday: "long", month: "long", day: "numeric" });
  const progress = Math.min(1, kpis.touches_this_week / kpis.weekly_touch_goal);

  return (
    <div className="page">
      <PageHeader
        title={date}
        lede={
          <>
            {data.queue.length} conversations are ranked for today. Work from the top: each row says why it is there.
          </>
        }
      />

      <Welcome topOpportunityId={data.queue.find((q) => q.opportunity_id)?.opportunity_id ?? null} />

      <section className="day-sheet" aria-label="This week">
        <div className="day-goal">
          <p className="day-figure tabular">
            {kpis.touches_this_week}
            <span> of {kpis.weekly_touch_goal} touches this week</span>
          </p>
          <div className="meter" role="progressbar" aria-valuenow={kpis.touches_this_week} aria-valuemin={0} aria-valuemax={kpis.weekly_touch_goal} aria-label="Weekly touch goal">
            <span style={{ width: `${progress * 100}%` }} />
          </div>
        </div>
        <dl className="day-stats">
          <div>
            <dt>Due today</dt>
            <dd className="tabular">{kpis.due_today}</dd>
          </div>
          <div className={kpis.overdue ? "is-alert" : ""}>
            <dt>Overdue</dt>
            <dd className="tabular">{kpis.overdue}</dd>
          </div>
          <div>
            <dt>New signals</dt>
            <dd className="tabular">{kpis.new_signals}</dd>
          </div>
          <div>
            <dt>Weighted pipeline</dt>
            <dd className="tabular">{cadShort(kpis.weighted_pipeline)}</dd>
          </div>
        </dl>
      </section>

      <div className="two-col">
        <section aria-labelledby="queue-title">
          <h2 id="queue-title" className="section-title">
            Priority queue
          </h2>
          <ol className="queue">
            {data.queue.map((item, index) => (
              <li key={`${item.kind}-${item.opportunity_id ?? item.signal_id}`} className="queue-row">
                <span className="queue-rank tabular" aria-label={`Rank ${index + 1}`}>
                  {index + 1}
                </span>
                <div className="queue-main">
                  <div className="queue-meta">
                    <span className={`kind kind-${item.kind}`}>{KIND_HINT[item.kind]}</span>
                    <PracticeTag practice={item.practice} />
                    <DueTag due={item.due} />
                  </div>
                  <p className="queue-title">
                    {item.opportunity_id ? (
                      <Link to={`/opportunities/${item.opportunity_id}`}>{item.title}</Link>
                    ) : (
                      item.title
                    )}
                  </p>
                  <p className="queue-partner">
                    <Link to={`/partners/${item.partner_id}`}>{item.partner}</Link>
                    {item.next_step && <span>. Next: {item.next_step}</span>}
                  </p>
                  <ul className="reason-inline">
                    {item.reasons.map((reason) => (
                      <li key={reason}>{reason}</li>
                    ))}
                  </ul>
                </div>
                <div className="queue-side">
                  <p className="queue-score">
                    <span className="tabular">{item.score}</span>
                    <BandTag band={item.band} />
                  </p>
                  {item.kind === "prospect" ? (
                    <button
                      className="button primary small"
                      onClick={() =>
                        setComposer({
                          partnerId: item.partner_id,
                          partnerName: item.partner,
                          signalId: item.signal_id,
                          heading: item.title,
                          defaultGoal: "intro",
                        })
                      }
                    >
                      Draft outreach
                    </button>
                  ) : (
                    <Link className="button small" to={`/opportunities/${item.opportunity_id}`}>
                      {item.verb}
                    </Link>
                  )}
                </div>
              </li>
            ))}
          </ol>
        </section>

        <aside className="rail" aria-labelledby="recent-title">
          <h2 id="recent-title" className="section-title">
            Latest activity
          </h2>
          <ul className="timeline compact">
            {data.recent_activity.map((a) => (
              <li key={a.id}>
                <span className={`tl-kind k-${a.kind}`}>{a.kind}</span>
                <p>{a.summary}</p>
                <p className="muted small">
                  <Link to={`/partners/${a.partner_id}`}>{a.partner}</Link>, {relativeTime(a.occurred_at)}
                </p>
              </li>
            ))}
          </ul>
          <div className="rail-note">
            <h3>How the ranking works</h3>
            <p>
              Each score adds four capped parts: service fit, BANT qualification, momentum and date urgency. Open any
              opportunity to see every point explained, and disagree with it.
            </p>
          </div>
        </aside>
      </div>
      {composer && <OutreachComposer target={composer} onClose={() => setComposer(null)} />}
    </div>
  );
}
