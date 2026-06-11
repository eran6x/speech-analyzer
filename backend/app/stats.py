"""Aggregate progress stats across sessions: streaks, totals, averages.

Streaks are computed on UTC calendar days (we only store UTC timestamps).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from statistics import mean

from .models import Averages, Session, Stats

_DIMS = ("overall", "pace", "pauses", "confidence", "fluency")


def _session_date(timestamp: str):
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).astimezone(timezone.utc).date()


def _longest_streak(days: list) -> int:
    if not days:
        return 0
    longest = run = 1
    for prev, curr in zip(days, days[1:]):
        run = run + 1 if (curr - prev).days == 1 else 1
        longest = max(longest, run)
    return longest


def _current_streak(day_set: set, today) -> int:
    # Count back from today; if nothing today, allow the streak to end yesterday.
    if today in day_set:
        cursor = today
    elif (today - timedelta(days=1)) in day_set:
        cursor = today - timedelta(days=1)
    else:
        return 0
    streak = 0
    while cursor in day_set:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def compute_stats(sessions: list[Session]) -> Stats:
    days = sorted({_session_date(s.timestamp) for s in sessions})
    day_set = set(days)
    today = datetime.now(timezone.utc).date()
    week_ago = today - timedelta(days=6)

    averages = Averages(
        **{
            dim: round(mean(vals), 1)
            for dim in _DIMS
            if (vals := [getattr(s.scores, dim) for s in sessions if getattr(s.scores, dim) is not None])
        }
    )

    return Stats(
        total_sessions=len(sessions),
        current_streak=_current_streak(day_set, today),
        longest_streak=_longest_streak(days),
        sessions_this_week=sum(1 for s in sessions if _session_date(s.timestamp) >= week_ago),
        averages=averages,
    )
