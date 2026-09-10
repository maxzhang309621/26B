import math
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

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
        for seed, n, nd in ((3, 12, 4), (4, 10, 6), (0, 12, 6), (5, 16, 8)):
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


if __name__ == "__main__":
    unittest.main()
