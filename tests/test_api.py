from datetime import timedelta

from partnersignal import clock


def first_open(client, stage):
    return next(o for o in client.get("/api/opportunities").json() if o["stage"] == stage)


def test_health_reports_engine_and_fictional_data(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok" and body["data"] == "fictional"
    assert body["ai"]["live_model_available"] is False


def test_today_queue_is_ranked_and_explained(client):
    body = client.get("/api/today").json()
    scores = [item["score"] for item in body["queue"]]
    assert scores == sorted(scores, reverse=True)
    assert all(item["reasons"] for item in body["queue"])
    assert {"prospect", "follow_up"} <= {item["kind"] for item in body["queue"]}
    assert body["kpis"]["open_pipeline"] > body["kpis"]["weighted_pipeline"] > 0


def test_stage_gate_blocks_unqualified_progress_with_a_to_do_list(client):
    opp = next(o for o in client.get("/api/opportunities").json() if o["stage"] == "Prospect")
    response = client.post(f"/api/opportunities/{opp['id']}/stage", json={"stage": "Qualified"})
    assert response.status_code == 409
    assert response.json()["detail"]["to_do"]


def test_qualify_route_and_advance(client):
    opp = first_open(client, "Discovery")
    client.patch(
        f"/api/opportunities/{opp['id']}", json={"need": "high", "budget": "indicated", "authority": "decision_maker"}
    )
    assert client.post(f"/api/opportunities/{opp['id']}/stage", json={"stage": "Qualified"}).status_code == 200
    assert client.post(f"/api/opportunities/{opp['id']}/stage", json={"stage": "Solutioning"}).status_code == 409
    detail = client.get(f"/api/opportunities/{opp['id']}").json()
    recommended = next(s for s in detail["specialists"] if s.get("recommended"))
    client.post(f"/api/opportunities/{opp['id']}/assign", json={"specialist_id": recommended["id"]})
    moved = client.post(f"/api/opportunities/{opp['id']}/stage", json={"stage": "Solutioning"}).json()
    assert moved["stage"] == "Solutioning"
    assert moved["activities"][0]["kind"] == "stage"
    assert "HANDOFF" in moved["handoff"]["text"]


def test_logging_a_touch_sets_the_next_follow_up_from_the_stage_cadence(client):
    opp = first_open(client, "Proposal")
    client.post(
        "/api/activities",
        json={
            "partner_id": opp["partner_id"],
            "opportunity_id": opp["id"],
            "kind": "call",
            "summary": "Reviewed the proposal",
            "outcome": "connected",
        },
    )
    detail = client.get(f"/api/opportunities/{opp['id']}").json()
    assert detail["next_step_due"] == (clock.today() + timedelta(days=2)).isoformat()


def test_signal_to_outreach_to_logged_email(client):
    signal = client.get("/api/signals", params={"status": "new"}).json()[0]
    created = client.post(
        "/api/ai/outreach",
        json={"partner_id": signal["partner_id"], "signal_id": signal["id"], "goal": "intro", "engine": "local"},
    )
    assert created.status_code == 201
    draft = created.json()["draft"]
    assert draft["status"] == "draft" and draft["engine"] == "local"
    approved = client.post(
        f"/api/drafts/{draft['id']}/approve",
        json={"subject": draft["subject"], "body": draft["body"] + "\n\nP.S. edited"},
    ).json()
    assert approved["status"] == "approved" and approved["edited"] is True
    statuses = {s["id"]: s["status"] for s in client.get("/api/signals").json()}
    assert statuses[signal["id"]] == "actioned"
    partner = client.get(f"/api/partners/{signal['partner_id']}").json()
    assert "edited before sending" in partner["activities"][0]["summary"]


def test_convert_signal_opens_prospect(client):
    signal = client.get("/api/signals", params={"status": "new"}).json()[0]
    opp_id = client.post(f"/api/signals/{signal['id']}/convert", json={}).json()["opportunity_id"]
    opp = client.get(f"/api/opportunities/{opp_id}").json()
    assert opp["stage"] == "Prospect" and opp["signal"]["id"] == signal["id"]


def test_discovery_then_create_opportunity(client):
    notes = (
        "Jordan said their customer Coastline Fabrication wants to move 12 servers to Azure before the lease "
        "ends in December. The CFO has approved budget for an assessment."
    )
    body = client.post("/api/ai/discovery", json={"partner_id": "harbour", "notes": notes, "engine": "auto"}).json()
    result = body["result"]
    assert body["meta"]["engine"] == "local"
    assert result["practices"][0]["practice"] == "cloud"
    assert result["bant"]["budget"]["level"] == "confirmed"
    created = client.post(
        "/api/opportunities",
        json={
            "partner_id": "harbour",
            "service_key": result["practices"][0]["service_key"],
            "end_customer": result["end_customer"],
            "budget": result["bant"]["budget"]["level"],
            "need": result["bant"]["need"]["level"],
            "notes": notes,
        },
    )
    assert created.status_code == 201


def test_whitespace_reports_gaps_with_potential(client):
    body = client.get("/api/whitespace").json()
    cells = [c for row in body["rows"] for c in row["cells"].values()]
    assert any(c["status"] == "gap" and c["potential"] > 0 for c in cells)
    assert all(c["potential"] == 0 for c in cells if c["status"] == "attached")


def test_reports_and_csv_export(client):
    report = client.get("/api/reports").json()
    assert 0 < report["win_rate"] < 1
    assert len(report["activity_weeks"]) == 8
    csv_text = client.get("/api/export/opportunities.csv").text
    assert csv_text.startswith("Opportunity ID,Opportunity Name,Account Name")


def test_validation_and_not_found(client):
    assert client.get("/api/partners/nope").status_code == 404
    assert client.get("/api/opportunities/99999").status_code == 404
    assert client.post("/api/ai/discovery", json={"partner_id": "harbour", "notes": "short"}).status_code == 422
    assert (
        client.post("/api/activities", json={"partner_id": "harbour", "kind": "fax", "summary": "x"}).status_code == 422
    )
