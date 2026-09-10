"""Batch official PRACTICE tests only. Formal/official tests are hard-blocked."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from drill_io import (
    DEFAULT_DATA_DIR,
    load_robot_id,
    run_hunt,
    save_drill_log,
    wait_practice_enter,
    wait_practice_result,
)
from practice_guard import (
    FormalTestBlocked,
    assert_no_formal_files,
    reject_formal_argv,
    snapshot_files,
)
from robot_client import HttpTransport, RobotClient
from simulator_ui import inspect_and_guard, return_to_practice, start_practice


def _parse() -> argparse.Namespace:
    reject_formal_argv(sys.argv[1:])
    p = argparse.ArgumentParser(
        description="批量跑问题3/4【演练测试】。本程序不能、也不会启动正式测试。"
    )
    p.add_argument("--robot-id", default=None)
    p.add_argument("--url", default="http://127.0.0.1:2026")
    p.add_argument("--repeat-3", type=int, default=0, help="问题3演练次数")
    p.add_argument("--repeat-4", type=int, default=0, help="问题4演练次数")
    p.add_argument("--wait", type=float, default=180.0, help="每局等待接口开放的秒数")
    p.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="模拟器 JammersSimulatorData 目录，用于识别 practice/formal 日志",
    )
    p.add_argument(
        "--auto-start",
        action="store_true",
        help="尝试自动点击「开始问题X演练测试」（需无障碍启动模拟器）",
    )
    p.add_argument(
        "--no-auto-start",
        action="store_true",
        help="不点界面：每局请只点演练开始，脚本只负责 /enter 到 /exit",
    )
    p.add_argument("--dry-run", action="store_true", help="只打印计划，不连接模拟器")
    args = p.parse_args()
    if args.repeat_3 < 0 or args.repeat_4 < 0:
        raise SystemExit("次数不能为负")
    if args.repeat_3 == 0 and args.repeat_4 == 0:
        raise SystemExit("请指定 --repeat-3 和/或 --repeat-4（只跑演练）。")
    return args


def _plan(args: argparse.Namespace) -> list[int]:
    return [3] * args.repeat_3 + [4] * args.repeat_4


def _one_round(
    problem: int,
    robot_id: str,
    url: str,
    wait_s: float,
    data_dir: Path,
    auto_start: bool,
) -> dict:
    assert_no_formal_files(data_dir)
    baseline = snapshot_files(data_dir)
    inspect_and_guard()
    if auto_start:
        start_practice(problem)
    else:
        print(f"请只点击「开始问题{problem}演练测试」，不要点任何正式测试。")

    bot = RobotClient(robot_id=robot_id, transport=HttpTransport(url))
    t0 = time.time()
    ent = wait_practice_enter(
        bot,
        timeout_s=wait_s,
        data_dir=data_dir,
        baseline=baseline,
        ui_hook=inspect_and_guard,
    )
    print(
        f"P{problem} 已进入 remaining_real_duration_s={ent.get('remaining_real_duration_s')} "
        f"等待 {time.time() - t0:.1f}s"
    )
    stats = run_hunt(str(problem), bot)
    log_path = save_drill_log(str(problem), robot_id, stats, ent, bot.log)
    result = wait_practice_result(data_dir, problem, baseline)
    if auto_start:
        try:
            return_to_practice()
        except Exception as exc:
            print("返回演练页失败（可手动点「返回演练测试」）:", exc)

    summary = {
        "problem": problem,
        "mode": "practice",
        "stats": stats,
        "log_path": str(log_path),
        "official_result": str(result) if result else None,
    }
    print("本局:", json.dumps({k: summary[k] for k in summary if k != "stats"}, ensure_ascii=False))
    print("stats:", json.dumps(stats, ensure_ascii=False))
    return summary


def main() -> None:
    try:
        args = _parse()
    except FormalTestBlocked as exc:
        raise SystemExit(str(exc)) from exc

    plan = _plan(args)
    print("模式=演练-only  禁止正式测试")
    print("计划:", " ".join(f"P{n}演练" for n in plan))
    if args.dry_run:
        print("dry-run：未连接模拟器，未点击任何按钮。")
        return

    auto = args.auto_start and not args.no_auto_start
    robot_id = load_robot_id(args.robot_id)
    summaries = []
    try:
        inspect_and_guard()
        for i, problem in enumerate(plan, 1):
            print(f"\n======== 演练 {i}/{len(plan)} 问题{problem} ========")
            summaries.append(
                _one_round(
                    problem,
                    robot_id,
                    args.url,
                    args.wait,
                    args.data_dir,
                    auto,
                )
            )
    except FormalTestBlocked as exc:
        print(exc)
        raise SystemExit(2) from exc

    out = Path(__file__).resolve().parent.parent / "output" / "drill" / "batch-summary.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summaries, ensure_ascii=False, indent=2), encoding="utf-8")
    print("批汇总结:", out)


if __name__ == "__main__":
    main()
