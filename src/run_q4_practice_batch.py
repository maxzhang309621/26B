"""Q4 PRACTICE-only batch. Never starts or clicks 正式测试. Never runs 问题3.

Hard rules:
- No coordinate / image / SendKeys clicks (正式 sits next to 演练).
- Click allowlist is only 「开始问题4演练测试」 / 「返回演练测试」 / 演练完成「确认」.
- Formal activation dialogs abort the process immediately.
- Data-dir formal artifacts abort before /enter.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from drill_io import (
    load_robot_id,
    run_hunt,
    save_drill_log,
    snapshot_files,
    wait_practice_enter,
    wait_practice_result,
)
from practice_guard import (
    FormalTestBlocked,
    assert_no_formal_activation,
    assert_no_formal_files,
    new_formal_files,
    parse_practice_jammer_count,
    reject_non_q4_practice_argv,
)
from robot_client import HttpTransport, RobotClient
from simulator_ui import (
    click_q4_practice_done_ack,
    click_q4_practice_start,
    click_return_practice,
    list_control_names,
)

LOCAL_DATA_DIR = Path(
    r"d:\index\数模\B题\模拟器\CUMCM2026B\Jammers-simulator-win64"
    r"\Jammers-simulator\JammersSimulatorData"
)
POST_CLICK_WAIT_S = 5.2
PROBLEM = 4


def _parse() -> argparse.Namespace:
    reject_non_q4_practice_argv(sys.argv[1:])
    if os.environ.get("CUMCM_ALLOW_FORMAL"):
        raise FormalTestBlocked("禁止正式测试：即使设置了 CUMCM_ALLOW_FORMAL 也不会放行。")
    p = argparse.ArgumentParser(
        description="只批量跑【问题4演练测试】。本程序不能点击或启动正式测试。"
    )
    p.add_argument("--robot-id", default="202610057095")
    p.add_argument("--url", default="http://127.0.0.1:2026")
    p.add_argument("--repeat", type=int, default=5, help="问题4演练次数")
    p.add_argument("--wait", type=float, default=600.0, help="每局等待接口开放的秒数")
    p.add_argument("--data-dir", type=Path, default=LOCAL_DATA_DIR)
    p.add_argument(
        "--try-click",
        action="store_true",
        help="尝试自动点「开始问题4演练测试」（需无障碍启动）。失败则改口头提示。",
    )
    args = p.parse_args()
    if args.repeat < 1:
        raise SystemExit("--repeat 至少为 1")
    if args.repeat > 20:
        raise SystemExit("单次批量最多 20 局演练，避免误操作。")
    return args


_LAST_UI_CHECK = 0.0


def _guard_ui() -> None:
    global _LAST_UI_CHECK
    now = time.time()
    if now - _LAST_UI_CHECK < 2.0:
        return
    _LAST_UI_CHECK = now
    assert_no_formal_activation(list_control_names())


def _guard_data(data_dir: Path, baseline: set[Path] | None = None) -> None:
    assert_no_formal_files(data_dir)
    if baseline is not None:
        born = new_formal_files(data_dir, baseline)
        if born:
            raise FormalTestBlocked(f"出现正式测试文件，已中止: {[p.name for p in born]}")


def _try_start_q4_practice() -> bool:
    _guard_ui()
    try:
        if click_q4_practice_done_ack():
            print("已点掉「问题4演练测试完成」确认框（不是正式测试）")
            time.sleep(0.6)
    except FormalTestBlocked:
        raise
    except Exception:
        pass
    _guard_ui()
    try:
        click_return_practice()
        time.sleep(0.6)
    except FormalTestBlocked:
        raise
    except Exception:
        pass
    _guard_ui()
    click_q4_practice_start()
    print(f"已点击「开始问题4演练测试」，等待 {POST_CLICK_WAIT_S:.0f} 秒倒计时…")
    time.sleep(POST_CLICK_WAIT_S)
    _guard_ui()
    return True


def _one_round(
    idx: int,
    total: int,
    robot_id: str,
    url: str,
    wait_s: float,
    data_dir: Path,
    try_click: bool,
) -> dict:
    print(f"\n======== Q4 演练 {idx}/{total}  禁止正式测试 ========")
    _guard_data(data_dir)
    baseline = snapshot_files(data_dir)
    clicked = False
    if try_click:
        try:
            clicked = _try_start_q4_practice()
        except FormalTestBlocked:
            raise
        except Exception as exc:
            print("自动点击不可用（未暴露网页按钮，且不会改用坐标点）：", exc)
            print("请你只点「开始问题4演练测试」。绝对不要点正式测试。")
    else:
        print("请只点「开始问题4演练测试」，等 5 秒倒计时。绝对不要点正式测试。")

    bot = RobotClient(robot_id=robot_id, transport=HttpTransport(url))
    t0 = time.time()
    if not clicked:
        print("等待演练接口开放（倒计时结束才会 /enter）…")
    ent = wait_practice_enter(
        bot,
        timeout_s=wait_s,
        data_dir=data_dir,
        baseline=baseline,
        ui_hook=_guard_ui,
    )
    _guard_data(data_dir, baseline)
    time.sleep(0.3)
    print(
        f"已进入 remaining_real_duration_s={ent.get('remaining_real_duration_s')} "
        f"等待 {time.time() - t0:.1f}s"
    )
    ui_n = None
    labels = list_control_names()
    assert_no_formal_activation(labels)
    ui_n = parse_practice_jammer_count(labels, PROBLEM)
    if ui_n is None:
        time.sleep(0.25)
        labels = list_control_names()
        assert_no_formal_activation(labels)
        ui_n = parse_practice_jammer_count(labels, PROBLEM)
    print(f"演练窗源个数={ui_n if ui_n is not None else '未读到(按16)'}")
    stats = run_hunt(str(PROBLEM), bot, target_n=ui_n)
    _guard_data(data_dir, baseline)
    log_path = save_drill_log(
        str(PROBLEM), robot_id, stats, ent, bot.log, extra={"batch_index": idx, "mode": "practice"}
    )
    official = wait_practice_result(data_dir, PROBLEM, baseline, timeout_s=20.0)
    official_body = None
    ratio = None
    if official and official.is_file():
        official_body = json.loads(official.read_text(encoding="utf-8"))
        n = official_body.get("jammer_count")
        c = stats.get("cleared")
        if isinstance(n, int) and n > 0 and isinstance(c, int):
            ratio = c / n
            print(
                f"官方本局：干扰源 {n}（全向 {official_body.get('omnidirectional_jammer_count')} "
                f"定向 {official_body.get('directional_jammer_count')}）"
            )
            print(f"清除 {c}/{n}  正确率 {ratio:.1%}  虚拟时间 {stats.get('virtual_time_s'):.1f}s")
    print("stats:", json.dumps(stats, ensure_ascii=False))
    print("log:", log_path)
    for _ in range(12):
        _guard_ui()
        try:
            if click_q4_practice_done_ack():
                print("已点掉演练完成「确认」")
                break
        except FormalTestBlocked:
            raise
        except Exception:
            break
        time.sleep(0.4)
    return {
        "problem": PROBLEM,
        "mode": "practice",
        "index": idx,
        "stats": stats,
        "ratio": ratio,
        "official": official_body,
        "log_path": str(log_path),
    }


def main() -> None:
    try:
        args = _parse()
    except FormalTestBlocked as exc:
        raise SystemExit(str(exc)) from exc

    print("模式=问题4演练-only")
    print("硬规则：不点击、不启动、不进入正式测试；也不跑问题3；不用坐标点击。")
    print(f"计划：问题4演练 × {args.repeat}")
    robot_id = load_robot_id(args.robot_id)
    data_dir = args.data_dir
    summaries: list[dict] = []
    try:
        _guard_ui()
        _guard_data(data_dir)
        for i in range(1, args.repeat + 1):
            try:
                summaries.append(
                    _one_round(
                        i,
                        args.repeat,
                        robot_id,
                        args.url,
                        args.wait,
                        data_dir,
                        args.try_click,
                    )
                )
            except FormalTestBlocked:
                raise
            except Exception as exc:
                print(f"本局异常（已跳过，不点正式测试）: {exc}")
                summaries.append({"index": i, "error": str(exc), "mode": "practice"})
                try:
                    RobotClient(robot_id=robot_id, transport=HttpTransport(args.url)).exit()
                except Exception:
                    pass
                time.sleep(2.0)
            if i < args.repeat:
                print("准备下一局问题4演练…")
                time.sleep(1.5)
    except FormalTestBlocked as exc:
        print(exc)
        raise SystemExit(2) from exc

    ratios = [s["ratio"] for s in summaries if s.get("ratio") is not None]
    times = [s["stats"]["virtual_time_s"] for s in summaries if s.get("stats")]
    print("\n======== Q4 演练汇总 ========")
    if ratios:
        print(
            f"局数 {len(summaries)}  平均正确率 {sum(ratios)/len(ratios):.1%}  "
            f"最低 {min(ratios):.1%}  最高 {max(ratios):.1%}"
        )
    if times:
        print(f"平均虚拟时间 {sum(times)/len(times):.1f}s")
    out = Path(__file__).resolve().parent.parent / "output" / "drill" / "q4-batch-summary.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summaries, ensure_ascii=False, indent=2), encoding="utf-8")
    print("汇总文件:", out)


if __name__ == "__main__":
    main()
