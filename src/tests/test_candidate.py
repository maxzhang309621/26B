import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from candidate import (
    from_body,
    in_candidate_region,
    intersection_angle_deg,
    recommend_second,
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
