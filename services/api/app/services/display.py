"""Formatting of stored timestamps into the labels the UI shows (and parsing them back for demo seeding).

The UI shows relative labels ("6h", "4 min ago", "Today 08:40"); the database stores real timestamps so the
labels age naturally. Demo fixture dates without a year ("12 Aug") are in DEMO_YEAR.
"""

import math
import re
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

DEMO_YEAR = 2026


def number(value: Decimal | float) -> int | float:
    f = float(value)
    return int(f) if f.is_integer() else f


# ---- absolute -------------------------------------------------------------------------------------------
def day(d: date) -> str:
    return d.strftime("%d %b")


def day_year(d: date) -> str:
    return d.strftime("%d %b %Y")


def minute(dt: datetime) -> str:
    return _utc(dt).strftime("%d %b %H:%M")


def second(dt: datetime) -> str:
    return _utc(dt).strftime("%d %b %H:%M:%S")


def parse_day(text: str) -> date:
    return datetime.strptime(f"{text} {DEMO_YEAR}", "%d %b %Y").date()


def parse_day_year(text: str) -> date:
    return datetime.strptime(text, "%d %b %Y").date()


def parse_minute(text: str) -> datetime:
    return datetime.strptime(f"{text} {DEMO_YEAR}", "%d %b %H:%M %Y").replace(tzinfo=UTC)


def parse_second(text: str) -> datetime:
    return datetime.strptime(f"{text} {DEMO_YEAR}", "%d %b %H:%M:%S %Y").replace(tzinfo=UTC)


# ---- relative -------------------------------------------------------------------------------------------
def _utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)


def age_days(opened: datetime, now: datetime) -> int:
    return max(0, math.floor((_utc(now) - _utc(opened)).total_seconds() / 86400))


def hours_left(due: datetime, now: datetime) -> int:
    return round((_utc(due) - _utc(now)).total_seconds() / 3600)


def due_in(due: datetime | None, now: datetime, closed: bool = False) -> str:
    if closed or due is None:
        return "—"
    hours = hours_left(due, now)
    return f"{hours}h" if hours < 24 else f"{round(hours / 24)}d"


def last_login(dt: datetime | None, now: datetime) -> str:
    if dt is None:
        return "—"
    dt, now = _utc(dt), _utc(now)
    days = (now.date() - dt.date()).days
    if days == 0:
        return f"Today {dt:%H:%M}"
    if days == 1:
        return "Yesterday"
    if days < 7:
        return f"{days} days ago"
    return day(dt.date())


def last_sync(dt: datetime | None, now: datetime) -> str:
    if dt is None:
        return "—"
    dt, now = _utc(dt), _utc(now)
    minutes = math.floor((now - dt).total_seconds() / 60)
    if (now.date() - dt.date()).days == 1 and minutes >= 60:
        return f"Yesterday {dt:%H:%M}"
    if minutes < 60:
        return f"{max(minutes, 0)} min ago"
    if dt.date() == now.date():
        return f"{minutes // 60} h ago"
    return day(dt.date())


def parse_due_in(text: str, now: datetime) -> datetime | None:
    m = re.fullmatch(r"(\d+)([hd])", text)
    if not m:
        return None
    n = int(m.group(1))
    return now + (timedelta(hours=n) if m.group(2) == "h" else timedelta(days=n))


def parse_last_login(text: str, now: datetime) -> datetime | None:
    if text in ("—", ""):
        return None
    if m := re.fullmatch(r"Today (\d\d):(\d\d)", text):
        return now.replace(hour=int(m.group(1)), minute=int(m.group(2)), second=0, microsecond=0)
    if text == "Yesterday":
        return now - timedelta(days=1)
    if m := re.fullmatch(r"(\d+) days ago", text):
        return now - timedelta(days=int(m.group(1)))
    return datetime.combine(parse_day(text), datetime.min.time(), UTC)


def parse_last_sync(text: str, now: datetime) -> datetime | None:
    if text in ("—", ""):
        return None
    if m := re.fullmatch(r"(\d+) min ago", text):
        return now - timedelta(minutes=int(m.group(1)))
    if m := re.fullmatch(r"(\d+) h ago", text):
        return now - timedelta(hours=int(m.group(1)))
    if m := re.fullmatch(r"Yesterday (\d\d):(\d\d)", text):
        return (now - timedelta(days=1)).replace(
            hour=int(m.group(1)), minute=int(m.group(2)), second=0, microsecond=0
        )
    return datetime.combine(parse_day(text), datetime.min.time(), UTC)
