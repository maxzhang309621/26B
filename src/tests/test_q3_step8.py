import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from geometry import dist
from policy import HuntPolicy


class _ClearBot:
    def __init__(self, target=(30.0, 30.0)):
        self.target = target
        self.position = (0.0, 0.0)
        self.clear_calls = 0

    def clear(self, x, y, channel):
        self.position = (x, y)
        self.clear_calls += 1
        result = "success" if dist(self.position, self.target) <= 20.0 else "no_target_in_range"
        return {"accepted": True, "clear_result": result}


class TestQ3Step8(unittest.TestCase):
    def test_insert_delta_and_cheapest_future_edge(self):
        policy = HuntPolicy(_ClearBot(), enable_step8_clear_ready_insertion=True)
        route = [(0.0, 0.0), (100.0, 0.0), (100.0, 100.0), (0.0, 100.0)]
        policy._step8_prepare_route(route)
        policy._step8_set_edge_start(0)
        clear_point = (80.0, 60.0)
        edges = policy._step8_future_edges()

        expected = dist(edges[1][1], clear_point) + dist(clear_point, edges[1][2]) - dist(edges[1][1], edges[1][2])
        self.assertAlmostEqual(
            policy._step8_insert_delta(edges[1][1], clear_point, edges[1][2]),
            expected,
        )
        self.assertEqual(policy._step8_choose_insertion_edge(clear_point, edges)[0], 1)

    def test_executed_edge_cannot_be_skipped_and_cleared_channel_is_not_repeated(self):
        bot = _ClearBot()
        policy = HuntPolicy(bot, enable_step8_clear_ready_insertion=True)
        policy._step8_prepare_route([(0.0, 0.0), (100.0, 0.0), (200.0, 0.0)])
        policy._step8_set_edge_start(0)
        policy._step8_mark_edge_executed(1)
        self.assertEqual(policy._step8_executed_edges, set())
        policy._step8_mark_edge_executed(0)
        policy._step8_set_edge_start(1)
        self.assertEqual(policy._step8_executed_edges, {0})
        self.assertEqual(policy._step8_choose_insertion_edge((150.0, 0.0))[0], 1)

        policy.book.add_direction(3, (0.0, 0.0), 45.0)
        self.assertTrue(policy._step8_queue_clear_ready(3, (30.0, 30.0)))
        policy._step8_set_edge_start(0)
        # The queued item is tied to edge 1; servicing edge 0 must not clear it.
        self.assertFalse(policy._step8_service_before_edge(0))
        self.assertEqual(bot.clear_calls, 0)
        policy._step8_set_edge_start(1)
        self.assertTrue(policy._step8_service_before_edge(1))
        self.assertIn(3, policy.book.cleared)
        self.assertEqual(bot.clear_calls, 1)
        self.assertFalse(policy._step8_service_before_edge(1))
        self.assertEqual(bot.clear_calls, 1)

    def test_directional_branch_rejects_step8_insertion(self):
        policy = HuntPolicy(
            _ClearBot(),
            directional=True,
            enable_step8_clear_ready_insertion=True,
        )
        self.assertFalse(policy._step8_insertion_enabled)
        self.assertEqual(policy._step8_future_edges(), [])
        self.assertIsNone(policy._step8_choose_insertion_edge((1.0, 1.0), []))

    def test_deterministic_clear_ready_smoke(self):
        bot = _ClearBot()
        policy = HuntPolicy(bot, enable_step8_clear_ready_insertion=True)
        policy._step8_prepare_route([(0.0, 0.0), (100.0, 0.0), (100.0, 100.0)])
        policy._step8_set_edge_start(0)
        policy.book.add_direction(5, (0.0, 0.0), 45.0)
        policy.book.add_direction(5, (100.0, 0.0), 161.565)

        policy._localize_and_clear(5)
        self.assertIn(5, policy._step8_ready)
        self.assertNotIn(5, policy.book.cleared)
        self.assertTrue(policy._step8_service_before_edge(0))
        self.assertIn(5, policy.book.cleared)
        self.assertEqual(bot.clear_calls, 1)


if __name__ == "__main__":
    unittest.main()
