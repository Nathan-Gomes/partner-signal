import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { CASE_STUDY } from "./Welcome";

interface Step {
  path: string | (() => string);
  target: string; // CSS selector to highlight
  title: string;
  body: string;
  area: string; // the part of partner-services work this step covers
}

let topOpportunity: number | null = null;
export function rememberTopOpportunity(id: number | null) {
  topOpportunity = id;
}

const STEPS: Step[] = [
  {
    path: "/",
    target: ".queue-row",
    title: "Start the day knowing who to call",
    body: "Every conversation that needs attention is ranked, and each row says why: an overdue follow-up, a customer deadline, a fresh lead.",
    area: "Follow-up discipline",
  },
  {
    path: "/signals",
    target: ".signal-card",
    title: "Find new business from real signals",
    body: "Renewals, products reaching end of support, and services a partner has never sold. Each card is a concrete reason to reach out, with a suggested service.",
    area: "Prospecting",
  },
  {
    path: "/capture?sample=clinic&run=1",
    target: ".review",
    title: "Turn a phone call into a qualified opportunity",
    body: "Rough notes go in; the AI assistant returns the customer's problem, the best-fit service and how qualified the deal is, quoting the notes as evidence. A person reviews before anything is saved.",
    area: "Discovery and qualification",
  },
  {
    path: () => (topOpportunity ? `/opportunities/${topOpportunity}` : "/pipeline"),
    target: ".breakdown",
    title: "See exactly why a deal is a priority",
    body: "The score adds up four things anyone can check: service fit, qualification, momentum and urgency. It explains itself instead of hiding behind a number.",
    area: "Prioritizing with evidence",
  },
  {
    path: () => (topOpportunity ? `/opportunities/${topOpportunity}` : "/pipeline"),
    target: ".specialists",
    title: "Bring in the right specialist",
    body: "One click routes the deal to the least-busy technical specialist and sends a written handoff brief, so nobody starts from zero.",
    area: "Specialist collaboration",
  },
  {
    path: "/pipeline",
    target: ".board",
    title: "Keep the pipeline honest",
    body: "Drag a card forward and the system checks the evidence first. A deal can't be called qualified until the need, budget or timeline is actually known.",
    area: "Pipeline accuracy",
  },
  {
    path: "/reports",
    target: ".report-stats",
    title: "Report what a manager asks for",
    body: "Open pipeline, win rate, time to close and follow-through by week, plus a CRM-ready export.",
    area: "Reporting",
  },
];

interface TourApi {
  start: () => void;
  active: boolean;
}
const TourContext = createContext<TourApi>({ start: () => undefined, active: false });
export const useTour = () => useContext(TourContext);

export function TourProvider({ children }: { children: ReactNode }) {
  const [index, setIndex] = useState<number | null>(null);
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const location = useLocation();
  const highlighted = useRef<Element | null>(null);

  const start = useCallback(() => setIndex(0), []);
  const stop = useCallback(() => setIndex(null), []);

  useEffect(() => {
    if (params.get("tour") === "1") {
      params.delete("tour");
      setParams(params, { replace: true });
      setIndex(0);
    }
  }, [params, setParams]);

  // Navigate to the step's page when the step changes.
  useEffect(() => {
    if (index === null || index >= STEPS.length) return;
    const step = STEPS[index];
    const path = typeof step.path === "function" ? step.path() : step.path;
    if (location.pathname + location.search !== path) navigate(path);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [index]);

  // Highlight the target once it exists on the page.
  useEffect(() => {
    highlighted.current?.classList.remove("tour-target");
    highlighted.current = null;
    if (index === null || index >= STEPS.length) return;
    let tries = 0;
    const timer = window.setInterval(() => {
      const el = document.querySelector(STEPS[index].target);
      if (el || ++tries > 60) {
        window.clearInterval(timer);
        if (el) {
          el.classList.add("tour-target");
          const tall = el.getBoundingClientRect().height > window.innerHeight * 0.55;
          el.scrollIntoView({
            behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth",
            block: tall ? "start" : "center",
          });
          highlighted.current = el;
        }
      }
    }, 100);
    return () => window.clearInterval(timer);
  }, [index, location.pathname, location.search]);

  useEffect(() => {
    if (index === null) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") stop();
      if (e.key === "ArrowRight") setIndex((i) => (i === null ? i : Math.min(STEPS.length, i + 1)));
      if (e.key === "ArrowLeft") setIndex((i) => (i === null ? i : Math.max(0, i - 1)));
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [index, stop]);

  useEffect(() => () => highlighted.current?.classList.remove("tour-target"), []);

  return (
    <TourContext.Provider value={{ start, active: index !== null }}>
      {children}
      {index !== null && (
        <aside className="tour" role="dialog" aria-labelledby="tour-title" aria-live="polite">
          {index < STEPS.length ? (
            <>
              <div className="tour-top">
                <span className="tour-count">
                  Step {index + 1} of {STEPS.length}
                </span>
                <button className="tour-close" onClick={stop} aria-label="End the tour">
                  ×
                </button>
              </div>
              <p className="tour-job">{STEPS[index].area}</p>
              <h2 id="tour-title">{STEPS[index].title}</h2>
              <p>{STEPS[index].body}</p>
              <div className="tour-progress" aria-hidden>
                {STEPS.map((_, i) => (
                  <span key={i} className={i <= index ? "on" : ""} />
                ))}
              </div>
              <div className="tour-actions">
                <button className="button small" onClick={() => setIndex(Math.max(0, index - 1))} disabled={index === 0}>
                  Back
                </button>
                <button className="button primary small" onClick={() => setIndex(index + 1)} autoFocus>
                  {index === STEPS.length - 1 ? "Finish" : "Next"}
                </button>
              </div>
            </>
          ) : (
            <>
              <div className="tour-top">
                <span className="tour-count">Tour complete</span>
                <button className="tour-close" onClick={stop} aria-label="Close">
                  ×
                </button>
              </div>
              <h2 id="tour-title">That's the whole workflow</h2>
              <p>
                Find the right partner, qualify the conversation, bring in a specialist, follow up on time, and report on it.
                Everything is clickable: try dragging a pipeline card or drafting an e-mail from a signal.
              </p>
              <div className="tour-actions">
                <a className="button small" href={CASE_STUDY} target="_blank" rel="noreferrer">
                  How it was built
                </a>
                <button className="button primary small" onClick={stop} autoFocus>
                  Explore on my own
                </button>
              </div>
            </>
          )}
        </aside>
      )}
    </TourContext.Provider>
  );
}
