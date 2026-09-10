import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mock_sim import MockSim, Source
from robot_client import FnTransport, RobotClient


class TestProtocolTiming(unittest.TestCase):
    def setUp(self):
        self.sim = MockSim(robot_id="team-test")
        self.bot = RobotClient(robot_id="team-test", transport=FnTransport(self.sim.handle))

    def test_attachment_table2_times(self):
        ent = self.bot.enter(request_id="enter-1")
        self.assertTrue(ent["accepted"])
        self.assertEqual(self.bot.virtual_time_s, 0)

        r2 = self.bot.measure(300, 400, 1, request_id="measure-1")
        self.assertTrue(r2["accepted"])
        self.assertAlmostEqual(r2["virtual_time_s"], 105.0, places=6)

        r3 = self.bot.measure(300, 400, 2, request_id="measure-2")
        self.assertAlmostEqual(r3["virtual_time_s"], 111.0, places=6)

        r4 = self.bot.clear(300, 0, 3, request_id="clear-1")
        self.assertEqual(r4["clear_result"], "no_target_in_range")
        self.assertAlmostEqual(r4["virtual_time_s"], 194.0, places=6)
        self.assertEqual(self.bot.channel, 2)

        r5 = self.bot.measure(300, 0, 2, request_id="measure-3")
        self.assertAlmostEqual(r5["virtual_time_s"], 199.0, places=6)

        r6 = self.bot.exit(request_id="exit-1")
        self.assertEqual(r6["exit_reason"], "user_exit")
        self.assertAlmostEqual(r6["virtual_time_s"], 199.0, places=6)

    def test_unknown_field_rejected(self):
        self.bot.enter()
        status, body = self.bot.transport.post(
            "/measure",
            {
                "arena_id": "default",
                "robot_id": "team-test",
                "request_id": "bad-1",
                "position": {"x": 0, "y": 0},
                "channel": 1,
                "foo": 1,
            },
        )
        self.assertEqual(status, 200)
        self.assertIs(body["accepted"], False)
        self.assertEqual(body["virtual_time_s"], 0)

    def test_clear_does_not_switch_channel(self):
        self.bot.enter()
        self.bot.measure(0, 0, 5)
        self.assertEqual(self.bot.channel, 5)
        self.bot.clear(0, 0, 8)
        self.assertEqual(self.bot.channel, 5)

    def test_repeat_measure_same_error(self):
        self.sim.sources = [Source(channel=3, xy=(100.0, 0.0), r_eff=1200.0)]
        self.bot.enter()
        a = self.bot.measure(0, 0, 3)
        b = self.bot.measure(0, 0, 3)
        self.assertEqual(a["measure_result"], "direction")
        self.assertEqual(a["svd_deg"], b["svd_deg"])

    def test_near_and_clear(self):
        self.sim.sources = [Source(channel=1, xy=(3.0, 0.0), r_eff=1200.0)]
        self.bot.enter()
        m = self.bot.measure(0, 0, 1)
        self.assertEqual(m["measure_result"], "near")
        c = self.bot.clear(0, 0, 1)
        self.assertEqual(c["clear_result"], "success")
        c2 = self.bot.clear(0, 0, 1)
        self.assertEqual(c2["clear_result"], "no_target_in_range")

    def test_directional_back_no_signal(self):
        self.sim.sources = [Source(channel=4, xy=(0.0, 0.0), r_eff=1200.0, heading_deg=0.0)]
        self.bot.enter()
        west = self.bot.measure(-100, 0, 4)
        self.assertEqual(west["measure_result"], "no_signal")
        east = self.bot.measure(100, 0, 4)
        self.assertEqual(east["measure_result"], "direction")


if __name__ == "__main__":
    unittest.main()
