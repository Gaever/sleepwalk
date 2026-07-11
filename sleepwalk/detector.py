from __future__ import annotations

import dataclasses
import hashlib
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


RECENT_RESET_WINDOW = timedelta(hours=1)


LIMIT_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"usage limit",
        r"Usage limit reached",
        r"You've reached your usage limit\. Try again after your limit resets\.",
        r"rate limit",
        r"limit reached",
        r"reached your .*limit",
        r"hit your .*limit",
        r"session limit",
        r"resets? (at|in)",
        r"resets?\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?",
        r"try again (later|after|at)",
        r"5-hour limit",
        r"out of (messages|usage)",
        r"individual quota reached",
        r"please upgrade your subscription to increase your limits",
    )
)

ACTIVE_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"esc to interrupt",
        r"ctrl\+?c to interrupt",
        r"\binterrupt\)",
        r"\b\d+\s+background terminals?\b",
    )
)


@dataclasses.dataclass(frozen=True)
class Detection:
    state: str
    matched: str | None = None
    reset_in: timedelta | None = None
    pane_hash: str | None = None


def detect(text: str) -> Detection:
    relevant = "\n".join(line for line in text.splitlines()[-80:] if line.strip())
    pane_hash = hashlib.sha256(relevant.encode("utf-8", errors="ignore")).hexdigest()

    active_match = first_match(ACTIVE_PATTERNS, relevant)
    if active_match:
        return Detection("active", active_match.group(0), None, pane_hash)

    limit_match = first_match(LIMIT_PATTERNS, relevant)
    if limit_match:
        return Detection("limited", limit_match.group(0), parse_reset_delta(relevant), pane_hash)

    return Detection("idle", None, parse_reset_delta(relevant), pane_hash)


def first_match(patterns: tuple[re.Pattern[str], ...], text: str) -> re.Match[str] | None:
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            return match
    return None


def parse_reset_delta(text: str, now: datetime | None = None) -> timedelta | None:
    return parse_relative_reset(text) or parse_absolute_reset(text, now)


def parse_relative_reset(text: str) -> timedelta | None:
    for pattern in (
        r"resets?\s+in\s+(?:(?P<h>\d+)\s*h)?\s*(?:(?P<m>\d+)\s*m)?\s*(?:(?P<s>\d+)\s*s)?",
        r"resets?\s+in\s+(?:(?P<h2>\d+)\s+hours?)?\s*(?:(?P<m2>\d+)\s+minutes?)?\s*(?:(?P<s2>\d+)\s+seconds?)?",
    ):
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            continue
        groups = match.groupdict()
        hours = int(groups.get("h") or groups.get("h2") or 0)
        minutes = int(groups.get("m") or groups.get("m2") or 0)
        seconds = int(groups.get("s") or groups.get("s2") or 0)
        if hours or minutes or seconds:
            return timedelta(hours=hours, minutes=minutes, seconds=seconds)
    return None


def parse_absolute_reset(text: str, now: datetime | None = None) -> timedelta | None:
    pattern = re.compile(
        r"resets?(?:\s+at)?\s+"
        r"(?P<hour>\d{1,2})(?::(?P<minute>\d{2}))?\s*(?P<ampm>am|pm)?"
        r"(?:\s*\((?P<tz>[^)]+)\))?",
        re.IGNORECASE,
    )
    for match in pattern.finditer(text):
        hour = int(match.group("hour"))
        minute = int(match.group("minute") or 0)
        ampm = (match.group("ampm") or "").lower()
        tz_name = match.group("tz")
        if hour > 23 or minute > 59:
            continue
        if ampm:
            if hour < 1 or hour > 12:
                continue
            if ampm == "am":
                hour = 0 if hour == 12 else hour
            elif ampm == "pm":
                hour = 12 if hour == 12 else hour + 12

        tz = timezone_from_name(tz_name)
        current = now.astimezone(tz) if now else datetime.now(tz)
        reset_at = current.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if reset_at < current:
            elapsed = current - reset_at
            if elapsed <= RECENT_RESET_WINDOW:
                return timedelta(0)
            reset_at += timedelta(days=1)
        return reset_at - current
    return None


def timezone_from_name(name: str | None):
    if not name:
        return datetime.now().astimezone().tzinfo
    try:
        return ZoneInfo(name.strip())
    except ZoneInfoNotFoundError:
        return datetime.now().astimezone().tzinfo


def format_duration(delta: timedelta | None) -> str:
    if delta is None:
        return "-"
    total = max(0, int(delta.total_seconds()))
    hours, rem = divmod(total, 3600)
    minutes, seconds = divmod(rem, 60)
    if hours:
        return f"{hours}h{minutes:02d}m"
    if minutes:
        return f"{minutes}m{seconds:02d}s"
    return f"{seconds}s"
