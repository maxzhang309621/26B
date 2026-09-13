import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from coverage import (
    COVER_R,
    Q4_OPT_INNER_N,
    Q4_OPT_OUTER_N,
    Q4_OPT_OUTER_R,
    coverage_ok,
    q4_double_ring_cover_ok,
    q4_double_ring_search_time,
    q4_double_ring_waypoints,
    q4_opt_inner_r,
    q4_opt_search_waypoints,
    q4_outer_phase_rad,
    regular_ring_rho_interval,
    regular_ring_search_time,
)


class TestQ4DoubleRingGeometry(unittest.TestCase):
    def test_radial_shares_zero_ray_stagger_does_not(self):
        radial = q4_double_ring_waypoints(7, 1000.0, 12, 1865.0, align="radial", enroute_r=None)
        stagger = q4_double_ring_waypoints(7, 1000.0, 12, 1865.0, align="stagger", enroute_r=None)
        inner = radial[1:8]
        outer_r = radial[8:]
        outer_s = stagger[8:]
        self.assertAlmostEqual(math.atan2(inner[0][1], inner[0][0]), 0.0, places=9)
        self.assertAlmostEqual(math.atan2(outer_r[0][1], outer_r[0][0]), 0.0, places=9)
        self.assertAlmostEqual(
            math.atan2(outer_s[0][1], outer_s[0][0]),
            q4_outer_phase_rad(7, 12, "stagger"),
            places=9,
        )

    def test_hexagon_inner_without_enroute_fails_front_cover(self):
        cover = q4_double_ring_cover_ok(
            6, 1150.0, 12, 1865.0, align="radial", enroute_r=None
        )
        self.assertTrue(cover["omni"])
        self.assertFalse(cover["directional"])

    def test_eleven_outer_stagger_fails_dense_front_cover(self):
        cover = q4_double_ring_cover_ok(
            7,
            1000.0,
            11,
            1900.0,
            align="stagger",
            enroute_r=None,
            n_radial=8,
            n_ang=72,
            n_headings=24,
        )
        self.assertFalse(cover["directional"])

    def test_opt_heptagon_dodecagon_is_shortest_dense_feasible(self):
        inner_r = q4_opt_inner_r()
        interval = regular_ring_rho_interval(7)
        self.assertIsNotNone(interval)
        self.assertAlmostEqual(inner_r, interval[0], places=9)
        self.assertLessEqual(inner_r, COVER_R + 1e-9)
        self.assertTrue(coverage_ok(q4_opt_search_waypoints()[: 1 + Q4_OPT_INNER_N]))

        opt = q4_double_ring_search_time(
            Q4_OPT_INNER_N,
            inner_r,
            Q4_OPT_OUTER_N,
            Q4_OPT_OUTER_R,
            align="radial",
            enroute_r=None,
            n_radial=8,
            n_ang=72,
            n_headings=24,
        )
        octagon = q4_double_ring_search_time(
            8,
            1000.0,
            12,
            Q4_OPT_OUTER_R,
            align="radial",
            enroute_r=None,
            n_radial=8,
            n_ang=72,
            n_headings=24,
        )
        stagger = q4_double_ring_search_time(
            Q4_OPT_INNER_N,
            inner_r,
            Q4_OPT_OUTER_N,
            Q4_OPT_OUTER_R,
            align="stagger",
            enroute_r=None,
            n_radial=8,
            n_ang=72,
            n_headings=24,
        )
        self.assertTrue(opt["feasible"])
        self.assertTrue(octagon["feasible"])
        self.assertEqual(opt["n_stops"], 20)
        self.assertLess(opt["total_s"], octagon["total_s"])
        if stagger["feasible"]:
            self.assertLess(opt["path_m"], stagger["path_m"])
        self.assertEqual(len(q4_opt_search_waypoints()), 20)
        self.assertAlmostEqual(
            regular_ring_search_time(7)["ring_r"],
            inner_r,
            places=9,
        )


if __name__ == "__main__":
    unittest.main()
