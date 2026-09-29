"""Relational model: partners, prospect signals, opportunities, activities, specialists, drafts."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class Partner(Base):
    __tablename__ = "partners"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    partner_type: Mapped[str] = mapped_column(String(40))  # MSP, VAR, integrator...
    tier: Mapped[str] = mapped_column(String(20))
    city: Mapped[str] = mapped_column(String(60))
    province: Mapped[str] = mapped_column(String(4))
    verticals: Mapped[list[str]] = mapped_column(JSON, default=list)
    vendors: Mapped[list[str]] = mapped_column(JSON, default=list)
    contact_name: Mapped[str] = mapped_column(String(80))
    contact_title: Mapped[str] = mapped_column(String(80))
    contact_email: Mapped[str] = mapped_column(String(120))
    trailing_revenue: Mapped[int] = mapped_column(Integer)  # 12-month distribution revenue, CAD
    services_revenue: Mapped[int] = mapped_column(Integer)  # 12-month services revenue, CAD
    # Share of 12-month product revenue by practice, used for whitespace analysis.
    product_mix: Mapped[dict[str, float]] = mapped_column(JSON, default=dict)
    services_used: Mapped[list[str]] = mapped_column(JSON, default=list)  # practice keys
    about: Mapped[str] = mapped_column(Text, default="")

    signals: Mapped[list[Signal]] = relationship(back_populates="partner", cascade="all, delete-orphan")
    opportunities: Mapped[list[Opportunity]] = relationship(back_populates="partner", cascade="all, delete-orphan")
    activities: Mapped[list[Activity]] = relationship(back_populates="partner", cascade="all, delete-orphan")


class Specialist(Base):
    __tablename__ = "specialists"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    title: Mapped[str] = mapped_column(String(80))
    practice: Mapped[str] = mapped_column(String(20))
    capacity: Mapped[int] = mapped_column(Integer)  # open opportunities they can carry


class Signal(Base):
    """A prospecting trigger derived from distribution, renewal or vendor data."""

    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    partner_id: Mapped[str] = mapped_column(ForeignKey("partners.id"))
    kind: Mapped[str] = mapped_column(String(30))  # end_of_support, renewal, purchase, attach_gap...
    source: Mapped[str] = mapped_column(String(40))
    practice: Mapped[str] = mapped_column(String(20))
    service_key: Mapped[str] = mapped_column(String(30))
    title: Mapped[str] = mapped_column(String(160))
    detail: Mapped[str] = mapped_column(Text)
    strength: Mapped[int] = mapped_column(Integer)  # 1-5
    detected_on: Mapped[date] = mapped_column(Date)
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="new")  # new | actioned | dismissed

    partner: Mapped[Partner] = relationship(back_populates="signals")


class Opportunity(Base):
    __tablename__ = "opportunities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    partner_id: Mapped[str] = mapped_column(ForeignKey("partners.id"))
    signal_id: Mapped[int | None] = mapped_column(ForeignKey("signals.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(160))
    end_customer: Mapped[str] = mapped_column(String(120))
    industry: Mapped[str] = mapped_column(String(60))
    practice: Mapped[str] = mapped_column(String(20))
    service_key: Mapped[str] = mapped_column(String(30))
    stage: Mapped[str] = mapped_column(String(20))
    value: Mapped[int] = mapped_column(Integer)
    budget: Mapped[str] = mapped_column(String(20), default="unknown")
    authority: Mapped[str] = mapped_column(String(20), default="unknown")
    need: Mapped[str] = mapped_column(String(20), default="unknown")
    timeline: Mapped[str] = mapped_column(String(20), default="unknown")
    challenge: Mapped[str] = mapped_column(Text, default="")
    next_step: Mapped[str] = mapped_column(String(200), default="")
    next_step_due: Mapped[date | None] = mapped_column(Date, nullable=True)
    specialist_id: Mapped[str | None] = mapped_column(ForeignKey("specialists.id"), nullable=True)
    created_on: Mapped[date] = mapped_column(Date)
    stage_changed_on: Mapped[date] = mapped_column(Date)
    closed_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    close_reason: Mapped[str] = mapped_column(String(160), default="")

    partner: Mapped[Partner] = relationship(back_populates="opportunities")
    specialist: Mapped[Specialist | None] = relationship()
    activities: Mapped[list[Activity]] = relationship(back_populates="opportunity")


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    partner_id: Mapped[str] = mapped_column(ForeignKey("partners.id"))
    opportunity_id: Mapped[int | None] = mapped_column(ForeignKey("opportunities.id"), nullable=True)
    kind: Mapped[str] = mapped_column(String(20))  # call | email | meeting | note | handoff | stage
    summary: Mapped[str] = mapped_column(Text)
    outcome: Mapped[str] = mapped_column(String(30), default="")  # connected, voicemail, replied...
    occurred_at: Mapped[datetime] = mapped_column(DateTime)

    partner: Mapped[Partner] = relationship(back_populates="activities")
    opportunity: Mapped[Opportunity | None] = relationship(back_populates="activities")


class Draft(Base):
    """An outreach draft. Drafts are never sent by the system: a person approves and logs them."""

    __tablename__ = "drafts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    partner_id: Mapped[str] = mapped_column(ForeignKey("partners.id"))
    opportunity_id: Mapped[int | None] = mapped_column(ForeignKey("opportunities.id"), nullable=True)
    signal_id: Mapped[int | None] = mapped_column(ForeignKey("signals.id"), nullable=True)
    goal: Mapped[str] = mapped_column(String(30))
    subject: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    original_body: Mapped[str] = mapped_column(Text)
    personalization: Mapped[list[dict[str, str]]] = mapped_column(JSON, default=list)
    engine: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft | approved
    created_at: Mapped[datetime] = mapped_column(DateTime)
