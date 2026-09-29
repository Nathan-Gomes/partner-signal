"""Queries and state changes behind the API: the daily queue, pipeline, handoffs and reports."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..catalog import (
    BANT_QUESTIONS,
    OPEN_STAGES,
    PLAYBOOKS,
    PRACTICES,
    SERVICES_BY_KEY,
    STAGE_CADENCE,
    STAGE_NAMES,
    STAGE_PROBABILITY,
)
from ..models import Activity, Draft, Opportunity, Partner, Signal, Specialist
from .scoring import Priority, bant_score, check_stage_gate, priority

WEEKLY_TOUCH_GOAL = 40
URGENCY_FIRST = ["urgency", "momentum", "fit", "qualification"]
ATTACH_BENCHMARK = 0.09  # services revenue a healthy partner attaches per dollar of product in a practice


class NotFound(LookupError):
    pass


# ---------- helpers ----------


def last_touches(session: Session) -> dict[int, date]:
    rows = session.execute(
        select(Activity.opportunity_id, func.max(Activity.occurred_at))
        .where(Activity.opportunity_id.is_not(None))
        .group_by(Activity.opportunity_id)
    )
    return {opp_id: moment.date() for opp_id, moment in rows if opp_id is not None}


def partner_last_touch(session: Session) -> dict[str, date]:
    rows = session.execute(select(Activity.partner_id, func.max(Activity.occurred_at)).group_by(Activity.partner_id))
    return {pid: moment.date() for pid, moment in rows}


def weighted(opp: Opportunity) -> float:
    return opp.value * STAGE_PROBABILITY[opp.stage]


def serialize_priority(result: Priority) -> dict:
    return {
        "score": result.score,
        "band": result.band,
        "flags": result.flags,
        "components": [
            {"key": c.key, "label": c.label, "points": round(c.points, 1), "max": c.max_points, "reasons": c.reasons}
            for c in result.components
        ],
    }


def opportunity_summary(opp: Opportunity, today: date, touches: dict[int, date]) -> dict:
    result = priority(opp, today, touches.get(opp.id), opp_signal(opp))
    service = SERVICES_BY_KEY[opp.service_key]
    return {
        "id": opp.id,
        "title": opp.title,
        "partner_id": opp.partner_id,
        "partner": opp.partner.name,
        "end_customer": opp.end_customer,
        "industry": opp.industry,
        "practice": opp.practice,
        "service_key": opp.service_key,
        "service": service.name,
        "stage": opp.stage,
        "value": opp.value,
        "weighted_value": round(weighted(opp)),
        "next_step": opp.next_step,
        "next_step_due": opp.next_step_due,
        "days_in_stage": (today - opp.stage_changed_on).days,
        "last_touch": touches.get(opp.id),
        "specialist": opp.specialist.name if opp.specialist else None,
        "bant": {k: getattr(opp, k) for k in ("budget", "authority", "need", "timeline")},
        "priority": serialize_priority(result),
    }


def opp_signal(opp: Opportunity) -> Signal | None:
    if opp.signal_id is None:
        return None
    return next((s for s in opp.partner.signals if s.id == opp.signal_id), None)


def load_opportunities(session: Session):
    return session.scalars(
        select(Opportunity).options(
            selectinload(Opportunity.partner).selectinload(Partner.signals),
            selectinload(Opportunity.specialist),
        )
    ).all()


def get_opportunity(session: Session, opp_id: int) -> Opportunity:
    opp = session.get(Opportunity, opp_id)
    if opp is None:
        raise NotFound(f"Opportunity {opp_id} not found.")
    return opp


def get_partner(session: Session, partner_id: str) -> Partner:
    partner = session.get(Partner, partner_id)
    if partner is None:
        raise NotFound(f"Partner '{partner_id}' not found.")
    return partner


def signal_score(signal: Signal, today: date) -> int:
    score = signal.strength * 12
    if signal.deadline:
        until = (signal.deadline - today).days
        score += 20 if 0 <= until <= 45 else 12 if until <= 120 else 0
    score += 6 if (today - signal.detected_on).days <= 3 else 0
    return min(score, 95)


def serialize_signal(signal: Signal, today: date) -> dict:
    service = SERVICES_BY_KEY[signal.service_key]
    return {
        "id": signal.id,
        "partner_id": signal.partner_id,
        "partner": signal.partner.name,
        "kind": signal.kind,
        "source": signal.source,
        "practice": signal.practice,
        "service_key": signal.service_key,
        "service": service.name,
        "title": signal.title,
        "detail": signal.detail,
        "strength": signal.strength,
        "detected_on": signal.detected_on,
        "deadline": signal.deadline,
        "status": signal.status,
        "score": signal_score(signal, today),
        "estimated_value": service.typical_value,
    }


# ---------- today ----------


def today_view(session: Session, today: date) -> dict:
    opportunities = load_opportunities(session)
    touches = last_touches(session)
    open_opps = [o for o in opportunities if o.stage in OPEN_STAGES]
    queue: list[dict] = []
    for opp in open_opps:
        summary = opportunity_summary(opp, today, touches)
        flags = summary["priority"]["flags"]
        if "overdue" in flags or "due_today" in flags:
            action, verb = "follow_up", "Follow up"
        elif opp.stage == "Qualified" and not opp.specialist_id:
            action, verb = "route", "Route to specialist"
        elif "stalled" in flags:
            action, verb = "reengage", "Re-engage"
        else:
            continue
        ordered = sorted(summary["priority"]["components"], key=lambda c: URGENCY_FIRST.index(c["key"]))
        reasons = [r for c in ordered for r in c["reasons"] if not r.startswith(("unknown:", "no "))][:3]
        queue.append(
            {
                "kind": action,
                "verb": verb,
                "score": summary["priority"]["score"],
                "band": summary["priority"]["band"],
                "title": opp.title,
                "partner": opp.partner.name,
                "partner_id": opp.partner_id,
                "opportunity_id": opp.id,
                "signal_id": None,
                "next_step": opp.next_step,
                "due": opp.next_step_due,
                "stage": opp.stage,
                "reasons": reasons,
                "practice": opp.practice,
            }
        )
    new_signals = session.scalars(
        select(Signal).where(Signal.status == "new").options(selectinload(Signal.partner))
    ).all()
    for signal in new_signals:
        score = signal_score(signal, today)
        reasons = [f"{signal.source}, strength {signal.strength}/5"]
        if signal.deadline:
            reasons.append(f"customer deadline in {(signal.deadline - today).days} days")
        queue.append(
            {
                "kind": "prospect",
                "verb": "Start outreach",
                "score": score,
                "band": "Hot" if score >= 70 else "Warm" if score >= 45 else "Cool",
                "title": signal.title,
                "partner": signal.partner.name,
                "partner_id": signal.partner_id,
                "opportunity_id": None,
                "signal_id": signal.id,
                "next_step": f"Introduce the {SERVICES_BY_KEY[signal.service_key].name.lower()}",
                "due": None,
                "stage": "Signal",
                "reasons": reasons,
                "practice": signal.practice,
            }
        )
    queue.sort(key=lambda item: (-item["score"], item["title"]))

    week_start = datetime.combine(today - timedelta(days=today.weekday()), datetime.min.time())
    week = session.scalars(select(Activity).where(Activity.occurred_at >= week_start)).all()
    touches_week = sum(a.kind in ("call", "email", "meeting") for a in week)
    recent = session.scalars(
        select(Activity).options(selectinload(Activity.partner)).order_by(Activity.occurred_at.desc()).limit(8)
    ).all()
    due = [o for o in open_opps if o.next_step_due]
    return {
        "date": today,
        "kpis": {
            "touches_this_week": touches_week,
            "weekly_touch_goal": WEEKLY_TOUCH_GOAL,
            "due_today": sum(o.next_step_due == today for o in due),
            "overdue": sum(o.next_step_due < today for o in due),
            "open_pipeline": sum(o.value for o in open_opps),
            "weighted_pipeline": round(sum(weighted(o) for o in open_opps)),
            "open_opportunities": len(open_opps),
            "new_signals": len(new_signals),
            "qualified_or_later": sum(STAGE_NAMES.index(o.stage) >= 2 for o in open_opps),
        },
        "queue": queue[:14],
        "recent_activity": [serialize_activity(a) for a in recent],
    }


def serialize_activity(activity: Activity) -> dict:
    return {
        "id": activity.id,
        "partner_id": activity.partner_id,
        "partner": activity.partner.name,
        "opportunity_id": activity.opportunity_id,
        "kind": activity.kind,
        "summary": activity.summary,
        "outcome": activity.outcome,
        "occurred_at": activity.occurred_at,
    }


# ---------- partners & whitespace ----------


def whitespace_cells(partner: Partner) -> dict[str, dict]:
    cells = {}
    for practice in PRACTICES:
        share = partner.product_mix.get(practice, 0.0)
        attached = practice in partner.services_used
        product = partner.trailing_revenue * share
        if share < 0.08:
            status, potential = "none", 0.0
        elif attached:
            status, potential = "attached", 0.0
        else:
            status, potential = "gap", round(product * ATTACH_BENCHMARK, -2)
        cells[practice] = {
            "share": round(share, 2),
            "product_revenue": round(product),
            "status": status,
            "potential": potential,
        }
    # Training has no product revenue: it is a gap whenever attach rate is well below benchmark.
    rate = partner.services_revenue / partner.trailing_revenue
    if "training" not in partner.services_used and rate < 0.05:
        cells["training"] = {
            "share": 0,
            "product_revenue": 0,
            "status": "gap",
            "potential": round(partner.trailing_revenue * 0.003, -2),
        }
    return cells


def partner_summary(partner: Partner, today: date, last: dict[str, date]) -> dict:
    open_opps = [o for o in partner.opportunities if o.stage in OPEN_STAGES]
    cells = whitespace_cells(partner)
    return {
        "id": partner.id,
        "name": partner.name,
        "partner_type": partner.partner_type,
        "tier": partner.tier,
        "city": partner.city,
        "province": partner.province,
        "contact_name": partner.contact_name,
        "contact_title": partner.contact_title,
        "verticals": partner.verticals,
        "trailing_revenue": partner.trailing_revenue,
        "services_revenue": partner.services_revenue,
        "attach_rate": round(partner.services_revenue / partner.trailing_revenue, 3),
        "open_opportunities": len(open_opps),
        "open_pipeline": sum(o.value for o in open_opps),
        "new_signals": sum(s.status == "new" for s in partner.signals),
        "whitespace_potential": sum(c["potential"] for c in cells.values()),
        "last_touch": last.get(partner.id),
        "days_since_touch": (today - last[partner.id]).days if partner.id in last else None,
    }


def list_partners(session: Session, today: date) -> list[dict]:
    partners = session.scalars(
        select(Partner)
        .options(selectinload(Partner.opportunities), selectinload(Partner.signals))
        .order_by(Partner.name)
    ).all()
    last = partner_last_touch(session)
    return [partner_summary(p, today, last) for p in partners]


def partner_detail(session: Session, partner_id: str, today: date) -> dict:
    partner = get_partner(session, partner_id)
    last = partner_last_touch(session)
    touches = last_touches(session)
    activities = sorted(partner.activities, key=lambda a: a.occurred_at, reverse=True)[:25]
    return {
        **partner_summary(partner, today, last),
        "contact_email": partner.contact_email,
        "vendors": partner.vendors,
        "about": partner.about,
        "product_mix": partner.product_mix,
        "services_used": partner.services_used,
        "whitespace": whitespace_cells(partner),
        "signals": [serialize_signal(s, today) for s in sorted(partner.signals, key=lambda s: -s.strength)],
        "opportunities": [
            opportunity_summary(o, today, touches)
            for o in sorted(partner.opportunities, key=lambda o: STAGE_NAMES.index(o.stage))
        ],
        "activities": [serialize_activity(a) for a in activities],
    }


def whitespace_matrix(session: Session) -> dict:
    partners = session.scalars(select(Partner).order_by(Partner.name)).all()
    rows = [(p, whitespace_cells(p)) for p in partners]
    totals = {k: sum(cells[k]["potential"] for _, cells in rows) for k in PRACTICES}
    rows.sort(key=lambda row: -sum(c["potential"] for c in row[1].values()))
    return {
        "practices": list(PRACTICES),
        "rows": [{"partner_id": p.id, "partner": p.name, "tier": p.tier, "cells": cells} for p, cells in rows],
        "totals": totals,
        "benchmark": ATTACH_BENCHMARK,
    }


# ---------- signals ----------


def list_signals(session: Session, today: date, status: str | None, practice: str | None) -> list[dict]:
    query = select(Signal).options(selectinload(Signal.partner))
    if status:
        query = query.where(Signal.status == status)
    if practice:
        query = query.where(Signal.practice == practice)
    results = [serialize_signal(s, today) for s in session.scalars(query)]
    return sorted(results, key=lambda s: -s["score"])


def set_signal_status(session: Session, signal_id: int, status: str) -> Signal:
    signal = session.get(Signal, signal_id)
    if signal is None:
        raise NotFound(f"Signal {signal_id} not found.")
    signal.status = status
    session.commit()
    return signal


def convert_signal(session: Session, signal_id: int, today: date, end_customer: str = "") -> Opportunity:
    signal = session.get(Signal, signal_id)
    if signal is None:
        raise NotFound(f"Signal {signal_id} not found.")
    service = SERVICES_BY_KEY[signal.service_key]
    opp = Opportunity(
        partner_id=signal.partner_id,
        signal_id=signal.id,
        title=f"{service.name} - {signal.partner.name}",
        end_customer=end_customer or "To be confirmed",
        industry="",
        practice=signal.practice,
        service_key=signal.service_key,
        stage="Prospect",
        value=service.typical_value,
        next_step=f"Introduce the {service.name.lower()} to {signal.partner.contact_name.split()[0]}",
        next_step_due=today,
        created_on=today,
        stage_changed_on=today,
    )
    signal.status = "actioned"
    session.add(opp)
    session.flush()
    session.add(
        Activity(
            partner_id=signal.partner_id,
            opportunity_id=opp.id,
            kind="note",
            outcome="",
            occurred_at=datetime.now(),
            summary=f"Opportunity opened from signal: {signal.title}",
        )
    )
    session.commit()
    return opp


# ---------- opportunities ----------


def list_opportunities(
    session: Session, today: date, stage: str | None = None, practice: str | None = None
) -> list[dict]:
    touches = last_touches(session)
    rows = [
        opportunity_summary(o, today, touches)
        for o in load_opportunities(session)
        if (stage is None or o.stage == stage) and (practice is None or o.practice == practice)
    ]
    return sorted(rows, key=lambda r: (STAGE_NAMES.index(r["stage"]), -r["priority"]["score"]))


def specialist_candidates(session: Session, practice: str) -> list[dict]:
    loads = Counter(
        session.scalars(
            select(Opportunity.specialist_id).where(
                Opportunity.stage.in_(OPEN_STAGES), Opportunity.specialist_id.is_not(None)
            )
        )
    )
    specialists = session.scalars(select(Specialist).where(Specialist.practice == practice)).all()
    rows = [
        {
            "id": s.id,
            "name": s.name,
            "title": s.title,
            "practice": s.practice,
            "load": loads[s.id],
            "capacity": s.capacity,
            "utilization": round(loads[s.id] / s.capacity, 2),
        }
        for s in specialists
    ]
    rows.sort(key=lambda r: float(r["utilization"]))  # type: ignore[arg-type]
    if rows:
        rows[0]["recommended"] = True
    return rows


def handoff_brief(opp: Opportunity, today: date) -> dict:
    service = SERVICES_BY_KEY[opp.service_key]
    _, known, missing = bant_score(opp)
    recent = sorted(opp.activities, key=lambda a: a.occurred_at, reverse=True)[:4]
    questions = [BANT_QUESTIONS[m] for m in missing] + PLAYBOOKS[opp.practice].questions[:2]
    signal = opp_signal(opp)
    sections = {
        "Context": f"{opp.partner.name} ({opp.partner.partner_type}, {opp.partner.city}) is working with "
        f"{opp.end_customer} ({opp.industry or 'industry TBC'}).",
        "Customer challenge": opp.challenge or "Not yet captured in the customer's words.",
        "Proposed starting point": f"{service.name}, {service.duration}. {service.summary}",
        "Qualification": ", ".join(known) if known else "Not yet qualified",
        "Open questions": questions[:5],
        "Trigger": signal.title if signal else "Inbound / relationship-sourced",
        "Recent touches": [f"{a.occurred_at:%b} {a.occurred_at.day}: {a.summary}" for a in recent],
        "Ask": f"Join a 30-minute scoping call with {opp.partner.contact_name} and confirm the scope "
        f"before a proposal. Target value ${opp.value:,}.",
    }
    lines = [f"HANDOFF: {opp.title}", ""]
    for heading, body in sections.items():
        lines.append(heading.upper())
        if isinstance(body, list):
            lines.extend(f"- {item}" for item in body)
        else:
            lines.append(str(body))
        lines.append("")
    return {"sections": sections, "text": "\n".join(lines).strip(), "generated_on": today}


def opportunity_detail(session: Session, opp_id: int, today: date) -> dict:
    opp = get_opportunity(session, opp_id)
    touches = last_touches(session)
    drafts = session.scalars(
        select(Draft).where(Draft.opportunity_id == opp.id).order_by(Draft.created_at.desc())
    ).all()
    return {
        **opportunity_summary(opp, today, touches),
        "challenge": opp.challenge,
        "close_reason": opp.close_reason,
        "created_on": opp.created_on,
        "contact_name": opp.partner.contact_name,
        "contact_title": opp.partner.contact_title,
        "specialist_id": opp.specialist_id,
        "signal": serialize_signal(s, today) if (s := opp_signal(opp)) else None,
        "activities": [
            serialize_activity(a) for a in sorted(opp.activities, key=lambda a: a.occurred_at, reverse=True)
        ],
        "drafts": [serialize_draft(d) for d in drafts],
        "specialists": specialist_candidates(session, opp.practice),
        "handoff": handoff_brief(opp, today),
        "playbook": {"questions": PLAYBOOKS[opp.practice].questions, "triggers": PLAYBOOKS[opp.practice].triggers},
    }


EDITABLE = {
    "title",
    "end_customer",
    "industry",
    "value",
    "budget",
    "authority",
    "need",
    "timeline",
    "challenge",
    "next_step",
    "next_step_due",
    "service_key",
}


def update_opportunity(session: Session, opp_id: int, changes: dict) -> Opportunity:
    opp = get_opportunity(session, opp_id)
    for key, value in changes.items():
        if key in EDITABLE and value is not None:
            setattr(opp, key, value)
    if "service_key" in changes and changes["service_key"]:
        opp.practice = SERVICES_BY_KEY[changes["service_key"]].practice
    session.commit()
    return opp


def change_stage(session: Session, opp_id: int, stage: str, today: date, reason: str = "") -> Opportunity:
    opp = get_opportunity(session, opp_id)
    check_stage_gate(opp, stage)
    previous = opp.stage
    if previous == stage:
        return opp
    opp.stage, opp.stage_changed_on = stage, today
    if stage in ("Won", "Lost"):
        opp.closed_on, opp.close_reason, opp.next_step, opp.next_step_due = today, reason, "", None
    else:
        opp.next_step_due = today + timedelta(days=STAGE_CADENCE[stage])
    session.add(
        Activity(
            partner_id=opp.partner_id,
            opportunity_id=opp.id,
            kind="stage",
            outcome=stage.lower(),
            occurred_at=datetime.now(),
            summary=f"Stage moved {previous} → {stage}" + (f": {reason}" if reason else ""),
        )
    )
    session.commit()
    return opp


def assign_specialist(session: Session, opp_id: int, specialist_id: str) -> Opportunity:
    opp = get_opportunity(session, opp_id)
    specialist = session.get(Specialist, specialist_id)
    if specialist is None:
        raise NotFound(f"Specialist '{specialist_id}' not found.")
    opp.specialist_id = specialist.id
    session.add(
        Activity(
            partner_id=opp.partner_id,
            opportunity_id=opp.id,
            kind="handoff",
            outcome="sent",
            occurred_at=datetime.now(),
            summary=f"Handoff brief sent to {specialist.name} ({specialist.title}).",
        )
    )
    session.commit()
    return opp


def log_activity(
    session: Session,
    today: date,
    partner_id: str,
    kind: str,
    summary: str,
    outcome: str = "",
    opportunity_id: int | None = None,
    next_step: str | None = None,
    next_step_due: date | None = None,
) -> Activity:
    get_partner(session, partner_id)
    activity = Activity(
        partner_id=partner_id,
        opportunity_id=opportunity_id,
        kind=kind,
        summary=summary,
        outcome=outcome,
        occurred_at=datetime.now(),
    )
    session.add(activity)
    if opportunity_id is not None:
        opp = get_opportunity(session, opportunity_id)
        if next_step:
            opp.next_step = next_step
        # Follow-up discipline: every logged touch sets the next due date from the stage cadence
        # unless the person chose one explicitly.
        if opp.stage in OPEN_STAGES:
            opp.next_step_due = next_step_due or today + timedelta(days=STAGE_CADENCE[opp.stage])
    session.commit()
    return activity


def create_opportunity(session: Session, today: date, data: dict, notes: str = "") -> Opportunity:
    get_partner(session, data["partner_id"])
    service = SERVICES_BY_KEY[data["service_key"]]
    opp = Opportunity(
        partner_id=data["partner_id"],
        title=data.get("title") or service.name,
        end_customer=data.get("end_customer") or "To be confirmed",
        industry=data.get("industry") or "",
        practice=service.practice,
        service_key=service.key,
        stage="Discovery",
        value=data.get("value") or service.typical_value,
        budget=data.get("budget", "unknown"),
        authority=data.get("authority", "unknown"),
        need=data.get("need", "unknown"),
        timeline=data.get("timeline", "unknown"),
        challenge=data.get("challenge", ""),
        next_step=data.get("next_step", ""),
        next_step_due=today + timedelta(days=STAGE_CADENCE["Discovery"]),
        created_on=today,
        stage_changed_on=today,
    )
    session.add(opp)
    session.flush()
    session.add(
        Activity(
            partner_id=opp.partner_id,
            opportunity_id=opp.id,
            kind="call",
            outcome="connected",
            occurred_at=datetime.now(),
            summary="Discovery call captured" + (f": {notes[:220]}" if notes else "."),
        )
    )
    session.commit()
    return opp


# ---------- drafts ----------


def serialize_draft(draft: Draft) -> dict:
    return {
        "id": draft.id,
        "partner_id": draft.partner_id,
        "opportunity_id": draft.opportunity_id,
        "signal_id": draft.signal_id,
        "goal": draft.goal,
        "subject": draft.subject,
        "body": draft.body,
        "edited": draft.body.strip() != draft.original_body.strip(),
        "personalization": draft.personalization,
        "engine": draft.engine,
        "status": draft.status,
        "created_at": draft.created_at,
    }


def approve_draft(session: Session, draft_id: int, today: date, subject: str, body: str) -> Draft:
    draft = session.get(Draft, draft_id)
    if draft is None:
        raise NotFound(f"Draft {draft_id} not found.")
    draft.subject, draft.body, draft.status = subject, body, "approved"
    edited = " (edited before sending)" if body.strip() != draft.original_body.strip() else ""
    log_activity(
        session,
        today,
        draft.partner_id,
        "email",
        f"Sent: “{subject}”{edited}",
        "sent",
        opportunity_id=draft.opportunity_id,
    )
    if draft.signal_id:
        signal = session.get(Signal, draft.signal_id)
        if signal and signal.status == "new":
            signal.status = "actioned"
    session.commit()
    return draft


# ---------- reports ----------


def reports(session: Session, today: date) -> dict:
    opportunities = load_opportunities(session)
    open_opps = [o for o in opportunities if o.stage in OPEN_STAGES]
    closed = [o for o in opportunities if o.closed_on and (today - o.closed_on).days <= 180]
    won = [o for o in closed if o.stage == "Won"]
    funnel = [
        {
            "stage": s,
            "count": sum(o.stage == s for o in opportunities),
            "value": sum(o.value for o in opportunities if o.stage == s),
        }
        for s in STAGE_NAMES[:6]
    ]
    by_practice = []
    for key, label in PRACTICES.items():
        items = [o for o in open_opps if o.practice == key]
        by_practice.append(
            {
                "practice": key,
                "label": label,
                "open_value": sum(o.value for o in items),
                "weighted_value": round(sum(weighted(o) for o in items)),
                "won_value": sum(o.value for o in won if o.practice == key),
                "count": len(items),
            }
        )

    weeks: dict[str, Counter] = defaultdict(Counter)
    start = today - timedelta(days=today.weekday() + 7 * 7)
    for activity in session.scalars(
        select(Activity).where(Activity.occurred_at >= datetime.combine(start, datetime.min.time()))
    ):
        day = activity.occurred_at.date()
        week = day - timedelta(days=day.weekday())
        if activity.kind in ("call", "email", "meeting"):
            weeks[week.isoformat()][activity.kind] += 1
    activity_weeks = [
        {
            "week": (start + timedelta(weeks=i)).isoformat(),
            **{k: weeks[(start + timedelta(weeks=i)).isoformat()][k] for k in ("call", "email", "meeting")},
        }
        for i in range(8)
    ]

    signals = session.scalars(select(Signal)).all()
    sources = Counter(s.source for s in signals)
    actioned = Counter(s.source for s in signals if s.status == "actioned")
    cycle = [(o.closed_on - o.created_on).days for o in won if o.closed_on]
    return {
        "funnel": funnel,
        "by_practice": by_practice,
        "activity_weeks": activity_weeks,
        "signal_sources": [{"source": k, "total": v, "actioned": actioned[k]} for k, v in sources.most_common()],
        "win_rate": round(len(won) / len(closed), 2) if closed else None,
        "won_value": sum(o.value for o in won),
        "closed_count": len(closed),
        "won_count": len(won),
        "avg_cycle_days": round(sum(cycle) / len(cycle)) if cycle else None,
        "open_pipeline": sum(o.value for o in open_opps),
        "weighted_pipeline": round(sum(weighted(o) for o in open_opps)),
        "stalled": sum("stalled" in priority(o, today, None).flags for o in open_opps),
    }
