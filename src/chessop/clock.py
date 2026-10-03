"""Time as the app reads it: the clock it is given, and the learner's day (public spec §3).

A `Clock` returns the current time in seconds since the epoch; the app takes one at its factory
so tests can move time, `time.time` otherwise. A learner's day is the local date in their IANA
time zone, the machine's own zone when they have none. The site's usage is counted by UTC day.
"""

from collections.abc import Callable
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

Clock = Callable[[], float]


def zone(name: object) -> ZoneInfo | None:
    """The IANA time zone called `name`, None when it names none."""
    if not isinstance(name, str) or not name or len(name) > 64:
        return None
    try:
        return ZoneInfo(name)
    except (ValueError, KeyError, OSError):  # malformed, unknown, or not a zone file
        return None


def day(at: float, timezone: str | None) -> str:
    """The ISO date of `at` in `timezone`, in the machine's zone when that names none."""
    tz = zone(timezone)
    if tz is None:
        return date.fromtimestamp(at).isoformat()
    return datetime.fromtimestamp(at, tz).date().isoformat()


def utc_day(at: float) -> str:
    """The ISO date of `at` in UTC: the day the site's usage is counted by (public spec §12)."""
    return datetime.fromtimestamp(at, UTC).date().isoformat()


def utc_midnight(iso_date: str) -> float:
    """When the UTC day `iso_date` begins, in seconds since the epoch."""
    return datetime.fromisoformat(iso_date).replace(tzinfo=UTC).timestamp()
