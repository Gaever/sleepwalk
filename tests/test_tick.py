from unittest import TestCase
from unittest.mock import patch

from sleepwalk.cli import tick
from sleepwalk.config import Config, SessionConfig


class ScheduledTickTest(TestCase):
    def test_sends_without_waiting_for_displayed_reset_time(self):
        config = Config(sessions=(SessionConfig("claude"),))
        pane = "You've hit your session limit - resets in 17h"

        with (
            patch("sleepwalk.cli.capture_pane", return_value=pane),
            patch("sleepwalk.cli.send_text") as send_text,
            patch("sleepwalk.cli.append_log"),
        ):
            tick(config)

        send_text.assert_called_once_with("claude", "продолжай", None)
