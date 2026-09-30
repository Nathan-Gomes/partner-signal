import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

const KEY = "ps-welcome-dismissed";
export const CASE_STUDY = "https://www.nathan-gomes.com/Project-PartnerSignal.dc.html";

function dismissedBefore(): boolean {
  try {
    return window.localStorage.getItem(KEY) === "1";
  } catch {
    return false;
  }
}

export function Welcome({ topOpportunityId }: { topOpportunityId: number | null }) {
  const [params, setParams] = useSearchParams();
  const [hidden, setHidden] = useState(() => dismissedBefore() && params.get("intro") !== "1");
  if (hidden) return null;

  function dismiss() {
    try {
      window.localStorage.setItem(KEY, "1");
    } catch {
      /* private mode: dismiss for this visit only */
    }
    if (params.get("intro")) setParams({});
    setHidden(true);
  }

  return (
    <section className="welcome" aria-labelledby="welcome-title">
      <div className="welcome-text">
        <h2 id="welcome-title">Welcome to PartnerSignal</h2>
        <p>
          A working demo of how a professional-services associate could run the day: find the right reseller partner to
          call, qualify the opportunity, bring in the right specialist, and follow up on time. Every company and person is
          fictional.
        </p>
        <p className="welcome-links">
          <a href={CASE_STUDY} target="_blank" rel="noreferrer">
            Read the case study
          </a>
          <button className="link-button" onClick={dismiss}>
            Hide this intro
          </button>
        </p>
      </div>
      <ol className="welcome-steps">
        <li>
          <Link to="/capture">
            <strong>Capture a call</strong>
            <span>Paste sample notes and watch them become a qualified opportunity, with the evidence highlighted.</span>
          </Link>
        </li>
        <li>
          <Link to={topOpportunityId ? `/opportunities/${topOpportunityId}` : "/pipeline"}>
            <strong>Open the top conversation</strong>
            <span>See exactly why it ranks first, then route it to a specialist with a written handoff.</span>
          </Link>
        </li>
        <li>
          <Link to="/signals">
            <strong>Draft outreach from a signal</strong>
            <span>Generate a personalized e-mail, edit it, tick the review checklist, and log it.</span>
          </Link>
        </li>
      </ol>
    </section>
  );
}
