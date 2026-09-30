"""Runtime settings, read from environment variables (or a local .env file)."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PARTNERSIGNAL_", env_file=".env", extra="ignore")

    database_url: str = "sqlite:///data/partnersignal.db"
    # The Claude integration is optional. Without a key every AI endpoint uses the
    # deterministic local engine, which returns the same schema.
    anthropic_api_key: str | None = None
    claude_model: str = "claude-opus-5"
    # Guard rails for a public demo: cap live model calls per visitor and per day.
    ai_calls_per_visitor_hour: int = 12
    ai_calls_per_day: int = 300
    max_note_chars: int = 6000
    reseed_on_start: bool = True
    # The demo's dates ("due today", "overdue") are relative to the day it was seeded; reseed when the
    # local date changes so a long-running instance never shows yesterday's "today".
    reseed_daily: bool = True
    timezone: str = "America/Toronto"
    commit: str = "local"


@lru_cache
def get_settings() -> Settings:
    return Settings()
