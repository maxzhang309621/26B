import math
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from candidate import front_compatible
from dir_corrector import (
    HEAR_R_MAX,
    SILENCE_R,
    heading_feasible,
    heard_region,
    locate_quality_dir,
    next_station_dir,
)
from geometry import dist, locate_quality, point_in_convex_polygon
from mock_sim import MockSim, Source
from robot_client import FnTransport, RobotClient
from runner_q4 import run_q4


def _bearing(a, b):
    return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))


class TestDirCorrector(unittest.TestCase):
    def test_heading_feasible_true_source_after_one_hear(self):
        s1 = (0.0, 0.0)
        g = (800.0, 0.0)
        # Source faces the robot (west). Origin is in the front lobe.
        self.assertTrue(heading_feasible(g, [s1]))
        env = heard_region([s1], [_bearing(s1, g)], delta_deg=1.0)
        self.assertFalse(env.empty)
        self.assertTrue(point_in_convex_polygon(g, env.vertices))
        self.assertLessEqual(dist(g, s1), HEAR_R_MAX + 1e-6)

    def test_silence_behind_keeps_source_front_excludes(self):
        s1 = (0.0, 0.0)
        g = (800.0, 0.0)
        behind = (1100.0, 0.0)
        on_ray = (400.0, 0.0)
        self.assertTrue(heading_feasible(g, [s1], [behind]))
        self.assertFalse(heading_feasible(g, [s1], [on_ray]))
        far = (800.0, 1100.0)
        self.assertGreater(dist(g, far), SILENCE_R)
        self.assertTrue(heading_feasible(g, [s1], [far]))

    def test_two_station_contains_truth_and_sec_not_worse(self):
        s1 = (0.0, 0.0)
        s2 = (0.0, 600.0)
        g = (850.0, 0.0)
        th1 = _bearing(s1, g)
        th2 = _bearing(s2, g)
        base = locate_quality([s1, s2], [th1, th2], delta_deg=1.0)
        q, fallback = locate_quality_dir([s1, s2], [th1, th2], delta_deg=1.0, baseline=base)
        self.assertFalse(fallback)
        self.assertTrue(point_in_convex_polygon(g, q.region.vertices))
        self.assertLessEqual(q.sec_radius, base.sec_radius + 1e-6)

    def test_hear_beyond_1500_is_infeasible(self):
        s1 = (0.0, 0.0)
        far = (1600.0, 0.0)
        self.assertFalse(heading_feasible(far, [s1]))

    def test_next_station_not_behind_lobe(self):
        s1 = (0.0, 0.0)
        th = 0.0
        env = heard_region([s1], [th], delta_deg=1.0)
        p = next_station_dir(s1, th, now=s1, region_vertices=env.vertices)
        self.assertIsNotNone(p)
        self.assertTrue(front_compatible(s1, th, p))
        self.assertGreater(dist(p, s1), 5.0)

    def test_single_station_falls_back_to_problem1(self):
        s1 = (0.0, 0.0)
        _q, fallback = locate_quality_dir([s1], [0.0], delta_deg=1.0)
        self.assertTrue(fallback)

    def test_q3_locate_quality_signature_unchanged(self):
        s1 = (0.0, 0.0)
        s2 = (400.0, 0.0)
        g = (200.0, 300.0)
        q = locate_quality([s1, s2], [_bearing(s1, g), _bearing(s2, g)])
        self.assertTrue(hasattr(q, "can_clear_20"))
        self.assertFalse(q.region.empty)

    def test_q4_mock_seed_clears_with_corrector(self):
        rng = random.Random(3)
        n, nd = 12, 4
        chs = rng.sample(range(1, 21), n)
        sources = []
        for i, ch in enumerate(chs):
            r = 400.0 + math.sqrt(rng.random()) * 1300.0
            a = rng.random() * 2.0 * math.pi
            xy = (r * math.cos(a), r * math.sin(a))
            heading = math.degrees(a) if i < nd else None
            sources.append(
                Source(channel=ch, xy=xy, r_eff=rng.uniform(1000.0, 1500.0), heading_deg=heading)
            )
        sim = MockSim(robot_id="team-test", sources=sources)
        bot = RobotClient(robot_id="team-test", transport=FnTransport(sim.handle))
        stats = run_q4(bot, use_dir_corrector=True)
        self.assertEqual(stats["cleared"], n, msg=str(stats.get("channels")))
        self.assertTrue(stats["dir_corrector"])
        self.assertIn("corrector_fallback", stats)
        self.assertIn("corrector_used", stats)

    def test_q4_mock_switch_off_still_clears(self):
        rng = random.Random(3)
        n, nd = 12, 4
        chs = rng.sample(range(1, 21), n)
        sources = []
        for i, ch in enumerate(chs):
            r = 400.0 + math.sqrt(rng.random()) * 1300.0
            a = rng.random() * 2.0 * math.pi
            xy = (r * math.cos(a), r * math.sin(a))
            heading = math.degrees(a) if i < nd else None
            sources.append(
                Source(channel=ch, xy=xy, r_eff=rng.uniform(1000.0, 1500.0), heading_deg=heading)
            )
        sim = MockSim(robot_id="team-test", sources=sources)
        bot = RobotClient(robot_id="team-test", transport=FnTransport(sim.handle))
        stats = run_q4(bot, use_dir_corrector=False)
        self.assertEqual(stats["cleared"], n)
        self.assertFalse(stats["dir_corrector"])
        self.assertEqual(stats["corrector_used"], 0)


if __name__ == "__main__":
    unittest.main()
