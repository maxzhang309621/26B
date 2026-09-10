# -*- coding: utf-8 -*-
"""
视频策略对接官方模拟器 — 仅演练
用法（倒计时结束后）：
  python run_video_practice.py q3
  python run_video_practice.py q4
禁止：问题3/4 正式测试
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from video_impl import HttpWorld, ROBOT_ID, VideoRobot, OUT

MODE_HELP = """
==================================================
视频策略 | 仅演练 | 正式测试三次机会禁止触碰
队号: {rid}
==================================================
1) 模拟器只点「问题3演练测试」或「问题4演练测试」
2) 等 5 秒倒计时结束、接口就绪
3) 再运行本脚本
""".format(rid=ROBOT_ID)


def main():
    print(MODE_HELP)
    if len(sys.argv) < 2 or sys.argv[1] not in ("q3", "q4"):
        print("用法: python run_video_practice.py q3")
        print("      python run_video_practice.py q4")
        return
    mode = sys.argv[1]
    directional = mode == "q4"
    print(f"即将用视频策略跑 {'问题4' if directional else '问题3'} 演练。")
    print("请确认界面是「演练」不是「正式」。5 秒后 /enter …")
    time.sleep(5)

    w = HttpWorld(robot_id=ROBOT_ID)
    ent = w.enter()
    print("/enter", ent)
    if ent.get("accepted") is not True:
        print("进入失败。检查：是否已开演练、倒计时是否结束、队号是否一致。")
        return
    print("剩余现实时间 s:", ent.get("remaining_real_duration_s"))

    bot = VideoRobot(w, directional=directional)
    try:
        stats = bot.run()
    except Exception as e:
        print("策略异常，尝试 /exit：", e)
        stats = {"error": str(e), "cleared": w.n_cleared, "steps": bot.steps, "total_time": w.virtual_t}
    try:
        ex = w.exit()
        print("/exit", ex)
    except Exception as e:
        print("/exit 失败（窗口可能已关）", e)
        ex = {}

    result = {
        "mode": mode,
        "practice_only": True,
        "robot_id": ROBOT_ID,
        "stats": stats,
        "n_cleared": w.n_cleared,
        "virtual_time_s": w.virtual_t,
        "exit": ex,
    }
    outp = OUT / f"video_practice_{mode}_log.json"
    outp.write_text(json.dumps({"result": result, "log_tail": w.log[-30:]}, ensure_ascii=False, indent=2), encoding="utf-8")
    print("---- 演练结束 ----")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("日志:", outp)


if __name__ == "__main__":
    main()
