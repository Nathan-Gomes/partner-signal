import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, type Bant, type EngineMeta, type Extraction, type Meta, type PartnerSummary } from "../api";
import { EngineNote, PageHeader, PracticeTag } from "../components/ui";
import { BANT_LABEL } from "../format";

const SAMPLES: { partner: string; label: string; notes: string }[] = [
  {
    partner: "northstar",
    label: "Clinic ransomware worry",
    notes:
      "Call with Maya at Northstar. Their client Lakeview Family Clinics had a phishing scare last month and the insurer now wants proof of tested backups before the renewal in November.\nNobody has done a restore test in two years. The clinic's operations director signs off on IT spend, and Maya thinks there's roughly $15k set aside in this year's budget.\nThey're also curious whether Copilot could help with patient intake forms, but not sure it's safe with health data.\nThey got another quote from a local provider, but it was just for backup software.",
  },
  {
    partner: "prairie",
    label: "Warehouse Wi-Fi",
    notes:
      "Spoke with Avery. Their customer Northern Grain Co-op is opening two new warehouse sites and the handheld scanners keep dropping connection in cold storage. Orders are getting mis-picked.\nThe IT manager is our contact; the GM approves anything over $10k. No budget number yet. They want it sorted before the spring intake.",
  },
  {
    partner: "granite",
    label: "AI offer for an MSP",
    notes:
      "Ryan (COO) wants a packaged AI readiness workshop Granite can resell to law and accounting clients. Leadership has approved budget to launch a new service line by January.\nMain concern: clients' sensitive data ending up in AI tools. They'd like a governance checklist and a way to measure a 60-day pilot.",
  },
];

interface Response {
  result: Extraction;
  meta: EngineMeta;
}

export function Capture() {
  const navigate = useNavigate();
  const client = useQueryClient();
  const partners = useQuery({ queryKey: ["partners"], queryFn: () => api.get<PartnerSummary[]>("/api/partners") });
  const meta = useQuery({ queryKey: ["meta"], queryFn: () => api.get<Meta>("/api/meta"), staleTime: Infinity });
  const [partnerId, setPartnerId] = useState("northstar");
  const [notes, setNotes] = useState("");
  const [engine, setEngine] = useState<"auto" | "local">("auto");
  const [review, setReview] = useState<Response | null>(null);
  const [bant, setBant] = useState<Bant | null>(null);
  const [serviceKey, setServiceKey] = useState("");
  const [customer, setCustomer] = useState("");

  const analyze = useMutation({
    mutationFn: () => api.post<Response>("/api/ai/discovery", { partner_id: partnerId, notes, engine }),
    onSuccess: (data) => {
      setReview(data);
      const b = data.result.bant;
      setBant({ budget: b.budget.level, authority: b.authority.level, need: b.need.level, timeline: b.timeline.level });
      setServiceKey(data.result.practices[0]?.service_key ?? "");
      setCustomer(data.result.end_customer);
    },
  });
  const create = useMutation({
    mutationFn: () =>
      api.post<{ opportunity_id: number }>("/api/opportunities", {
        partner_id: partnerId,
        service_key: serviceKey,
        end_customer: customer,
        industry: review?.result.industry ?? "",
        challenge: review?.result.challenges[0]?.quote ?? "",
        next_step: review?.result.next_step.slice(0, 200) ?? "",
        notes,
        ...bant,
      }),
    onSuccess: async (data) => {
      await client.invalidateQueries();
      navigate(`/opportunities/${data.opportunity_id}`);
    },
  });

  const quotes = useMemo(() => {
    if (!review) return [];
    const r = review.result;
    return [
      ...Object.values(r.bant).map((b) => b.quote),
      ...r.challenges.map((c) => c.quote),
      ...r.practices.map((p) => p.quote),
    ].filter((q) => q && notes.includes(q));
  }, [review, notes]);

  return (
    <div className="page">
      <PageHeader
        title="Capture a call"
        lede="Paste rough notes from a partner conversation. The assistant structures them into a qualification record, quoting the notes for every judgement, and you decide what gets saved."
      />
      <div className="capture">
        <section className="panel">
          <div className="field-row">
            <label className="field grow">
              Partner
              <select value={partnerId} onChange={(e) => setPartnerId(e.target.value)}>
                {partners.data?.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              Engine
              <select value={engine} onChange={(e) => setEngine(e.target.value as "auto" | "local")}>
                <option value="auto">Claude when available</option>
                <option value="local">Local rules only</option>
              </select>
            </label>
          </div>
          <label className="field">
            Call notes
            {review ? (
              <div className="notes-view" aria-label="Call notes with evidence highlighted">
                <Highlighted text={notes} quotes={quotes} />
              </div>
            ) : (
              <textarea
                rows={11}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Who you spoke with, the customer, what's going wrong, money, people, dates…"
              />
            )}
          </label>
          <div className="sample-row">
            <span className="muted small">Try a sample:</span>
            {SAMPLES.map((s) => (
              <button
                key={s.label}
                className="chip-button"
                onClick={() => {
                  setPartnerId(s.partner);
                  setNotes(s.notes);
                  setReview(null);
                }}
              >
                {s.label}
              </button>
            ))}
          </div>
          <div className="actions">
            {review ? (
              <button className="button" onClick={() => setReview(null)}>
                Edit notes
              </button>
            ) : (
              <button
                className="button primary"
                disabled={notes.trim().length < 20 || analyze.isPending}
                onClick={() => analyze.mutate()}
              >
                {analyze.isPending ? "Reading the notes…" : "Structure these notes"}
              </button>
            )}
          </div>
          {analyze.isError && <p className="form-error">{(analyze.error as Error).message}</p>}
        </section>

        {review && bant && (
          <section className="panel review">
            <EngineNote meta={review.meta} />
            <p className="review-summary">{review.result.summary}</p>

            <h2 className="panel-title">Service fit</h2>
            <ul className="fit-list">
              {review.result.practices.map((p) => (
                <li key={p.service_key}>
                  <label>
                    <input
                      type="radio"
                      name="service"
                      checked={serviceKey === p.service_key}
                      onChange={() => setServiceKey(p.service_key)}
                    />
                    <span>
                      <PracticeTag practice={p.practice} />{" "}
                      <strong>{meta.data?.services.find((s) => s.key === p.service_key)?.name ?? p.service_key}</strong>{" "}
                      <span className={`confidence c-${p.confidence}`}>{p.confidence} confidence</span>
                    </span>
                  </label>
                  <blockquote>{p.quote}</blockquote>
                </li>
              ))}
              {review.result.practices.length === 0 && <li className="muted">No clear service fit in these notes.</li>}
            </ul>

            <h2 className="panel-title">Qualification</h2>
            <p className="muted small">Adjust any level you disagree with before saving.</p>
            <div className="bant-review">
              {(Object.keys(bant) as (keyof Bant)[]).map((key) => (
                <div key={key} className="bant-item">
                  <label>
                    {key[0].toUpperCase() + key.slice(1)}
                    <select value={bant[key]} onChange={(e) => setBant({ ...bant, [key]: e.target.value })}>
                      {(meta.data?.bant_levels[key] ?? [bant[key]]).map((level) => (
                        <option key={level} value={level}>
                          {BANT_LABEL[level]}
                        </option>
                      ))}
                    </select>
                  </label>
                  {review.result.bant[key].quote ? (
                    <blockquote>{review.result.bant[key].quote}</blockquote>
                  ) : (
                    <p className="muted small">Not in the notes.</p>
                  )}
                </div>
              ))}
            </div>

            <div className="review-grid">
              <div>
                <h3>Ask next time</h3>
                <ol className="questions">
                  {review.result.follow_up_questions.map((q) => (
                    <li key={q}>{q}</li>
                  ))}
                </ol>
              </div>
              <div>
                <h3>Watch out for</h3>
                {review.result.risks.length ? (
                  <ul className="plain-list">
                    {review.result.risks.map((r) => (
                      <li key={r}>{r}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="muted small">No risks flagged.</p>
                )}
                <h3>Suggested next step</h3>
                <p>{review.result.next_step}</p>
              </div>
            </div>

            <div className="field-row">
              <label className="field grow">
                End customer
                <input value={customer} onChange={(e) => setCustomer(e.target.value)} placeholder="To be confirmed" />
              </label>
            </div>
            <button
              className="button primary"
              disabled={!serviceKey || create.isPending}
              onClick={() => create.mutate()}
            >
              {create.isPending ? "Saving…" : "Save as a Discovery opportunity"}
            </button>
          </section>
        )}
      </div>
    </div>
  );
}

function Highlighted({ text, quotes }: { text: string; quotes: string[] }) {
  const ranges: [number, number][] = [];
  for (const q of new Set(quotes)) {
    const start = text.indexOf(q);
    if (start >= 0) ranges.push([start, start + q.length]);
  }
  ranges.sort((a, b) => a[0] - b[0]);
  const parts: { text: string; mark: boolean }[] = [];
  let cursor = 0;
  for (const [start, end] of ranges) {
    if (end <= cursor) continue;
    const from = Math.max(start, cursor);
    if (from > cursor) parts.push({ text: text.slice(cursor, from), mark: false });
    parts.push({ text: text.slice(from, end), mark: true });
    cursor = end;
  }
  if (cursor < text.length) parts.push({ text: text.slice(cursor), mark: false });
  return (
    <>
      {parts.map((p, i) => (p.mark ? <mark key={i}>{p.text}</mark> : <span key={i}>{p.text}</span>))}
    </>
  );
}
