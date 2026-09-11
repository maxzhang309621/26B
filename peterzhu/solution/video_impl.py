# -*- coding: utf-8 -*-
"""
按「数模加油站」2026B 讲解实现（BV1KKYg6REiu）

Q1 半平面交集 → 凸多边形 → 直径 / 最小包围圆
Q2 最坏情况下第二检测点（交会角≈90°）
Q3 七星覆盖 + 主动交会 + MEC≤20m 清除 + 滚动插入
Q4 两段式：七星清全向/易听源 → 对面复测定向盲区

仅演练；禁止正式测试。
"""
from __future__ import annotations

import json
import math
import random
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.request import Request, urlopen

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, RegularPolygon

OUT = Path(__file__).resolve().parent
FIG = OUT / "figures"
FIG.mkdir(exist_ok=True)

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "SimSun", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

ARENA_R = 1800.0
EPS_DEG = 1.0
SPEED = 5.0
DET_T = 5.0
SW_T = 1.0
CLEAR_OK_T = 5.0
CLEAR_MISS_T = 3.0
NEAR_R = 5.0
CLEAR_R = 20.0
RX_MIN = 1000.0  # 视频按最小有效半径做覆盖保证
HEX_R = 1200.0   # 七星外圈：保证 1000m 半径盖住 1800m 圆域边缘间隙
CHANNELS = list(range(1, 21))
ROBOT_ID = "202610057095"
BASE_URL = "http://127.0.0.1:2026"


# ========================= 基础几何 =========================
def wrap_deg(a: float) -> float:
    return a % 360.0


def ang_diff_deg(a: float, b: float) -> float:
    return (a - b + 180.0) % 360.0 - 180.0


def bearing_of(p, g) -> float:
    v = np.asarray(g, float) - np.asarray(p, float)
    return wrap_deg(math.degrees(math.atan2(v[1], v[0])))


def in_wedge(deg: float, center: float, half: float = EPS_DEG) -> bool:
    return abs(ang_diff_deg(deg, center)) <= half + 1e-9


def ray_intersect(p1, ang1_deg, p2, ang2_deg):
    a1, a2 = math.radians(ang1_deg), math.radians(ang2_deg)
    d1 = np.array([math.cos(a1), math.sin(a1)])
    d2 = np.array([math.cos(a2), math.sin(a2)])
    A = np.column_stack([d1, -d2])
    if abs(np.linalg.det(A)) < 1e-12:
        return None
    t, s = np.linalg.solve(A, np.asarray(p2, float) - np.asarray(p1, float))
    if t < -1e-8 or s < -1e-8:
        return None
    return np.asarray(p1, float) + t * d1


def convex_hull(pts: np.ndarray) -> np.ndarray:
    pts = np.unique(np.round(np.asarray(pts, float), 6), axis=0)
    if len(pts) <= 2:
        return pts
    pts = pts[np.lexsort((pts[:, 1], pts[:, 0]))]

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in pts[::-1]:
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return np.asarray(lower[:-1] + upper[:-1], dtype=float)


def localization_polygon(stations, bearings, half=EPS_DEG) -> np.ndarray:
    """半平面/扇形交集：边界射线交点筛入全部扇形后取凸包。"""
    n = len(stations)
    if n < 2:
        return np.zeros((0, 2))
    rays = []
    for S, b in zip(stations, bearings):
        S = np.asarray(S, float)
        rays.append((S, wrap_deg(b - half)))
        rays.append((S, wrap_deg(b + half)))
    cands = []
    for i in range(len(rays)):
        for j in range(i + 1, len(rays)):
            if np.allclose(rays[i][0], rays[j][0]):
                continue
            ipt = ray_intersect(rays[i][0], rays[i][1], rays[j][0], rays[j][1])
            if ipt is None:
                continue
            ok = True
            for S, b in zip(stations, bearings):
                if not in_wedge(bearing_of(S, ipt), b, half):
                    ok = False
                    break
            if ok:
                cands.append(ipt)
    if len(cands) < 2:
        return np.zeros((0, 2))
    return convex_hull(np.asarray(cands))


def polygon_diameter(poly: np.ndarray):
    if len(poly) < 2:
        return 0.0, (None, None)
    best, pair = -1.0, (poly[0], poly[0])
    for i in range(len(poly)):
        for j in range(i + 1, len(poly)):
            d = float(np.linalg.norm(poly[i] - poly[j]))
            if d > best:
                best, pair = d, (poly[i], poly[j])
    return best, pair


def _circle_from2(a, b):
    c = 0.5 * (a + b)
    return c, float(np.linalg.norm(a - c))


def _circle_from3(a, b, c):
    d = 2 * (a[0] * (b[1] - c[1]) + b[0] * (c[1] - a[1]) + c[0] * (a[1] - b[1]))
    if abs(d) < 1e-12:
        return _circle_from2(a, b)
    ux = (
        (a[0] ** 2 + a[1] ** 2) * (b[1] - c[1])
        + (b[0] ** 2 + b[1] ** 2) * (c[1] - a[1])
        + (c[0] ** 2 + c[1] ** 2) * (a[1] - b[1])
    ) / d
    uy = (
        (a[0] ** 2 + a[1] ** 2) * (c[0] - b[0])
        + (b[0] ** 2 + b[1] ** 2) * (a[0] - c[0])
        + (c[0] ** 2 + c[1] ** 2) * (b[0] - a[0])
    ) / d
    cen = np.array([ux, uy])
    return cen, float(np.linalg.norm(cen - a))


def min_enclosing_circle(pts: np.ndarray, eps: float = 1e-7):
    """Welzl 最小包围圆。返回 (center, radius)。"""
    pts = np.asarray(pts, float)
    if len(pts) == 0:
        return np.zeros(2), 0.0
    if len(pts) == 1:
        return pts[0].copy(), 0.0
    order = list(range(len(pts)))
    random.shuffle(order)
    P = pts[order]

    def welzl(n, R):
        if n == 0 or len(R) == 3:
            if len(R) == 0:
                return np.zeros(2), 0.0
            if len(R) == 1:
                return R[0].copy(), 0.0
            if len(R) == 2:
                return _circle_from2(R[0], R[1])
            return _circle_from3(R[0], R[1], R[2])
        c, r = welzl(n - 1, R)
        p = P[n - 1]
        if np.linalg.norm(p - c) <= r + eps:
            return c, r
        return welzl(n - 1, R + [p])

    return welzl(len(P), [])


def diameter_circle_covers(poly: np.ndarray) -> Tuple[bool, float, float]:
    """以直径为直径的圆是否覆盖；同时给出 MEC 半径。"""
    if len(poly) == 0:
        return True, 0.0, 0.0
    diam, _ = polygon_diameter(poly)
    mec_c, mec_r = min_enclosing_circle(poly)
    covers = mec_r <= diam / 2.0 + 1e-6
    return bool(covers), float(diam), float(mec_r)


# ========================= 七星结构 =========================
def seven_star_points(hex_r: float = HEX_R) -> List[np.ndarray]:
    """中心 + 正六边形顶点。hex_r=1200 时，1000m 探测圆可盖住 1800m 目标圆边缘间隙。"""
    pts = [np.zeros(2)]
    for k in range(6):
        a = math.radians(60.0 * k)
        pts.append(np.array([hex_r * math.cos(a), hex_r * math.sin(a)]))
    return pts


def seven_star_opposite(hex_r: float = HEX_R) -> List[np.ndarray]:
    """Q4 第二段：相对七星外圈旋转 30°，用于定向背面复测。"""
    pts = []
    r = min(hex_r * 0.85, ARENA_R - 50)
    for k in range(6):
        a = math.radians(60.0 * k + 30.0)
        pts.append(np.array([r * math.cos(a), r * math.sin(a)]))
    pts.append(np.array([0.0, -0.35 * hex_r]))
    return pts


# ========================= Q2 最坏情况第二点 =========================
def sample_first_uncertainty(S1, b1, n_d=8, n_off=3):
    """第一次示向度 ±1° 扇形 × 距离 [200, RX_MIN+…] 上的假设源位置。"""
    S1 = np.asarray(S1, float)
    Gs = []
    for d in np.linspace(250.0, 1400.0, n_d):
        for off in np.linspace(-EPS_DEG, EPS_DEG, n_off):
            rad = math.radians(b1 + off)
            g = S1 + d * np.array([math.cos(rad), math.sin(rad)])
            if np.linalg.norm(g) <= ARENA_R + 1.0:
                Gs.append(g)
    return Gs


def worst_case_diameter(S1, b1, S2, hyps) -> float:
    S2 = np.asarray(S2, float)
    worst = 0.0
    valid = 0
    for g in hyps:
        if np.linalg.norm(S2 - g) < 30.0:
            continue
        b2 = bearing_of(S2, g)
        poly = localization_polygon([S1, S2], [b1, b2])
        if len(poly) < 2:
            worst = max(worst, 1e5)
            continue
        d, _ = polygon_diameter(poly)
        worst = max(worst, d)
        valid += 1
    if valid == 0:
        return 1e6
    return worst


def choose_second_point(S1, b1, current=None) -> np.ndarray:
    """
    视频：候选点须能覆盖第一次不确定区；对每个候选用最坏情况直径评估；
    几何上使两次视线接近 90°。
    """
    S1 = np.asarray(S1, float)
    hyps = sample_first_uncertainty(S1, b1)
    rad = math.radians(b1)
    u = np.array([math.cos(rad), math.sin(rad)])
    v = np.array([-u[1], u[0]])
    cands = []
    for d in (500.0, 700.0, 900.0, 1100.0):
        ghat = S1 + d * u
        for L in (400.0, 600.0, 800.0):
            for sign in (-1.0, 1.0):
                # 在假设源处近似正交
                p = ghat + sign * L * v
                if np.linalg.norm(p) <= ARENA_R + 80:
                    cands.append(p)
                # 70° 斜交，避免完全垂直但超出接收
                p2 = ghat + sign * L * (0.34 * u + 0.94 * v)
                if np.linalg.norm(p2) <= ARENA_R + 80:
                    cands.append(p2)
    if not cands:
        return S1 + 600 * v
    best, best_p = 1e18, cands[0]
    cur = np.zeros(2) if current is None else np.asarray(current, float)
    for p in cands:
        sc = worst_case_diameter(S1, b1, p, hyps)
        sc += 0.02 * float(np.linalg.norm(p - cur))  # 路程惩罚，滚动优化
        if sc < best:
            best, best_p = sc, p
    return np.asarray(best_p, float)


# ========================= 世界接口 =========================
@dataclass
class Source:
    channel: int
    pos: np.ndarray
    rx: float
    directional: bool = False
    heading_deg: float = 0.0
    cleared: bool = False

    def covers(self, p) -> bool:
        if self.cleared:
            return False
        p = np.asarray(p, float)
        if np.linalg.norm(p - self.pos) > self.rx:
            return False
        if not self.directional:
            return True
        ang = bearing_of(self.pos, p)
        return abs(ang_diff_deg(ang, self.heading_deg)) <= 90.0 + 1e-9


class LocalWorld:
    def __init__(self, sources: List[Source], seed: int = 0):
        self.sources = sources
        self.pos = np.zeros(2)
        self.channel = 1
        self.virtual_t = 0.0
        self.n_cleared = 0
        self.seed = seed
        self.log: List[dict] = []

    def _err(self) -> float:
        rng = random.Random(hash((round(self.pos[0], 1), round(self.pos[1], 1), self.seed)) % (2**32))
        return rng.uniform(-EPS_DEG, EPS_DEG)

    def measure(self, x, y, ch: int) -> dict:
        newp = np.array([x, y], float)
        move = float(np.linalg.norm(newp - self.pos)) / SPEED
        sw = SW_T if ch != self.channel else 0.0
        self.virtual_t += move + sw + DET_T
        self.pos, self.channel = newp, ch
        src = next((s for s in self.sources if s.channel == ch and not s.cleared), None)
        if src is None or not src.covers(self.pos):
            r = {"measure_result": "no_signal", "virtual_time_s": self.virtual_t}
        else:
            dist = float(np.linalg.norm(self.pos - src.pos))
            if dist <= NEAR_R:
                r = {"measure_result": "near", "virtual_time_s": self.virtual_t}
            else:
                svd = wrap_deg(bearing_of(self.pos, src.pos) + self._err())
                r = {"measure_result": "direction", "svd_deg": round(svd, 2), "virtual_time_s": self.virtual_t}
        self.log.append({"op": "measure", "x": x, "y": y, "ch": ch, **r})
        return r

    def clear(self, x, y, ch: int) -> dict:
        newp = np.array([x, y], float)
        move = float(np.linalg.norm(newp - self.pos)) / SPEED
        src = next((s for s in self.sources if s.channel == ch and not s.cleared), None)
        ok = src is not None and float(np.linalg.norm(newp - src.pos)) <= CLEAR_R
        self.virtual_t += move + (CLEAR_OK_T if ok else CLEAR_MISS_T)
        self.pos = newp
        if ok:
            src.cleared = True
            self.n_cleared += 1
            r = {"clear_result": "success", "virtual_time_s": self.virtual_t}
        else:
            r = {"clear_result": "no_target_in_range", "virtual_time_s": self.virtual_t}
        self.log.append({"op": "clear", "x": x, "y": y, "ch": ch, **r})
        return r


class HttpWorld:
    """官方模拟器。调用方必须已手动打开「演练测试」。"""

    def __init__(self, robot_id: str = ROBOT_ID, base_url: str = BASE_URL):
        self.robot_id = robot_id
        self.base_url = base_url
        self.pos = np.zeros(2)
        self.channel = 1
        self.virtual_t = 0.0
        self.n_cleared = 0
        self.log: List[dict] = []

    def _post(self, path: str, payload: dict) -> dict:
        req = Request(
            self.base_url + path,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _base(self, rid: str) -> dict:
        return {"arena_id": "default", "robot_id": self.robot_id, "request_id": rid}

    def enter(self) -> dict:
        r = self._post("/enter", self._base(f"enter-{uuid.uuid4().hex[:10]}"))
        self.log.append({"op": "enter", **r})
        return r

    def exit(self) -> dict:
        r = self._post("/exit", self._base(f"exit-{uuid.uuid4().hex[:10]}"))
        self.log.append({"op": "exit", **r})
        return r

    def measure(self, x, y, ch: int) -> dict:
        p = self._base(f"m-{uuid.uuid4().hex[:12]}")
        p["position"] = {"x": float(x), "y": float(y)}
        p["channel"] = int(ch)
        r = self._post("/measure", p)
        self.pos = np.array([x, y], float)
        self.channel = ch
        self.virtual_t = float(r.get("virtual_time_s") or self.virtual_t)
        self.log.append({"op": "measure", "x": x, "y": y, "ch": ch, **r})
        return r

    def clear(self, x, y, ch: int) -> dict:
        p = self._base(f"c-{uuid.uuid4().hex[:12]}")
        p["position"] = {"x": float(x), "y": float(y)}
        p["channel"] = int(ch)
        r = self._post("/clear", p)
        self.pos = np.array([x, y], float)
        self.virtual_t = float(r.get("virtual_time_s") or self.virtual_t)
        if r.get("clear_result") == "success":
            self.n_cleared += 1
        self.log.append({"op": "clear", "x": x, "y": y, "ch": ch, **r})
        return r


# ========================= 视频策略 =========================
class VideoRobot:
    def __init__(self, world, directional: bool = False):
        self.w = world
        self.directional = directional
        self.cleared = set()
        self.heard: Dict[int, List[Tuple[np.ndarray, object]]] = {}
        self.never_heard = set(CHANNELS)
        self.steps = 0

    def _try_clear_at(self, p, ch) -> bool:
        cr = self.w.clear(float(p[0]), float(p[1]), ch)
        self.steps += 1
        if cr.get("clear_result") == "success":
            self.cleared.add(ch)
            self.heard.pop(ch, None)
            return True
        return False

    def localize_and_clear(self, ch) -> bool:
        hist = self.heard.get(ch, [])
        if not hist:
            return False
        stations, bearings = [], []
        for p, info in hist:
            if info == "near":
                return self._try_clear_at(p, ch)
            stations.append(np.asarray(p, float))
            bearings.append(float(info))

        if len(stations) == 1:
            s2 = choose_second_point(stations[0], bearings[0], current=self.w.pos)
            resp = self.w.measure(float(s2[0]), float(s2[1]), ch)
            self.steps += 1
            if resp.get("measure_result") == "near":
                return self._try_clear_at(s2, ch)
            if resp.get("measure_result") == "direction":
                self.heard[ch].append((s2.copy(), resp["svd_deg"]))
                stations.append(s2)
                bearings.append(resp["svd_deg"])
            else:
                # 定向可能在背面：换另一侧正交点
                rad = math.radians(bearings[0])
                v = np.array([-math.sin(rad), math.cos(rad)])
                alt = stations[0] + 600 * np.array([math.cos(rad), math.sin(rad)]) - 600 * v
                resp2 = self.w.measure(float(alt[0]), float(alt[1]), ch)
                self.steps += 1
                if resp2.get("measure_result") == "near":
                    return self._try_clear_at(alt, ch)
                if resp2.get("measure_result") == "direction":
                    self.heard[ch].append((alt.copy(), resp2["svd_deg"]))
                    stations.append(alt)
                    bearings.append(resp2["svd_deg"])
                else:
                    return False

        if len(stations) < 2:
            return False

        poly = localization_polygon(stations[-2:], bearings[-2:])
        if len(poly) >= 2:
            cen, mec_r = min_enclosing_circle(poly)
        else:
            ipt = ray_intersect(stations[-2], bearings[-2], stations[-1], bearings[-1])
            cen = ipt if ipt is not None else stations[-1]
            mec_r = 999.0

        # 视频：MEC 半径 ≤ 20m 即去圆心光学清除
        if mec_r <= CLEAR_R:
            if self._try_clear_at(cen, ch):
                return True
        else:
            # 尚未够小：沿最后示向度再走近一次
            b = bearings[-1]
            rad = math.radians(b)
            near_p = np.asarray(cen) + min(mec_r * 0.6, 80.0) * np.array([math.cos(rad), math.sin(rad)])
            resp = self.w.measure(float(near_p[0]), float(near_p[1]), ch)
            self.steps += 1
            if resp.get("measure_result") == "near":
                return self._try_clear_at(near_p, ch)
            if resp.get("measure_result") == "direction":
                self.heard[ch].append((near_p.copy(), resp["svd_deg"]))
                rad = math.radians(resp["svd_deg"])
                tgt = near_p + 25.0 * np.array([math.cos(rad), math.sin(rad)])
                if self._try_clear_at(tgt, ch):
                    return True
                # 20m 圆上试探
                for ang in range(0, 360, 45):
                    a = math.radians(ang)
                    p = tgt + 15.0 * np.array([math.cos(a), math.sin(a)])
                    if self._try_clear_at(p, ch):
                        return True
        # 最后：直接去 MEC 圆心清一次
        return self._try_clear_at(cen, ch)

    def scan_point(self, p, channels: List[int]) -> Optional[int]:
        """在侦察点扫频；发现信号立即返回该频道（滚动插入）。"""
        found = None
        for ch in channels:
            if ch in self.cleared:
                continue
            resp = self.w.measure(float(p[0]), float(p[1]), ch)
            self.steps += 1
            mr = resp.get("measure_result")
            if mr == "no_signal":
                continue
            self.never_heard.discard(ch)
            if mr == "near":
                self.heard.setdefault(ch, []).append((np.asarray(p, float), "near"))
                self.localize_and_clear(ch)
                found = ch
                break
            if mr == "direction":
                self.heard.setdefault(ch, []).append((np.asarray(p, float), resp["svd_deg"]))
                found = ch
                break
        return found

    def run(self, max_steps: int = 2500) -> dict:
        # —— 第一段：七星覆盖搜索 + 滚动插入定位清除 ——
        scout = seven_star_points()
        for p in scout:
            if self.steps >= max_steps:
                break
            unknown = [c for c in CHANNELS if c not in self.cleared]
            # 每点扫未清频道；发现则立刻交会清除，再继续剩余频道
            remain = list(unknown)
            safety = 0
            while remain and safety < 25:
                safety += 1
                hit = self.scan_point(p, remain)
                if hit is None:
                    break
                if hit not in self.cleared:
                    self.localize_and_clear(hit)
                remain = [c for c in CHANNELS if c not in self.cleared]

        # —— 第二段（Q4）：对面复测从未听到的频道 ——
        if self.directional:
            for p in seven_star_opposite():
                if self.steps >= max_steps:
                    break
                remain = [c for c in CHANNELS if c not in self.cleared]
                hit = self.scan_point(p, remain)
                if hit is not None and hit not in self.cleared:
                    self.localize_and_clear(hit)

        # 收尾：仍有 heard 未清的频道再追一次
        for ch in list(self.heard.keys()):
            if ch not in self.cleared:
                self.localize_and_clear(ch)

        n_src = getattr(self.w, "sources", None)
        total = len(n_src) if n_src is not None else max(self.w.n_cleared, 1)
        return {
            "cleared": self.w.n_cleared,
            "total": total if n_src is not None else self.w.n_cleared,
            "ratio": self.w.n_cleared / max(total if n_src is not None else 1, 1),
            "total_time": self.w.virtual_t,
            "avg_time": self.w.virtual_t / max(self.w.n_cleared, 1),
            "steps": self.steps,
        }


def random_scenario(n_src=None, directional_ratio=0.0, seed=0) -> LocalWorld:
    rng = random.Random(seed)
    if n_src is None:
        n_src = rng.randint(10, 16)
    channels = rng.sample(CHANNELS, n_src)
    sources = []
    n_dir = int(round(n_src * directional_ratio))
    for i, ch in enumerate(channels):
        r = ARENA_R * math.sqrt(rng.random())
        ang = rng.random() * 2 * math.pi
        pos = np.array([r * math.cos(ang), r * math.sin(ang)])
        rx = rng.uniform(RX_MIN, 1500.0)
        directional = i < n_dir
        heading = rng.uniform(0, 360) if directional else 0.0
        sources.append(Source(ch, pos, rx, directional, heading))
    return LocalWorld(sources, seed=seed)


# ========================= 作图与 Q1/Q2 演示 =========================
def plot_seven_star():
    pts = seven_star_points()
    fig, ax = plt.subplots(figsize=(6.5, 6.5), constrained_layout=True)
    ax.add_patch(Circle((0, 0), ARENA_R, fill=False, ls="--", color="gray", label="目标区域 1800m"))
    ax.add_patch(Circle((0, 0), RX_MIN, fill=False, ls=":", color="#90be6d", label="中心 1000m 探测"))
    for i, p in enumerate(pts):
        ax.add_patch(Circle(p, RX_MIN, fill=True, alpha=0.08, color="#2a9d8f"))
        ax.add_patch(Circle(p, RX_MIN, fill=False, color="#2a9d8f", lw=0.8))
        ax.scatter([p[0]], [p[1]], c="#264653", s=40, zorder=5)
        ax.text(p[0] + 30, p[1] + 30, f"S{i}", fontsize=8)
    ax.set_aspect("equal")
    ax.set_xlim(-2000, 2000)
    ax.set_ylim(-2000, 2000)
    ax.set_title("视频方案：七星覆盖（中心+正六边形，探测半径1000m）")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.savefig(FIG / "视频_七星覆盖.png", dpi=160)
    plt.close(fig)


def demo_q1_mec():
    random.seed(1)
    G = np.array([500.0, 200.0])
    S1, S2 = np.array([0.0, 0.0]), np.array([700.0, 50.0])
    b1 = wrap_deg(bearing_of(S1, G) + 0.4)
    b2 = wrap_deg(bearing_of(S2, G) - 0.3)
    poly = localization_polygon([S1, S2], [b1, b2])
    diam, pair = polygon_diameter(poly)
    covers, diam2, mec_r = diameter_circle_covers(poly)
    mec_c, _ = min_enclosing_circle(poly)

    fig, ax = plt.subplots(figsize=(6.5, 5.5), constrained_layout=True)
    if len(poly):
        cl = np.vstack([poly, poly[0]])
        ax.fill(cl[:, 0], cl[:, 1], color="#f4a261", alpha=0.5, label="半平面交集")
        ax.plot(cl[:, 0], cl[:, 1], "r-")
        mid = 0.5 * (pair[0] + pair[1])
        ax.add_patch(Circle(mid, diam / 2, fill=False, ls="--", color="blue", label=f"直径圆 R={diam/2:.1f}"))
        ax.add_patch(Circle(mec_c, mec_r, fill=False, color="#6a4c93", label=f"最小包围圆 R={mec_r:.1f}"))
    ax.scatter([G[0]], [G[1]], c="k", marker="*", s=120, label="真实源")
    ax.set_aspect("equal")
    ax.legend(fontsize=8)
    ax.set_title(f"Q1 视频口径：MEC vs D/2  覆盖={covers}")
    ax.grid(True, alpha=0.3)
    fig.savefig(FIG / "视频_Q1_MEC.png", dpi=160)
    plt.close(fig)
    return {"diameter": round(diam, 3), "mec_r": round(mec_r, 3), "covers": covers}


def demo_q2():
    S1 = np.zeros(2)
    G = np.array([800.0, 350.0])
    b1 = wrap_deg(bearing_of(S1, G) + 0.2)
    s2 = choose_second_point(S1, b1, current=S1)
    b2 = bearing_of(s2, G)
    poly = localization_polygon([S1, s2], [b1, b2])
    fig, ax = plt.subplots(figsize=(6.5, 6.2), constrained_layout=True)
    ax.add_patch(Circle((0, 0), ARENA_R, fill=False, ls="--", color="gray"))
    rad = math.radians(b1)
    ax.arrow(0, 0, 1000 * math.cos(rad), 1000 * math.sin(rad), color="#2a6fbb", head_width=25)
    if len(poly):
        cl = np.vstack([poly, poly[0]])
        ax.fill(cl[:, 0], cl[:, 1], color="#f4a261", alpha=0.55, label="二次交会区")
    ax.scatter([0], [0], c="blue", s=50, label="S1")
    ax.scatter([s2[0]], [s2[1]], c="red", marker="s", s=70, label="最坏情况 S2")
    ax.scatter([G[0]], [G[1]], c="k", marker="*", s=120, label="示意源")
    ax.set_aspect("equal")
    ax.set_xlim(-200, 1600)
    ax.set_ylim(-200, 1400)
    ax.legend(fontsize=8)
    ax.set_title("Q2 视频口径：最坏情况第二检测点")
    ax.grid(True, alpha=0.3)
    fig.savefig(FIG / "视频_Q2_最坏情况第二点.png", dpi=160)
    plt.close(fig)
    return {"S2": [round(float(s2[0]), 1), round(float(s2[1]), 1)]}


def run_local_mc(n=6):
    rows = []
    for seed in range(n):
        w = random_scenario(directional_ratio=0.0, seed=2000 + seed)
        st = VideoRobot(w, directional=False).run()
        st.update({"label": "Q3", "seed": seed})
        rows.append(st)
        print(f"  [视频Q3] {seed}: {st['cleared']}/{st['total']}  avg={st['avg_time']:.0f}s  T={st['total_time']:.0f}s")
    rows4 = []
    for seed in range(n):
        w = random_scenario(directional_ratio=0.35, seed=3000 + seed)
        st = VideoRobot(w, directional=True).run()
        st.update({"label": "Q4", "seed": seed})
        rows4.append(st)
        print(f"  [视频Q4] {seed}: {st['cleared']}/{st['total']}  avg={st['avg_time']:.0f}s  T={st['total_time']:.0f}s")
    return rows, rows4


def main_local():
    print("=== 视频实现：Q1 MEC ===")
    q1 = demo_q1_mec()
    print(q1)
    print("=== 视频实现：Q2 最坏情况第二点 ===")
    q2 = demo_q2()
    print(q2)
    plot_seven_star()
    print("=== 本地 MC（视频策略）===")
    r3, r4 = run_local_mc(6)
    summary = {
        "method": "video seven-star + worst-case S2 + MEC<=20 + two-phase Q4",
        "Q1": q1,
        "Q2": q2,
        "Q3_mean_ratio": float(np.mean([r["ratio"] for r in r3])),
        "Q3_mean_avg_s": float(np.mean([r["avg_time"] for r in r3])),
        "Q4_mean_ratio": float(np.mean([r["ratio"] for r in r4])),
        "Q4_mean_avg_s": float(np.mean([r["avg_time"] for r in r4])),
        "seven_star_hex_r_m": HEX_R,
        "detect_radius_assumed_m": RX_MIN,
    }
    (OUT / "video_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("figures:", FIG)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "practice":
        print("请用: python run_video_practice.py q3  或  python run_video_practice.py q4")
        print("必须先在模拟器点「演练测试」，禁止正式测。")
    else:
        main_local()
