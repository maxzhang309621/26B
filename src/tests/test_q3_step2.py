import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from belief import ChannelBook
from candidate import in_candidate_region, recommend_second_options
from geometry import (
    Q3_ARENA_R,
    dist,
    entirely_excluded_by_no_signal,
    intersect_feasible_region,
    point_in_convex_polygon,
    smallest_enclosing_circle,
)
from q3_optimized_policy import HuntPolicy, _third_point


class TestConservativeFeasibleRegion(unittest.TestCase):
    def test_rounding_margin_contains_wraparound_boundary(self):
        source = (
            1500.0 * math.cos(math.radians(-1.005)),
            1500.0 * math.sin(math.radians(-1.005)),
        )
        region = intersect_feasible_region([(0.0, 0.0)], [0.0])
        self.assertFalse(region.empty)
        self.assertTrue(point_in_convex_polygon(source, region.vertices))

        too_narrow = intersect_feasible_region(
            [(0.0, 0.0)],
            [0.0],
            angle_half_width_deg=1.0,
        )
        self.assertFalse(point_in_convex_polygon(source, too_narrow.vertices))

    def test_arena_and_positive_range_boundaries_are_contained(self):
        source = (1800.0, 0.0)
        stations = [(300.0, 0.0), (900.0, 500.0)]
        bearings = [
            math.degrees(math.atan2(source[1] - y, source[0] - x)) % 360.0
            for x, y in stations
        ]
        region = intersect_feasible_region(stations, bearings)
        self.assertFalse(region.empty)
        self.assertTrue(region.bounded)
        self.assertTrue(point_in_convex_polygon(source, region.vertices))
        self.assertAlmostEqual(dist(stations[0], source), 1500.0, places=7)

    def test_known_delta_one_counterexample_no_longer_certifies_clear(self):
        source = (-519.895408, 197.047288)
        stations = [(0.0, 0.0), (-567.001411, 872.358527)]
        bearings = [158.24, 272.99]
        region = intersect_feasible_region(stations, bearings)
        self.assertTrue(point_in_convex_polygon(source, region.vertices))
        center, radius = smallest_enclosing_circle(region.vertices)
        self.assertGreater(radius, 20.0)
        self.assertGreater(dist(center, source), 20.0)

    def test_no_signal_is_only_a_contradiction_check(self):
        polygon = [(-2.0, -2.0), (2.0, -2.0), (2.0, 2.0), (-2.0, 2.0)]
        self.assertTrue(entirely_excluded_by_no_signal(polygon, [(0.0, 0.0)]))
        self.assertFalse(entirely_excluded_by_no_signal(polygon, [(1002.0, 0.0)]))


class TestStep2CandidateLegality(unittest.TestCase):
    def test_edge_case_returns_no_illegal_radial_clamp(self):
        self.assertEqual(recommend_second_options((1800.0, 0.0), 0.0), [])
        self.assertEqual(
            recommend_second_options((912.176, -1389.412), 323.342),
            [],
        )

    def test_every_returned_option_is_legal(self):
        station = (0.0, 0.0)
        options = recommend_second_options(station, 30.0)
        self.assertEqual(len(options), 2)
        for point in options:
            self.assertTrue(in_candidate_region(station, 30.0, point))
            self.assertLessEqual(dist(point, (0.0, 0.0)), Q3_ARENA_R + 1e-6)

    def test_third_point_is_clamped_inside_arena(self):
        point = _third_point(
            [(1790.0, -100.0), (1790.0, 100.0)],
            (0.0, 0.0),
            arena_radius=Q3_ARENA_R,
        )
        self.assertLessEqual(dist(point, (0.0, 0.0)), Q3_ARENA_R)


class _NoSignalBot:
    def __init__(self):
        self.position = (0.0, 0.0)

    def measure(self, x, y, channel):
        self.position = (x, y)
        return {"accepted": True, "measure_result": "no_signal"}


class TestNoSignalBookkeeping(unittest.TestCase):
    def test_q3_scan_records_no_signal_without_clearing(self):
        policy = HuntPolicy(_NoSignalBot(), directional=False)
        policy._scan_point((10.0, 20.0), [4])
        self.assertEqual(policy.book.no_signal_at[4], [(10.0, 20.0)])
        self.assertNotIn(4, policy.book.cleared)
        self.assertEqual(policy.book.detections.get(4), None)

    def test_book_keeps_negative_and_positive_evidence_separate(self):
        book = ChannelBook()
        book.record_no_signal(2, (0.0, 0.0))
        book.add_direction(2, (1200.0, 0.0), 180.0)
        self.assertEqual(book.no_signal_at[2], [(0.0, 0.0)])
        self.assertEqual(len(book.detections[2]), 1)


if __name__ == "__main__":
    unittest.main()