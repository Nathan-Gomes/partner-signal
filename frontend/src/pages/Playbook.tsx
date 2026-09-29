import { useQuery } from "@tanstack/react-query";
import { api, type Meta, type PracticeKey } from "../api";
import { ErrorState, Loading, PageHeader } from "../components/ui";
import { cad, PRACTICE_LABEL } from "../format";

const PRACTICES: PracticeKey[] = ["security", "cloud", "network", "ai", "lifecycle", "training"];

export function Playbook() {
  const query = useQuery({ queryKey: ["meta"], queryFn: () => api.get<Meta>("/api/meta"), staleTime: Infinity });
  if (query.isLoading) return <Loading label="Loading playbook" />;
  if (query.error || !query.data) return <ErrorState error={query.error} />;
  const { playbooks, services, stages } = query.data;

  return (
    <div className="page">
      <PageHeader
        title="Playbook"
        lede="What to listen for, what to ask, and what to offer in each practice. The same definitions drive the scoring rules and the AI prompts."
      />
      <nav className="toc" aria-label="Practices">
        {PRACTICES.map((p) => (
          <a key={p} href={`#pb-${p}`}>
            <span className={`dot p-${p}`} aria-hidden />
            {PRACTICE_LABEL[p]}
          </a>
        ))}
      </nav>
      {PRACTICES.map((p) => {
        const book = playbooks[p];
        return (
          <section key={p} id={`pb-${p}`} className="panel playbook">
            <h2 className="playbook-title">
              <span className={`dot p-${p}`} aria-hidden />
              {PRACTICE_LABEL[p]}
            </h2>
            <div className="playbook-grid">
              <div>
                <h3>Listen for</h3>
                <ul className="plain-list">
                  {book.triggers.map((t) => (
                    <li key={t}>{t}</li>
                  ))}
                </ul>
              </div>
              <div>
                <h3>Ask</h3>
                <ol className="questions">
                  {book.questions.map((q) => (
                    <li key={q}>{q}</li>
                  ))}
                </ol>
              </div>
              <div>
                <h3>Offer</h3>
                <ul className="service-list">
                  {services
                    .filter((s) => s.practice === p)
                    .map((s) => (
                      <li key={s.key}>
                        <strong>{s.name}</strong>
                        <span className="muted small block">
                          {s.duration}, typically {cad(s.typical_value)}
                        </span>
                        <span className="small block">{s.summary}</span>
                      </li>
                    ))}
                </ul>
                {book.ai_use_cases.length > 0 && (
                  <>
                    <h3>AI use cases to raise</h3>
                    <ul className="plain-list">
                      {book.ai_use_cases.map((u) => (
                        <li key={u}>{u}</li>
                      ))}
                    </ul>
                  </>
                )}
              </div>
            </div>
          </section>
        );
      })}
      <section className="panel">
        <h2 className="panel-title">Stage definitions and follow-up cadence</h2>
        <table className="data-table">
          <thead>
            <tr>
              <th scope="col">Stage</th>
              <th scope="col" className="num">Weighting</th>
              <th scope="col" className="num">Follow up within</th>
              <th scope="col">To enter this stage</th>
            </tr>
          </thead>
          <tbody>
            {stages.map((s) => (
              <tr key={s.name}>
                <th scope="row">{s.name}</th>
                <td className="num tabular">{Math.round(s.probability * 100)}%</td>
                <td className="num tabular">{s.cadence_days} days</td>
                <td>{GATES[s.name]}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

const GATES: Record<string, string> = {
  Prospect: "A signal or introduction worth a first conversation.",
  Discovery: "A conversation has started about a real customer.",
  Qualified: "A documented need plus at least two of budget, authority and timeline.",
  Solutioning: "Qualified, and a technical specialist is assigned.",
  Proposal: "Solutioning, and at least an indicated budget.",
  Won: "Customer accepted the scope. Record why.",
  Lost: "Record why, so the pattern shows up in reporting.",
};
