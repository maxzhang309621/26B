import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from practice_guard import (
    FormalTestBlocked,
    assert_no_formal_activation,
    assert_no_formal_files,
    assert_safe_click_target,
    can_ack_q3_practice_done,
    can_ack_q4_practice_done,
    is_allowed_practice_click,
    is_allowed_q3_practice_click,
    is_allowed_q4_practice_click,
    is_formal_path,
    is_practice_result,
    parse_practice_jammer_count,
    reject_formal_argv,
    reject_non_q3_practice_argv,
    reject_non_q4_practice_argv,
)


class TestPracticeGuard(unittest.TestCase):
    def test_practice_result_name(self):
        p = Path("practice-p3-1-AAAA-BBBB-CCCC-DDDD.result.json")
        self.assertTrue(is_practice_result(p, 3))
        self.assertFalse(is_practice_result(p, 4))

    def test_formal_filenames(self):
        self.assertTrue(is_formal_path(Path("formal-p3-1-XXXX.jlog")))
        self.assertTrue(is_formal_path(Path("formal-attempt-1.tmp")))
        self.assertFalse(is_formal_path(Path("practice-p3-1-AAAA.result.json")))
        self.assertFalse(
            is_formal_path(Path("practice-p3-6256802001849213277-958N-HY6X-VUYX-HKG5.jlog"))
        )
        self.assertFalse(is_formal_path(Path("formal-statistics-queue.sqlite3")))
        self.assertFalse(is_formal_path(Path("formal-statistics-queue.sqlite3-wal")))
        self.assertFalse(is_formal_path(Path("formal-statistics-queue.sqlite3-shm")))

    def test_click_allowlist(self):
        self.assertTrue(is_allowed_practice_click("开始问题3演练测试", 3))
        self.assertTrue(is_allowed_practice_click("  开始问题4演练测试  ", 4))
        self.assertFalse(is_allowed_practice_click("开始问题3演练测试", 4))
        self.assertFalse(is_allowed_practice_click("开始问题3正式测试", 3))
        self.assertFalse(is_allowed_practice_click("开始问题4正式测试", 4))
        self.assertFalse(is_allowed_practice_click("确认开始", 3))
        self.assertFalse(is_allowed_practice_click("返回问题4正式测试", 4))

    def test_reject_formal_argv(self):
        with self.assertRaises(FormalTestBlocked):
            reject_formal_argv(["--formal"])
        with self.assertRaises(FormalTestBlocked):
            reject_formal_argv(["--official"])
        with self.assertRaises(FormalTestBlocked):
            reject_formal_argv(["问题3正式测试"])
        reject_formal_argv(["--repeat-3", "2", "--url", "http://127.0.0.1:2026"])
        with self.assertRaises(FormalTestBlocked):
            reject_non_q4_practice_argv(["--repeat-3", "2"])
        with self.assertRaises(FormalTestBlocked):
            reject_non_q3_practice_argv(["--repeat-4", "2"])
        with self.assertRaises(FormalTestBlocked):
            reject_non_q3_practice_argv(["--formal"])

    def test_q3_done_ack_only_on_practice_dialog(self):
        self.assertTrue(
            can_ack_q3_practice_done(["问题3演练测试完成", "确认", "行为日志已保存"])
        )
        self.assertFalse(can_ack_q3_practice_done(["开始问题3演练测试", "确认"]))
        self.assertFalse(
            can_ack_q3_practice_done(["即将开始问题3正式测试", "确认", "问题3演练测试完成"])
        )
        self.assertFalse(can_ack_q3_practice_done(["问题3演练测试完成", "确认开始"]))
        self.assertTrue(is_allowed_q3_practice_click("开始问题3演练测试"))
        self.assertTrue(is_allowed_q3_practice_click("返回演练测试"))
        self.assertFalse(is_allowed_q3_practice_click("开始问题4演练测试"))
        self.assertFalse(is_allowed_q3_practice_click("开始问题3正式测试"))
        self.assertFalse(is_allowed_q3_practice_click("确认开始"))
        assert_safe_click_target("开始问题3演练测试")

    def test_q4_done_ack_only_on_practice_dialog(self):
        self.assertTrue(
            can_ack_q4_practice_done(["问题4演练测试完成", "确认", "行为日志已保存"])
        )
        self.assertFalse(can_ack_q4_practice_done(["开始问题4演练测试", "确认"]))
        self.assertFalse(
            can_ack_q4_practice_done(["即将开始问题4正式测试", "确认", "问题4演练测试完成"])
        )
        self.assertFalse(can_ack_q4_practice_done(["问题4演练测试完成", "确认开始"]))
        self.assertTrue(is_allowed_q4_practice_click("开始问题4演练测试"))
        self.assertTrue(is_allowed_q4_practice_click("返回演练测试"))
        self.assertFalse(is_allowed_q4_practice_click("开始问题3演练测试"))
        self.assertFalse(is_allowed_q4_practice_click("开始问题4正式测试"))
        self.assertFalse(is_allowed_q4_practice_click("确认开始"))
        with self.assertRaises(FormalTestBlocked):
            assert_safe_click_target("开始问题4正式测试")
        with self.assertRaises(FormalTestBlocked):
            assert_safe_click_target("确认开始")
        assert_safe_click_target("开始问题4演练测试")

    def test_formal_activation_vs_idle_menu(self):
        assert_no_formal_activation(["开始问题4演练测试", "开始问题4正式测试"])
        with self.assertRaises(FormalTestBlocked):
            assert_no_formal_activation(["即将开始问题4正式测试", "取消"])
        with self.assertRaises(FormalTestBlocked):
            assert_no_formal_activation(["再次确认开始"])
        with self.assertRaises(FormalTestBlocked):
            assert_no_formal_activation(["确认开始", "取消"])

    def test_data_dir_formal_file(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "ok.txt").write_text("x", encoding="utf-8")
            (d / "formal-statistics-queue.sqlite3").write_bytes(b"x")
            assert_no_formal_files(d)
            (d / "formal-p3-1.jlog").write_bytes(b"x")
            with self.assertRaises(FormalTestBlocked):
                assert_no_formal_files(d)

    def test_parse_practice_jammer_count(self):
        live = [
            "问题4 演练 测试",
            "本次演练测试干扰源数量",
            "共",
            "12",
            "个， 全向",
            "10",
            "个， 定向",
            "2",
            "个",
            "测试窗口剩余",
            "开始问题4正式测试",
        ]
        self.assertEqual(parse_practice_jammer_count(live, 4), 12)
        done = live + ["测试已结束"]
        self.assertIsNone(parse_practice_jammer_count(done, 4))
        self.assertIsNone(parse_practice_jammer_count(["开始问题4演练测试"], 4))
        with self.assertRaises(FormalTestBlocked):
            parse_practice_jammer_count(["确认开始", "本次演练测试干扰源数量", "共", "12", "个"], 4)


if __name__ == "__main__":
    unittest.main()
