import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from coverage import (
    COVER_R,
    Q3_RING_PHASE_DEG,
    Q3_RING_R,
    coverage_ok,
    directional_waypoints,
    omni_waypoints,
    q3_coverage_certificate,
    q3_waypoints,
    q3_worst_case_distance,
    regular_ring_rho_interval,
    regular_ring_search_time,
)
from q3_optimized_policy import HuntPolicy


class _IdleBot:
    position = (0.0, 0.0)


class TestQ3AnalyticCoverage(unittest.TestCase):
    def test_certificate_matches_endpoint_proof(self):
        certificate = q3_coverage_certificate()

        self.assertEqual(certificate["ring_count"], 6)
        self.assertEqual(certificate["ring_radius_m"], Q3_RING_R)
        self.assertAlmostEqual(
            certificate["maximum_nearest_angle_rad"],
            math.pi / 6.0,
            places=12,
        )
        self.assertAlmostEqual(
            q3_worst_case_distance(),
            988.5114204360128,
            places=9,
        )
        self.assertAlmostEqual(
            certificate["worst_case_distance_m"],
            988.5114204360128,
            places=9,
        )
        self.assertAlmostEqual(
            certificate["overall_worst_case_distance_m"],
            COVER_R,
            places=9,
        )
        self.assertTrue(certificate["passes"])

    def test_six_points_pass_sampling_and_five_fail(self):
        six_ring = q3_waypoints()
        five_ring = omni_waypoints(ring_r=1200.0, n=5)

        self.assertEqual(len(six_ring), 7)
        self.assertTrue(coverage_ok(six_ring))
        self.assertFalse(coverage_ok(five_ring))

    def test_certificate_validates_the_actual_waypoint_geometry(self):
        good = q3_waypoints()
        rotated = [
            (0.0, 0.0),
            *[
                (
                    Q3_RING_R * math.cos(math.radians(17.0 + 60.0 * k)),
                    Q3_RING_R * math.sin(math.radians(17.0 + 60.0 * k)),
                )
                for k in range(6)
            ],
        ]
        duplicate = [*good[:-1], good[-2]]
        missing_center = good[1:]
        wrong_radius = [*good]
        wrong_radius[-1] = (1000.0, 0.0)
        uneven_angles = [*good]
        uneven_angles[-1] = (
            Q3_RING_R * math.cos(math.radians(300.0)),
            Q3_RING_R * math.sin(math.radians(300.0)),
        )
        five_ring = omni_waypoints(ring_r=Q3_RING_R, n=5)

        self.assertTrue(q3_coverage_certificate(waypoints=good)["passes"])
        self.assertAlmostEqual(
            math.degrees(math.atan2(good[1][1], good[1][0])),
            Q3_RING_PHASE_DEG,
            places=9,
        )
        self.assertTrue(q3_coverage_certificate(waypoints=rotated)["passes"])
        for bad in (duplicate, missing_center, wrong_radius, uneven_angles, five_ring):
            certificate = q3_coverage_certificate(waypoints=bad)
            self.assertFalse(certificate["passes"])
            self.assertFalse(certificate["analytic_proof_valid"])
        self.assertAlmostEqual(
            q3_coverage_certificate(
                ring_r=1200.0,
                waypoints=omni_waypoints(ring_r=1200.0, n=5),
            )["worst_case_distance_m"],
            1088.5984495213224,
            places=9,
        )


class TestQ3Q4WaypointIsolation(unittest.TestCase):
    def test_q3_policy_retains_fastest_eight_ring_route(self):
        policy = HuntPolicy(_IdleBot(), directional=False)

        self.assertEqual(policy.waypoints, omni_waypoints())
        self.assertEqual(len(policy.waypoints), 9)
        self.assertNotEqual(policy.waypoints, q3_waypoints())

    def test_q4_policy_keeps_original_omni_inner_route(self):
        policy = HuntPolicy(_IdleBot(), directional=True)
        original_inner = omni_waypoints()

        self.assertEqual(policy.waypoints[: len(original_inner)], original_inner)
        self.assertEqual(policy.waypoints, directional_waypoints())
        self.assertEqual(len(original_inner), 9)
        self.assertNotEqual(policy.waypoints[:7], q3_waypoints())


class TestRegularRingSearchTime(unittest.TestCase):
    def test_pentagon_cannot_cover(self):
        self.assertIsNone(regular_ring_rho_interval(5))
        self.assertFalse(regular_ring_search_time(5)["feasible"])

    def test_hexagon_is_smallest_feasible_and_shortest_full_sweep(self):
        lo, hi = regular_ring_rho_interval(6)
        expected_lo = 1800.0 * math.cos(math.pi / 6.0) - math.sqrt(
            COVER_R ** 2 - 1800.0 ** 2 * math.sin(math.pi / 6.0) ** 2
        )
        self.assertAlmostEqual(lo, expected_lo, places=9)
        self.assertAlmostEqual(hi, 2.0 * COVER_R * math.cos(math.pi / 6.0), places=9)
        times = [regular_ring_search_time(n) for n in range(6, 13)]
        self.assertTrue(all(row["feasible"] for row in times))
        best = min(times, key=lambda row: row["total_s"])
        self.assertEqual(best["n"], 6)
        hexagon = times[0]
        heptagon = times[1]
        self.assertLess(hexagon["total_s"], heptagon["total_s"])
        self.assertAlmostEqual(hexagon["dwell_s"], 119.0 + 6 * 120.0, places=9)
        self.assertTrue(
            coverage_ok(omni_waypoints(ring_r=lo + 1e-6, n=6), cover_r=COVER_R)
        )


if __name__ == "__main__":
    unittest.main()
