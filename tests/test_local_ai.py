from partnersignal.ai.local import OutreachContext, draft_outreach, extract_discovery

NOTES = (
    "Call with Maya at Northstar. Their client Lakeview Family Clinics had a phishing scare last month and the "
    "insurer now wants proof of tested backups before the renewal in November. Nobody has done a restore test in "
    "two years. The clinic's operations director signs off on IT spend, and Maya thinks there's roughly $15k set "
    "aside in this year's budget."
)


def test_extraction_finds_practice_bant_and_verbatim_evidence():
    result = extract_discovery(NOTES, "Northstar IT Group")
    assert result.practices[0].practice == "security"
    assert result.practices[0].service_key == "sec-ransomware"
    assert result.end_customer == "Lakeview Family Clinics"
    assert result.bant.need.level == "high"
    assert result.bant.authority.level == "decision_maker"
    assert result.bant.budget.level == "indicated"
    for item in (result.bant.budget, result.bant.authority, result.bant.need, result.bant.timeline):
        assert item.quote == "" or item.quote in NOTES
    assert all(challenge.quote in NOTES for challenge in result.challenges)


def test_short_keywords_do_not_match_inside_words():
    result = extract_discovery("The owner wants a quote. She wanted to know about pricing for next year.", "P")
    assert "network" not in [p.practice for p in result.practices]


def test_missing_bant_becomes_follow_up_questions():
    result = extract_discovery("They mentioned their Wi-Fi keeps dropping in the warehouse.", "Prairie")
    assert result.practices[0].practice == "network"
    assert result.bant.budget.level == "unknown"
    assert "Budget not discussed" in result.missing_information
    assert any("budget" in q.lower() for q in result.follow_up_questions)
    assert "Book a 20-minute follow-up" in result.next_step


def test_outreach_draft_is_personalized_and_explains_itself():
    ctx = OutreachContext(
        goal="intro",
        partner_name="Prairie Digital",
        contact_first="Avery",
        practice="network",
        service_key="net-assessment",
        signal_title="Wireless access points ordered for two sites",
    )
    draft = draft_outreach(ctx)
    assert draft.body.startswith("Hi Avery,")
    assert "\u201cWireless access points ordered for two sites.\u201d" in draft.body
    assert any("Prospect signal" in note.reason for note in draft.personalization)
    assert "{" not in draft.body and draft.review_checklist


def test_concise_tone_is_shorter():
    base = dict(goal="follow_up", partner_name="P", contact_first="A", practice="cloud", service_key="cloud-readiness")
    assert len(draft_outreach(OutreachContext(**base, tone="concise")).body) < len(
        draft_outreach(OutreachContext(**base)).body
    )
