# -*- coding: utf-8 -*-
"""
B题机器狗客户端 — 仅演练模式
硬规则：绝不启动/点击正式测试；本脚本只在你已手动打开「演练测试」且接口就绪后连接。
"""
from __future__ import annotations

import json
import uuid
import time
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

BASE_URL = "http://127.0.0.1:2026"
# TODO: 改成你们的参赛队号（须与模拟器登录一致）
ROBOT_ID = "202610057095"

# 安全开关：必须为 True 才允许发动作；默认只做连通性探测时可先 False
ALLOW_ACTIONS = True


def post(path: str, payload: dict, timeout: float = 10.0) -> dict:
    req = Request(
        BASE_URL + path,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def base(request_id: str) -> dict:
    return {
        "arena_id": "default",
        "robot_id": ROBOT_ID,
        "request_id": request_id,
    }


def probe_only() -> None:
    """只探测端口是否开放，不 enter，避免误开局。"""
    print("探测", BASE_URL, "…（不会调用 /enter）")
    try:
        # 用错误路径看是否有 HTTP 服务；404 也说明端口在听
        req = Request(BASE_URL + "/__practice_probe__", method="GET")
        urlopen(req, timeout=2)
    except HTTPError as e:
        print(f"端口有响应 HTTP {e.code} — 模拟器接口可能已起来（请确认当前是「演练」不是「正式」）")
    except URLError as e:
        print("连不上接口：", e.reason)
        print("请先：启动模拟器 → 登录 → 只点「问题3/4演练测试」→ 倒计时结束后再运行。")
    except Exception as e:
        print("探测异常：", e)


def run_smoke_practice() -> None:
    """
    极短演练冒烟：enter → 原点测频道1 → exit。
    运行前请人工确认模拟器界面标题/入口是「演练测试」。
    """
    if ROBOT_ID.startswith("REPLACE"):
        raise SystemExit("请先把 ROBOT_ID 改成参赛队号")
    if not ALLOW_ACTIONS:
        raise SystemExit("ALLOW_ACTIONS=False，仅允许 probe")

    print("!!! 请再次确认：当前开的是演练测试，不是正式测试 !!!")
    print("3 秒后开始冒烟（Ctrl+C 取消）…")
    time.sleep(3)

    r = post("/enter", base(f"enter-{uuid.uuid4().hex[:10]}"))
    print("/enter", r)
    if r.get("accepted") is not True:
        print("进入失败，停止")
        return
    print("剩余现实时间 s:", r.get("remaining_real_duration_s"))

    m = post(
        "/measure",
        {
            **base(f"m-{uuid.uuid4().hex[:10]}"),
            "position": {"x": 0, "y": 0},
            "channel": 1,
        },
    )
    print("/measure", m)

    x = post("/exit", base(f"exit-{uuid.uuid4().hex[:10]}"))
    print("/exit", x)


if __name__ == "__main__":
    import sys

    print("=" * 50)
    print("模式：仅演练 | 正式测试三次机会：禁止触碰")
    print("=" * 50)
    if len(sys.argv) > 1 and sys.argv[1] == "smoke":
        run_smoke_practice()
    elif len(sys.argv) > 1 and sys.argv[1] in ("q3", "q4"):
        print("视频完整策略请改用：python run_video_practice.py", sys.argv[1])
    else:
        probe_only()
        print("冒烟：python run_practice_only.py smoke")
        print("视频策略演练：python run_video_practice.py q3  或  q4")
