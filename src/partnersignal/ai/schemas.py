"""Output contracts shared by the Claude engine and the local rules engine.

Both engines return exactly these shapes, so the UI and tests do not care which one ran.
Every judgement carries a verbatim quote from the notes so a person can check it.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

PracticeKey = Literal["security", "cloud", "network", "ai", "lifecycle", "training"]


class Evidence(BaseModel):
    point: str = Field(description="One-sentence customer challenge in plain language.")
    quote: str = Field(description="Verbatim excerpt from the notes that supports the point.")


class PracticeFit(BaseModel):
    practice: PracticeKey
    service_key: str = Field(description="Key of the best-matching catalog service.")
    confidence: Literal["low", "medium", "high"]
    quote: str = Field(description="Verbatim excerpt from the notes that supports this fit.")


class BudgetItem(BaseModel):
    level: Literal["unknown", "indicated", "confirmed"]
    quote: str = Field(description="Verbatim supporting excerpt, or an empty string if unknown.")


class AuthorityItem(BaseModel):
    level: Literal["unknown", "influencer", "decision_maker"]
    quote: str


class NeedItem(BaseModel):
    level: Literal["unknown", "low", "medium", "high"]
    quote: str


class TimelineItem(BaseModel):
    level: Literal["unknown", "6_plus_months", "3_6_months", "under_3_months"]
    quote: str


class Bant(BaseModel):
    budget: BudgetItem
    authority: AuthorityItem
    need: NeedItem
    timeline: TimelineItem


class DiscoveryExtraction(BaseModel):
    summary: str = Field(description="Two sentences a colleague could read in ten seconds.")
    end_customer: str = Field(description="End-customer organization name, or empty string if not named.")
    industry: str = Field(description="End-customer industry, or empty string if unclear.")
    challenges: list[Evidence]
    practices: list[PracticeFit] = Field(description="Relevant practices, strongest first. At most three.")
    bant: Bant
    missing_information: list[str]
    follow_up_questions: list[str] = Field(description="Three to five open questions for the next call.")
    risks: list[str]
    next_step: str


class PersonalizationNote(BaseModel):
    element: str = Field(description="Which part of the draft is personalized, e.g. 'Opening line'.")
    reason: str = Field(description="The record or signal that this line relies on.")


class OutreachDraft(BaseModel):
    subject: str
    body: str
    personalization: list[PersonalizationNote]
    review_checklist: list[str] = Field(description="What the sender must verify before sending.")


class AIResult(BaseModel):
    """Envelope returned by the API: the payload plus which engine produced it and why."""

    engine: Literal["claude", "local"]
    model: str
    note: str = ""
