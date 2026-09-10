import math
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from candidate import (
    ARENA_R,
    H_DEFAULT,
    in_candidate_region,
    intersection_angle_deg,
    recommend_second,
    to_body,
    from_body,
)
from coverage import coverage_ok, omni_waypoints
from geometry import add, dist, scale, unit
from mock_sim import MockSim, Source
from policy import HuntPolicy
from robot_client import FnTransport, RobotClient
from runner_q3 import run_q3


class TestCandidate(unittest.TestCase):
    def test_along_bearing_not_in_region(self):
        s1 = (0.0, 0.0)
        th = 30.0
        p = add(s1, scale(unit(th), 800.0))
        self.assertFalse(in_candidate_region(s1, th, p))

    def test_side_point_in_region_and_angle(self):
        s1 = (0.0, 0.0)
        th = 0.0
        g = (900.0, 0.0)
        s2 = recommend_second(s1, th, now=s1)
        self.assertLessEqual(dist(s2, (0.0, 0.0)), ARENA_R)
        self.assertTrue(in_candidate_region(s1, th, s2))
        ang = intersection_angle_deg(s1, s2, g)
        self.assertGreaterEqual(ang, 60.0)
        self.assertLessEqual(ang, 120.0)
        x, y = to_body(s1, th, s2)
        self.assertGreaterEqual(abs(y), 400.0)


class TestCoverage(unittest.TestCase):
    def test_omni_cover_worst_radius(self):
        wps = omni_waypoints()
        self.assertEqual(wps[0], (0.0, 0.0))
        self.assertEqual(len(wps), 9)
        self.assertTrue(coverage_ok(wps))


def _random_omni(n: int, rng: random.Random) -> list[Source]:
    chs = rng.sample(range(1, 21), n)
    out = []
    for ch in chs:
        r = math.sqrt(rng.random()) * 1700.0
        a = rng.random() * 2.0 * math.pi
        xy = (r * math.cos(a), r * math.sin(a))
        reff = rng.uniform(1000.0, 1500.0)
        out.append(Source(channel=ch, xy=xy, r_eff=reff))
    return out


class TestQ3Mock(unittest.TestCase):
    def test_clear_all_seeds(self):
        for seed, n in ((0, 10), (1, 12), (2, 16)):
            rng = random.Random(seed)
            sources = _random_omni(n, rng)
            sim = MockSim(robot_id="team-test", sources=sources)
            bot = RobotClient(robot_id="team-test", transport=FnTransport(sim.handle))
            stats = run_q3(bot)
            self.assertEqual(
                stats["cleared"],
                n,
                msg=f"seed={seed} n={n} cleared={stats['cleared']} ch={stats['channels']}",
            )
            self.assertGreater(len(bot.log), 4)


class _NoCreepPolicy(HuntPolicy):
    def __init__(self, bot) -> None:
        super().__init__(bot, directional=False)
        self.creep_attempts = 0

    def _creep_clear(self, ch, start, th):
        self.creep_attempts += 1
        return False


class _ExactBearingBot:
    def __init__(self, target):
        self.target = target
        self.position = (0.0, 0.0)
        self.measure_points = []
        self.clear_points = []

    def measure(self, x, y, channel):
        self.position = (x, y)
        self.measure_points.append((x, y))
        if dist((x, y), self.target) <= 5.0:
            return {"accepted": True, "measure_result": "near"}
        bearing = math.degrees(
            math.atan2(self.target[1] - y, self.target[0] - x)
        ) % 360.0
        return {
            "accepted": True,
            "measure_result": "direction",
            "svd_deg": round(bearing, 2),
        }

    def clear(self, x, y, channel):
        self.position = (x, y)
        self.clear_points.append((x, y))
        result = "success" if dist((x, y), self.target) <= 20.0 else "no_target_in_range"
        return {"accepted": True, "clear_result": result}


class TestTriangulationFirst(unittest.TestCase):
    def test_second_bearing_is_fused_before_creep(self):
        bot = _ExactBearingBot((800.0, 0.0))
        policy = _NoCreepPolicy(bot)
        policy.book.add_direction(3, (0.0, 0.0), 0.0)

        policy._localize_and_clear(3)

        self.assertIn(3, policy.book.cleared)
        self.assertEqual(policy.creep_attempts, 0)
        self.assertEqual(len(bot.measure_points), 1)
        self.assertEqual(len(bot.clear_points), 1)


class _AlwaysDirectionBot:
    def __init__(self):
        self.position = (0.0, 0.0)
        self.clear_calls = 0

    def measure(self, x, y, channel):
        self.position = (x, y)
        return {"accepted": True, "measure_result": "direction", "svd_deg": 0.0}

    def clear(self, x, y, channel):
        self.position = (x, y)
        self.clear_calls += 1
        return {"accepted": True, "clear_result": "no_target_in_range"}


class TestBoundedFallback(unittest.TestCase):
    def test_creep_fallback_runs_at_most_once_per_channel(self):
        bot = _AlwaysDirectionBot()
        policy = HuntPolicy(bot, directional=False)
        policy.book.add_direction(7, (0.0, 0.0), 0.0)

        policy._localize_and_clear(7)
        calls_after_first = policy.creep_calls
        steps_after_first = policy.creep_steps
        policy._home_and_clear(7)

        self.assertEqual(calls_after_first, 1)
        self.assertLessEqual(steps_after_first, 40)
        self.assertEqual(policy.creep_calls, calls_after_first)
        self.assertEqual(policy.creep_steps, steps_after_first)


if __name__ == "__main__":
    unittest.main()
