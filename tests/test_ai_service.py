import anthropic
import httpx2

from partnersignal.ai.service import Assistant, RateLimiter
from partnersignal.config import Settings


class FailingClaude:
    def extract_discovery(self, *_):
        raise anthropic.APIConnectionError(request=httpx2.Request("POST", "https://api.anthropic.com"))

    def draft_outreach(self, *_):
        raise anthropic.APIConnectionError(request=httpx2.Request("POST", "https://api.anthropic.com"))


def test_without_key_the_local_engine_answers_and_says_why():
    assistant = Assistant(Settings(anthropic_api_key=None))
    result, meta = assistant.discovery("Customer wants to migrate servers to Azure next quarter.", "P", "", "auto", "v")
    assert meta.engine == "local"
    assert "No API key" in meta.note
    assert result.practices[0].practice == "cloud"


def test_claude_failure_falls_back_without_breaking_the_request():
    assistant = Assistant(Settings(anthropic_api_key=None))
    assistant.claude = FailingClaude()
    result, meta = assistant.discovery("Ransomware worries after an audit finding.", "P", "", "auto", "v")
    assert meta.engine == "local"
    assert "connection error" in meta.note
    assert result.practices


def test_rate_limiter_caps_each_visitor():
    limiter = RateLimiter(per_hour=2, per_day=10)
    assert limiter.allow("a") and limiter.allow("a")
    assert not limiter.allow("a")
    assert limiter.allow("b")
