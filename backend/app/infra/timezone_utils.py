"""Timezone-aware date helpers for daily cap resets and scheduling."""

from __future__ import annotations

from datetime import date, datetime

from app.config import settings


def get_today_in_tz() -> date:
    """Calendar date in app_timezone.

    Used for debate usage tracking and daily cap resets.
    Falls back to UTC if the configured timezone is invalid.
    """
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(settings.app_timezone)
    except (ImportError, KeyError):
        from datetime import timezone
        tz = timezone.utc
    return datetime.now(tz).date()
