import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from practice_guard import (
    FormalTestBlocked,
    assert_no_formal_files,
    assert_ui_not_formal,
    is_allowed_practice_click,
    is_formal_path,
    is_practice_result,
    reject_formal_argv,
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
        self.assertFalse(is_allowed_practice_click("开始问题3正式测试", 3))
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

    def test_ui_formal_dialog(self):
        with self.assertRaises(FormalTestBlocked):
            assert_ui_not_formal(["开始正式测试", "取消"])
        assert_ui_not_formal(["开始问题3演练测试", "演练测试"])

    def test_data_dir_formal_file(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "ok.txt").write_text("x", encoding="utf-8")
            (d / "formal-statistics-queue.sqlite3").write_bytes(b"x")
            assert_no_formal_files(d)
            (d / "formal-p3-1.jlog").write_bytes(b"x")
            with self.assertRaises(FormalTestBlocked):
                assert_no_formal_files(d)


if __name__ == "__main__":
    unittest.main()
