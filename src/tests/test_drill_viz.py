import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from drill_viz import (
    extract_path,
    load_drill,
    reconstruct_sources,
    render_drill_map,
)
from log_parse import parse_action_log


def _measure(ch, x, y, result="direction", svd=0.0, accepted=True):
    body = {"accepted": accepted, "measure_result": result, "virtual_time_s": 1.0}
    if result == "direction":
        body["svd_deg"] = svd
    return {
        "path": "/measure",
        "request": {"channel": ch, "position": {"x": x, "y": y}},
        "response": body,
    }


def _clear(ch, x, y, ok=True):
    return {
        "path": "/clear",
        "request": {"channel": ch, "position": {"x": x, "y": y}},
        "response": {
            "accepted": True,
            "clear_result": "success" if ok else "no_target_in_range",
            "virtual_time_s": 2.0,
        },
    }


class TestDrillViz(unittest.TestCase):
    def test_extract_path_skips_rejected_and_collapses(self):
        log = [
            _measure(1, 0.0, 0.0, svd=10.0),
            _measure(1, 100.0, 0.0, accepted=False),
            _measure(1, 100.0, 0.0, svd=20.0),
            _clear(1, 100.0, 0.0),
        ]
        ev = extract_path(log)
        self.assertEqual(ev[0].xy, (0.0, 0.0))
        xs = [e.xy for e in ev]
        self.assertIn((100.0, 0.0), xs)
        self.assertEqual(ev[-1].kind, "clear")
        self.assertEqual(ev[-1].result, "success")

    def test_reconstruct_prefers_successful_clear(self):
        log = [
            _measure(4, 0.0, 0.0, svd=90.0),
            _measure(4, 200.0, 0.0, svd=90.0),
            _clear(4, 10.0, 400.0, ok=False),
            _clear(4, 5.0, 390.0, ok=True),
        ]
        srcs = reconstruct_sources(parse_action_log(log), problem="4")
        self.assertEqual(len(srcs), 1)
        self.assertEqual(srcs[0].channel, 4)
        self.assertTrue(srcs[0].cleared)
        self.assertEqual(srcs[0].origin, "clear")
        self.assertEqual(srcs[0].xy, (5.0, 390.0))

    def test_q3_sources_are_omni(self):
        log = [
            _measure(2, 0.0, 0.0, svd=0.0),
            _measure(2, 0.0, 400.0, svd=0.0),
            _clear(2, 300.0, 0.0),
        ]
        srcs = reconstruct_sources(parse_action_log(log), problem="3")
        self.assertEqual(srcs[0].directional, False)
        self.assertIsNone(srcs[0].heading_deg)

    def test_silence_closer_than_hear_marks_directional(self):
        src = (400.0, 0.0)
        log = [
            _measure(7, 0.0, 0.0, svd=0.0),
            {
                "path": "/measure",
                "request": {"channel": 7, "position": {"x": 500.0, "y": 0.0}},
                "response": {"accepted": True, "measure_result": "no_signal", "virtual_time_s": 1.0},
            },
            _clear(7, src[0], src[1]),
        ]
        srcs = reconstruct_sources(parse_action_log(log), problem="4")
        self.assertTrue(srcs[0].directional)
        self.assertIsNotNone(srcs[0].heading_deg)

    def test_render_writes_png(self):
        payload = {
            "problem": "4",
            "stats": {"cleared": 1, "virtual_time_s": 12.0, "q4_inner_n": 7, "q4_inner_r": 997.0},
            "log": [
                _measure(1, 0.0, 0.0, svd=45.0),
                _measure(1, 200.0, 0.0, svd=120.0),
                _clear(1, 80.0, 80.0),
            ],
        }
        with tempfile.TemporaryDirectory() as td:
            drill = Path(td) / "p4-test.json"
            drill.write_text(json.dumps(payload), encoding="utf-8")
            scene = load_drill(drill)
            self.assertEqual(scene.problem, "4")
            self.assertGreaterEqual(len(scene.events), 2)
            png = Path(td) / "map.png"
            render_drill_map(scene, png)
            self.assertTrue(png.is_file())
            self.assertGreater(png.stat().st_size, 1000)


if __name__ == "__main__":
    unittest.main()
