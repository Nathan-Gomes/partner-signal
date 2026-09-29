from partnersignal.logic import recommend


def test_security_signals_route_to_security():
    recommendation = recommend({"security_gap": 5, "compliance": 4, "engagement": 3})
    assert recommendation.service_key == "security"
    assert recommendation.score >= 80


def test_ai_signals_route_to_ai():
    recommendation = recommend({"ai_interest": 5, "data_readiness": 4, "engagement": 5})
    assert recommendation.service_key == "ai"
