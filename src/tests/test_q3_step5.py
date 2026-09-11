import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from policy import HuntPolicy


class _FakeBot:
    position = (0.0, 0.0)
    log: list = []

    def __init__(self, remaining_real_duration_s=1200):
        self.remaining_real_duration_s = remaining_real_duration_s
        self.virtual_time_s = 0.0
        self.measure_calls = 0
        self.clear_calls = 0
        self.exit_calls = 0

    def enter(self):
        return {
            "accepted": True,
            "remaining_real_duration_s": self.remaining_real_duration_s,
        }

    def measure(self, x, y, channel):
        self.measure_calls += 1
        return {"accepted": True, "measure_result": "no_signal"}

    def clear(self, x, y, channel):
        self.clear_calls += 1
        return {"accepted": True, "clear_result": "no_target_in_range"}

    def exit(self):
        self.exit_calls += 1
        return {"accepted": True}


class TestQ3Step5GuardAndTermination(unittest.TestCase):
    def test_deadline_blocks_actions_but_still_exits(self):
        bot = _FakeBot(remaining_real_duration_s=0)
        policy = HuntPolicy(
            bot,
            monotonic_clock=lambda: 0.0,
        )

        stats = policy.run()

        self.assertEqual(bot.measure_calls, 0)
        self.assertEqual(bot.clear_calls, 0)
        self.assertEqual(bot.exit_calls, 1)
        self.assertFalse(stats["completed"])
        self.assertEqual(stats["termination_reason"], "deadline_guard")

    def test_route_completion_does_not_require_unknown_channels_empty(self):
        bot = _FakeBot()
        policy = HuntPolicy(bot)
        policy._scan_point = lambda xy, channels: None
        policy._drain_pending = lambda future=None: None

        stats = policy.run()

        self.assertTrue(stats["route_completed"])
        self.assertEqual(stats["pending_at_exit"], 0)
        self.assertTrue(stats["unknown_channels_at_exit"])
        self.assertEqual(stats["termination_reason"], "coverage_complete")
        self.assertTrue(stats["completed"])

    def test_short_circuit_is_a_completed_coverage_exit(self):
        bot = _FakeBot()
        policy = HuntPolicy(bot)
        policy._scan_point = lambda xy, channels: None
        policy._drain_pending = lambda future=None: None
        policy.book.unknown_channels = lambda: []
        policy.book.pending = lambda: []

        stats = policy.run()

        self.assertFalse(stats["route_completed"])
        self.assertEqual(stats["termination_reason"], "coverage_short_circuit")
        self.assertTrue(stats["completed"])


if __name__ == "__main__":
    unittest.main()
