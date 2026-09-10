"""Shared practice-only drill session helpers."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from policy import HuntPolicy
from practice_guard import (
    FormalTestBlocked,
    assert_no_formal_files,
    is_practice_result,
    new_formal_files,
    snapshot_files,
)
from robot_client import RobotClient

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
DEFAULT_DATA_DIR = PROJECT / "Jammers-simulator" / "JammersSimulatorData"
DEFAULT_OUT_DIR = PROJECT / "output" / "drill"


def load_robot_id(cli: str | None) -> str:
    if cli:
        return cli.strip()
    env = os.environ.get("CUMCM_ROBOT_ID", "").strip()
    if env:
        return env
    for path in (PROJECT / "robot_id.txt", ROOT / "robot_id.txt"):
        if path.is_file():
            text = path.read_text(encoding="utf-8").strip().splitlines()
            if text and text[0].strip() and not text[0].startswith("#"):
                return text[0].strip()
    raise SystemExit(
        "缺少参赛队号。请用 --robot-id <队号>，或设置环境变量 CUMCM_ROBOT_ID，"
        "或在 26B/robot_id.txt 写入一行队号。"
    )


def wait_practice_enter(
    bot: RobotClient,
    timeout_s: float,
    data_dir: Path,
    baseline: set[Path],
    ui_hook=None,
) -> dict[str, Any]:
    deadline = time.time() + timeout_s
    rid = "enter-wait-1"
    last_body: dict[str, Any] | None = None
    while time.time() < deadline:
        assert_no_formal_files(data_dir)
        born = new_formal_files(data_dir, baseline)
        if born:
            raise FormalTestBlocked("等待进入时出现正式测试文件，已中止且不会 /enter。")
        if ui_hook:
            ui_hook()
        try:
            body = bot.enter(request_id=rid)
            last_body = body
            if body.get("accepted") is True:
                return body
            raise RuntimeError(
                "模拟器拒绝 /enter（队号须一致，且本局尚未进入）。"
                f" 响应={body}"
            )
        except (ConnectionError, TimeoutError, OSError):
            rid = "enter-wait-1"
        time.sleep(0.4)
    raise TimeoutError(f"等待 /enter 超时 {timeout_s:.0f}s，最后响应={last_body}")


def run_hunt(problem: str, bot: RobotClient) -> dict[str, Any]:
    return HuntPolicy(bot, directional=(problem == "4")).run(do_enter=False)


def save_drill_log(
    problem: str,
    robot_id: str,
    stats: dict[str, Any],
    enter: dict[str, Any],
    log: list,
    extra: dict[str, Any] | None = None,
) -> Path:
    DEFAULT_OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_path = DEFAULT_OUT_DIR / f"p{problem}-{stamp}.json"
    payload = {
        "problem": problem,
        "mode": "practice",
        "robot_id": robot_id,
        "stats": stats,
        "enter": enter,
        "log": log,
    }
    if extra:
        payload.update(extra)
    log_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return log_path


def wait_practice_result(
    data_dir: Path,
    problem: int,
    baseline: set[Path],
    timeout_s: float = 60.0,
) -> Path | None:
    deadline = time.time() + timeout_s
    log_dir = data_dir / "behavior-logs"
    while time.time() < deadline:
        born = new_formal_files(data_dir, baseline)
        if born:
            raise FormalTestBlocked("对局结束后出现正式测试文件，已中止后续批量。")
        now = snapshot_files(data_dir)
        for p in sorted(now - baseline, key=lambda x: x.stat().st_mtime if x.exists() else 0):
            if is_practice_result(p, problem):
                return p
            if p.parent == log_dir and p.suffix == ".json" and not is_practice_result(p):
                raise FormalTestBlocked(f"出现非演练结果文件 {p.name}，已中止。")
        time.sleep(0.3)
    return None
