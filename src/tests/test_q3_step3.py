import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from geometry import dist
from policy import HuntPolicy, _third_point


class _PositionBot:
    def __init__(self):
        self.position = (0.0, 0.0)
        self.measure_points = []

    def measure(self, x, y, channel):
        self.position = (x, y)
        self.measure_points.append((channel, (x, y)))
        return {"accepted": True, "measure_result": "direction", "svd_deg": 180.0}


class _CostProbePolicy(HuntPolicy):
    def __init__(self, bot, service_points):
        super().__init__(bot, directional=False)
        self.service_points = service_points
        self.service_order = []

    def _estimated_service_point(self, ch):
        return self.service_points[ch]

    def _localize_and_clear(self, ch):
        self.service_order.append(ch)
        self.bot.position = self.service_points[ch]
        self.book.mark_cleared(ch)


class TestRouteRecheckScheduling(unittest.TestCase):
    def test_future_legal_waypoint_defers_dedicated_measurement(self):
        bot = _PositionBot()
        policy = HuntPolicy(bot, directional=False)
        policy.book.add_direction(1, (0.0, 0.0), 22.5)
        waypoint = (1200.0, 0.0)

        policy._drain_pending([waypoint])

        self.assertEqual(policy.dedicated_localizations, 0)
        self.assertIn(1, policy.deferred_channels)
        self.assertEqual(policy._opportunistic_channels(waypoint), [1])
        self.assertEqual(bot.measure_points, [])

    def test_illegal_future_waypoint_does_not_defer(self):
        bot = _PositionBot()
        policy = _CostProbePolicy(bot, {1: (100.0, 0.0)})
        policy.book.add_direction(1, (0.0, 0.0), 0.0)

        policy._drain_pending([(1200.0, 0.0)])

        self.assertEqual(policy.service_order, [1])
        self.assertEqual(policy.dedicated_localizations, 1)
        self.assertEqual(policy.localization_services, 1)
        self.assertNotIn(1, policy.deferred_channels)

    def test_incremental_service_cost_beats_last_detection_distance(self):
        bot = _PositionBot()
        policy = _CostProbePolicy(
            bot,
            {
                1: (1500.0, 0.0),
                2: (100.0, 0.0),
            },
        )
        policy.book.add_direction(1, (10.0, 0.0), 0.0)
        policy.book.add_direction(2, (1000.0, 0.0), 180.0)

        policy._drain_pending([])

        self.assertEqual(policy.service_order, [2, 1])

    def test_two_bearings_count_as_service_not_dedicated_remeasure(self):
        bot = _PositionBot()
        policy = _CostProbePolicy(bot, {1: (100.0, 0.0)})
        policy.book.add_direction(1, (0.0, 0.0), 0.0)
        policy.book.add_direction(1, (1200.0, 0.0), 180.0)

        policy._drain_pending([])

        self.assertEqual(policy.localization_services, 1)
        self.assertEqual(policy.dedicated_localizations, 0)
    def test_shared_route_waypoint_rechecks_channels_without_extra_positions(self):
        bot = _PositionBot()
        policy = HuntPolicy(bot, directional=False)
        policy.book.add_direction(1, (0.0, 0.0), 22.5)
        policy.book.add_direction(2, (0.0, 0.0), 22.5)
        waypoint = (1200.0, 0.0)
        channels = policy._opportunistic_channels(waypoint)

        policy._scan_point(waypoint, channels)

        self.assertEqual(channels, [1, 2])
        self.assertEqual([point for _, point in bot.measure_points], [waypoint, waypoint])
        self.assertEqual(len(policy.book.detections[1]), 2)
        self.assertEqual(len(policy.book.detections[2]), 2)

    def test_directional_q4_never_uses_route_deferral(self):
        bot = _PositionBot()
        policy = HuntPolicy(bot, directional=True)
        policy.book.add_direction(1, (0.0, 0.0), 22.5)
        self.assertFalse(policy._eligible_route_probe(1, (1200.0, 0.0)))
        self.assertEqual(policy._opportunistic_channels((1200.0, 0.0)), [])

    def test_directional_third_point_is_not_clamped_to_q3_arena(self):
        point = _third_point(
            [(2000.0, -100.0), (2000.0, 100.0)],
            (0.0, 0.0),
            arena_radius=None,
        )
        self.assertGreater(dist(point, (0.0, 0.0)), 1800.0)


if __name__ == "__main__":
    unittest.main()