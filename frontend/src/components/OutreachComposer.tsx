import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { api, type Draft, type EngineMeta } from "../api";
import { EngineNote, useToast } from "./ui";

export interface ComposerTarget {
  partnerId: string;
  partnerName: string;
  contactName?: string;
  opportunityId?: number | null;
  signalId?: number | null;
  defaultGoal?: Goal;
  heading: string;
}
type Goal = "intro" | "follow_up" | "meeting" | "reengage";

const GOALS: { value: Goal; label: string }[] = [
  { value: "intro", label: "First introduction" },
  { value: "follow_up", label: "Discovery follow-up" },
  { value: "meeting", label: "Book a specialist call" },
  { value: "reengage", label: "Re-engage a quiet contact" },
];

interface Generated {
  draft: Draft;
  review_checklist: string[];
  meta: EngineMeta;
}

export function OutreachComposer({ target, onClose }: { target: ComposerTarget; onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const client = useQueryClient();
  const toast = useToast();
  const [goal, setGoal] = useState<Goal>(target.defaultGoal ?? (target.opportunityId ? "follow_up" : "intro"));
  const [tone, setTone] = useState<"warm" | "concise">("warm");
  const [engine, setEngine] = useState<"auto" | "local">("auto");
  const [result, setResult] = useState<Generated | null>(null);
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [checked, setChecked] = useState<boolean[]>([]);

  useEffect(() => {
    dialog.current?.showModal();
  }, []);

  const generate = useMutation({
    mutationFn: () =>
      api.post<Generated>("/api/ai/outreach", {
        partner_id: target.partnerId,
        opportunity_id: target.opportunityId ?? null,
        signal_id: target.signalId ?? null,
        goal,
        tone,
        engine,
      }),
    onSuccess: (data) => {
      setResult(data);
      setSubject(data.draft.subject);
      setBody(data.draft.body);
      setChecked(data.review_checklist.map(() => false));
    },
  });

  const approve = useMutation({
    mutationFn: () => api.post<Draft>(`/api/drafts/${result!.draft.id}/approve`, { subject, body }),
    onSuccess: async () => {
      await client.invalidateQueries();
      toast(`Logged the e-mail to ${target.partnerName}. Next follow-up date set.`);
      close();
    },
  });

  function close() {
    dialog.current?.close();
    onClose();
  }

  async function copy() {
    await navigator.clipboard?.writeText(`Subject: ${subject}\n\n${body}`);
    toast("Copied to clipboard.");
  }

  const edited = result ? body.trim() !== result.draft.body.trim() : false;
  const reviewed = checked.length > 0 && checked.every(Boolean);

  return (
    <dialog ref={dialog} className="drawer" onClose={onClose} aria-labelledby="composer-title">
      <div className="drawer-head">
        <div>
          <h2 id="composer-title">Draft outreach</h2>
          <p className="muted">
            {target.heading}. To {target.contactName ?? target.partnerName}
          </p>
        </div>
        <button className="icon-button" onClick={close} aria-label="Close">
          ×
        </button>
      </div>

      <div className="drawer-body">
        <fieldset className="composer-options">
          <label>
            Purpose
            <select value={goal} onChange={(e) => setGoal(e.target.value as Goal)}>
              {GOALS.map((g) => (
                <option key={g.value} value={g.value}>
                  {g.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Tone
            <select value={tone} onChange={(e) => setTone(e.target.value as "warm" | "concise")}>
              <option value="warm">Warm, full context</option>
              <option value="concise">Short and direct</option>
            </select>
          </label>
          <label>
            Engine
            <select value={engine} onChange={(e) => setEngine(e.target.value as "auto" | "local")}>
              <option value="auto">Claude when available</option>
              <option value="local">Local rules only</option>
            </select>
          </label>
          <button className="button primary" onClick={() => generate.mutate()} disabled={generate.isPending}>
            {generate.isPending ? "Drafting…" : result ? "Draft again" : "Write draft"}
          </button>
        </fieldset>
        {generate.isError && <p className="form-error">{(generate.error as Error).message}</p>}

        {!result && !generate.isPending && (
          <p className="empty-note">
            The draft uses the partner record, the signal or opportunity, and the service catalog. You edit it, check
            it, and send it from your own mail client. PartnerSignal never sends anything.
          </p>
        )}

        {result && (
          <>
            <EngineNote meta={result.meta} />
            <label className="field">
              Subject
              <input value={subject} onChange={(e) => setSubject(e.target.value)} />
            </label>
            <label className="field">
              Message {edited && <span className="edited">edited</span>}
              <textarea value={body} onChange={(e) => setBody(e.target.value)} rows={12} />
            </label>

            <div className="composer-grid">
              <section>
                <h3>Why it says what it says</h3>
                <ul className="plain-list">
                  {result.draft.personalization.map((p) => (
                    <li key={p.element}>
                      <strong>{p.element}.</strong> {p.reason}
                    </li>
                  ))}
                </ul>
              </section>
              <section>
                <h3>Before you send</h3>
                <ul className="checklist">
                  {result.review_checklist.map((item, i) => (
                    <li key={item}>
                      <label>
                        <input
                          type="checkbox"
                          checked={checked[i] ?? false}
                          onChange={(e) => setChecked(checked.map((v, j) => (j === i ? e.target.checked : v)))}
                        />
                        {item}
                      </label>
                    </li>
                  ))}
                </ul>
              </section>
            </div>
          </>
        )}
      </div>

      {result && (
        <div className="drawer-foot">
          <button className="button" onClick={copy}>
            Copy to clipboard
          </button>
          <button
            className="button primary"
            onClick={() => approve.mutate()}
            disabled={!reviewed || approve.isPending}
            title={reviewed ? "" : "Tick every review item first"}
          >
            {approve.isPending ? "Logging…" : "Mark as sent and log it"}
          </button>
        </div>
      )}
    </dialog>
  );
}
