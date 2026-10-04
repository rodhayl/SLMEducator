"""UTC instants with explicit provenance; legacy wall times remain unknown.

SQLite's built-in DATETIME adapter drops offsets. This codec preserves offsets
without changing existing SQL column declarations or rewriting historical rows.
Naive imported values stay naive; callers must never treat them as UTC/local.
"""

from datetime import date, datetime, timezone
from typing import TypeGuard
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import DateTime, String, cast, func
from sqlalchemy.types import TypeDecorator


def utc_now() -> datetime:
    """Return a timezone-aware UTC instant for every new application write."""
    return datetime.now(timezone.utc)


def known_instant(value: datetime | None) -> TypeGuard[datetime]:
    """Return whether an offset establishes the instant's provenance."""
    return (
        isinstance(value, datetime)
        and value.tzinfo is not None
        and value.utcoffset() is not None
    )


def timestamp_provenance(value: datetime | None) -> str:
    """Describe a timestamp without guessing the timezone of a legacy value."""
    return (
        "utc"
        if known_instant(value)
        else "legacy_unknown" if value is not None else "absent"
    )


class UTCDateTime(TypeDecorator):
    """Retain UTC offsets in SQLite DATETIME and preserve naive legacy values."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def bind_processor(self, dialect):
        if dialect.name != "sqlite":
            return super().bind_processor(dialect)

        def encode(value):
            if value is None:
                return None
            if not isinstance(value, datetime):
                raise TypeError("Timestamp writes require datetime values")
            if known_instant(value):
                value = value.astimezone(timezone.utc)
            # Keeping explicit naive values supports imports of unknown history.
            # Application clocks always supply utc_now(), never naive values.
            return value.isoformat(sep=" ", timespec="microseconds")

        return encode

    def result_processor(self, dialect, coltype):
        if dialect.name != "sqlite":
            return super().result_processor(dialect, coltype)

        def decode(value):
            if value is None or isinstance(value, datetime):
                return value
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed.astimezone(timezone.utc) if known_instant(parsed) else parsed

        return decode


def known_timestamp_clause(column):
    """Restrict SQLite time filters/order to offset-bearing persisted instants."""
    value = cast(column, String)
    return value.like("%+__:__") | value.like("%-__:__") | value.like("%Z")


def known_before(column, instant: datetime, *, inclusive: bool = False):
    """Compare only explicit instants, including mixed persisted UTC offsets."""
    right = func.julianday(instant.isoformat())
    comparison = (
        func.julianday(column) <= right if inclusive else func.julianday(column) < right
    )
    return known_timestamp_clause(column) & comparison


def known_after(column, instant: datetime, *, inclusive: bool = False):
    """Compare only explicit instants, excluding unknown legacy wall times."""
    right = func.julianday(instant.isoformat())
    comparison = (
        func.julianday(column) >= right if inclusive else func.julianday(column) > right
    )
    return known_timestamp_clause(column) & comparison


def validate_timezone(name: str) -> str:
    """Validate an explicit IANA zone; never infer host/browser timezone."""
    if not isinstance(name, str) or not name or len(name) > 100:
        raise ValueError("Choose a valid IANA timezone")
    try:
        ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as error:
        raise ValueError("Choose a valid IANA timezone") from error
    return name


def user_timezone(user) -> str:
    """Return the user's explicit zone, or the documented UTC default."""
    configured = (getattr(user, "settings", None) or {}).get("timezone", "UTC")
    try:
        return validate_timezone(configured)
    except ValueError:
        return "UTC"


def local_date(user, instant: datetime | None = None) -> date:
    """Calculate a day from a known instant under the user's chosen policy."""
    instant = utc_now() if instant is None else instant
    if not known_instant(instant):
        raise ValueError("Legacy timestamp timezone is unknown")
    return instant.astimezone(ZoneInfo(user_timezone(user))).date()


def last_activity_day(user) -> date | None:
    """Resolve new activity provenance; old date-only streaks remain unknown."""
    raw = (user.settings or {}).get("activity_clock", {}).get("last_at")
    try:
        value = datetime.fromisoformat(raw) if raw else None
    except (TypeError, ValueError):
        return None
    return local_date(user, value) if known_instant(value) else None


def record_activity_day(user) -> None:
    """Update participation streak from known local days, preserving legacy evidence."""
    now = utc_now()
    today, previous = local_date(user, now), last_activity_day(user)
    settings = dict(user.settings or {})
    if previous is None and user.last_activity_date:
        settings.setdefault(
            "legacy_streak",
            {
                "last_activity_date": user.last_activity_date.isoformat(),
                "current_streak": user.current_streak,
                "longest_streak": user.longest_streak,
                "provenance": "unknown_day_timezone",
            },
        )
    if previous != today:
        user.current_streak = (
            (user.current_streak or 0) + 1
            if previous and (today - previous).days == 1
            else 1
        )
        user.longest_streak = max(user.longest_streak or 0, user.current_streak)
    user.last_activity_date = today
    settings["activity_clock"] = {
        "last_at": now.isoformat(),
        "timezone": user_timezone(user),
    }
    user.settings = settings


def duration_minutes(start: datetime | None, end: datetime | None) -> int | None:
    """Calculate elapsed time only when both instants have explicit offsets."""
    if not known_instant(start) or not known_instant(end):
        return None
    return max(0, int((end - start).total_seconds() / 60))


def record_goal_day(user, goal, *, new: bool = False) -> None:
    """Record the policy used for a goal update without reinterpreting old dates."""
    settings = dict(user.settings or {})
    clocks = dict(settings.get("daily_goal_clocks", {}))
    prior = dict(clocks.get(str(goal.id), {}))
    zone = user_timezone(user)
    previous = list(prior.get("previous_timezones", []))
    old_zone = prior.get("timezone", "legacy_unknown")
    if not new and old_zone != zone and old_zone not in previous:
        previous.append(old_zone)
    clocks[str(goal.id)] = {
        "timezone": zone,
        "previous_timezones": previous,
        "recorded_at": utc_now().isoformat(),
    }
    settings["daily_goal_clocks"] = clocks
    user.settings = settings


def goal_day_info(user, goal=None) -> dict:
    """Expose current and historical civil-day policy rather than assume a zone."""
    entry = (
        (user.settings or {}).get("daily_goal_clocks", {}).get(str(goal.id), {})
        if goal
        else {}
    )
    return {
        "timezone": user_timezone(user),
        "day_timezone": entry.get("timezone"),
        "day_provenance": (
            "recorded" if entry else "legacy_unknown" if goal else "current_policy"
        ),
        "mixed_day_policy": bool(entry.get("previous_timezones")),
    }
