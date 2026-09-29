"""Transparent opportunity scoring and outreach helpers for the fictional CRM demo."""

from __future__ import annotations

from dataclasses import dataclass

SERVICE_LABELS = {
    "security": "Cybersecurity assessment",
    "cloud": "Cloud migration discovery",
    "network": "Networking assessment",
    "ai": "AI readiness workshop",
    "training": "Technical training plan",
}

SPECIALISTS = {
    "security": "Security Solutions Specialist",
    "cloud": "Cloud & Hybrid IT Specialist",
    "network": "Networking Practice Specialist",
    "ai": "AI Solutions Specialist",
    "training": "Enablement & Training Specialist",
}


@dataclass(frozen=True)
class Recommendation:
    score: int
    service_key: str
    reasoning: list[str]


def recommend(signals: dict[str, int]) -> Recommendation:
    """Score declared partner signals using simple, reviewable business rules."""
    weighted = {
        "security": signals.get("security_gap", 0) * 3 + signals.get("compliance", 0) * 2,
        "cloud": signals.get("legacy_infrastructure", 0) * 3 + signals.get("cloud_interest", 0) * 2,
        "network": signals.get("network_refresh", 0) * 3 + signals.get("remote_work", 0),
        "ai": signals.get("ai_interest", 0) * 3 + signals.get("data_readiness", 0) * 2,
        "training": signals.get("training_need", 0) * 3 + signals.get("skill_gap", 0) * 2,
    }
    service_key = max(weighted, key=weighted.get)
    score = min(97, round(20 + weighted[service_key] * 2.4 + signals.get("engagement", 0) * 3))
    reasons = {
        "security": ["security posture gap", "compliance pressure"],
        "cloud": ["legacy infrastructure", "stated cloud interest"],
        "network": ["network refresh timing", "distributed-work requirements"],
        "ai": ["AI use-case interest", "available data foundation"],
        "training": ["stated skills gap", "team enablement need"],
    }[service_key]
    present = [reason for reason in reasons if _signal_for_reason(reason, signals)]
    return Recommendation(score=score, service_key=service_key, reasoning=present or reasons[:1])


def _signal_for_reason(reason: str, signals: dict[str, int]) -> bool:
    mapping = {
        "security posture gap": "security_gap",
        "compliance pressure": "compliance",
        "legacy infrastructure": "legacy_infrastructure",
        "stated cloud interest": "cloud_interest",
        "network refresh timing": "network_refresh",
        "distributed-work requirements": "remote_work",
        "AI use-case interest": "ai_interest",
        "available data foundation": "data_readiness",
        "stated skills gap": "skill_gap",
        "team enablement need": "training_need",
    }
    return signals.get(mapping[reason], 0) > 0


def outreach(partner: dict[str, object]) -> dict[str, str]:
    recommendation = recommend(partner["signals"])
    service = SERVICE_LABELS[recommendation.service_key]
    name = str(partner["contact_name"]).split()[0]
    company = str(partner["company"])
    challenge = str(partner["challenge"]).rstrip(".")
    return {
        "subject": f"A practical next step for {company}'s {service.lower()} needs",
        "body": (
            f"Hi {name},\n\n"
            f"Thanks for sharing that {challenge.lower()}. Based on that conversation, a short "
            f"{service.lower()} could help clarify priorities, scope and the right technical path before "
            f"you commit to a larger project.\n\n"
            "Would a 20-minute discovery conversation next week be useful? I can bring in the right "
            "specialist once we understand the outcomes you are aiming for.\n\n"
            "Best,\nNathan"
        ),
        "service": service,
        "specialist": SPECIALISTS[recommendation.service_key],
    }
