"""HTTP routes. Business rules live in services/; this module validates input and maps errors."""

from __future__ import annotations

import csv
import io
import os
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import clock
from ..ai.local import OutreachContext
from ..ai.service import Assistant
from ..catalog import BANT_LEVELS, PLAYBOOKS, PRACTICES, SERVICES, SERVICES_BY_KEY, STAGES
from ..config import get_settings
from ..db import SessionLocal, get_session
from ..models import Draft, Signal, Specialist
from ..seed import seed
from ..services import workflow as wf
from ..services.scoring import GateError

router = APIRouter(prefix="/api")
Budget = Literal["unknown", "indicated", "confirmed"]
Authority = Literal["unknown", "influencer", "decision_maker"]
Need = Literal["unknown", "low", "medium", "high"]
Timeline = Literal["unknown", "6_plus_months", "3_6_months", "under_3_months"]
Engine = Literal["auto", "claude", "local"]


def today(request: Request) -> date:
    """The demo's current date. Reseeds the fictional data once the local date has moved on."""
    current = clock.today()
    state = request.app.state
    if get_settings().reseed_daily and getattr(state, "seeded_on", current) != current:
        with state.seed_lock:
            if state.seeded_on != current:
                with SessionLocal() as session:
                    seed(session, current)
                state.seeded_on = current
    return current


def assistant(request: Request) -> Assistant:
    return request.app.state.assistant


def visitor(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    return forwarded.split(",")[0].strip() or (request.client.host if request.client else "anonymous")


def not_found(error: wf.NotFound) -> HTTPException:
    return HTTPException(status_code=404, detail=str(error))


# ---------- reference data ----------


@router.get("/health")
def health(request: Request) -> dict:
    return {
        "status": "ok",
        "service": "partnersignal",
        "commit": os.environ.get("RENDER_GIT_COMMIT", get_settings().commit)[:7],
        "data": "fictional",
        "ai": assistant(request).status,
    }


@router.get("/meta")
def meta(session: Session = Depends(get_session)) -> dict:
    specialists = session.query(Specialist).all()
    return {
        "practices": PRACTICES,
        "services": [s.__dict__ for s in SERVICES],
        "stages": [{"name": n, "probability": p, "cadence_days": c} for n, p, c in STAGES],
        "bant_levels": BANT_LEVELS,
        "specialists": [{"id": s.id, "name": s.name, "title": s.title, "practice": s.practice} for s in specialists],
        "playbooks": {
            k: {"triggers": p.triggers, "questions": p.questions, "ai_use_cases": p.ai_use_cases}
            for k, p in PLAYBOOKS.items()
        },
    }


# ---------- today, partners, signals ----------


@router.get("/today")
def today_view(session: Session = Depends(get_session), day: date = Depends(today)) -> dict:
    return wf.today_view(session, day)


@router.get("/partners")
def partners(session: Session = Depends(get_session), day: date = Depends(today)) -> list[dict]:
    return wf.list_partners(session, day)


@router.get("/partners/{partner_id}")
def partner(partner_id: str, session: Session = Depends(get_session), day: date = Depends(today)) -> dict:
    try:
        return wf.partner_detail(session, partner_id, day)
    except wf.NotFound as error:
        raise not_found(error) from error


@router.get("/whitespace")
def whitespace(session: Session = Depends(get_session)) -> dict:
    return wf.whitespace_matrix(session)


@router.get("/signals")
def signals(
    status: str | None = None,
    practice: str | None = None,
    session: Session = Depends(get_session),
    day: date = Depends(today),
) -> list[dict]:
    return wf.list_signals(session, day, status, practice)


class ConvertSignal(BaseModel):
    end_customer: str = Field("", max_length=120)


@router.post("/signals/{signal_id}/convert")
def convert_signal(
    signal_id: int, body: ConvertSignal, session: Session = Depends(get_session), day: date = Depends(today)
) -> dict:
    try:
        opp = wf.convert_signal(session, signal_id, day, body.end_customer)
    except wf.NotFound as error:
        raise not_found(error) from error
    return {"opportunity_id": opp.id}


@router.post("/signals/{signal_id}/dismiss")
def dismiss_signal(signal_id: int, session: Session = Depends(get_session)) -> dict:
    try:
        signal = wf.set_signal_status(session, signal_id, "dismissed")
    except wf.NotFound as error:
        raise not_found(error) from error
    return {"id": signal.id, "status": signal.status}


# ---------- opportunities ----------


@router.get("/opportunities")
def opportunities(
    stage: str | None = None,
    practice: str | None = None,
    session: Session = Depends(get_session),
    day: date = Depends(today),
) -> list[dict]:
    return wf.list_opportunities(session, day, stage, practice)


@router.get("/opportunities/{opp_id}")
def opportunity(opp_id: int, session: Session = Depends(get_session), day: date = Depends(today)) -> dict:
    try:
        return wf.opportunity_detail(session, opp_id, day)
    except wf.NotFound as error:
        raise not_found(error) from error


class NewOpportunity(BaseModel):
    partner_id: str
    service_key: str
    title: str = Field("", max_length=160)
    end_customer: str = Field("", max_length=120)
    industry: str = Field("", max_length=60)
    value: int | None = Field(None, ge=0, le=5_000_000)
    budget: Budget = "unknown"
    authority: Authority = "unknown"
    need: Need = "unknown"
    timeline: Timeline = "unknown"
    challenge: str = Field("", max_length=1000)
    next_step: str = Field("", max_length=200)
    notes: str = Field("", max_length=6000)


@router.post("/opportunities", status_code=201)
def create_opportunity(
    body: NewOpportunity, session: Session = Depends(get_session), day: date = Depends(today)
) -> dict:
    if body.service_key not in SERVICES_BY_KEY:
        raise HTTPException(422, "Unknown service.")
    try:
        opp = wf.create_opportunity(session, day, body.model_dump(exclude={"notes"}), body.notes)
    except wf.NotFound as error:
        raise not_found(error) from error
    return {"opportunity_id": opp.id}


class OpportunityPatch(BaseModel):
    title: str | None = Field(None, max_length=160)
    end_customer: str | None = Field(None, max_length=120)
    industry: str | None = Field(None, max_length=60)
    value: int | None = Field(None, ge=0, le=5_000_000)
    budget: Budget | None = None
    authority: Authority | None = None
    need: Need | None = None
    timeline: Timeline | None = None
    challenge: str | None = Field(None, max_length=1000)
    next_step: str | None = Field(None, max_length=200)
    next_step_due: date | None = None
    service_key: str | None = None


@router.patch("/opportunities/{opp_id}")
def patch_opportunity(
    opp_id: int, body: OpportunityPatch, session: Session = Depends(get_session), day: date = Depends(today)
) -> dict:
    if body.service_key and body.service_key not in SERVICES_BY_KEY:
        raise HTTPException(422, "Unknown service.")
    try:
        wf.update_opportunity(session, opp_id, body.model_dump(exclude_unset=True))
        return wf.opportunity_detail(session, opp_id, day)
    except wf.NotFound as error:
        raise not_found(error) from error


class StageChange(BaseModel):
    stage: str
    reason: str = Field("", max_length=160)


@router.post("/opportunities/{opp_id}/stage")
def change_stage(
    opp_id: int, body: StageChange, session: Session = Depends(get_session), day: date = Depends(today)
) -> dict:
    try:
        wf.change_stage(session, opp_id, body.stage, day, body.reason)
    except wf.NotFound as error:
        raise not_found(error) from error
    except GateError as error:
        raise HTTPException(409, {"message": str(error), "to_do": error.missing}) from error
    return wf.opportunity_detail(session, opp_id, day)


class Assign(BaseModel):
    specialist_id: str


@router.post("/opportunities/{opp_id}/assign")
def assign(opp_id: int, body: Assign, session: Session = Depends(get_session), day: date = Depends(today)) -> dict:
    try:
        wf.assign_specialist(session, opp_id, body.specialist_id)
    except wf.NotFound as error:
        raise not_found(error) from error
    return wf.opportunity_detail(session, opp_id, day)


class NewActivity(BaseModel):
    partner_id: str
    opportunity_id: int | None = None
    kind: Literal["call", "email", "meeting", "note"]
    summary: str = Field(min_length=3, max_length=1000)
    outcome: str = Field("", max_length=30)
    next_step: str | None = Field(None, max_length=200)
    next_step_due: date | None = None


@router.post("/activities", status_code=201)
def create_activity(body: NewActivity, session: Session = Depends(get_session), day: date = Depends(today)) -> dict:
    try:
        activity = wf.log_activity(session, day, **body.model_dump())
    except wf.NotFound as error:
        raise not_found(error) from error
    return {"id": activity.id}


# ---------- AI assistance ----------


class DiscoveryRequest(BaseModel):
    partner_id: str
    notes: str = Field(min_length=20)
    engine: Engine = "auto"


@router.post("/ai/discovery")
def discovery(body: DiscoveryRequest, request: Request, session: Session = Depends(get_session)) -> dict:
    settings = get_settings()
    if len(body.notes) > settings.max_note_chars:
        raise HTTPException(422, f"Notes are limited to {settings.max_note_chars} characters in the demo.")
    try:
        partner = wf.get_partner(session, body.partner_id)
    except wf.NotFound as error:
        raise not_found(error) from error
    context = (
        f"{partner.name}: {partner.partner_type}, {partner.tier} tier, {partner.city} {partner.province}. "
        f"Contact {partner.contact_name}, {partner.contact_title}. Verticals: {', '.join(partner.verticals)}."
    )
    extraction, meta = assistant(request).discovery(body.notes, partner.name, context, body.engine, visitor(request))
    return {"result": extraction.model_dump(), "meta": meta.model_dump()}


class OutreachRequest(BaseModel):
    partner_id: str
    opportunity_id: int | None = None
    signal_id: int | None = None
    goal: Literal["intro", "follow_up", "meeting", "reengage"] = "intro"
    tone: Literal["warm", "concise"] = "warm"
    engine: Engine = "auto"


@router.post("/ai/outreach", status_code=201)
def outreach(body: OutreachRequest, request: Request, session: Session = Depends(get_session)) -> dict:
    try:
        partner = wf.get_partner(session, body.partner_id)
        opp = wf.get_opportunity(session, body.opportunity_id) if body.opportunity_id else None
    except wf.NotFound as error:
        raise not_found(error) from error
    signal = session.get(Signal, body.signal_id) if body.signal_id else (wf.opp_signal(opp) if opp else None)
    service_key = opp.service_key if opp else signal.service_key if signal else "ai-readiness"
    ctx = OutreachContext(
        goal=body.goal,
        partner_name=partner.name,
        contact_first=partner.contact_name.split()[0],
        practice=SERVICES_BY_KEY[service_key].practice,
        service_key=service_key,
        signal_title=signal.title if signal else "",
        signal_detail=signal.detail if signal else "",
        end_customer=opp.end_customer if opp and opp.end_customer != "To be confirmed" else "",
        challenge=opp.challenge if opp else "",
        specialist=opp.specialist.name if opp and opp.specialist else "",
        tone=body.tone,
    )
    result, meta = assistant(request).outreach(ctx, body.engine, visitor(request))
    draft = Draft(
        partner_id=partner.id,
        opportunity_id=opp.id if opp else None,
        signal_id=signal.id if signal else None,
        goal=body.goal,
        subject=result.subject,
        body=result.body,
        original_body=result.body,
        personalization=[n.model_dump() for n in result.personalization],
        engine=meta.engine,
        created_at=clock.now(),
    )
    session.add(draft)
    session.commit()
    return {"draft": wf.serialize_draft(draft), "review_checklist": result.review_checklist, "meta": meta.model_dump()}


class DraftApproval(BaseModel):
    subject: str = Field(min_length=3, max_length=200)
    body: str = Field(min_length=10, max_length=4000)


@router.post("/drafts/{draft_id}/approve")
def approve(
    draft_id: int, body: DraftApproval, session: Session = Depends(get_session), day: date = Depends(today)
) -> dict:
    try:
        draft = wf.approve_draft(session, draft_id, day, body.subject, body.body)
    except wf.NotFound as error:
        raise not_found(error) from error
    return wf.serialize_draft(draft)


# ---------- reporting ----------


@router.get("/reports")
def reports(session: Session = Depends(get_session), day: date = Depends(today)) -> dict:
    return wf.reports(session, day)


@router.get("/export/opportunities.csv")
def export_csv(
    session: Session = Depends(get_session), day: date = Depends(today), include_closed: bool = Query(True)
) -> StreamingResponse:
    rows = wf.list_opportunities(session, day)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "Opportunity ID",
            "Opportunity Name",
            "Account Name",
            "End Customer",
            "Practice",
            "Service",
            "Stage",
            "Amount",
            "Probability",
            "Expected Revenue",
            "Next Step",
            "Next Step Due",
            "Budget",
            "Authority",
            "Need",
            "Timeline",
            "Priority Score",
            "Specialist",
        ]
    )
    for r in rows:
        if not include_closed and r["stage"] in ("Won", "Lost"):
            continue
        writer.writerow(
            [
                r["id"],
                r["title"],
                r["partner"],
                r["end_customer"],
                PRACTICES[r["practice"]],
                r["service"],
                r["stage"],
                r["value"],
                f"{r['weighted_value'] / r['value']:.2f}" if r["value"] else 0,
                r["weighted_value"],
                r["next_step"],
                r["next_step_due"] or "",
                *r["bant"].values(),
                r["priority"]["score"],
                r["specialist"] or "",
            ]
        )
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=partnersignal-pipeline-{day}.csv"},
    )
