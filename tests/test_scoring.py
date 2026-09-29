from datetime import date, timedelta

import pytest

from partnersignal.models import Opportunity, Signal
from partnersignal.services.scoring import GateError, bant_score, check_stage_gate, priority

TODAY = date(2026, 10, 1)


def make_opp(**overrides) -> Opportunity:
    values = dict(
        partner_id="p",
        title="t",
        end_customer="c",
        industry="",
        practice="security",
        service_key="sec-posture",
        stage="Discovery",
        value=10000,
        budget="unknown",
        authority="unknown",
        need="unknown",
        timeline="unknown",
        challenge="",
        next_step="Call",
        next_step_due=TODAY,
        specialist_id=None,
        created_on=TODAY - timedelta(days=5),
        stage_changed_on=TODAY - timedelta(days=2),
    )
    values.update(overrides)
    return Opportunity(**values)


def test_bant_score_counts_known_fields_and_lists_missing():
    points, reasons, missing = bant_score(make_opp(budget="confirmed", need="high"))
    assert points == 15
    assert reasons == ["budget confirmed", "urgent business need"]
    assert missing == ["authority", "timeline"]


def test_priority_is_bounded_and_every_component_explains_itself():
    opp = make_opp(
        budget="confirmed",
        authority="decision_maker",
        need="high",
        timeline="under_3_months",
        challenge="x",
        next_step_due=TODAY - timedelta(days=3),
    )
    signal = Signal(strength=5, title="Renewals", source="Renewal calendar", deadline=TODAY + timedelta(days=20))
    result = priority(opp, TODAY, TODAY, signal)
    assert 0 <= result.score <= 100
    assert result.band == "Hot"
    assert "overdue" in result.flags
    assert all(component.reasons for component in result.components)
    assert all(component.points <= component.max_points for component in result.components)


def test_cold_record_scores_low_and_reports_what_is_missing():
    opp = make_opp(next_step_due=None, next_step="")
    result = priority(opp, TODAY, None)
    assert result.band == "Cool"
    assert "no_next_step" in result.flags
    qualification = next(c for c in result.components if c.key == "qualification")
    assert "unknown: budget, authority, need, timeline" in qualification.reasons


def test_stalled_opportunity_is_flagged_and_loses_momentum():
    fresh = priority(make_opp(), TODAY, TODAY)
    stalled = priority(make_opp(stage_changed_on=TODAY - timedelta(days=30)), TODAY, TODAY)
    assert "stalled" in stalled.flags
    assert stalled.score < fresh.score


def test_qualified_gate_requires_need_and_two_more_bant_fields():
    with pytest.raises(GateError) as error:
        check_stage_gate(make_opp(budget="confirmed", authority="decision_maker"), "Qualified")
    assert any("problem" in question for question in error.value.missing)
    check_stage_gate(make_opp(need="high", budget="indicated", timeline="3_6_months"), "Qualified")


def test_solutioning_gate_requires_specialist():
    opp = make_opp(stage="Qualified", need="high", budget="indicated", authority="influencer")
    with pytest.raises(GateError, match="specialist"):
        check_stage_gate(opp, "Solutioning")
    opp.specialist_id = "sp-rao"
    check_stage_gate(opp, "Solutioning")


def test_moving_backwards_or_closing_is_always_allowed():
    check_stage_gate(make_opp(stage="Proposal"), "Discovery")
    check_stage_gate(make_opp(), "Lost")
