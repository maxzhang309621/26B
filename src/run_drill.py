"""Official simulator PRACTICE drill: wait for API, run Q3/Q4, dump action log.

This entry never starts a formal test. If the UI or log dir looks like 正式测试,
it aborts before /enter.
"""

from __future__ import annotations

import argparse
import json
import sys
import time

from drill_io import (
    DEFAULT_DATA_DIR,
    load_robot_id,
    run_hunt,
    save_drill_log,
    wait_practice_enter,
)
from practice_guard import FormalTestBlocked, reject_formal_argv, snapshot_files
from robot_client import HttpTransport, RobotClient
from simulator_ui import inspect_and_guard


def main() -> None:
    try:
        reject_formal_argv(sys.argv[1:])
    except FormalTestBlocked as exc:
        raise SystemExit(str(exc)) from exc

    p = argparse.ArgumentParser(description="对接官方模拟器【演练测试】（问题3/4）。禁止正式测试。")
    p.add_argument("--problem", choices=("3", "4"), default="3")
    p.add_argument("--robot-id", default=None)
    p.add_argument("--url", default="http://127.0.0.1:2026")
    p.add_argument("--wait", type=float, default=600.0, help="等待接口开放的秒数")
    args = p.parse_args()

    robot_id = load_robot_id(args.robot_id)
    data_dir = DEFAULT_DATA_DIR
    baseline = snapshot_files(data_dir)
    try:
        inspect_and_guard()
    except FormalTestBlocked as exc:
        raise SystemExit(str(exc)) from exc

    bot = RobotClient(robot_id=robot_id, transport=HttpTransport(args.url))
    print(f"队号={robot_id!r}  地址={args.url}  问题={args.problem}  模式=演练")
    print("请只启动「演练测试」。若界面出现正式测试字样，本程序会立刻退出。正在等待 /enter …")
    t0 = time.time()
    try:
        ent = wait_practice_enter(
            bot,
            timeout_s=args.wait,
            data_dir=data_dir,
            baseline=baseline,
            ui_hook=inspect_and_guard,
        )
    except FormalTestBlocked as exc:
        raise SystemExit(str(exc)) from exc
    print(
        f"已进入  remaining_real_duration_s={ent.get('remaining_real_duration_s')}  "
        f"等待用时 {time.time() - t0:.1f}s"
    )

    stats = run_hunt(args.problem, bot)
    log_path = save_drill_log(args.problem, robot_id, stats, ent, bot.log)
    print("结果:", json.dumps(stats, ensure_ascii=False))
    print("动作日志:", log_path)


if __name__ == "__main__":
    main()
