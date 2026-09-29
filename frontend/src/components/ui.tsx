import { createContext, useCallback, useContext, useState, type ReactNode } from "react";
import type { Component, EngineMeta, PracticeKey, Priority } from "../api";
import { dueLabel, PRACTICE_LABEL } from "../format";

/* ---------- the signal strip: four capped components that add up to the priority score ---------- */

const COMPONENT_ORDER: Component["key"][] = ["fit", "qualification", "momentum", "urgency"];

export function SignalStrip({ priority, size = "sm" }: { priority: Priority; size?: "sm" | "lg" }) {
  const parts = COMPONENT_ORDER.map((key) => priority.components.find((c) => c.key === key)!);
  const label = parts.map((p) => `${p.label} ${Math.round(p.points)} of ${p.max}`).join(", ");
  return (
    <div className={`strip strip-${size}`} role="img" aria-label={`Priority ${priority.score}: ${label}`}>
      <span className="strip-score">{priority.score}</span>
      <span className="strip-track">
        {parts.map((p) => (
          <span key={p.key} className="strip-slot" style={{ flexGrow: p.max }} title={`${p.label}: ${Math.round(p.points)}/${p.max}`}>
            <span className={`strip-fill c-${p.key}`} style={{ width: `${(p.points / p.max) * 100}%` }} />
          </span>
        ))}
      </span>
    </div>
  );
}

export function PriorityBreakdown({ priority }: { priority: Priority }) {
  return (
    <div className="breakdown">
      <div className="breakdown-head">
        <div>
          <p className="breakdown-score">
            {priority.score}
            <span>/100</span>
          </p>
          <p className="muted small">Priority, not probability. It ranks which conversation needs you first.</p>
        </div>
        <BandTag band={priority.band} />
      </div>
      <SignalStrip priority={priority} size="lg" />
      <ul className="breakdown-list">
        {COMPONENT_ORDER.map((key) => {
          const c = priority.components.find((item) => item.key === key)!;
          return (
            <li key={key}>
              <span className={`swatch c-${key}`} aria-hidden />
              <div>
                <p className="breakdown-label">
                  {c.label}
                  <span className="tabular">
                    {Math.round(c.points)} / {c.max}
                  </span>
                </p>
                <ul className="reason-list">
                  {c.reasons.map((reason) => (
                    <li key={reason}>{reason}</li>
                  ))}
                </ul>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

/* ---------- tags ---------- */

export function PracticeTag({ practice }: { practice: PracticeKey | string }) {
  return (
    <span className="practice-tag">
      <span className={`dot p-${practice}`} aria-hidden />
      {PRACTICE_LABEL[practice] ?? practice}
    </span>
  );
}

export function BandTag({ band }: { band: string }) {
  return <span className={`band band-${band.toLowerCase()}`}>{band}</span>;
}

export function DueTag({ due }: { due: string | null }) {
  const label = dueLabel(due);
  if (!label) return null;
  const icon = label.tone === "overdue" ? "!" : label.tone === "today" ? "•" : "";
  return (
    <span className={`due due-${label.tone}`}>
      {icon && <span aria-hidden>{icon}</span>}
      {label.text}
    </span>
  );
}

export function EngineNote({ meta }: { meta: EngineMeta }) {
  return (
    <p className={`engine engine-${meta.engine}`}>
      <strong>{meta.engine === "claude" ? `Drafted with Claude (${meta.model})` : "Drafted by the local rules engine"}</strong>
      {meta.note && <span> {meta.note}</span>}
    </p>
  );
}

/* ---------- page furniture ---------- */

export function PageHeader({ title, lede, actions }: { title: string; lede?: ReactNode; actions?: ReactNode }) {
  return (
    <header className="page-header">
      <div>
        <h1>{title}</h1>
        {lede && <p className="lede">{lede}</p>}
      </div>
      {actions && <div className="page-actions">{actions}</div>}
    </header>
  );
}

export function Loading({ label = "Loading" }: { label?: string }) {
  return (
    <div className="state" role="status">
      <span className="spinner" aria-hidden />
      {label}…
    </div>
  );
}

export function ErrorState({ error }: { error: unknown }) {
  const message = error instanceof Error ? error.message : "Something went wrong.";
  return (
    <div className="state state-error" role="alert">
      <strong>Could not load this view.</strong> {message} The free server may still be waking up; reload in a few
      seconds.
    </div>
  );
}

/* ---------- toasts ---------- */

type Toast = { id: number; text: string; tone: "ok" | "warn" };
const ToastContext = createContext<(text: string, tone?: Toast["tone"]) => void>(() => undefined);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const push = useCallback((text: string, tone: Toast["tone"] = "ok") => {
    const id = Date.now() + Math.random();
    setToasts((items) => [...items, { id, text, tone }]);
    setTimeout(() => setToasts((items) => items.filter((t) => t.id !== id)), 4200);
  }, []);
  return (
    <ToastContext.Provider value={push}>
      {children}
      <div className="toasts" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className={`toast toast-${t.tone}`}>
            {t.text}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export const useToast = () => useContext(ToastContext);
