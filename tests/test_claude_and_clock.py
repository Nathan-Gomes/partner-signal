import json
from datetime import timedelta

import anthropic
import httpx2

from partnersignal import clock
from partnersignal.ai.claude import ClaudeEngine
from partnersignal.ai.local import OutreachContext, draft_outreach, extract_discovery

NOTES = (
    "Maya said their client Lakeview Family Clinics had a phishing scare and the insurer wants proof of tested "
    "backups before the renewal in November. The operations director signs off on IT spend."
)


def _engine_with(reply: dict, seen: list) -> ClaudeEngine:
    """A ClaudeEngine whose HTTP layer is a stub: the real SDK builds and parses, no network is used."""

    def handler(request: httpx2.Request) -> httpx2.Response:
        seen.append(json.loads(request.content))
        body = {
            "id": "msg_test",
            "type": "message",
            "role": "assistant",
            "model": "claude-opus-5",
            "content": [{"type": "text", "text": json.dumps(reply)}],
            "stop_reason": "end_turn",
            "stop_sequence": None,
            "usage": {"input_tokens": 10, "output_tokens": 10},
        }
        return httpx2.Response(200, json=body)

    engine = ClaudeEngine("test-key", "claude-opus-5")
    engine.client = anthropic.Anthropic(
        api_key="test-key",
        max_retries=0,
        http_client=anthropic.DefaultHttpxClient(transport=httpx2.MockTransport(handler)),
    )
    return engine


def test_claude_discovery_request_and_parsing():
    expected = extract_discovery(NOTES, "Northstar IT Group")
    seen: list = []
    result = _engine_with(expected.model_dump(), seen).extract_discovery(NOTES, "Northstar IT Group, MSP")
    request = seen[0]
    assert request["model"] == "claude-opus-5"
    assert "verbatim" in request["system"]
    assert NOTES in request["messages"][0]["content"]
    assert request["output_config"]["format"]["type"] == "json_schema"
    assert result.bant.need.level == expected.bant.need.level
    assert result.practices[0].service_key == expected.practices[0].service_key


def test_claude_outreach_request_and_parsing():
    ctx = OutreachContext(
        goal="intro",
        partner_name="Prairie Digital",
        contact_first="Avery",
        practice="network",
        service_key="net-assessment",
        signal_title="Wireless access points ordered for two sites",
    )
    seen: list = []
    draft = _engine_with(draft_outreach(ctx).model_dump(), seen).draft_outreach(ctx)
    assert "Prairie Digital" in seen[0]["messages"][0]["content"]
    assert draft.body.startswith("Hi Avery,")


def test_demo_reseeds_when_the_local_date_changes(client, monkeypatch):
    first = client.get("/api/today").json()["date"]
    tomorrow = clock.today() + timedelta(days=1)
    monkeypatch.setattr(clock, "today", lambda: tomorrow)
    body = client.get("/api/today").json()
    assert body["date"] == tomorrow.isoformat() != first
    assert body["kpis"]["due_today"] > 0  # due dates were re-anchored to the new day
