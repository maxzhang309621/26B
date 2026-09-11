import math
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from belief import ChannelBook
from coverage import (
    Q4_OUTER_FULL_N,
    Q4_OUTER_FULL_R,
    Q4_OUTER_LITE_N,
    Q4_OUTER_LITE_R,
    coverage_ok,
    covering_phases,
    directional_front_cover_ok,
    directional_waypoints,
    omni_waypoints,
    pick_q4_outer_ring,
    q4_spiral_waypoints,
)
from geometry import dist
from mock_sim import MockSim, Source
from robot_client import FnTransport, RobotClient
from runner_q4 import run_q4, run_q4_bounce, run_q4_spiral, run_q4_v2


def _mix_sources(n: int, n_dir: int, rng: random.Random) -> list[Source]:
    chs = rng.sample(range(1, 21), n)
    out = []
    for i, ch in enumerate(chs):
        r = 400.0 + math.sqrt(rng.random()) * 1300.0
        a = rng.random() * 2.0 * math.pi
        xy = (r * math.cos(a), r * math.sin(a))
        reff = rng.uniform(1000.0, 1500.0)
        heading = None
        if i < n_dir:
            # outward
            heading = math.degrees(a)
        out.append(Source(channel=ch, xy=xy, r_eff=reff, heading_deg=heading))
    return out


class TestQ4Mock(unittest.TestCase):
    def test_outward_and_omni(self):
        cases = (
            (3, 12, 4),
            (4, 10, 6),
            (0, 12, 6),
            (5, 16, 8),
            (7, 16, 14),
            (8, 14, 10),
            (9, 16, 8),
            (11, 12, 12),
        )
        for seed, n, nd in cases:
            rng = random.Random(seed)
            sources = _mix_sources(n, nd, rng)
            sim = MockSim(robot_id="team-test", sources=sources)
            bot = RobotClient(robot_id="team-test", transport=FnTransport(sim.handle))
            stats = run_q4(bot)
            self.assertEqual(
                stats["cleared"],
                n,
                msg=f"seed={seed} n={n} nd={nd} cleared={stats['cleared']} {stats['channels']}",
            )
            self.assertIn("travel_s", stats)
            self.assertIn("detect_s", stats)
            self.assertIn("clear_miss", stats)

    def test_cover_inner_before_outer(self):
        rng = random.Random(3)
        sources = _mix_sources(12, 4, rng)
        sim = MockSim(robot_id="team-test", sources=sources)
        bot = RobotClient(robot_id="team-test", transport=FnTransport(sim.handle))
        stats = run_q4(bot)
        self.assertEqual(stats["cleared"], 12)
        origin, inner_wps, outer_wps = covering_phases(directional_waypoints())
        seen_outer = False
        for rec in bot.log:
            if rec.get("path") != "/measure":
                continue
            body = rec.get("response") or {}
            if body.get("accepted") is not True:
                continue
            p = rec["request"]["position"]
            xy = (p["x"], p["y"])
            on_outer = any(dist(xy, w) < 8.0 for w in outer_wps)
            on_inner = any(dist(xy, w) < 8.0 for w in inner_wps)
            if on_outer:
                seen_outer = True
            elif on_inner and seen_outer:
                self.fail("inner-ring covering scan after outer ring started")

    def test_pick_q4_outer_ring(self):
        self.assertEqual(
            pick_q4_outer_ring(12, 4),
            (Q4_OUTER_FULL_R, Q4_OUTER_FULL_N),
        )
        self.assertEqual(
            pick_q4_outer_ring(16, 0),
            (Q4_OUTER_LITE_R, 0),
        )
        self.assertEqual(
            pick_q4_outer_ring(2, 7),
            (Q4_OUTER_FULL_R, Q4_OUTER_FULL_N),
        )
        self.assertEqual(
            pick_q4_outer_ring(2, 10),
            (Q4_OUTER_FULL_R, Q4_OUTER_FULL_N),
        )
        self.assertEqual(
            pick_q4_outer_ring(None, None),
            (Q4_OUTER_FULL_R, Q4_OUTER_FULL_N),
        )

    def test_v_nofar_fixed_outer(self):
        sources = _mix_sources(14, 4, random.Random(5))
        sim = MockSim(robot_id="team-test", sources=sources)
        bot = RobotClient(robot_id="team-test", transport=FnTransport(sim.handle))
        stats = run_q4(bot)
        self.assertEqual(stats["cleared"], 14)
        self.assertEqual(stats["q4_outer_n"], Q4_OUTER_FULL_N)
        self.assertEqual(stats["q4_outer_r"], Q4_OUTER_FULL_R)
        self.assertEqual(Q4_OUTER_FULL_R, 1865.0)

    def test_dynamic_outer_from_enter(self):
        sources = _mix_sources(14, 4, random.Random(5))
        sim = MockSim(robot_id="team-test", sources=sources)
        bot = RobotClient(robot_id="team-test", transport=FnTransport(sim.handle))
        stats = run_q4_v2(bot, q4_omni_n=10, q4_dir_n=4)
        self.assertEqual(stats["cleared"], 14)
        self.assertEqual(stats["q4_outer_n"], Q4_OUTER_FULL_N)

    def test_certificate_route_geometry(self):
        from coverage import Q4_INNER_N, Q4_INNER_R, directional_certificate

        pts = directional_waypoints()
        self.assertEqual(len(pts), 1 + Q4_INNER_N + Q4_OUTER_FULL_N)
        self.assertEqual(pts[0], (0.0, 0.0))
        origin, inner, outer = covering_phases(pts)
        self.assertEqual(len(inner), Q4_INNER_N)
        self.assertEqual(len(outer), Q4_OUTER_FULL_N)
        self.assertTrue(all(abs(dist(p, (0.0, 0.0)) - Q4_INNER_R) < 1e-6 for p in inner))
        self.assertTrue(all(abs(dist(p, (0.0, 0.0)) - Q4_OUTER_FULL_R) < 1e-6 for p in outer))
        self.assertTrue(directional_front_cover_ok(pts, include_ring_enroute=False))
        cert = directional_certificate()
        self.assertTrue(cert["ok"], msg=cert)
        self.assertGreaterEqual(cert["leaves"], 5000)

    def test_near_center_outward(self):
        src = [
            Source(channel=4, xy=(130.0, 40.0), r_eff=1000.0, heading_deg=17.0),
            Source(channel=9, xy=(1400.0, -200.0), r_eff=1100.0, heading_deg=None),
        ]
        sim = MockSim(robot_id="team-test", sources=src)
        bot = RobotClient(robot_id="team-test", transport=FnTransport(sim.handle))
        stats = run_q4(bot)
        self.assertEqual(stats["cleared"], 2, msg=stats)


class TestQ4Spiral(unittest.TestCase):
    def test_spiral_certificates(self):
        pts = list(q4_spiral_waypoints())
        self.assertGreaterEqual(len(pts), 20)
        self.assertEqual(pts[0], (0.0, 0.0))
        self.assertTrue(coverage_ok(pts))
        # Spiral is experimental; hull certificate is for the 21-point ring route.
        self.assertNotEqual(pts, directional_waypoints())

    def test_spiral_mock_clears(self):
        for seed, n, nd in ((3, 12, 4), (5, 14, 4), (8, 14, 10)):
            rng = random.Random(seed)
            sources = _mix_sources(n, nd, rng)
            sim = MockSim(robot_id="team-test", sources=sources)
            bot = RobotClient(robot_id="team-test", transport=FnTransport(sim.handle))
            stats = run_q4_spiral(bot)
            self.assertEqual(
                stats["cleared"],
                n,
                msg=f"seed={seed} n={n} nd={nd} cleared={stats['cleared']}",
            )
            self.assertEqual(stats["q4_route"], "spiral")

    def test_run_q4_stays_rings(self):
        sources = _mix_sources(12, 4, random.Random(3))
        sim = MockSim(robot_id="team-test", sources=sources)
        bot = RobotClient(robot_id="team-test", transport=FnTransport(sim.handle))
        stats = run_q4(bot)
        self.assertEqual(stats["q4_route"], "rings")
        self.assertEqual(stats["cleared"], 12)


class TestQ4Bounce(unittest.TestCase):
    def test_bounce_uses_same_cover_set(self):
        from coverage import q4_bounce_waypoints

        bounce = q4_bounce_waypoints()
        rings = directional_waypoints()
        self.assertEqual(bounce[0], (0.0, 0.0))
        self.assertEqual(len(bounce), len(rings))
        self.assertNotEqual(bounce, rings)

    def test_bounce_mock_clears(self):
        for seed, n, nd in ((3, 12, 4), (5, 14, 4), (8, 14, 10)):
            sources = _mix_sources(n, nd, random.Random(seed))
            sim = MockSim(robot_id="team-test", sources=sources)
            bot = RobotClient(robot_id="team-test", transport=FnTransport(sim.handle))
            stats = run_q4_bounce(bot)
            self.assertEqual(stats["cleared"], n, msg=f"seed={seed}")
            self.assertEqual(stats["q4_route"], "bounce")

    def test_practice_hunt_wires_rings(self):
        import inspect

        from drill_io import run_hunt

        src = inspect.getsource(run_hunt)
        self.assertIn("run_q4", src)
        self.assertNotIn("run_q4_bounce", src)


if __name__ == "__main__":
    unittest.main()
