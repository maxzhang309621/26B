"""Hard guards: practice drills only. Never start or continue a formal test."""

from __future__ import annotations

import re
from pathlib import Path

FORMAL_NAME_MARKERS = (
    "正式",
    "formal",
    "official",
    "startformal",
    "activation_ticket",
)

PRACTICE_START_BUTTON = {
    3: "开始问题3演练测试",
    4: "开始问题4演练测试",
}
PRACTICE_NAV = "演练测试"
PRACTICE_RETURN = "返回演练测试"
Q3_PRACTICE_START = PRACTICE_START_BUTTON[3]
Q4_PRACTICE_START = PRACTICE_START_BUTTON[4]
Q3_PRACTICE_DONE_TITLE = "问题3演练测试完成"
Q4_PRACTICE_DONE_TITLE = "问题4演练测试完成"
Q3_PRACTICE_DONE_ACK = "确认"
Q4_PRACTICE_DONE_ACK = "确认"

FORMAL_UI_MARKERS = (
    "正式测试",
    "开始正式测试",
    "再次确认开始",
    "确认开始",
    "开始问题3正式测试",
    "开始问题4正式测试",
    "返回问题3正式测试",
    "返回问题4正式测试",
    "即将开始问题3正式测试",
    "即将开始问题4正式测试",
)

# Idle home screen lists 正式按钮；那不算已经启动正式测试。
# 只有确认框 / 即将开始 才视为正式测试正在被激活，必须立刻停、且不得再点任何按钮。
FORMAL_ACTIVATION_MARKERS = (
    "即将开始问题3正式测试",
    "即将开始问题4正式测试",
    "即将开始问题3正式",
    "即将开始问题4正式",
    "再次确认开始",
    "开始正式测试",
    "确认开始",
)

# Exact names this process must never Invoke, even if someone asks.
CLICK_NEVER = (
    "确认开始",
    "再次确认开始",
    "开始正式测试",
    "开始问题3正式测试",
    "开始问题4正式测试",
    "返回问题3正式测试",
    "返回问题4正式测试",
    "即将开始问题3正式测试",
    "即将开始问题4正式测试",
    "正式测试",
)


class FormalTestBlocked(RuntimeError):
    """Raised when anything looks like an official (formal) test."""


def normalize_label(text: str) -> str:
    return "".join(str(text).split())


def is_forbidden_label(text: str) -> bool:
    n = normalize_label(text)
    if not n:
        return False
    low = n.lower()
    if "正式" in n:
        return True
    if "formal" in low or "official" in low:
        return True
    if n in {normalize_label(x) for x in CLICK_NEVER}:
        return True
    if "确认开始" in n or "再次确认" in n:
        return True
    return False


def assert_safe_click_target(text: str) -> None:
    """Last-line check immediately before any UI Invoke."""
    n = normalize_label(text)
    if not n:
        raise FormalTestBlocked("拒绝点击空控件名。")
    if is_forbidden_label(text) or "正式" in n:
        raise FormalTestBlocked(f"拒绝点击疑似正式测试控件: {text!r}")
    if n in {normalize_label(x) for x in CLICK_NEVER}:
        raise FormalTestBlocked(f"拒绝点击黑名单控件: {text!r}")


def is_allowed_practice_click(text: str, problem: int | None = None) -> bool:
    n = normalize_label(text)
    if not n or is_forbidden_label(text):
        return False
    allowed = {normalize_label(PRACTICE_NAV), normalize_label(PRACTICE_RETURN)}
    if problem in PRACTICE_START_BUTTON:
        allowed.add(normalize_label(PRACTICE_START_BUTTON[problem]))
    else:
        allowed.update(normalize_label(v) for v in PRACTICE_START_BUTTON.values())
    return n in allowed


def _can_ack_practice_done(labels: list[str], title: str, ack: str) -> bool:
    """True only for a practice-finished dialog, never 正式测试确认."""
    if is_formal_activation_dialog(labels):
        return False
    texts = [normalize_label(x) for x in labels]
    if normalize_label(title) not in texts:
        return False
    if any("正式测试完成" in t for t in texts):
        return False
    if any("确认开始" in t or "再次确认" in t for t in texts):
        return False
    if any("正式" in t and "演练" not in t and "统计" not in t for t in texts):
        if any("即将开始" in t for t in texts):
            return False
    return normalize_label(ack) in texts


def can_ack_q3_practice_done(labels: list[str]) -> bool:
    """True only for the Q3 practice-finished dialog, never 正式测试确认."""
    return _can_ack_practice_done(labels, Q3_PRACTICE_DONE_TITLE, Q3_PRACTICE_DONE_ACK)


def can_ack_q4_practice_done(labels: list[str]) -> bool:
    """True only for the Q4 practice-finished dialog, never 正式测试确认."""
    return _can_ack_practice_done(labels, Q4_PRACTICE_DONE_TITLE, Q4_PRACTICE_DONE_ACK)


def is_allowed_q3_practice_click(text: str) -> bool:
    """Q3 演练专用：只能点问题3演练开始或返回演练页。问题4演练也不点。"""
    n = normalize_label(text)
    if not n or is_forbidden_label(text) or "正式" in n:
        return False
    if "问题4" in n:
        return False
    allowed = {
        normalize_label(Q3_PRACTICE_START),
        normalize_label(PRACTICE_RETURN),
        normalize_label(PRACTICE_NAV),
    }
    return n in allowed


def is_allowed_q4_practice_click(text: str) -> bool:
    """Q4 演练专用：只能点问题4演练开始或返回演练页。问题3演练也不点。"""
    n = normalize_label(text)
    if not n or is_forbidden_label(text) or "正式" in n:
        return False
    if "问题3" in n:
        return False
    allowed = {
        normalize_label(Q4_PRACTICE_START),
        normalize_label(PRACTICE_RETURN),
        normalize_label(PRACTICE_NAV),
    }
    return n in allowed


def reject_formal_argv(argv: list[str]) -> None:
    for raw in argv:
        key = raw.lstrip("-").lower()
        if key in {"formal", "official", "exam", "startformal", "ticket", "activation"}:
            raise FormalTestBlocked("禁止正式测试：命令行出现正式测试开关。")
        if "正式" in raw:
            raise FormalTestBlocked("禁止正式测试：命令行出现「正式」。")
        compact = raw.replace("-", "").replace("_", "").lower()
        if "formal" in compact or "official" in compact or "startformal" in compact:
            raise FormalTestBlocked(f"禁止正式测试：命令行片段 {raw!r}。")


def reject_non_q4_practice_argv(argv: list[str]) -> None:
    """Q4-only runner: no P3, no formal, no generic problem switch."""
    reject_formal_argv(argv)
    for raw in argv:
        low = raw.lower()
        if "repeat-3" in low or "repeat3" in low.replace("-", ""):
            raise FormalTestBlocked("本入口只跑问题4演练，拒绝 --repeat-3。")
        compact = low.replace("-", "").replace("_", "")
        if "problem3" in compact or raw in {"--problem=3", "--problem3"}:
            raise FormalTestBlocked("本入口只跑问题4演练，拒绝问题3参数。")


def reject_non_q3_practice_argv(argv: list[str]) -> None:
    """Q3-only runner: no P4, no formal, no generic problem switch."""
    reject_formal_argv(argv)
    for raw in argv:
        low = raw.lower()
        if "repeat-4" in low or "repeat4" in low.replace("-", ""):
            raise FormalTestBlocked("本入口只跑问题3演练，拒绝 --repeat-4。")
        compact = low.replace("-", "").replace("_", "")
        if "problem4" in compact or raw in {"--problem=4", "--problem4"}:
            raise FormalTestBlocked("本入口只跑问题3演练，拒绝问题4参数。")


# Simulator always keeps an empty upload/statistics queue. Not a live formal run.
_FORMAL_INFRA_PREFIXES = (
    "formal-statistics-queue",
    "formal-statistics",
    "formal_statistics",
)


def is_infrastructure_path(path: Path) -> bool:
    name = path.name.lower()
    return any(name.startswith(p) for p in _FORMAL_INFRA_PREFIXES)


def is_formal_path(path: Path) -> bool:
    """True only for artifacts of an actual formal test run, not simulator infra."""
    if is_infrastructure_path(path):
        return False
    name = path.name.lower()
    if name.startswith("practice-"):
        return False
    if name.endswith(".jlog"):
        return True
    if name.startswith("formal-p3-") or name.startswith("formal-p4-"):
        return True
    if "formal-attempt" in name or "formal_behavior" in name:
        return True
    if "正式" in path.name:
        return True
    return False


def is_practice_result(path: Path, problem: int | None = None) -> bool:
    name = path.name
    if not name.startswith("practice-") or not name.endswith(".result.json"):
        return False
    if problem is not None and not name.startswith(f"practice-p{problem}-"):
        return False
    return True


def scan_data_dir_for_formal(data_dir: Path) -> list[Path]:
    if not data_dir.is_dir():
        return []
    hits: list[Path] = []
    for p in data_dir.rglob("*"):
        if p.is_file() and is_formal_path(p):
            hits.append(p)
    return hits


def assert_no_formal_files(data_dir: Path, extra_new: set[Path] | None = None) -> None:
    hits = scan_data_dir_for_formal(data_dir)
    if extra_new:
        hits.extend(sorted(extra_new))
    if hits:
        shown = ", ".join(str(p.name) for p in hits[:8])
        raise FormalTestBlocked(
            "禁止正式测试：数据目录出现正式测试痕迹，已中止。"
            f" 文件={shown}"
        )


def snapshot_files(data_dir: Path) -> set[Path]:
    if not data_dir.is_dir():
        return set()
    return {p for p in data_dir.rglob("*") if p.is_file()}


def new_formal_files(data_dir: Path, baseline: set[Path]) -> set[Path]:
    now = snapshot_files(data_dir)
    return {p for p in now - baseline if is_formal_path(p)}


def assert_ui_not_formal(labels: list[str]) -> None:
    for lab in labels:
        n = normalize_label(lab)
        for marker in FORMAL_UI_MARKERS:
            if normalize_label(marker) in n:
                raise FormalTestBlocked(f"禁止正式测试：界面出现 {lab!r}，已中止。")
        if is_forbidden_label(lab) and "演练" not in lab:
            raise FormalTestBlocked(f"禁止正式测试：界面控件 {lab!r}，已中止。")


def is_formal_activation_dialog(labels: list[str]) -> str | None:
    for lab in labels:
        n = normalize_label(lab)
        for marker in FORMAL_ACTIVATION_MARKERS:
            m = normalize_label(marker)
            if m == n or (m and m in n):
                return lab
    return None


def assert_no_formal_activation(labels: list[str]) -> None:
    hit = is_formal_activation_dialog(labels)
    if hit:
        raise FormalTestBlocked(f"禁止正式测试：检测到正式测试确认框 {hit!r}，已中止且不会点击。")


def parse_practice_jammer_count(labels: list[str], problem: int = 4) -> int | None:
    """Read 共 N 个 from the Q4/Q3 practice window only. Never from 正式测试."""
    assert_no_formal_activation(labels)
    blob = "".join(normalize_label(x) for x in labels)
    if "本次演练测试干扰源数量" not in blob:
        return None
    if "测试已结束" in blob:
        return None
    idx = blob.find("本次演练测试干扰源数量")
    m = re.search(r"共(\d{1,2})个", blob[idx : idx + 80])
    if not m:
        return None
    n = int(m.group(1))
    if problem == 4 and 10 <= n <= 16:
        return n
    if problem == 3 and n == 8:
        return n
    return None
