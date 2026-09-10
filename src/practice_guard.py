"""Hard guards: practice drills only. Never start or continue a formal test."""

from __future__ import annotations

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
    return False


def is_allowed_practice_click(text: str, problem: int | None = None) -> bool:
    n = normalize_label(text)
    allowed = {normalize_label(PRACTICE_NAV), normalize_label(PRACTICE_RETURN)}
    allowed.update(normalize_label(v) for v in PRACTICE_START_BUTTON.values())
    if problem in PRACTICE_START_BUTTON:
        allowed.add(normalize_label(PRACTICE_START_BUTTON[problem]))
    return n in allowed and not is_forbidden_label(text)


def reject_formal_argv(argv: list[str]) -> None:
    for raw in argv:
        key = raw.lstrip("-").lower()
        if key in {"formal", "official", "exam", "startformal"}:
            raise FormalTestBlocked("禁止正式测试：命令行出现正式测试开关。")
        if "正式" in raw:
            raise FormalTestBlocked("禁止正式测试：命令行出现「正式」。")
        compact = raw.replace("-", "").replace("_", "").lower()
        if "formal" in compact or "official" in compact:
            raise FormalTestBlocked(f"禁止正式测试：命令行片段 {raw!r}。")


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
