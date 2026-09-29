# PartnerSignal

PartnerSignal is a fictional partner-operations workspace for turning reseller discovery notes into visible follow-up actions, service recommendations, specialist handoffs and personalized outreach drafts.

It is a portfolio demonstration of the workflow described in early-career professional-services and customer-success roles. It is **not connected to Ingram Micro, Xvantage, or any live CRM**, and every company, contact and opportunity in the application is fictional.

## What it demonstrates

- Partner and opportunity tracking backed by SQLite
- Transparent rules that map stated needs to cybersecurity, cloud, networking, AI and training paths
- A reasoned specialist handoff rather than an opaque recommendation
- Tailored discovery outreach based on the partner context
- Follow-up tracking and an intentionally simple opportunity pipeline
- FastAPI service endpoints with automated tests

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
uvicorn partnersignal.app:app --reload
```

Open `http://127.0.0.1:8000`.

## Technology

Python, FastAPI, SQLite, JavaScript, HTML, CSS, pytest, and GitHub Actions.

## Design note

The opportunity score is deliberately rules-based and reviewable. It helps prioritize conversations, but it does not decide whether an opportunity is real or replace technical, sales, or customer-success judgment.
