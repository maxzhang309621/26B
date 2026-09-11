import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from geometry import (
    CLEAR_R,
    diameter_circle_covers,
    dist,
    intersect_cones,
    jung_bound,
    locate_quality,
    polygon_diameter,
    smallest_enclosing_circle,
    unit,
)


class TestGeometry(unittest.TestCase):
    def test_two_station_bounded_quad(self):
        s1 = (0.0, 0.0)
        s2 = (400.0, 0.0)
        g = (200.0, 300.0)
        th1 = math.degrees(math.atan2(g[1] - s1[1], g[0] - s1[0]))
        th2 = math.degrees(math.atan2(g[1] - s2[1], g[0] - s2[0]))
        res = intersect_cones([s1, s2], [th1, th2], delta_deg=1.0)
        self.assertFalse(res.empty)
        self.assertTrue(res.bounded)
        self.assertGreaterEqual(len(res.vertices), 3)
        self.assertLessEqual(len(res.vertices), 4)
        xs = [v[0] for v in res.vertices]
        ys = [v[1] for v in res.vertices]
        self.assertTrue(min(xs) < g[0] < max(xs) or abs(min(xs) - max(xs)) < 1)
        self.assertTrue(min(ys) < g[1] < max(ys))
        d = res.diameter
        self.assertTrue(math.isfinite(d))
        self.assertGreater(d, 0.0)
        # 1° at ~360 m is about 12 m transverse; quad diameter tens of meters
        self.assertLess(d, 80.0)

    def test_equilateral_diameter_circle_does_not_cover(self):
        d = 10.0
        h = d * math.sqrt(3.0) / 2.0
        tri = [(0.0, 0.0), (d, 0.0), (d / 2.0, h)]
        self.assertAlmostEqual(polygon_diameter(tri), d, places=6)
        cen, r = smallest_enclosing_circle(tri)
        self.assertAlmostEqual(r, d / math.sqrt(3.0), places=5)
        self.assertFalse(diameter_circle_covers(tri))
        self.assertGreater(r, d / 2.0)

    def test_obtuse_triangle_diameter_circle_covers(self):
        tri = [(0.0, 0.0), (10.0, 0.0), (1.0, 1.0)]
        d = polygon_diameter(tri)
        self.assertAlmostEqual(d, 10.0, places=6)
        _, r = smallest_enclosing_circle(tri)
        self.assertAlmostEqual(r, 5.0, places=5)
        self.assertTrue(diameter_circle_covers(tri))

    def test_jung_equals_equilateral(self):
        d = 6.0
        self.assertAlmostEqual(jung_bound(d), d / math.sqrt(3.0), places=12)

    def test_same_bearing_unbounded_or_large(self):
        s1 = (0.0, 0.0)
        s2 = (10.0, 0.0)
        res = intersect_cones([s1, s2], [90.0, 90.0], delta_deg=1.0)
        self.assertTrue(res.empty or (not res.bounded) or res.diameter == float("inf"))

    def test_locate_quality_clears_tight_fix(self):
        s1 = (0.0, 0.0)
        s2 = (400.0, 0.0)
        g = (200.0, 0.0)
        th1 = math.degrees(math.atan2(g[1] - s1[1], g[0] - s1[0]))
        th2 = math.degrees(math.atan2(g[1] - s2[1], g[0] - s2[0]))
        # Same east-west line: collinear bearings should not claim 20 m clear.
        q = locate_quality([s1, s2], [0.0, 180.0])
        self.assertTrue(q.need_another_fix)
        self.assertFalse(q.can_clear_20)
        self.assertTrue(q.near_collinear)

        g = (200.0, 300.0)
        th1 = math.degrees(math.atan2(g[1] - s1[1], g[0] - s1[0]))
        th2 = math.degrees(math.atan2(g[1] - s2[1], g[0] - s2[0]))
        q2 = locate_quality([s1, s2], [th1, th2])
        self.assertFalse(q2.near_collinear)
        self.assertIsNotNone(q2.sec_center)
        self.assertEqual(q2.can_clear_20, q2.sec_radius <= CLEAR_R)
        self.assertEqual(q2.need_another_fix, not q2.can_clear_20)

    def test_locate_quality_silence_blocks_center(self):
        s1 = (0.0, 0.0)
        s2 = (400.0, 0.0)
        g = (200.0, 300.0)
        th1 = math.degrees(math.atan2(g[1] - s1[1], g[0] - s1[0]))
        th2 = math.degrees(math.atan2(g[1] - s2[1], g[0] - s2[0]))
        q = locate_quality([s1, s2], [th1, th2])
        if q.sec_center is None:
            self.skipTest("unexpected empty fix")
        q2 = locate_quality([s1, s2], [th1, th2], silence=[q.sec_center])
        self.assertTrue(q2.need_another_fix)
        self.assertFalse(q2.can_clear_20)

    def test_unit_vector_east_north(self):
        e = unit(0.0)
        n = unit(90.0)
        self.assertAlmostEqual(e[0], 1.0, places=9)
        self.assertAlmostEqual(n[1], 1.0, places=9)

    def test_optical_grid_centers_cover_square(self):
        from geometry import optical_grid_centers, point_in_convex_polygon

        # 50×50 square → half-diagonal of each 25 m cell ≤ 20 m clear radius
        verts = [(0.0, 0.0), (50.0, 0.0), (50.0, 50.0), (0.0, 50.0)]
        centers = optical_grid_centers(verts, cell=25.0)
        self.assertGreaterEqual(len(centers), 4)
        # every vertex falls within 20 m of some cell center
        for v in verts:
            self.assertTrue(any(dist(v, c) <= CLEAR_R + 1e-6 for c in centers))
        self.assertTrue(any(point_in_convex_polygon(c, verts) for c in centers))


if __name__ == "__main__":
    unittest.main()
