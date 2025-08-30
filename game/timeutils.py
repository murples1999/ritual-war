"""Timezone-aware time utilities for the game."""

import datetime
from zoneinfo import ZoneInfo
from .config import TIMEZONE


def get_timezone():
    """Get the timezone object for the game."""
    return ZoneInfo(TIMEZONE)


def now() -> datetime.datetime:
    """Get current timezone-aware datetime."""
    return datetime.datetime.now(ZoneInfo(TIMEZONE))


def today_key() -> str:
    """Get today's date as a string key in the game timezone."""
    return now().strftime("%Y-%m-%d")


def hours_ago(hours: int) -> datetime.datetime:
    """Get datetime N hours ago in game timezone."""
    return now() - datetime.timedelta(hours=hours)


def timestamp_from_hours(hours: int) -> int:
    """Get timestamp N hours from now."""
    future = now() + datetime.timedelta(hours=hours)
    return int(future.timestamp())


def hours_until(timestamp: int) -> float:
    """Get hours until the given timestamp."""
    target = datetime.datetime.fromtimestamp(timestamp, ZoneInfo(TIMEZONE))
    delta = target - now()
    return max(0.0, delta.total_seconds() / 3600)


def hours_since(timestamp: int) -> float:
    """Get hours since the given timestamp."""
    past = datetime.datetime.fromtimestamp(timestamp, ZoneInfo(TIMEZONE))
    delta = now() - past
    return delta.total_seconds() / 3600


def get_freshness_bucket(hours_old: float) -> str:
    """Get freshness bucket label for given age in hours."""
    from .config import FRESH_BUCKETS
    
    for min_hours, max_hours, label in FRESH_BUCKETS:
        if min_hours <= hours_old < max_hours:
            return label
    return "Expired"