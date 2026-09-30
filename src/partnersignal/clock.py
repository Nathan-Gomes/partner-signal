"""One clock for the whole app, in the demo's business time zone.

Render runs in UTC, so date.today() there flips at 8 pm Toronto time and new activity timestamps
land hours "in the future" of the seeded ones. Everything reads the time from here instead.
"""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from .config import get_settings


def now() -> datetime:
    """Current local time, naive (the database stores naive local timestamps)."""
    return datetime.now(ZoneInfo(get_settings().timezone)).replace(tzinfo=None)


def today() -> date:
    return now().date()
