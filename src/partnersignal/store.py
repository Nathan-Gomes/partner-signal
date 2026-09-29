"""SQLite-backed fictional partner data for the public demo."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .logic import SERVICE_LABELS, SPECIALISTS, recommend

SEED_PARTNERS = [
    {
        "id": "northstar-it",
        "company": "Northstar IT Group",
        "contact_name": "Maya Chen",
        "vertical": "Managed services",
        "region": "Ontario",
        "stage": "Discovery",
        "last_touch": "2026-09-25",
        "next_follow_up": "2026-09-30",
        "challenge": "A healthcare client needs a clearer ransomware recovery plan before renewal.",
        "notes": "Asked about security assessment scope and compliance documentation.",
        "signals": {"security_gap": 5, "compliance": 4, "engagement": 4, "cloud_interest": 1},
    },
    {
        "id": "harbour-tech",
        "company": "Harbour Tech Solutions",
        "contact_name": "Jordan Patel",
        "vertical": "Mid-market VAR",
        "region": "British Columbia",
        "stage": "Qualified",
        "last_touch": "2026-09-22",
        "next_follow_up": "2026-09-29",
        "challenge": "A manufacturing customer is retiring on-premise servers over the next year.",
        "notes": "Requested a migration discovery workshop before a formal proposal.",
        "signals": {"legacy_infrastructure": 5, "cloud_interest": 5, "engagement": 4, "data_readiness": 2},
    },
    {
        "id": "prairie-digital",
        "company": "Prairie Digital Partners",
        "contact_name": "Avery Thompson",
        "vertical": "Regional reseller",
        "region": "Saskatchewan",
        "stage": "Contacted",
        "last_touch": "2026-09-19",
        "next_follow_up": "2026-09-27",
        "challenge": "A growing distribution business is experiencing unreliable warehouse connectivity.",
        "notes": "Partner mentioned expansion to two new sites and mobile scanning issues.",
        "signals": {"network_refresh": 5, "remote_work": 3, "engagement": 3},
    },
    {
        "id": "cobalt-cloud",
        "company": "Cobalt Cloud Advisors",
        "contact_name": "Samira Ali",
        "vertical": "Cloud consultancy",
        "region": "Quebec",
        "stage": "Technical review",
        "last_touch": "2026-09-24",
        "next_follow_up": "2026-10-01",
        "challenge": "A financial-services client wants to prioritize AI use cases without exposing sensitive data.",
        "notes": "Interested in an AI readiness workshop and governance conversation.",
        "signals": {"ai_interest": 5, "data_readiness": 4, "engagement": 5, "compliance": 2},
    },
    {
        "id": "summit-works",
        "company": "Summit Works",
        "contact_name": "Ethan Martin",
        "vertical": "Technology retailer",
        "region": "Alberta",
        "stage": "Nurture",
        "last_touch": "2026-09-11",
        "next_follow_up": "2026-10-03",
        "challenge": "The technical sales team needs better cloud and security discovery conversations.",
        "notes": "Training interest is clear, but timing depends on Q4 planning.",
        "signals": {"training_need": 5, "skill_gap": 4, "engagement": 2},
    },
    {
        "id": "vector-link",
        "company": "VectorLink Networks",
        "contact_name": "Noah Williams",
        "vertical": "Network integrator",
        "region": "Atlantic Canada",
        "stage": "Proposal",
        "last_touch": "2026-09-26",
        "next_follow_up": "2026-10-02",
        "challenge": "A public-sector customer needs a network segmentation plan for a new remote access program.",
        "notes": "Solution outline is being reviewed with a networking specialist.",
        "signals": {"network_refresh": 4, "remote_work": 5, "engagement": 5, "security_gap": 2},
    },
]


def database_path() -> Path:
    configured = Path(__import__("os").environ.get("PARTNER_SIGNAL_DB", "data/partner-signal.db"))
    configured.parent.mkdir(parents=True, exist_ok=True)
    return configured


def connection(path: Path | None = None) -> sqlite3.Connection:
    db = sqlite3.connect(path or database_path())
    db.row_factory = sqlite3.Row
    return db


def initialize(path: Path | None = None) -> None:
    with connection(path) as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS partners (
              id TEXT PRIMARY KEY, company TEXT NOT NULL, contact_name TEXT NOT NULL,
              vertical TEXT NOT NULL, region TEXT NOT NULL, stage TEXT NOT NULL,
              last_touch TEXT NOT NULL, next_follow_up TEXT NOT NULL, challenge TEXT NOT NULL,
              notes TEXT NOT NULL, signals TEXT NOT NULL, follow_up_complete INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        if db.execute("SELECT COUNT(*) FROM partners").fetchone()[0] == 0:
            db.executemany(
                """INSERT INTO partners
                (id, company, contact_name, vertical, region, stage, last_touch, next_follow_up, challenge, notes, signals)
                VALUES (:id, :company, :contact_name, :vertical, :region, :stage, :last_touch, :next_follow_up, :challenge, :notes, :signals)""",
                [{**partner, "signals": json.dumps(partner["signals"])} for partner in SEED_PARTNERS],
            )


def _serialize(row: sqlite3.Row) -> dict[str, Any]:
    partner = dict(row)
    partner["signals"] = json.loads(partner["signals"])
    partner["follow_up_complete"] = bool(partner["follow_up_complete"])
    recommendation = recommend(partner["signals"])
    partner.update(
        {
            "opportunity_score": recommendation.score,
            "recommended_service": SERVICE_LABELS[recommendation.service_key],
            "specialist": SPECIALISTS[recommendation.service_key],
            "reasoning": recommendation.reasoning,
        }
    )
    return partner


def list_partners(path: Path | None = None) -> list[dict[str, Any]]:
    initialize(path)
    with connection(path) as db:
        rows = db.execute("SELECT * FROM partners ORDER BY next_follow_up ASC, company ASC").fetchall()
    return [_serialize(row) for row in rows]


def get_partner(partner_id: str, path: Path | None = None) -> dict[str, Any] | None:
    initialize(path)
    with connection(path) as db:
        row = db.execute("SELECT * FROM partners WHERE id = ?", (partner_id,)).fetchone()
    return _serialize(row) if row else None


def complete_follow_up(partner_id: str, path: Path | None = None) -> dict[str, Any] | None:
    initialize(path)
    with connection(path) as db:
        db.execute("UPDATE partners SET follow_up_complete = 1 WHERE id = ?", (partner_id,))
    return get_partner(partner_id, path)
