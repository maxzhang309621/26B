import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from candidate import (
    Y_MIN,
    from_body,
    front_compatible,
    in_candidate_region,
    intersection_angle_deg,
    next_stations,
    recommend_second,
    recommend_second_sides_compact,
    to_body,
)
from geometry import add, dist, scale, unit


class TestCandidate(unittest.TestCase):
    def test_along_bearing_not_in_region(self):
        s1 = (0.0, 0.0)
        th = 40.0
        along = add(s1, scale(unit(th), 800.0))
        self.assertFalse(in_candidate_region(s1, th, along))

    def test_side_point_in_region(self):
        s1 = (0.0, 0.0)
        th = 0.0
        p = from_body(s1, th, 800.0, 600.0)
        self.assertTrue(in_candidate_region(s1, th, p))
        self.assertLessEqual(dist(p, (0.0, 0.0)), 1800.0)

    def test_recommend_orthogonal_angle(self):
        s1 = (0.0, 0.0)
        th = 30.0
        g = add(s1, scale(unit(th), 900.0))
        s2 = recommend_second(s1, th)
        self.assertTrue(in_candidate_region(s1, th, s2))
        beta = intersection_angle_deg(s1, s2, g)
        self.assertGreaterEqual(beta, 60.0)
        self.assertLessEqual(beta, 120.0)
        self.assertLessEqual(dist(s2, (0.0, 0.0)), 1800.0)

    def test_compact_second_is_closer(self):
        s1 = (0.0, 0.0)
        th = 0.0
        far = recommend_second(s1, th, now=s1)
        a, b = recommend_second_sides_compact(s1, th)
        self.assertLess(dist(a, s1), dist(far, s1))
        self.assertLess(dist(b, s1), dist(far, s1))
        self.assertGreater(dist(a, s1), 400.0)

    def test_next_stations_reject_along_bearing(self):
        s1 = (0.0, 0.0)
        th = 0.0
        pts = next_stations(s1, th, now=s1, directional=False)
        self.assertTrue(pts)
        along = add(s1, scale(unit(th), 800.0))
        self.assertFalse(in_candidate_region(s1, th, along))
        g = (900.0, 0.0)
        pref = pts[0]
        ang = intersection_angle_deg(s1, pref, g)
        self.assertGreaterEqual(ang, 60.0)
        self.assertLessEqual(ang, 120.0)
        for p in pts:
            _x, y = to_body(s1, th, p)
            self.assertGreaterEqual(abs(y), Y_MIN - 1e-6)

    def test_next_stations_directional_front_only(self):
        s1 = (0.0, 0.0)
        th = 0.0
        along = from_body(s1, th, 900.0, 0.0)
        self.assertGreaterEqual(abs(to_body(s1, th, along)[1]), 0.0)
        pts = next_stations(s1, th, now=s1, directional=True)
        self.assertTrue(pts)
        for p in pts:
            self.assertTrue(front_compatible(s1, th, p))
            _x, y = to_body(s1, th, p)
            self.assertGreaterEqual(abs(y), 400.0 - 1e-6)
            self.assertNotIn(p, next_stations(s1, th, directional=True, silence=[p]))
