from datetime import UTC, datetime, timedelta
from unittest import TestCase
from unittest.mock import patch

from sleepwalk.cli import tick
from sleepwalk.config import Config, SessionConfig
from sleepwalk.state import SessionState


class ScheduledTickTest(TestCase):
    def test_sends_when_remembered_reset_has_passed(self):
        now = datetime(2026, 7, 11, 1, 10, tzinfo=UTC)
        state = {
            "claude": SessionState(
                expected_reset_at=(now - timedelta(minutes=30)).isoformat(),
            )
        }
        config = Config(sessions=(SessionConfig("claude"),))
        pane = "You've hit your session limit - resets 12:40am (Asia/Jakarta)"

        with (
            patch("sleepwalk.cli.load_state", return_value=state),
            patch("sleepwalk.cli.utcnow", return_value=now),
            patch("sleepwalk.cli.capture_pane", return_value=pane),
            patch("sleepwalk.cli.send_text") as send_text,
            patch("sleepwalk.cli.save_state"),
            patch("sleepwalk.cli.append_log"),
        ):
            tick(config, scheduled=True)

        send_text.assert_called_once_with("claude", "продолжай", None)
        self.assertIsNone(state["claude"].expected_reset_at)
