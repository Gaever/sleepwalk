from datetime import datetime, timedelta
from unittest import TestCase
from zoneinfo import ZoneInfo

from sleepwalk.detector import parse_absolute_reset


class ParseAbsoluteResetTest(TestCase):
    def test_recently_passed_reset_is_due(self):
        now = datetime(2026, 7, 11, 0, 54, tzinfo=ZoneInfo("Asia/Jakarta"))

        result = parse_absolute_reset(
            "You've hit your session limit - resets 12:40am (Asia/Jakarta)",
            now,
        )

        self.assertEqual(result, timedelta(0))

    def test_future_reset_remains_in_the_same_day(self):
        now = datetime(2026, 7, 10, 9, 10, tzinfo=ZoneInfo("Asia/Jakarta"))

        result = parse_absolute_reset(
            "You've hit your session limit - resets 10:40pm (Asia/Jakarta)",
            now,
        )

        self.assertEqual(result, timedelta(hours=13, minutes=30))

    def test_old_reset_time_is_treated_as_the_next_day(self):
        now = datetime(2026, 7, 11, 7, 10, tzinfo=ZoneInfo("Asia/Jakarta"))

        result = parse_absolute_reset(
            "You've hit your session limit - resets 12:40am (Asia/Jakarta)",
            now,
        )

        self.assertEqual(result, timedelta(hours=17, minutes=30))
