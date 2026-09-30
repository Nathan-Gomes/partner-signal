"""Explainable prioritization and qualification rules.

The priority score answers one question: *which conversation deserves attention first?*
It is not a win probability. Each of its four components is capped, and every point
comes with a sentence explaining where it came from, so a person can disagree with it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from ..catalog import BANT_QUESTIONS, OPEN_STAGES, STAGE_NAMES
from ..models import Opportunity, Signal

BANT_POINTS = {
    "budget": {"unknown": 0, "indicated": 4, "confirmed": 7.5},
    "authority": {"unknown": 0, "influencer": 4, "decision_maker": 7.5},
    "need": {"unknown": 0, "low": 2, "medium": 5, "high": 7.5},
    "timeline": {"unknown": 0, "6_plus_months": 2, "3_6_months": 5, "under_3_months": 7.5},
}
BANT_LABELS = {
    "indicated": "budget indicated",
    "confirmed": "budget confirmed",
    "influencer": "talking to an influencer",
    "decision_maker": "decision maker engaged",
    "low": "low-severity need",
    "medium": "clear business need",
    "high": "urgent business need",
    "6_plus_months": "timeline beyond 6 months",
    "3_6_months": "3-6 month timeline",
    "under_3_months": "decision inside 3 months",
}
STALL_DAYS = {"Prospect": 21, "Discovery": 14, "Qualified": 21, "Solutioning": 21, "Proposal": 14}


@dataclass
class Component:
    key: str
    label: str
    points: float
    max_points: int
    reasons: list[str] = field(default_factory=list)


@dataclass
class Priority:
    score: int
    band: str
    components: list[Component]
    flags: list[str]


def bant_score(opp: Opportunity) -> tuple[float, list[str], list[str]]:
    """Return (points out of 30, reasons, unknown BANT fields)."""
    points, reasons, missing = 0.0, [], []
    for key, table in BANT_POINTS.items():
        level = getattr(opp, key)
        points += table.get(level, 0)
        (missing.append(key) if level == "unknown" else reasons.append(BANT_LABELS[level]))
    return points, reasons, missing


def days_since(value: date | None, today: date) -> int | None:
    return None if value is None else (today - value).days


def priority(opp: Opportunity, today: date, last_touch: date | None, signal: Signal | None = None) -> Priority:
    flags: list[str] = []

    # 1. Fit: how strong is the evidence that this service is relevant?
    fit = Component("fit", "Service fit", 0, 25)
    if signal is not None:
        fit.points = signal.strength * 3
        fit.reasons.append(f"{signal.source} signal: {signal.title} (strength {signal.strength}/5)")
    if opp.challenge:
        fit.points += 5
        fit.reasons.append("customer challenge documented in their own words")
    partner = opp.partner if "partner" in opp.__dict__ else None
    if partner is not None and opp.practice in partner.services_used:
        fit.points += 5
        fit.reasons.append("partner has resold services in this practice before")
    if not fit.reasons:
        fit.reasons.append("no supporting signal recorded yet")
    fit.points = min(fit.points, fit.max_points)

    # 2. Qualification: BANT completeness.
    points, reasons, missing = bant_score(opp)
    qual = Component("qualification", "Qualification (BANT)", points, 30, reasons or ["nothing qualified yet"])
    if missing:
        qual.reasons.append("unknown: " + ", ".join(missing))

    # 3. Momentum: is the conversation alive?
    momentum = Component("momentum", "Momentum", 0, 20)
    gap = days_since(last_touch, today)
    if gap is None:
        momentum.reasons.append("no logged touches yet")
    else:
        momentum.points = 20 if gap <= 3 else 15 if gap <= 7 else 8 if gap <= 14 else 2
        momentum.reasons.append(
            "last touch today" if gap == 0 else f"last touch {gap} day{'s' if gap != 1 else ''} ago"
        )
    in_stage = (today - opp.stage_changed_on).days
    if opp.stage in STALL_DAYS and in_stage > STALL_DAYS[opp.stage]:
        momentum.points = max(0, momentum.points - 6)
        momentum.reasons.append(f"{in_stage} days in {opp.stage} (stall threshold {STALL_DAYS[opp.stage]})")
        flags.append("stalled")

    # 4. Urgency: dates that make waiting expensive.
    urgency = Component("urgency", "Urgency", 0, 25)
    if opp.next_step_due is not None:
        due_in = (opp.next_step_due - today).days
        if due_in < 0:
            urgency.points += 12
            urgency.reasons.append(f"follow-up overdue by {-due_in} day{'s' if due_in != -1 else ''}")
            flags.append("overdue")
        elif due_in == 0:
            urgency.points += 10
            urgency.reasons.append("follow-up due today")
            flags.append("due_today")
        elif due_in <= 3:
            urgency.points += 5
            urgency.reasons.append("follow-up due tomorrow" if due_in == 1 else f"follow-up due in {due_in} days")
    if signal is not None and signal.deadline is not None:
        until = (signal.deadline - today).days
        if 0 <= until <= 120:
            urgency.points += 8 if until <= 60 else 5
            urgency.reasons.append(f"customer deadline in {until} days ({signal.deadline:%b} {signal.deadline.day})")
    if not urgency.reasons:
        urgency.reasons.append("no date pressure recorded")
    urgency.points = min(urgency.points, urgency.max_points)

    if opp.stage in OPEN_STAGES and not opp.next_step:
        flags.append("no_next_step")

    components = [fit, qual, momentum, urgency]
    score = round(sum(c.points for c in components))
    band = "Hot" if score >= 70 else "Warm" if score >= 45 else "Cool"
    return Priority(score, band, components, flags)


class GateError(ValueError):
    """Raised when a stage change skips a qualification requirement."""

    def __init__(self, message: str, missing: list[str]):
        super().__init__(message)
        self.missing = missing


def check_stage_gate(opp: Opportunity, target: str) -> None:
    """Enforce the minimum evidence a stage requires before an opportunity can move forward."""
    if target not in STAGE_NAMES:
        raise GateError(f"Unknown stage '{target}'.", [])
    if target in ("Won", "Lost") or STAGE_NAMES.index(target) <= STAGE_NAMES.index(opp.stage):
        return
    _, _, missing = bant_score(opp)
    order = STAGE_NAMES.index(target)
    if order >= STAGE_NAMES.index("Qualified"):
        known = 4 - len(missing)
        if "need" in missing or known < 3:
            raise GateError(
                "Qualified requires a documented need plus at least two of budget, authority and timeline.",
                [BANT_QUESTIONS[key] for key in missing],
            )
    if order >= STAGE_NAMES.index("Solutioning") and not opp.specialist_id:
        raise GateError(
            "Assign a technical specialist before moving into Solutioning.",
            ["Route the opportunity to a specialist from the handoff panel."],
        )
    if order >= STAGE_NAMES.index("Proposal") and "budget" in missing:
        raise GateError("A proposal needs at least an indicated budget.", [BANT_QUESTIONS["budget"]])
