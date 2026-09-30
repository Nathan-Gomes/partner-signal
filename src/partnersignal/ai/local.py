"""Deterministic 'local engine': keyword and pattern rules that fill the same schemas as Claude.

It exists so the public demo works without an API key, so tests are reproducible, and as a
baseline to compare the model against. It is intentionally simple and says so in its output.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..catalog import BANT_QUESTIONS, PLAYBOOKS, PRACTICES, SERVICES_BY_KEY, inline
from .schemas import (
    AuthorityItem,
    Bant,
    BudgetItem,
    DiscoveryExtraction,
    Evidence,
    NeedItem,
    OutreachDraft,
    PersonalizationNote,
    PracticeFit,
    TimelineItem,
)

SERVICE_HINTS: list[tuple[str, str]] = [
    (r"ransomware|restore|backup|tabletop|incident response", "sec-ransomware"),
    (r"\bsoc\b|managed detection|mdr|24x7|monitoring", "sec-mdr"),
    (r"vmware|broadcom|per-core|hypervisor|virtuali[sz]ation", "cloud-vmware"),
    (r"migrat|move (the |our |their )?servers|lift", "cloud-migration"),
    (r"copilot|pilot group|adoption", "ai-copilot"),
    (r"label|classif|governance|sensitive data|data leak|privacy", "ai-governance"),
    (r"sd-wan|branch|wan\b", "net-sdwan"),
    (r"segment|zero.trust|remote access|\bot\b", "net-segmentation"),
    (r"imag|deploy|rollout|asset tag", "life-deploy"),
    (r"dispos|itad|data destruction|recycl", "life-itad"),
    (r"end of support|end-of-support|server 2016|\beol\b", "life-eos"),
    (r"certif|bootcamp|engineers? need", "train-cert"),
    (r"sales team|reps|account managers|discovery skills", "train-sales"),
]
DEFAULT_SERVICE = {
    "security": "sec-posture",
    "cloud": "cloud-readiness",
    "network": "net-assessment",
    "ai": "ai-readiness",
    "lifecycle": "life-deploy",
    "training": "train-sales",
}

BANT_RULES: dict[str, list[tuple[str, str]]] = {
    "budget": [
        (
            "confirmed",
            r"budget (is |was |has been )?(approved|confirmed|allocated|set aside|signed off)|"
            r"approved (budget|funding|spend)|funding (is )?approved|po (is )?ready",
        ),
        ("indicated", r"budget|\$\s?\d|\d+\s?k\b|funding|grant|spend|afford|cost|price|quote"),
    ],
    "authority": [
        (
            "decision_maker",
            r"\b(cio|cto|ceo|coo|cfo|owner|president|vp|vice president|director|board|"
            r"council|decision[- ]maker|signs? off|final say|managing partner)\b",
        ),
        (
            "influencer",
            r"\b(it manager|manager|administrator|admin|engineer|coordinator|lead|analyst|"
            r"champion|recommend)\b",
        ),
    ],
    "need": [
        (
            "high",
            r"urgent|breach|ransomware|attack|outage|compromis|audit|insurer|insurance|compliance|"
            r"premium|deadline|must|can't|cannot|fail|lost|mis-?pick|down\b",
        ),
        (
            "medium",
            r"problem|issue|struggl|slow|complain|pain|concern|risk|frustrat|drop|manual|"
            r"want|need|looking for|interested|nobody|never|no one",
        ),
    ],
    "timeline": [
        (
            "under_3_months",
            r"(this|next) (week|month)|within (\d+|a few|two|three|four|six) weeks|\b\d{1,2} days\b|"
            r"before (the )?(renewal|holidays|winter break|year[- ]end)|by (end of )?"
            r"(october|november|december|january|month[- ]end)|asap|right away",
        ),
        (
            "3_6_months",
            r"(this|next) quarter|\bq[1-4]\b|spring|summer|(in|within) (3|4|5|6|three|four|five|six)"
            r" months|by (february|march|april|may|june)",
        ),
        ("6_plus_months", r"next (fiscal )?year|12 months|later (this|next) year|no rush|eventually|someday"),
    ],
}
NEGATIONS = {
    "budget": r"\bno budget\b|\bno (?:budget |dollar )?(?:number|figure|amount)\b|not (?:yet )?budgeted|"
    r"budget (?:is|isn't|is not) (?:not )?(?:set|approved|confirmed)|without (?:a )?budget",
}
RISK_RULES: list[tuple[str, str]] = [
    (
        r"incumbent|another (vendor|provider|partner)|competitor|other quote|shopping around",
        "Competing provider mentioned: confirm what would make this partner choose our services.",
    ),
    (r"not sure|unclear|maybe|might|thinking about", "Customer language is tentative; the need may not be committed."),
    (
        r"freeze|cut|delay|postpone|re-?forecast",
        "Budget or timing pressure mentioned; confirm the project is still funded.",
    ),
]
CUSTOMER_PATTERN = re.compile(
    r"(?:customer|client|end customer|account)(?:,| is| called| named|:)?\s+"
    r"((?:[A-Z][\w&'.-]*\s?){1,5})"
)


def sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [part.strip(" -*•") for part in parts if len(part.strip()) > 3]


def _first_match(pattern: str, lines: list[str]) -> str:
    regex = re.compile(pattern, re.IGNORECASE)
    return next((line for line in lines if regex.search(line)), "")


def _practice_scores(lines: list[str]) -> dict[str, tuple[int, str]]:
    scores: dict[str, tuple[int, str]] = {}
    for key, playbook in PLAYBOOKS.items():
        best_line, total, best = "", 0, 0
        for line in lines:
            lowered = line.lower()
            line_score = sum(
                weight for word, weight in playbook.keywords.items() if re.search(_keyword_pattern(word), lowered)
            )
            total += line_score
            if line_score > best:
                best, best_line = line_score, line
        if total:
            scores[key] = (total, best_line)
    return scores


def _keyword_pattern(word: str) -> str:
    # Short keywords (ai, wan, site) must match whole words, allowing a plural; longer ones are stems.
    tail = r"s?\b" if len(word) <= 4 else ""
    return rf"\b{re.escape(word)}{tail}"


def _service_for(practice: str, text: str) -> str:
    lowered = text.lower()
    for service in SERVICES_BY_KEY.values():  # a service the partner asked for by name wins
        if service.practice == practice and service.name.lower() in lowered:
            return service.key
    for pattern, key in SERVICE_HINTS:
        if SERVICES_BY_KEY[key].practice == practice and re.search(pattern, text, re.IGNORECASE):
            return key
    return DEFAULT_SERVICE[practice]


def extract_discovery(notes: str, partner_name: str = "The partner") -> DiscoveryExtraction:
    lines = sentences(notes)
    scored = sorted(_practice_scores(lines).items(), key=lambda item: -item[1][0])
    practices = [
        PracticeFit(
            practice=key,  # type: ignore[arg-type]
            service_key=_service_for(key, notes),  # type: ignore[arg-type]
            confidence="high" if score >= 10 else "medium" if score >= 5 else "low",
            quote=line,
        )
        for key, (score, line) in scored[:3]
        if score >= 3
    ]

    found: dict[str, tuple[str, str]] = {}
    for field, rules in BANT_RULES.items():
        negated = _first_match(NEGATIONS[field], lines) if field in NEGATIONS else ""
        if negated:  # "no budget yet" is evidence that budget is unknown, not that it exists
            found[field] = ("unknown", negated)
            continue
        for level, pattern in rules:
            quote = _first_match(pattern, lines)
            if quote:
                found[field] = (level, quote)
                break
        found.setdefault(field, ("unknown", ""))
    bant = Bant(
        budget=BudgetItem(level=found["budget"][0], quote=found["budget"][1]),  # type: ignore[arg-type]
        authority=AuthorityItem(level=found["authority"][0], quote=found["authority"][1]),  # type: ignore[arg-type]
        need=NeedItem(level=found["need"][0], quote=found["need"][1]),  # type: ignore[arg-type]
        timeline=TimelineItem(level=found["timeline"][0], quote=found["timeline"][1]),  # type: ignore[arg-type]
    )
    missing = [field for field, (level, _) in found.items() if level == "unknown"]

    need_pattern = BANT_RULES["need"][0][1] + "|" + BANT_RULES["need"][1][1]
    challenge_lines = [line for line in lines if re.search(need_pattern, line, re.IGNORECASE)][:3]
    challenges = [Evidence(point=_as_point(line), quote=line) for line in challenge_lines]

    match = CUSTOMER_PATTERN.search(notes)
    customer = match.group(1).strip() if match else ""
    top = practices[0] if practices else None
    questions = [BANT_QUESTIONS[field] for field in missing]
    if top:
        questions += [q for q in PLAYBOOKS[top.practice].questions if q not in questions]
    risks = [message for pattern, message in RISK_RULES if re.search(pattern, notes, re.IGNORECASE)]
    if "authority" in missing:
        risks.append("No decision maker identified yet.")

    known = 4 - len(missing)
    if top is None:
        next_step = "Book a second discovery call; the notes do not point to a clear service yet."
    elif found["need"][0] != "unknown" and known >= 3:
        next_step = (
            f"Route to the {PRACTICES[top.practice]} specialist and book a scoping call for the "
            f"{inline(SERVICES_BY_KEY[top.service_key].name)}."
        )
    else:
        next_step = "Book a 20-minute follow-up to confirm " + ", ".join(missing) + "."

    headline = challenges[0].point if challenges else f"{partner_name} shared early context without a specific problem."
    fit = f" Strongest fit: {PRACTICES[top.practice]} ({inline(SERVICES_BY_KEY[top.service_key].name)})." if top else ""
    summary = f"{headline}{fit} {known} of 4 BANT elements are evidenced in the notes."

    return DiscoveryExtraction(
        summary=summary,
        end_customer=customer,
        industry="",
        challenges=challenges,
        practices=practices,
        bant=bant,
        missing_information=[_missing_text(field, found[field][1]) for field in missing],
        follow_up_questions=questions[:5],
        risks=risks,
        next_step=next_step,
    )


def _missing_text(field: str, quote: str) -> str:
    return f"{field.title()} came up but is not known yet" if quote else f"{field.title()} not discussed"


def _as_point(line: str) -> str:
    line = re.sub(
        r"^(they|she|he|we|customer|client)\s+(said|mentioned|noted)\s+(that\s+)?", "", line, flags=re.IGNORECASE
    )
    return (line[:1].upper() + line[1:]).rstrip(".") + "."


def possessive(name: str) -> str:
    return f"{name}'" if name.endswith("s") else f"{name}'s"


@dataclass
class OutreachContext:
    goal: str  # intro | follow_up | meeting | reengage
    partner_name: str
    contact_first: str
    practice: str
    service_key: str
    signal_title: str = ""
    signal_detail: str = ""
    end_customer: str = ""
    challenge: str = ""
    specialist: str = ""
    sender: str = "Nathan"
    tone: str = "warm"  # warm | concise


def draft_outreach(ctx: OutreachContext) -> OutreachDraft:
    service = SERVICES_BY_KEY[ctx.service_key]
    practice = PRACTICES[ctx.practice]
    who = ctx.end_customer or "your customer"
    first_word, _, rest = service.summary.partition(" ")
    summary_mid = f"{inline(first_word)} {rest}"  # the summary, continuing a sentence
    notes: list[PersonalizationNote] = []
    if ctx.goal == "intro":
        subject = f"Idea for {ctx.partner_name}: {inline(service.name)}"
        opening = (
            f"I was looking at your recent activity and one item stood out: \u201c{ctx.signal_title}.\u201d"
            if ctx.signal_title
            else f"I've been looking at where {ctx.partner_name} is growing in {inline(practice)}."
        )
        if ctx.signal_title:
            notes.append(PersonalizationNote(element="Opening line", reason=f"Prospect signal: {ctx.signal_title}"))
        middle = (
            f"Partners in a similar spot often start with the {inline(service.name)} "
            f"({service.duration}): {summary_mid} "
            "It gives you something concrete to bring to the customer without committing to a large project."
        )
        ask = "Would a 15-minute call this week be useful to see whether it fits any of your accounts?"
    elif ctx.goal == "follow_up":
        subject = f"Following up: {service.name} for {who}"
        opening = f"Thanks again for walking me through {possessive(who)} situation."
        if ctx.challenge:
            opening += f" What stood out was: “{ctx.challenge.rstrip('.')}.”"
            notes.append(PersonalizationNote(element="Recap", reason="Customer challenge recorded on the opportunity"))
        middle = f"Based on that, the {inline(service.name)} looks like the right first step. It covers {summary_mid}"
        ask = "Could you confirm the budget range and who else should be part of the next conversation?"
    elif ctx.goal == "meeting":
        subject = f"Bringing in a specialist for {who}"
        opening = (
            f"I'd like to bring {ctx.specialist or 'one of our specialists'} into the next conversation about {who}."
        )
        if ctx.specialist:
            notes.append(PersonalizationNote(element="Specialist introduction", reason=f"Routed to {ctx.specialist}"))
        middle = (
            f"They have delivered the {inline(service.name)} for similar customers and can answer the "
            "technical questions directly, so you are not relaying details back and forth."
        )
        ask = "Do Tuesday or Thursday afternoon work for a 30-minute scoping call?"
    else:  # reengage
        subject = f"Still a priority for {who}?"
        opening = f"It's been a little while since we spoke about the {inline(service.name)} for {who}."
        middle = (
            "If priorities have shifted, that's completely fine. If it's still on the list, I can send a "
            "short summary of what the first two weeks would look like so it's easy to take to the customer."
        )
        ask = "Is this still worth pursuing this quarter, or should I check back later?"
    notes.append(PersonalizationNote(element="Greeting", reason=f"Primary contact on the {ctx.partner_name} record"))
    notes.append(
        PersonalizationNote(element="Service suggestion", reason=f"{practice} practice, catalog item '{service.name}'")
    )

    paragraphs = [f"Hi {ctx.contact_first},", opening, middle, ask, f"Thanks,\n{ctx.sender}"]
    if ctx.tone == "concise":
        paragraphs = [f"Hi {ctx.contact_first},", f"{opening} {ask}", f"Thanks,\n{ctx.sender}"]
    return OutreachDraft(
        subject=subject,
        body="\n\n".join(paragraphs),
        personalization=notes,
        review_checklist=[
            "Confirm every customer detail is accurate and shareable with the partner.",
            "Do not promise pricing, dates or specialist availability that has not been confirmed.",
            "Adjust the tone to your relationship with this contact.",
        ],
    )
