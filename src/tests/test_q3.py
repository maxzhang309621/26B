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
from coverage import coverage_ok, omni_waypoints, q3_waypoints, open_path_channel_order, open_path_cost
from geometry import add, dist, scale, unit
from mock_sim import MockSim, Source
from policy import HuntPolicy
from robot_client import FnTransport, RobotClient
from runner_q3 import run_q3, run_q3_batch


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

    def test_batch_clear_all_seeds(self):
        for seed, n in ((0, 10), (1, 12), (2, 16)):
            rng = random.Random(seed)
            sources = _random_omni(n, rng)
            sim = MockSim(robot_id="team-test", sources=sources)
            bot = RobotClient(robot_id="team-test", transport=FnTransport(sim.handle))
            stats = run_q3_batch(bot)
            self.assertEqual(stats["cleared"], n, msg=f"seed={seed} {stats}")
            self.assertEqual(stats["q3_path_profile"], "batch")
            self.assertEqual(stats["q3_ring_n"], 6)
            self.assertAlmostEqual(stats["q3_ring_r"], 1150.0, places=6)

    def test_batch_uses_hexagon_cover(self):
        bot = _MoveBot()
        policy = HuntPolicy(bot, directional=False, q3_path_profile="batch")
        self.assertEqual(policy.waypoints, q3_waypoints())
        self.assertEqual(len(policy.waypoints), 7)

    def test_batch_searches_ring_before_offpath_clear(self):
        rng = random.Random(1)
        sources = _random_omni(12, rng)
        sim = MockSim(robot_id="team-test", sources=sources)
        bot = RobotClient(robot_id="team-test", transport=FnTransport(sim.handle))
        stats = run_q3_batch(bot)
        self.assertEqual(stats["cleared"], 12)
        cover = q3_waypoints()
        last_cover_i = -1
        first_off_clear_i = None
        for i, rec in enumerate(bot.log):
            path = rec.get("path")
            if path not in ("/measure", "/clear"):
                continue
            body = rec.get("response") or {}
            if body.get("accepted") is not True:
                continue
            pos = (rec.get("request") or {}).get("position")
            if not pos:
                continue
            xy = (pos["x"], pos["y"])
            if path == "/measure" and any(dist(xy, w) < 8.0 for w in cover):
                last_cover_i = i
            elif path == "/clear" and body.get("clear_result") == "success":
                if all(dist(xy, w) > 80.0 for w in cover) and first_off_clear_i is None:
                    first_off_clear_i = i
        if first_off_clear_i is not None:
            self.assertLess(last_cover_i, first_off_clear_i)


class _MoveBot:
    def __init__(self, xy=(0.0, 0.0)):
        self.position = xy
        self.virtual_time_s = 0.0
        self.log = []
        self.measures = []

    def measure(self, x, y, channel):
        self.position = (x, y)
        self.measures.append((channel, (x, y)))
        return {"accepted": True, "measure_result": "direction", "svd_deg": 0.0}

    def clear(self, x, y, channel):
        self.position = (x, y)
        return {"accepted": True, "clear_result": "miss"}


class TestRecedingHorizonClear(unittest.TestCase):
    def test_open_path_channel_order_starts_at_near_city(self):
        order = open_path_channel_order(
            (0.0, 0.0),
            {1: (1000.0, 0.0), 2: (80.0, 0.0), 3: (80.0, 900.0)},
        )
        self.assertEqual(order[0], 2)
        self.assertEqual(set(order), {1, 2, 3})
        self.assertGreater(
            open_path_cost((0.0, 0.0), [(1000.0, 0.0), (80.0, 0.0), (80.0, 900.0)]),
            open_path_cost((0.0, 0.0), [(80.0, 0.0), (80.0, 900.0), (1000.0, 0.0)]),
        )

    def test_rh_pick_uses_open_tsp_from_current_pose(self):
        bot = _MoveBot((0.0, 0.0))
        policy = HuntPolicy(bot, directional=False, q3_path_profile="batch")
        pts = {1: (1000.0, 0.0), 2: (90.0, 0.0), 3: (90.0, 850.0)}
        for ch in pts:
            policy.book.add_direction(ch, (0.0, 0.0), 0.0)
        policy._estimated_service_point = lambda ch: pts[ch]
        self.assertEqual(policy._rh_pick_channel(None), 2)

    def test_rh_service_step_truncates_long_second_look(self):
        bot = _MoveBot((0.0, 0.0))
        policy = HuntPolicy(bot, directional=False, q3_path_profile="batch")
        policy.book.add_direction(4, (0.0, 0.0), 0.0)
        policy._estimated_service_point = lambda ch: (900.0, 0.0)
        policy._rh_service_step(4)
        gap = dist(bot.position, (0.0, 0.0))
        self.assertGreater(gap, 100.0)
        self.assertLess(gap, 400.0)
        self.assertEqual(bot.measures[0][0], 4)

    def test_batch_rh_replans_more_than_source_count(self):
        rng = random.Random(1)
        sources = _random_omni(12, rng)
        sim = MockSim(robot_id="team-test", sources=sources)
        bot = RobotClient(robot_id="team-test", transport=FnTransport(sim.handle))
        stats = run_q3_batch(bot)
        self.assertEqual(stats["cleared"], 12)
        self.assertGreaterEqual(stats["q3_rh_replans"], 12)
        self.assertGreaterEqual(stats["q3_rh_steps"], 12)


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
