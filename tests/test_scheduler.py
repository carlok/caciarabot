from datetime import datetime
from zoneinfo import ZoneInfo

from caciarabot.llm.scheduler import seconds_until_next

_TZ = ZoneInfo("Europe/Rome")


def test_target_later_today():
    now = datetime(2026, 1, 1, 8, 0, tzinfo=_TZ)
    assert seconds_until_next("09:00", _TZ, now=now) == 3600


def test_target_already_passed_today_rolls_to_tomorrow():
    now = datetime(2026, 1, 1, 10, 0, tzinfo=_TZ)
    seconds = seconds_until_next("09:00", _TZ, now=now)
    assert seconds == 23 * 3600


def test_target_exactly_now_rolls_to_tomorrow():
    now = datetime(2026, 1, 1, 9, 0, tzinfo=_TZ)
    seconds = seconds_until_next("09:00", _TZ, now=now)
    assert seconds == 24 * 3600
