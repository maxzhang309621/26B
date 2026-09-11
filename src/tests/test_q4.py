import math
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from belief import ChannelBook
from coverage import covering_phases, directional_waypoints, omni_waypoints
from geometry import dist
from mock_sim import MockSim, Source
from robot_client import FnTransport, RobotClient
from runner_q4 import run_q4


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

    def test_near_center_outward(self):
        src = [
            Source(channel=4, xy=(130.0, 40.0), r_eff=1000.0, heading_deg=17.0),
            Source(channel=9, xy=(1400.0, -200.0), r_eff=1100.0, heading_deg=None),
        ]
        sim = MockSim(robot_id="team-test", sources=src)
        bot = RobotClient(robot_id="team-test", transport=FnTransport(sim.handle))
        stats = run_q4(bot)
        self.assertEqual(stats["cleared"], 2, msg=stats)


if __name__ == "__main__":
    unittest.main()
