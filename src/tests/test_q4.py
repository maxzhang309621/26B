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
    no_skip_open_path_channel_order,
    pick_q4_outer_ring,
    q4_hex_listen_set,
    q4_listen_set,
    q4_opt_inner_r,
    q4_opt_search_waypoints,
    sector_fused_order,
)
from candidate import recommend_second_sides_compact
from geometry import dist
from mock_sim import MockSim, Source
from robot_client import FnTransport, RobotClient
from runner_q4 import run_q4, run_q4_hexbatch, run_q4_pathopt, run_q4_v2
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

    def test_sector_fused_order_interleaves_radii(self):
        fused = sector_fused_order(q4_listen_set())
        _origin, inner_wps, outer_wps = covering_phases(q4_listen_set())
        seen_inner: set[tuple[float, float]] = set()
        interleaved = False
        for p in fused:
            if any(dist(p, w) < 8.0 for w in outer_wps):
                if len(seen_inner) < len(inner_wps):
                    interleaved = True
                    break
            else:
                for w in inner_wps:
                    if dist(p, w) < 8.0:
                        seen_inner.add((round(w[0], 6), round(w[1], 6)))
        self.assertTrue(interleaved)
        path = open_path_order((0.0, 0.0), fused[:13])
        self.assertEqual(len(path), 13)

    def test_pathopt_interleaves_inner_outer(self):
        rng = random.Random(11)
        sources = _mix_sources(12, 12, rng)
        sim = MockSim(robot_id="team-test", sources=sources)
        bot = RobotClient(robot_id="team-test", transport=FnTransport(sim.handle))
        stats = run_q4_pathopt(bot)
        self.assertEqual(stats["cleared"], 12, msg=stats)
        _origin, inner_wps, outer_wps = covering_phases(directional_waypoints())
        seen_inner: set[tuple[float, float]] = set()
        seen_outer_before_inner_done = False
        for rec in bot.log:
            if rec.get("path") != "/measure":
                continue
            body = rec.get("response") or {}
            if body.get("accepted") is not True:
                continue
            p = rec["request"]["position"]
            xy = (p["x"], p["y"])
            if any(dist(xy, w) < 8.0 for w in outer_wps):
                if len(seen_inner) < len(inner_wps):
                    seen_outer_before_inner_done = True
                    break
            else:
                for w in inner_wps:
                    if dist(xy, w) < 8.0:
                        seen_inner.add((round(w[0], 6), round(w[1], 6)))
        self.assertTrue(seen_outer_before_inner_done)

    def test_pathopt_clears_during_cover(self):
        rng = random.Random(5)
        sources = _mix_sources(14, 4, rng)
        sim = MockSim(robot_id="team-test", sources=sources)
        bot = RobotClient(robot_id="team-test", transport=FnTransport(sim.handle))
        stats = run_q4_pathopt(bot)
        self.assertEqual(stats["cleared"], 14)
        cover = q4_listen_set()
        last_cover_i = -1
        first_off_clear_i = None
        for i, rec in enumerate(bot.log):
            path = rec.get("path")
            if path not in ("/measure", "/clear"):
                continue
            body = rec.get("response") or {}
            if body.get("accepted") is not True:
                continue
            req = rec.get("request") or {}
            p = req.get("position")
            if not p:
                continue
            xy = (p["x"], p["y"])
            if path == "/measure" and any(dist(xy, w) < 8.0 for w in cover):
                last_cover_i = i
            elif path == "/clear" and body.get("clear_result") == "success":
                if all(dist(xy, w) > 80.0 for w in cover) and first_off_clear_i is None:
                    first_off_clear_i = i
        if first_off_clear_i is not None and last_cover_i >= 0:
            self.assertLess(first_off_clear_i, last_cover_i)

    def test_pathopt_drains_pending_during_cover(self):
        class _Bot:
            position = (0.0, 0.0)
            virtual_time_s = 0.0
            log: list = []

            def measure(self, x, y, channel):
                self.position = (x, y)
                return {"accepted": True, "measure_result": "direction", "svd_deg": 180.0}

            def clear(self, x, y, channel):
                self.position = (x, y)
                return {"accepted": True, "clear_result": "success"}

        policy = HuntPolicy(_Bot(), directional=True, q4_path_profile="pathopt")
        policy._cover_phase = True
        policy._pathopt_rejoin = (2100.0, 0.0)
        policy.book.add_direction(1, (1800.0, 0.0), 180.0)
        policy._drain_pending()
        self.assertNotIn(1, policy.book.pending())

    def test_pathopt_benchmark_seed0_full_clear(self):
        from q4_benchmark import _mix_sources as mix_seed

        sources = mix_seed(0)
        sim = MockSim(robot_id="team-test", sources=sources)
        bot = RobotClient(robot_id="team-test", transport=FnTransport(sim.handle))
        stats = run_q4_pathopt(bot)
        self.assertEqual(stats["cleared"], len(sources), msg=stats)

    def test_hexbatch_uses_opt_search_rings(self):
        policy = HuntPolicy(_BotHex(), directional=True, q4_path_profile="hexbatch")
        opt = q4_opt_search_waypoints()
        self.assertEqual(policy.waypoints, opt)
        self.assertEqual(policy.q4_path_profile, "hexbatch")
        self.assertEqual(len(opt), 1 + 7 + 12)
        self.assertNotEqual(policy.waypoints[:9], omni_waypoints())

    def test_hexbatch_does_not_change_vnofar_default(self):
        policy = HuntPolicy(_BotHex(), directional=True)
        self.assertEqual(policy.q4_path_profile, "v_nofar")
        self.assertEqual(policy.waypoints[:9], omni_waypoints())

    def test_hexbatch_near_center_outward(self):
        src = [
            Source(channel=4, xy=(130.0, 40.0), r_eff=1000.0, heading_deg=17.0),
            Source(channel=9, xy=(1400.0, -200.0), r_eff=1100.0, heading_deg=None),
        ]
        sim = MockSim(robot_id="team-test", sources=src)
        bot = RobotClient(robot_id="team-test", transport=FnTransport(sim.handle))
        stats = run_q4_hexbatch(bot)
        self.assertEqual(stats["cleared"], 2, msg=stats)
        self.assertEqual(stats["q4_path_profile"], "hexbatch")
        self.assertEqual(stats["q4_inner_n"], 7)
        self.assertAlmostEqual(stats["q4_inner_r"], q4_opt_inner_r(), places=6)
        self.assertEqual(stats["q4_outer_n"], 12)
        self.assertAlmostEqual(stats["q4_outer_r"], 1865.0, places=6)

    def test_practice_run_hunt_uses_hexbatch(self):
        from drill_io import run_hunt

        src = [
            Source(channel=4, xy=(130.0, 40.0), r_eff=1000.0, heading_deg=17.0),
            Source(channel=9, xy=(1400.0, -200.0), r_eff=1100.0, heading_deg=None),
        ]
        sim = MockSim(robot_id="team-test", sources=src)
        bot = RobotClient(robot_id="team-test", transport=FnTransport(sim.handle))
        enter = bot.enter()
        self.assertTrue(enter.get("accepted"))
        stats = run_hunt("4", bot)
        self.assertEqual(stats["cleared"], 2, msg=stats)
        self.assertEqual(stats["q4_path_profile"], "hexbatch")
        self.assertEqual(stats["q4_inner_n"], 7)
        self.assertAlmostEqual(stats["q4_inner_r"], q4_opt_inner_r(), places=6)
        self.assertEqual(stats["q4_outer_n"], 12)
        self.assertAlmostEqual(stats["q4_outer_r"], 1865.0, places=6)
        self.assertGreaterEqual(stats["q4_rh_replans"], 1)

    def test_hexbatch_mixed_full_clear(self):
        for seed, n, nd in ((3, 12, 4), (5, 16, 8), (11, 12, 12)):
            rng = random.Random(seed)
            sources = _mix_sources(n, nd, rng)
            sim = MockSim(robot_id="team-test", sources=sources)
            bot = RobotClient(robot_id="team-test", transport=FnTransport(sim.handle))
            stats = run_q4_hexbatch(bot)
            self.assertEqual(stats["cleared"], n, msg=f"seed={seed} {stats}")
            self.assertEqual(stats["q4_path_profile"], "hexbatch")
            move = stats["move_decomposition"]
            self.assertAlmostEqual(
                move["backbone_scan_s"] + move["localization_s"] + move["clear_detour_s"],
                stats["travel_s"],
                places=5,
            )

    def test_hexbatch_searches_before_offpath_clear(self):
        rng = random.Random(5)
        sources = _mix_sources(14, 4, rng)
        sim = MockSim(robot_id="team-test", sources=sources)
        bot = RobotClient(robot_id="team-test", transport=FnTransport(sim.handle))
        stats = run_q4_hexbatch(bot)
        self.assertEqual(stats["cleared"], 14)
        cover = q4_hex_listen_set()
        last_cover_i = -1
        first_off_clear_i = None
        for i, rec in enumerate(bot.log):
            path = rec.get("path")
            if path not in ("/measure", "/clear"):
                continue
            body = rec.get("response") or {}
            if body.get("accepted") is not True:
                continue
            req = rec.get("request") or {}
            p = req.get("position")
            if not p:
                continue
            xy = (p["x"], p["y"])
            if path == "/measure" and any(dist(xy, w) < 8.0 for w in cover):
                last_cover_i = i
            elif path == "/clear" and body.get("clear_result") == "success":
                if all(dist(xy, w) > 80.0 for w in cover) and first_off_clear_i is None:
                    first_off_clear_i = i
        if first_off_clear_i is not None and last_cover_i >= 0:
            self.assertLess(last_cover_i, first_off_clear_i)

    def test_hexbatch_skips_drain_during_cover(self):
        policy = HuntPolicy(_BotHex(), directional=True, q4_path_profile="hexbatch")
        policy._cover_phase = True
        policy.book.add_direction(1, (1800.0, 0.0), 180.0)
        policy._drain_pending()
        self.assertIn(1, policy.book.pending())

    def test_hexbatch_benchmark_seed0_full_clear(self):
        from q4_benchmark import _mix_sources as mix_seed

        sources = mix_seed(0)
        sim = MockSim(robot_id="team-test", sources=sources)
        bot = RobotClient(robot_id="team-test", transport=FnTransport(sim.handle))
        stats = run_q4_hexbatch(bot)
        self.assertEqual(stats["cleared"], len(sources), msg=stats)
        self.assertGreaterEqual(stats["q4_rh_replans"], 1)

    def test_hexbatch_outer_adjacent_directional_full_clear(self):
        from q4_benchmark import _mix_sources as mix_seed

        sources = mix_seed(1)
        sim = MockSim(robot_id="team-test", sources=sources)
        bot = RobotClient(robot_id="team-test", transport=FnTransport(sim.handle))
        stats = run_q4_hexbatch(bot)
        self.assertEqual(stats["cleared"], len(sources), msg=stats)


    def test_no_skip_open_path_clears_near_before_far(self):
        start = (1800.0, 0.0)
        pts = {
            1: (1500.0, 80.0),
            2: (-900.0, 0.0),
            3: (-900.0, 400.0),
            4: (-850.0, -350.0),
        }
        order = no_skip_open_path_channel_order(start, pts, local_m=650.0)
        self.assertEqual(order[0], 1)
        self.assertLess(order.index(1), order.index(2))
        self.assertLess(order.index(1), order.index(3))
        self.assertLess(order.index(1), order.index(4))

    def test_hexbatch_pick_does_not_skip_nearest(self):
        bot = _BotHex()
        bot.position = (1800.0, 0.0)
        policy = HuntPolicy(bot, directional=True, q4_path_profile="hexbatch")
        policy.book.add_direction(1, (1800.0, 0.0), 180.0)
        policy.book.add_direction(2, (-1500.0, 400.0), 0.0)
        policy.book.add_direction(3, (-1500.0, -400.0), 0.0)
        self.assertEqual(policy._rh_pick_channel(None), 1)

    def test_hexbatch_one_obs_proxy_is_along_bearing(self):
        policy = HuntPolicy(_BotHex(), directional=True, q4_path_profile="hexbatch")
        s1 = (1000.0, 0.0)
        policy.book.add_direction(4, s1, 180.0)
        proxy = policy._estimated_service_point(4)
        self.assertLess(abs(proxy[1]), 80.0)
        self.assertLess(proxy[0], s1[0] - 100.0)
        sides = recommend_second_sides_compact(s1, 180.0)
        self.assertTrue(all(dist(proxy, p) > 200.0 for p in sides))

    def test_hexbatch_second_fix_uses_one_side(self):
        bot = _RecordingBot()
        policy = HuntPolicy(bot, directional=True, q4_path_profile="hexbatch")
        s1 = (1000.0, 0.0)
        policy.book.add_direction(4, s1, 180.0)
        bot.position = (1865.0, 0.0)
        policy._take_second_fix(4, s1, 180.0)
        self.assertLessEqual(len(bot.measured), 2)
        lateral = [y for (_x, y, _ch) in bot.measured if abs(y) > 200.0]
        self.assertLessEqual(len(lateral), 1)

    def test_hexbatch_seed3_travel_not_folded(self):
        rng = random.Random(3)
        sources = _mix_sources(12, 6, rng)
        sim = MockSim(robot_id="team-test", sources=sources)
        bot = RobotClient(robot_id="team-test", transport=FnTransport(sim.handle))
        stats = run_q4_hexbatch(bot)
        self.assertEqual(stats["cleared"], 12, msg=stats)
        self.assertLess(stats["travel_s"], 6100.0)
        self.assertLess(stats["move_decomposition"]["localization_s"], 2100.0)


class _BotHex:
    position = (0.0, 0.0)
    virtual_time_s = 0.0
    log: list = []

    def measure(self, x, y, channel):
        self.position = (x, y)
        return {"accepted": True, "measure_result": "direction", "svd_deg": 180.0}

    def clear(self, x, y, channel):
        self.position = (x, y)
        return {"accepted": True, "clear_result": "success"}


class _RecordingBot:
    def __init__(self) -> None:
        self.position = (0.0, 0.0)
        self.virtual_time_s = 0.0
        self.log: list = []
        self.measured: list[tuple[float, float, int]] = []

    def measure(self, x, y, channel):
        self.position = (x, y)
        self.measured.append((x, y, channel))
        return {"accepted": True, "measure_result": "no_signal"}

    def clear(self, x, y, channel):
        self.position = (x, y)
        return {"accepted": True, "clear_result": "no_target_in_range"}


if __name__ == "__main__":
    unittest.main()
