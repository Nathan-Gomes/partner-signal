# Methodology

## Purpose

The demo models a partner-facing professional-services workflow: capture discovery context, prioritize the next conversation, suggest a relevant practice area, and route the opportunity to a specialist.

## Data boundary

All data is fictional. The software makes no connection to Ingram Micro, Xvantage, a CRM, customers, or partner accounts.

## Recommendation model

Each partner has explicit, inspectable signals on a 0-5 scale. A weighted rule maps those signals to one of five paths:

| Path | Examples of considered signals |
| --- | --- |
| Cybersecurity assessment | security gap, compliance pressure |
| Cloud migration discovery | legacy infrastructure, cloud interest |
| Networking assessment | network refresh, distributed work |
| AI readiness workshop | AI use-case interest, data readiness |
| Technical training plan | skills gap, training need |

The highest weighted path, plus an engagement adjustment, forms the 0-100 opportunity-fit score. The UI exposes the contributing reasons for every partner, because the score is a prompt for discovery, not a decision engine.

## Follow-up behavior

The public demo stores follow-up completion in its local SQLite file. Render's free filesystem can reset after a restart, which is intentional: the app is a demonstration environment, not a production CRM.
