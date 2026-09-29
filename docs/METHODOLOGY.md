# Methodology

## Priority score

Computed in `src/partnersignal/services/scoring.py` for every open opportunity.

**Service fit (max 25)**
- Linked prospect signal: strength (1–5) × 3
- Customer challenge recorded in the customer's words: +5
- Partner has resold services in this practice before: +5

**Qualification (max 30)**, 7.5 points per BANT field at its strongest level

| Field | Levels (points) |
| --- | --- |
| Budget | unknown 0, indicated 4, confirmed 7.5 |
| Authority | unknown 0, influencer 4, decision maker 7.5 |
| Need | unknown 0, low 2, medium 5, high 7.5 |
| Timeline | unknown 0, 6+ months 2, 3–6 months 5, under 3 months 7.5 |

**Momentum (max 20)**
- Last touch ≤3 days 20, ≤7 days 15, ≤14 days 8, older 2
- Stalled (days in stage above threshold: Prospect 21, Discovery 14, Qualified 21, Solutioning 21, Proposal 14): −6

**Urgency (max 25)**
- Follow-up overdue +12, due today +10, due in 1–3 days +5
- Customer deadline from the linked signal: ≤60 days +8, ≤120 days +5

Bands: Hot ≥70, Warm ≥45, Cool below. The timeline is scored once, under qualification, so it cannot
double-count as urgency.

## Stage gates

| Target stage | Requirement |
| --- | --- |
| Qualified | Need is known, and at least three of the four BANT fields are known |
| Solutioning | A technical specialist is assigned |
| Proposal | Budget is at least indicated |

Moving backwards, or closing as won or lost, is always allowed. Closing requires a reason, which
feeds win/loss reporting. A blocked move returns HTTP 409 with the questions that would unblock it.

## Follow-up cadence

Logging a call, e-mail or meeting sets the next due date from the stage's cadence unless a date is
chosen: Prospect 4 days, Discovery 3, Qualified 5, Solutioning 4, Proposal 2.

## Signal score

Strength × 12, plus 20 for a customer deadline within 45 days (12 within 120), plus 6 when detected in
the last three days, capped at 95.

## Whitespace

For each partner and practice, product revenue = 12-month revenue × the practice's share. If the share
is at least 8% and the partner has never attached services in that practice, the gap is product
revenue × a 9% services-attach benchmark. Training is a gap when the partner's overall attach rate is
below 5%.

## AI engines

Both engines fill the schemas in `src/partnersignal/ai/schemas.py`.

- **Claude**: `messages.parse` with Pydantic output models. System prompts include the service catalog
  and BANT definitions, require verbatim quotes, and forbid invented names, numbers or dates. Refusals,
  truncated responses and API errors fall back to the local engine.
- **Local rules**: keyword weights per practice (from the playbooks), regular-expression rules for each
  BANT level, and templates for outreach. It is deterministic and used by the test suite.

## Charts and colour

Categorical colours (practices, score components, activity series) come from a palette checked for
lightness, chroma, colour-vision-deficiency separation and contrast. Practice colours always sit next to
a text label, so identity never depends on colour alone. Due and overdue states use reserved amber and
brick colours with a text label and a symbol.
