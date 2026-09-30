"""Chooses an engine per request, enforces demo limits, and falls back safely.

Order of preference: Claude (when a key is configured and the visitor is under the limit),
otherwise the local engine. A Claude failure never breaks the workflow: the request is
answered by the local engine and the envelope says why.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict, deque

import anthropic

from .. import clock
from ..config import Settings
from . import local
from .claude import ClaudeEngine, EngineUnavailable
from .schemas import AIResult, DiscoveryExtraction, OutreachDraft

log = logging.getLogger(__name__)
LOCAL_MODEL = "rules-v2"


class RateLimiter:
    def __init__(self, per_hour: int, per_day: int):
        self.per_hour, self.per_day = per_hour, per_day
        self.hits: dict[str, deque[float]] = defaultdict(deque)
        self.day, self.day_count = clock.today(), 0

    def allow(self, visitor: str) -> bool:
        now = time.time()
        if clock.today() != self.day:
            self.day, self.day_count = clock.today(), 0
        window = self.hits[visitor]
        while window and now - window[0] > 3600:
            window.popleft()
        if len(window) >= self.per_hour or self.day_count >= self.per_day:
            return False
        window.append(now)
        self.day_count += 1
        return True


class Assistant:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.claude = (
            ClaudeEngine(settings.anthropic_api_key, settings.claude_model) if settings.anthropic_api_key else None
        )
        self.limiter = RateLimiter(settings.ai_calls_per_visitor_hour, settings.ai_calls_per_day)

    @property
    def status(self) -> dict[str, object]:
        return {
            "live_model_available": self.claude is not None,
            "model": self.settings.claude_model if self.claude else LOCAL_MODEL,
            "limits": {
                "per_visitor_hour": self.settings.ai_calls_per_visitor_hour,
                "per_day": self.settings.ai_calls_per_day,
            },
        }

    def _choose(self, prefer: str, visitor: str) -> tuple[bool, str]:
        if prefer == "local":
            return False, "Local rules engine selected."
        if self.claude is None:
            return False, "No API key is configured on this deployment, so the local rules engine answered."
        if not self.limiter.allow(visitor):
            return False, "Demo limit for live model calls reached; the local rules engine answered."
        return True, ""

    def discovery(
        self, notes: str, partner_name: str, partner_context: str, prefer: str, visitor: str
    ) -> tuple[DiscoveryExtraction, AIResult]:
        use_claude, note = self._choose(prefer, visitor)
        if use_claude and self.claude:
            try:
                result = self.claude.extract_discovery(notes, partner_context)
                return result, AIResult(engine="claude", model=self.settings.claude_model)
            except (anthropic.APIError, EngineUnavailable) as error:
                log.warning("Claude discovery extraction failed: %s", error)
                note = f"Live model unavailable ({_describe(error)}); the local rules engine answered."
        return local.extract_discovery(notes, partner_name), AIResult(engine="local", model=LOCAL_MODEL, note=note)

    def outreach(self, ctx: local.OutreachContext, prefer: str, visitor: str) -> tuple[OutreachDraft, AIResult]:
        use_claude, note = self._choose(prefer, visitor)
        if use_claude and self.claude:
            try:
                return self.claude.draft_outreach(ctx), AIResult(engine="claude", model=self.settings.claude_model)
            except (anthropic.APIError, EngineUnavailable) as error:
                log.warning("Claude outreach draft failed: %s", error)
                note = f"Live model unavailable ({_describe(error)}); the local rules engine answered."
        return local.draft_outreach(ctx), AIResult(engine="local", model=LOCAL_MODEL, note=note)


def _describe(error: Exception) -> str:
    if isinstance(error, anthropic.RateLimitError):
        return "rate limited"
    if isinstance(error, anthropic.APIStatusError):
        return f"HTTP {error.status_code}"
    if isinstance(error, anthropic.APIConnectionError):
        return "connection error"
    return str(error)
