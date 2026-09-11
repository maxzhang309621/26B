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
    covering_phases,
    directional_front_cover_ok,
    directional_waypoints,
    omni_waypoints,
    open_path_order,
    pick_q4_outer_ring,
    q4_listen_set,
    sector_fused_order,
)
from geometry import dist
from mock_sim import MockSim, Source
from robot_client import FnTransport, RobotClient
from runner_q4 import run_q4, run_q4_pathopt, run_q4_v2
from policy import HuntPolicy


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
            (Q4_OUTER_LITE_R, Q4_OUTER_LITE_N),
        )
        self.assertEqual(
            pick_q4_outer_ring(16, 0),
            (Q4_OUTER_LITE_R, 0),
        )
        self.assertEqual(
            pick_q4_outer_ring(2, 7),
            (Q4_OUTER_LITE_R, Q4_OUTER_LITE_N),
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

    def test_dynamic_outer_from_enter(self):
        sources = _mix_sources(14, 4, random.Random(5))
        sim = MockSim(robot_id="team-test", sources=sources)
        bot = RobotClient(robot_id="team-test", transport=FnTransport(sim.handle))
        stats = run_q4_v2(bot, q4_omni_n=10, q4_dir_n=4)
        self.assertEqual(stats["cleared"], 14)
        self.assertEqual(stats["q4_outer_n"], Q4_OUTER_LITE_N)

    def test_near_center_outward(self):
        src = [
            Source(channel=4, xy=(130.0, 40.0), r_eff=1000.0, heading_deg=17.0),
            Source(channel=9, xy=(1400.0, -200.0), r_eff=1100.0, heading_deg=None),
        ]
        sim = MockSim(robot_id="team-test", sources=src)
        bot = RobotClient(robot_id="team-test", transport=FnTransport(sim.handle))
        stats = run_q4(bot)
        self.assertEqual(stats["cleared"], 2, msg=stats)

    def test_cover_inner_before_outer_only_vnofar(self):
        rng = random.Random(3)
        sources = _mix_sources(12, 4, rng)
        sim = MockSim(robot_id="team-test", sources=sources)
        bot = RobotClient(robot_id="team-test", transport=FnTransport(sim.handle))
        stats = run_q4_pathopt(bot)
        self.assertEqual(stats["cleared"], 12)
        self.assertEqual(stats["q4_path_profile"], "pathopt")

    def test_pathopt_near_center_outward(self):
        src = [
            Source(channel=4, xy=(130.0, 40.0), r_eff=1000.0, heading_deg=17.0),
            Source(channel=9, xy=(1400.0, -200.0), r_eff=1100.0, heading_deg=None),
        ]
        sim = MockSim(robot_id="team-test", sources=src)
        bot = RobotClient(robot_id="team-test", transport=FnTransport(sim.handle))
        stats = run_q4_pathopt(bot)
        self.assertEqual(stats["cleared"], 2, msg=stats)

    def test_pathopt_mixed_full_clear(self):
        for seed, n, nd in ((3, 12, 4), (5, 16, 8), (11, 12, 12)):
            rng = random.Random(seed)
            sources = _mix_sources(n, nd, rng)
            sim = MockSim(robot_id="team-test", sources=sources)
            bot = RobotClient(robot_id="team-test", transport=FnTransport(sim.handle))
            stats = run_q4_pathopt(bot)
            self.assertEqual(stats["cleared"], n, msg=f"seed={seed} {stats}")
            move = stats["move_decomposition"]
            self.assertAlmostEqual(
                move["backbone_scan_s"] + move["localization_s"] + move["clear_detour_s"],
                stats["travel_s"],
                places=5,
            )

    def test_sector_fused_order_and_open_path(self):
        pts = q4_listen_set()
        fused = sector_fused_order(pts)
        self.assertTrue(all(dist(p, (0.0, 0.0)) > 1.0 for p in fused))
        self.assertEqual(len(fused), len({(round(p[0], 6), round(p[1], 6)) for p in fused}))
        path = open_path_order((0.0, 0.0), fused[:5])
        self.assertEqual(len(path), 5)
        self.assertEqual(set((round(p[0], 6), round(p[1], 6)) for p in path),
                         set((round(p[0], 6), round(p[1], 6)) for p in fused[:5]))

    def test_front_cover_ok_dense_flag(self):
        self.assertTrue(directional_front_cover_ok())
        coarse_fail = directional_front_cover_ok(dense=True, n_radial=8, n_ang=72, n_headings=24)
        self.assertIsInstance(coarse_fail, bool)

    def test_pathopt_defers_expensive_pending_during_cover(self):
        class _Bot:
            position = (0.0, 0.0)
            virtual_time_s = 0.0
            log: list = []

            def measure(self, x, y, channel):
                self.position = (x, y)
                return {"accepted": True, "measure_result": "direction", "svd_deg": 180.0}

            def clear(self, x, y, channel):
                return {"accepted": True, "clear_result": "no_target_in_range"}

        policy = HuntPolicy(_Bot(), directional=True, q4_path_profile="pathopt")
        policy._cover_phase = True
        policy._pathopt_rejoin = (2100.0, 0.0)
        policy.book.add_direction(1, (1800.0, 0.0), 180.0)
        policy.q4_insert_delta_max_m = 1.0
        before = list(policy.book.pending())
        policy._drain_pending()
        self.assertEqual(policy.book.pending(), before)


if __name__ == "__main__":
    unittest.main()
