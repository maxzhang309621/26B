
# robot_client.py — 对接官方模拟器 http://127.0.0.1:2026
# 用法：先启动模拟器并登录，再改 ROBOT_ID 后运行。
import json, time, uuid
from urllib.request import Request, urlopen

BASE_URL = "http://127.0.0.1:2026"
ROBOT_ID = "202610057095"

def post(path, payload):
    req = Request(BASE_URL + path, data=json.dumps(payload).encode("utf-8"),
                  headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))

def base(rid):
    return {"arena_id": "default", "robot_id": ROBOT_ID, "request_id": rid}

def measure(x, y, ch, rid=None):
    rid = rid or f"m-{uuid.uuid4().hex[:12]}"
    p = base(rid); p["position"]={"x":x,"y":y}; p["channel"]=ch
    return post("/measure", p)

def clear(x, y, ch, rid=None):
    rid = rid or f"c-{uuid.uuid4().hex[:12]}"
    p = base(rid); p["position"]={"x":x,"y":y}; p["channel"]=ch
    return post("/clear", p)

if __name__ == "__main__":
    r = post("/enter", base("enter-1"))
    print(r)
    # 将 solution/solve_b.py 中的 robot_strategy 接到真实 measure/clear 即可
    post("/exit", base("exit-1"))
