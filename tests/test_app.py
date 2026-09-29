from fastapi.testclient import TestClient

from partnersignal.app import app


def test_health_endpoint(tmp_path, monkeypatch):
    monkeypatch.setenv("PARTNER_SIGNAL_DB", str(tmp_path / "demo.db"))
    with TestClient(app) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_overview_and_partner_data(tmp_path, monkeypatch):
    monkeypatch.setenv("PARTNER_SIGNAL_DB", str(tmp_path / "demo.db"))
    with TestClient(app) as client:
        overview = client.get("/api/overview").json()
        partners = client.get("/api/partners").json()
    assert overview["partners"] == 6
    assert overview["qualified"] >= 3
    assert partners[0]["opportunity_score"] > 0
    assert partners[0]["recommended_service"]


def test_outreach_and_complete_follow_up(tmp_path, monkeypatch):
    monkeypatch.setenv("PARTNER_SIGNAL_DB", str(tmp_path / "demo.db"))
    with TestClient(app) as client:
        outreach = client.get("/api/partners/northstar-it/outreach")
        completed = client.post("/api/partners/northstar-it/complete-follow-up")
    assert outreach.status_code == 200
    assert "Northstar" in outreach.json()["subject"]
    assert completed.json()["follow_up_complete"] is True
