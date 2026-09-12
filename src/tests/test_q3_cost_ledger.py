import math
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mock_sim import MockSim, Source
from policy import MAX_ACTION_ATTEMPTS, HuntPolicy, action_stats
from robot_client import FnTransport, RobotClient
from runner_q3 import run_q3
from runner_q4 import run_q4


class TestActionStatsDecomposition(unittest.TestCase):
    def test_manual_log_decomposition(self):
        log = [
            {
                "path": "/measure",
                "request": {"position": {"x": 0.0, "y": 0.0}, "channel": 1},
                "response": {"accepted": True, "virtual_time_s": 5.0},
            },
            {
                "path": "/measure",
                "request": {"position": {"x": 100.0, "y": 0.0}, "channel": 2},
                "response": {"accepted": True, "virtual_time_s": 31.0},
            },
            {
                "path": "/clear",
                "request": {"position": {"x": 100.0, "y": 0.0}, "channel": 2},
                "response": {
                    "accepted": True,
                    "virtual_time_s": 36.0,
                    "clear_result": "success",
                },
            },
            {
                "path": "/clear",
                "request": {"position": {"x": 200.0, "y": 0.0}, "channel": 2},
                "response": {
                    "accepted": True,
                    "virtual_time_s": 59.0,
                    "clear_result": "no_target_in_range",
                },
            },
        ]
        stats = action_stats(log)
        self.assertAlmostEqual(stats["travel_s"], 40.0)
        self.assertAlmostEqual(stats["detect_s"], 10.0)
        self.assertAlmostEqual(stats["switch_s"], 1.0)
        self.assertAlmostEqual(stats["clear_ok_s"], 5.0)
        self.assertAlmostEqual(stats["clear_miss_s"], 3.0)
        self.assertEqual(stats["n_measure"], 2)
        self.assertEqual(stats["n_clear"], 2)
        self.assertEqual(stats["clear_ok"], 1)
        self.assertEqual(stats["clear_miss"], 1)
        total = (
            stats["travel_s"]
            + stats["detect_s"]
            + stats["switch_s"]
            + stats["clear_ok_s"]
            + stats["clear_miss_s"]
        )
        self.assertAlmostEqual(total, 59.0, places=6)

    def test_real_run_decomposition_sums_to_virtual_time(self):
        sim = MockSim(robot_id="ledger-test", sources=[Source(channel=3, xy=(50.0, 0.0), r_eff=1200.0)])
        bot = RobotClient(robot_id="ledger-test", transport=FnTransport(sim.handle))
        stats = run_q3(bot)
        self.assertEqual(stats["cleared"], 1)
        ledger = action_stats(bot.log)
        total = (
            ledger["travel_s"]
            + ledger["detect_s"]
            + ledger["switch_s"]
            + ledger["clear_ok_s"]
            + ledger["clear_miss_s"]
        )
        self.assertAlmostEqual(total, bot.virtual_time_s, places=6)
        self.assertAlmostEqual(ledger["detect_s"], 5.0 * ledger["n_measure"], places=6)
        self.assertAlmostEqual(ledger["clear_ok_s"], 5.0 * ledger["clear_ok"], places=6)
        self.assertAlmostEqual(ledger["clear_miss_s"], 3.0 * ledger["clear_miss"], places=6)
        channel_sum = sum(e["total_s"] for e in ledger["per_channel"].values())
        self.assertAlmostEqual(channel_sum, bot.virtual_time_s, places=6)
        self.assertIn(3, ledger["per_channel"])

    def test_move_decomposition_sums_to_travel(self):
        sim = MockSim(robot_id="move-ledger-test", sources=[Source(channel=3, xy=(50.0, 0.0), r_eff=1200.0)])
        bot = RobotClient(robot_id="move-ledger-test", transport=FnTransport(sim.handle))
        stats = run_q3(bot)
        move = stats["move_decomposition"]
        self.assertAlmostEqual(
            move["backbone_scan_s"] + move["localization_s"] + move["clear_detour_s"],
            move["total_s"],
            places=6,
        )
        self.assertAlmostEqual(move["total_s"], stats["travel_s"], places=6)
        self.assertAlmostEqual(
            move["backbone_scan_s"],
            move["backbone_planned_s"] + move["backbone_rejoin_s"],
            places=6,
        )
        # Cover-enroute may fold a near-origin source into the backbone, so
        # dedicated localization travel can be zero.
        self.assertGreaterEqual(move["localization_s"], 0.0)
        self.assertGreater(move["clear_detour_s"], 0.0)

    def test_clear_audit_covers_all_clears(self):
        sim = MockSim(robot_id="audit-test", sources=[Source(channel=3, xy=(50.0, 0.0), r_eff=1200.0)])
        bot = RobotClient(robot_id="audit-test", transport=FnTransport(sim.handle))
        stats = run_q3(bot)
        audit = stats["clear_audit"]
        self.assertNotIn("unknown", audit)
        total_attempts = sum(e["attempts"] for e in audit.values())
        self.assertEqual(total_attempts, stats["clear_ok"] + stats["clear_miss"])
        self.assertEqual(sum(e["success"] for e in audit.values()), stats["clear_ok"])
        self.assertEqual(sum(e["miss"] for e in audit.values()), stats["clear_miss"])

    def test_move_decomposition_directional_consistent(self):
        rng = random.Random(7)
        sources = []
        for i in range(3):
            r = 400.0 + math.sqrt(rng.random()) * 1300.0
            a = rng.random() * 2.0 * math.pi
            sources.append(
                Source(
                    channel=i + 1,
                    xy=(r * math.cos(a), r * math.sin(a)),
                    r_eff=rng.uniform(1000.0, 1500.0),
                )
            )
        sim = MockSim(robot_id="move-q4-test", sources=sources)
        bot = RobotClient(robot_id="move-q4-test", transport=FnTransport(sim.handle))
        stats = run_q4(bot)
        self.assertEqual(stats["cleared"], 3)
        move = stats["move_decomposition"]
        self.assertAlmostEqual(
            move["backbone_scan_s"] + move["localization_s"] + move["clear_detour_s"],
            move["total_s"],
            places=6,
        )
        self.assertAlmostEqual(move["total_s"], stats["travel_s"], places=6)
        self.assertAlmostEqual(
            move["backbone_scan_s"],
            move["backbone_planned_s"] + move["backbone_rejoin_s"],
            places=6,
        )


class _RejectMeasureBot:
    position = (0.0, 0.0)
    log: list = []
    remaining_real_duration_s = 1200

    def __init__(self):
        self.virtual_time_s = 0.0
        self.measure_calls = 0
        self.clear_calls = 0
        self.exit_calls = 0

    def enter(self):
        return {"accepted": True, "remaining_real_duration_s": 1200}

    def measure(self, x, y, channel):
        self.measure_calls += 1
        return {"accepted": False}

    def clear(self, x, y, channel):
        self.clear_calls += 1
        return {"accepted": False}

    def exit(self):
        self.exit_calls += 1
        return {"accepted": True}


class _FlakyExitBot(_RejectMeasureBot):
    def exit(self):
        self.exit_calls += 1
        if self.exit_calls == 1:
            raise ConnectionError("transient")
        return {"accepted": True}


class TestStep5RetryGuards(unittest.TestCase):
    def test_measure_rejects_then_failure_after_retries(self):
        bot = _RejectMeasureBot()
        policy = HuntPolicy(bot)
        stats = policy.run()
        self.assertEqual(bot.measure_calls, MAX_ACTION_ATTEMPTS)
        self.assertEqual(stats["termination_reason"], "action_failure")
        self.assertFalse(stats["completed"])
        self.assertTrue(stats["exit_accepted"])

    def test_exit_retries_on_transient_failure(self):
        bot = _FlakyExitBot()
        policy = HuntPolicy(bot)
        stats = policy.run()
        self.assertEqual(bot.exit_calls, 2)
        self.assertTrue(stats["exit_accepted"])


if __name__ == "__main__":
    unittest.main()
