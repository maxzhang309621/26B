"""Q3 PRACTICE-only batch. Never starts or clicks 正式测试. Never runs 问题4.

Selected scheme: hexagon cover + receding-horizon batch clear (run_q3_batch).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from drill_io import (
    DEFAULT_DATA_DIR,
    load_robot_id,
    peek_practice_result_meta,
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
    reject_non_q3_practice_argv,
)
from practice_session import (
    PracticeBusy,
    claim_practice_api,
    finish_round_api,
    release_practice_lock,
)
from robot_client import HttpTransport, RobotClient
from simulator_ui import (
    click_q3_practice_done_ack,
    click_q3_practice_start,
    click_return_practice,
    list_control_names,
)

ALT_DATA_DIR = Path(
    r"d:\index\数模\B题\模拟器\CUMCM2026B\Jammers-simulator-win64"
    r"\Jammers-simulator\JammersSimulatorData"
)
POST_CLICK_WAIT_S = 8.0
PROBLEM = 3
POST_ENTER_SETTLE_S = 1.0
INTER_ROUND_S = 4.0
ERROR_COOLDOWN_S = 6.0


def _default_data_dir() -> Path:
    if DEFAULT_DATA_DIR.is_dir():
        return DEFAULT_DATA_DIR
    if ALT_DATA_DIR.is_dir():
        return ALT_DATA_DIR
    return DEFAULT_DATA_DIR


def _probe_measure_ready(bot: RobotClient, tries: int = 16) -> None:
    last: Exception | None = None
    for i in range(tries):
        try:
            bot.measure(0.0, 0.0, 1)
            return
        except (ConnectionError, TimeoutError, OSError, RuntimeError) as exc:
            last = exc
            time.sleep(0.45 + 0.12 * i)
    raise RuntimeError(f"enter 后 measure 未就绪: {last}")


def _parse() -> argparse.Namespace:
    reject_non_q3_practice_argv(sys.argv[1:])
    if os.environ.get("CUMCM_ALLOW_FORMAL"):
        raise FormalTestBlocked("禁止正式测试：即使设置了 CUMCM_ALLOW_FORMAL 也不会放行。")
    p = argparse.ArgumentParser(
        description="只批量跑【问题3演练测试】。方案=正六边形先搜后清。不能点击正式测试。"
    )
    p.add_argument("--robot-id", default="202610057095")
    p.add_argument("--url", default="http://127.0.0.1:2026")
    p.add_argument("--repeat", type=int, default=5, help="问题3演练次数")
    p.add_argument("--wait", type=float, default=600.0, help="每局等待接口开放的秒数")
    p.add_argument("--data-dir", type=Path, default=_default_data_dir())
    p.add_argument(
        "--try-click",
        action="store_true",
        help="尝试自动点「开始问题3演练测试」（需无障碍启动）。失败则改口头提示。",
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


def _try_start_q3_practice() -> bool:
    from practice_guard import normalize_label

    _guard_ui()
    try:
        if click_q3_practice_done_ack():
            print("已点掉「问题3演练测试完成」确认框（不是正式测试）")
            time.sleep(0.8)
    except FormalTestBlocked:
        raise
    except Exception:
        pass
    _guard_ui()
    try:
        click_return_practice()
        time.sleep(1.0)
    except FormalTestBlocked:
        raise
    except Exception:
        pass
    want = normalize_label("开始问题3演练测试")
    for _ in range(8):
        _guard_ui()
        labs = list_control_names()
        if any(normalize_label(x) == want for x in labs):
            break
        try:
            click_return_practice()
        except Exception:
            pass
        time.sleep(0.8)
    _guard_ui()
    click_q3_practice_start()
    print(f"已点击「开始问题3演练测试」，等待 {POST_CLICK_WAIT_S:.0f} 秒倒计时…")
    time.sleep(POST_CLICK_WAIT_S)
    _guard_ui()
    return True


def _dismiss_done() -> None:
    for _ in range(12):
        _guard_ui()
        try:
            if click_q3_practice_done_ack():
                print("已点掉演练完成「确认」")
                return
        except FormalTestBlocked:
            raise
        except Exception:
            return
        time.sleep(0.4)


def _one_round(
    idx: int,
    total: int,
    robot_id: str,
    url: str,
    wait_s: float,
    data_dir: Path,
    try_click: bool,
) -> dict:
    print(f"\n======== Q3 演练 {idx}/{total}  禁止正式测试 ========")
    print("方案=正六边形听点 + 先搜后清 + 滚动时域最短路")
    finish_round_api(url, robot_id, timeout_s=45.0)
    _guard_data(data_dir)
    baseline = snapshot_files(data_dir)
    clicked = False
    if try_click:
        try:
            clicked = _try_start_q3_practice()
        except FormalTestBlocked:
            raise
        except Exception as exc:
            print("自动点击不可用（未暴露网页按钮，且不会改用坐标点）：", exc)
            print("请你只点「开始问题3演练测试」。绝对不要点正式测试。")
    else:
        print("请只点「开始问题3演练测试」，等 5 秒倒计时。绝对不要点正式测试。")

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
    time.sleep(POST_ENTER_SETTLE_S)
    print(
        f"已进入 remaining_real_duration_s={ent.get('remaining_real_duration_s')} "
        f"等待 {time.time() - t0:.1f}s"
    )
    _probe_measure_ready(bot)
    labels = list_control_names()
    assert_no_formal_activation(labels)
    ui_n = parse_practice_jammer_count(labels, PROBLEM)
    if ui_n is None:
        time.sleep(0.25)
        labels = list_control_names()
        assert_no_formal_activation(labels)
        ui_n = parse_practice_jammer_count(labels, PROBLEM)
    print(f"演练窗源个数={ui_n if ui_n is not None else '未读到(按16)'}")
    case_meta = peek_practice_result_meta(data_dir, baseline, PROBLEM, timeout_s=4.0)
    if case_meta:
        print(
            f"官方预告 jammer_count={case_meta.get('jammer_count')} "
            f"omni={case_meta.get('omnidirectional_jammer_count')}"
        )
    stats = run_hunt(str(PROBLEM), bot, target_n=ui_n)
    _guard_data(data_dir, baseline)
    log_path = save_drill_log(
        str(PROBLEM),
        robot_id,
        stats,
        ent,
        bot.log,
        extra={"batch_index": idx, "mode": "practice", "scheme": "hexagon-batch-rh"},
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
            print(f"官方本局：干扰源 {n}")
            print(f"清除 {c}/{n}  正确率 {ratio:.1%}  虚拟时间 {stats.get('virtual_time_s'):.1f}s")
    print("stats:", json.dumps(stats, ensure_ascii=False))
    print("log:", log_path)
    try:
        bot.exit()
    except Exception:
        pass
    _dismiss_done()
    finish_round_api(url, robot_id, timeout_s=60.0)
    return {
        "problem": PROBLEM,
        "mode": "practice",
        "scheme": "hexagon-batch-rh",
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

    print("模式=问题3演练-only")
    print("方案=正六边形听点 + 先搜后清 + 滚动时域最短路")
    print("硬规则：不点击、不启动、不进入正式测试；也不跑问题4；不用坐标点击。")
    print(f"计划：问题3演练 × {args.repeat}")
    robot_id = load_robot_id(args.robot_id)
    data_dir = args.data_dir
    summaries: list[dict] = []
    try:
        try:
            claim_practice_api("run_q3_practice_batch", args.url, robot_id)
        except PracticeBusy as exc:
            raise SystemExit(str(exc)) from exc
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
                try:
                    _dismiss_done()
                except FormalTestBlocked:
                    raise
                except Exception:
                    pass
                finish_round_api(args.url, robot_id, timeout_s=60.0)
                time.sleep(ERROR_COOLDOWN_S)
            if i < args.repeat:
                print("准备下一局问题3演练…")
                time.sleep(INTER_ROUND_S)
    except FormalTestBlocked as exc:
        print(exc)
        raise SystemExit(2) from exc
    finally:
        release_practice_lock()

    ratios = [s["ratio"] for s in summaries if s.get("ratio") is not None]
    times = [s["stats"]["virtual_time_s"] for s in summaries if s.get("stats")]
    print("\n======== Q3 演练汇总 ========")
    if ratios:
        print(
            f"局数 {len(summaries)}  平均正确率 {sum(ratios)/len(ratios):.1%}  "
            f"最低 {min(ratios):.1%}  最高 {max(ratios):.1%}"
        )
    if times:
        print(f"平均虚拟时间 {sum(times)/len(times):.1f}s")
    out = Path(__file__).resolve().parent.parent / "output" / "drill" / "q3-hexagon-batch-summary.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summaries, ensure_ascii=False, indent=2), encoding="utf-8")
    print("汇总文件:", out)


if __name__ == "__main__":
    main()
