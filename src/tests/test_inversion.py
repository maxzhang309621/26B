import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from geometry import dist
from inversion import invert_channel, truth_in_cones
from log_parse import parse_action_log, parse_drill_file
from mock_sim import MockSim, Source
from robot_client import FnTransport, RobotClient
from runner_q3 import run_q3
from validation import bearing_residuals_deg, summarize_truth, validate_consistency, validate_with_truth


def _random_omni(n: int, rng):
    chs = rng.sample(range(1, 21), n)
    out = []
    for ch in chs:
        r = math.sqrt(rng.random()) * 1700.0
        a = rng.random() * 2.0 * math.pi
        xy = (r * math.cos(a), r * math.sin(a))
        reff = rng.uniform(1000.0, 1500.0)
        out.append(Source(channel=ch, xy=xy, r_eff=reff))
    return out


def _measure(ch, x, y, svd, accepted=True):
    return {
        "path": "/measure",
        "request": {"channel": ch, "position": {"x": x, "y": y}},
        "response": {
            "accepted": accepted,
            "measure_result": "direction",
            "svd_deg": svd,
        },
    }


class TestLogParse(unittest.TestCase):
    def test_two_station_extract_and_skip_rejected(self):
        log = [
            _measure(3, 0.0, 0.0, 45.0),
            _measure(3, 400.0, 0.0, 135.0, accepted=False),
            _measure(3, 400.0, 0.0, 120.12),
            {
                "path": "/measure",
                "request": {"channel": 3, "position": {"x": 10.0, "y": 10.0}},
                "response": {"accepted": True, "measure_result": "no_signal"},
            },
        ]
        obs = parse_action_log(log)[3]
        self.assertEqual(obs.stations, [(0.0, 0.0), (400.0, 0.0)])
        self.assertEqual(obs.bearings_deg, [45.0, 120.12])
        self.assertEqual(obs.silence, [(10.0, 10.0)])

    def test_empty_log(self):
        self.assertEqual(parse_action_log([]), {})

    def test_drill_file_wrapper(self):
        payload = {"log": [_measure(1, 0, 0, 10.0), _measure(1, 100, 0, 20.0)]}
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "d.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            grouped = parse_drill_file(path)
        self.assertEqual(len(grouped[1].stations), 2)

    def test_missing_drill_file(self):
        with self.assertRaises(FileNotFoundError):
            parse_drill_file(Path("no-such-drill-file.json"))


class TestInversion(unittest.TestCase):
    def test_zero_error_two_station_contains_truth(self):
        s1, s2 = (0.0, 0.0), (400.0, 0.0)
        g = (200.0, 300.0)
        th1 = math.degrees(math.atan2(g[1] - s1[1], g[0] - s1[0]))
        th2 = math.degrees(math.atan2(g[1] - s2[1], g[0] - s2[0]))
        from log_parse import ChannelObs

        obs = ChannelObs(channel=7, stations=[s1, s2], bearings_deg=[th1, th2])
        inv = invert_channel(obs)
        self.assertFalse(inv.region.empty)
        self.assertTrue(inv.region.bounded)
        self.assertTrue(truth_in_cones(obs.stations, obs.bearings_deg, g))
        self.assertIsNotNone(inv.point_est)
        self.assertLess(dist(inv.point_est, g), inv.region.diameter + 1e-6)
        met = validate_with_truth(inv, obs, g)
        self.assertTrue(met.inside_region)
        self.assertTrue(met.residuals_within_1deg)
        for r in met.residuals_deg:
            self.assertLessEqual(abs(r), 1e-9)

    def test_consistency_does_not_require_truth(self):
        from log_parse import ChannelObs

        s1, s2 = (0.0, 0.0), (400.0, 0.0)
        g = (200.0, 300.0)
        th1 = math.degrees(math.atan2(g[1] - s1[1], g[0] - s1[0]))
        th2 = math.degrees(math.atan2(g[1] - s2[1], g[0] - s2[0]))
        obs = ChannelObs(
            channel=2,
            stations=[s1, s2],
            bearings_deg=[th1, th2],
            clear_xy=[g],
            clear_ok=[True],
        )
        inv = invert_channel(obs)
        cons = validate_consistency(inv, obs)
        self.assertEqual(cons.mode, "consistency_only_not_accuracy")
        self.assertTrue(cons.clear_agree)
        self.assertFalse(cons.empty)


class TestResidualBand(unittest.TestCase):
    def test_plus_minus_one_degree(self):
        s = (0.0, 0.0)
        g = (100.0, 0.0)
        res = bearing_residuals_deg([s], [1.0], g)
        self.assertAlmostEqual(res[0], -1.0, places=9)


class TestMockContainment(unittest.TestCase):
    def test_q3_seed0_containment_rate_one(self):
        import random

        sources = _random_omni(10, random.Random(0))
        sim = MockSim(robot_id="team-test", sources=sources)
        bot = RobotClient(robot_id="team-test", transport=FnTransport(sim.handle))
        run_q3(bot)
        truth = {s.channel: s.xy for s in sources}
        grouped = parse_action_log(bot.log)
        rows = []
        for ch, obs in grouped.items():
            if ch not in truth or len(obs.stations) < 2:
                continue
            inv = invert_channel(obs)
            rows.append(validate_with_truth(inv, obs, truth[ch]))
        self.assertGreaterEqual(len(rows), 8)
        summary = summarize_truth(rows)
        self.assertEqual(summary.containment_rate, 1.0)
        self.assertEqual(summary.residual_1deg_rate, 1.0)


class TestSummarize(unittest.TestCase):
    def test_containment_rate_one(self):
        from validation import TruthMetrics

        row = TruthMetrics(
            channel=1,
            n_direction=2,
            inside_region=True,
            err_m=3.0,
            residuals_deg=[0.2, -0.1],
            residual_max_abs_deg=0.2,
            residuals_within_1deg=True,
            clear_ok_any=True,
            clear_dist_m=5.0,
            can_clear_20=False,
            sec_radius=30.0,
        )
        s = summarize_truth([row])
        self.assertEqual(s.containment_rate, 1.0)
        self.assertEqual(s.residual_1deg_rate, 1.0)


if __name__ == "__main__":
    unittest.main()
