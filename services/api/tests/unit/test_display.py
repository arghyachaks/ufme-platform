from datetime import UTC, datetime, timedelta

import pytest

from app.services import display as fmt

NOW = datetime(2026, 10, 18, 12, 0, tzinfo=UTC)


@pytest.mark.parametrize("label", ["Today 08:40", "Yesterday", "3 days ago", "02 Jun", "—"])
def test_last_login_roundtrip(label: str) -> None:
    assert fmt.last_login(fmt.parse_last_login(label, NOW), NOW) == label


@pytest.mark.parametrize("label", ["4 min ago", "52 min ago", "1 h ago", "Yesterday 22:00", "05 Aug"])
def test_last_sync_roundtrip(label: str) -> None:
    assert fmt.last_sync(fmt.parse_last_sync(label, NOW), NOW) == label


@pytest.mark.parametrize("label", ["6h", "1d", "3d", "—"])
def test_due_in_roundtrip(label: str) -> None:
    assert fmt.due_in(fmt.parse_due_in(label, NOW), NOW) == label


def test_labels_age_with_time() -> None:
    synced = fmt.parse_last_sync("4 min ago", NOW)
    assert fmt.last_sync(synced, NOW + timedelta(minutes=10)) == "14 min ago"
    assert fmt.due_in(NOW + timedelta(hours=6), NOW, closed=True) == "—"
    assert fmt.age_days(NOW - timedelta(days=3, hours=2), NOW) == 3
    assert fmt.hours_left(NOW - timedelta(hours=8), NOW) == -8


def test_absolute_formats() -> None:
    assert fmt.day(fmt.parse_day("12 Aug")) == "12 Aug"
    assert fmt.day_year(fmt.parse_day_year("01 Jul 2026")) == "01 Jul 2026"
    assert fmt.minute(fmt.parse_minute("12 Aug 09:14")) == "12 Aug 09:14"
    assert fmt.second(fmt.parse_second("17 Aug 10:42:03")) == "17 Aug 10:42:03"
    assert fmt.number(1284000) == 1284000 and fmt.number(12.5) == 12.5
