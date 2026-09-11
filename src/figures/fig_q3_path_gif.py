"""Animate the current Q3 HuntPolicy path on a local mock (no official simulator)."""

from __future__ import annotations

import math
import random
import sys
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import animation, font_manager
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, FancyArrowPatch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from coverage import omni_waypoints, q3_waypoints
from mock_sim import MockSim, Source
from robot_client import FnTransport, RobotClient
from runner_q3 import run_q3, run_q3_batch

ARENA_R = 1800.0
BLUE = "#2166AC"
RED = "#B2182B"
GREEN = "#1B7837"
ORANGE = "#F1A340"
GREY = "#888888"
LIGHT = "#D0D0D0"
INK = "#222222"

OUT_GIF = ROOT.parent / "output" / "figures" / "q3_complete_path.gif"
OUT_PNG = ROOT.parent / "output" / "figures" / "q3_complete_path.png"
OUT_BATCH_GIF = ROOT.parent / "output" / "figures" / "q3_batch_path.gif"
OUT_BATCH_PNG = ROOT.parent / "output" / "figures" / "q3_batch_path.png"
OUT_CMP_GIF = ROOT.parent / "output" / "figures" / "q3_path_compare.gif"
OUT_CMP_PNG = ROOT.parent / "output" / "figures" / "q3_path_compare.png"


def _setup_font() -> None:
    mpl.rcParams.update(
        {
            "font.size": 10,
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "legend.fontsize": 9,
            "axes.unicode_minus": False,
        }
    )
    for name in ("Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Source Han Sans SC"):
        if any(name.lower() in f.name.lower() for f in font_manager.fontManager.ttflist):
            mpl.rcParams["font.sans-serif"] = [name, "DejaVu Sans"]
            return
    mpl.rcParams["font.sans-serif"] = ["DejaVu Sans"]


def _mix_omni(seed: int, n: int) -> list[Source]:
    rng = random.Random(seed)
    out: list[Source] = []
    for ch in rng.sample(range(1, 21), n):
        r = math.sqrt(rng.random()) * 1700.0
        a = rng.random() * 2.0 * math.pi
        out.append(
            Source(
                channel=ch,
                xy=(r * math.cos(a), r * math.sin(a)),
                r_eff=rng.uniform(1000.0, 1500.0),
            )
        )
    return out


def _dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _events(log: list[dict]) -> list[dict]:
    out: list[dict] = []
    for rec in log:
        path = rec.get("path")
        if path not in ("/measure", "/clear"):
            continue
        body = rec.get("response") or {}
        if body.get("accepted") is not True:
            continue
        pos = (rec.get("request") or {}).get("position")
        if not pos:
            continue
        xy = (float(pos["x"]), float(pos["y"]))
        ch = rec.get("request", {}).get("channel")
        vt = float(body.get("virtual_time_s") or 0.0)
        if path == "/measure":
            out.append(
                {
                    "xy": xy,
                    "kind": "measure",
                    "channel": ch,
                    "result": body.get("measure_result"),
                    "vt": vt,
                }
            )
        else:
            out.append(
                {
                    "xy": xy,
                    "kind": "clear",
                    "channel": ch,
                    "result": body.get("clear_result"),
                    "vt": vt,
                }
            )
    return out


def _stops(events: list[dict]) -> list[dict]:
    """Collapse consecutive actions at the same coordinate into one stop."""
    stops: list[dict] = []
    for ev in events:
        if stops and _dist(stops[-1]["xy"], ev["xy"]) < 1.0:
            stops[-1]["events"].append(ev)
            stops[-1]["vt"] = ev["vt"]
        else:
            action = "检测" if ev["kind"] == "measure" else "清除"
            stops.append({"xy": ev["xy"], "events": [ev], "vt": ev["vt"], "action": action})
        if ev["kind"] == "clear" and ev["result"] == "success":
            stops[-1]["action"] = "清除"
    return stops


def _apply(events: list[dict], heard: set[int], cleared: set[int]) -> None:
    for ev in events:
        ch = ev["channel"]
        if ch is None:
            continue
        if ev["kind"] == "measure" and ev["result"] in ("direction", "near"):
            heard.add(int(ch))
        if ev["kind"] == "clear" and ev["result"] == "success":
            cleared.add(int(ch))
            heard.add(int(ch))


def _interpolate(stops: list[dict], step_m: float = 70.0) -> list[dict]:
    frames: list[dict] = []
    heard: set[int] = set()
    cleared: set[int] = set()
    trail: list[tuple[float, float]] = [(0.0, 0.0)]
    if not stops:
        return frames

    def push(xy, action, vt, pause: int = 1) -> None:
        for _ in range(pause):
            frames.append(
                {
                    "xy": xy,
                    "trail": list(trail),
                    "heard": set(heard),
                    "cleared": set(cleared),
                    "action": action,
                    "vt": vt,
                }
            )

    first = stops[0]
    trail = [first["xy"]]
    _apply(first["events"], heard, cleared)
    push(first["xy"], first["action"], first["vt"], pause=4)

    for i in range(1, len(stops)):
        a = stops[i - 1]["xy"]
        b = stops[i]["xy"]
        gap = _dist(a, b)
        n = max(1, int(round(gap / step_m)))
        for k in range(1, n + 1):
            t = k / n
            xy = (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))
            trail.append(xy)
            arriving = k == n
            if arriving:
                _apply(stops[i]["events"], heard, cleared)
            push(
                xy,
                stops[i]["action"] if arriving else "行驶",
                stops[i]["vt"] if arriving else stops[i - 1]["vt"],
                pause=3 if arriving else 1,
            )
    return frames


def _heading(trail: list[tuple[float, float]]) -> float:
    if len(trail) < 2:
        return math.pi / 2
    x0, y0 = trail[-2]
    x1, y1 = trail[-1]
    if abs(x1 - x0) < 1e-9 and abs(y1 - y0) < 1e-9:
        return math.pi / 2
    return math.atan2(y1 - y0, x1 - x0)


def build_run(seed: int, n: int, runner, tag: str) -> tuple[list[Source], dict, list[dict]]:
    sources = _mix_omni(seed, n)
    sim = MockSim(robot_id=f"q3-path-gif-{tag}", sources=sources)
    bot = RobotClient(robot_id=f"q3-path-gif-{tag}", transport=FnTransport(sim.handle))
    stats = runner(bot)
    frames = _interpolate(_stops(_events(bot.log)))
    return sources, stats, frames


def _draw_static(ax, sources: list[Source], waypoints: list[tuple[float, float]]) -> None:
    ax.add_patch(Circle((0.0, 0.0), ARENA_R, fill=False, ls="--", lw=1.0, ec=GREY, zorder=0))
    ax.add_patch(Circle((0.0, 0.0), 1200.0, fill=False, ls=":", lw=0.8, ec=LIGHT, zorder=0))
    ring = waypoints[1:] + [waypoints[1]]
    ax.plot(
        [p[0] for p in ring],
        [p[1] for p in ring],
        color=LIGHT,
        lw=1.4,
        ls="--",
        zorder=1,
        label="计划听点环（8×1200 m）",
    )
    ax.scatter(
        [p[0] for p in waypoints],
        [p[1] for p in waypoints],
        s=28,
        c="white",
        edgecolors=BLUE,
        linewidths=1.1,
        zorder=3,
    )
    ax.scatter([0.0], [0.0], s=42, c=BLUE, zorder=4)
    ax.set_aspect("equal")
    ax.set_xlim(-2100, 2100)
    ax.set_ylim(-2100, 2350)
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    for spine in ax.spines.values():
        spine.set_linewidth(0.6)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def render(
    sources: list[Source],
    stats: dict,
    frames: list[dict],
    *,
    title_text: str,
    out_gif: Path,
    out_png: Path,
    waypoints: list[tuple[float, float]] | None = None,
) -> None:
    _setup_font()
    if waypoints is None:
        waypoints = omni_waypoints()
    src_by_ch = {s.channel: s for s in sources}
    out_gif.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(7.2, 7.4), dpi=110)
    _draw_static(ax, sources, waypoints)
    trail_line, = ax.plot([], [], color=BLUE, lw=1.8, alpha=0.9, zorder=2, label="实际行驶轨迹")
    unk = ax.scatter([], [], s=36, c=LIGHT, edgecolors=GREY, zorder=5, label="未发现")
    heard_sc = ax.scatter([], [], s=42, c=ORANGE, edgecolors=INK, zorder=6, label="已听待清")
    clr_sc = ax.scatter([], [], s=52, marker="*", c=GREEN, edgecolors=INK, zorder=7, label="已清除")
    robot = ax.scatter([], [], s=70, c=RED, marker="o", zorder=8, label="机器狗")
    arrow = FancyArrowPatch((0, 0), (1, 1), mutation_scale=12, color=RED, lw=0, zorder=9)
    ax.add_patch(arrow)
    title = ax.set_title("")
    status = ax.text(
        0.02,
        0.98,
        "",
        transform=ax.transAxes,
        va="top",
        ha="left",
        fontsize=9,
        color=INK,
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.82, "pad": 3.5},
    )
    ax.legend(loc="lower right", frameon=True, fancybox=False, edgecolor="#DDDDDD")

    def _pts(chs: set[int]) -> list[tuple[float, float]]:
        pts = [src_by_ch[ch].xy for ch in chs if ch in src_by_ch]
        return pts if pts else [(1e9, 1e9)]

    def update(i: int):
        fr = frames[i]
        trail_line.set_data([p[0] for p in fr["trail"]], [p[1] for p in fr["trail"]])
        u = set(src_by_ch) - fr["heard"] - fr["cleared"]
        h = fr["heard"] - fr["cleared"]
        unk.set_offsets(_pts(u))
        heard_sc.set_offsets(_pts(h))
        clr_sc.set_offsets(_pts(fr["cleared"]))
        robot.set_offsets([fr["xy"]])
        ang = _heading(fr["trail"])
        dx, dy = 90.0 * math.cos(ang), 90.0 * math.sin(ang)
        arrow.set_positions(fr["xy"], (fr["xy"][0] + dx, fr["xy"][1] + dy))
        title.set_text(title_text)
        status.set_text(
            f"动作：{fr['action']}\n"
            f"虚拟时间：{fr['vt']:.0f} s\n"
            f"已清除：{len(fr['cleared'])} / {stats['cleared']}"
        )
        return trail_line, unk, heard_sc, clr_sc, robot, arrow, title, status

    update(len(frames) - 1)
    fig.savefig(out_png, dpi=160, bbox_inches="tight", facecolor="white")
    anim = animation.FuncAnimation(fig, update, frames=len(frames), interval=55, blit=False)
    anim.save(str(out_gif), writer=animation.PillowWriter(fps=18))
    plt.close(fig)


def _panel_artists(ax, src_by_ch, waypoints: list[tuple[float, float]] | None = None):
    if waypoints is None:
        waypoints = omni_waypoints()
    _draw_static(ax, [], waypoints)
    trail_line, = ax.plot([], [], color=BLUE, lw=1.6, alpha=0.9, zorder=2)
    unk = ax.scatter([], [], s=28, c=LIGHT, edgecolors=GREY, zorder=5)
    heard_sc = ax.scatter([], [], s=34, c=ORANGE, edgecolors=INK, zorder=6)
    clr_sc = ax.scatter([], [], s=44, marker="*", c=GREEN, edgecolors=INK, zorder=7)
    robot = ax.scatter([], [], s=56, c=RED, marker="o", zorder=8)
    arrow = FancyArrowPatch((0, 0), (1, 1), mutation_scale=10, color=RED, lw=0, zorder=9)
    ax.add_patch(arrow)
    status = ax.text(
        0.02,
        0.98,
        "",
        transform=ax.transAxes,
        va="top",
        ha="left",
        fontsize=8,
        color=INK,
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.82, "pad": 2.5},
    )
    return trail_line, unk, heard_sc, clr_sc, robot, arrow, status


def render_compare(
    sources: list[Source],
    left: tuple[dict, list[dict], str],
    right: tuple[dict, list[dict], str],
) -> None:
    _setup_font()
    src_by_ch = {s.channel: s for s in sources}
    stats_l, frames_l, title_l = left
    stats_r, frames_r, title_r = right
    n = max(len(frames_l), len(frames_r))
    OUT_CMP_GIF.parent.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, 2, figsize=(12.6, 6.5), dpi=95)
    fig.suptitle("问题 3 行驶路径对照（同一组 12 个全向源）", fontsize=13, color=INK, y=0.98)
    arts = [
        _panel_artists(axes[0], src_by_ch, omni_waypoints()),
        _panel_artists(axes[1], src_by_ch, q3_waypoints()),
    ]
    axes[0].set_title(title_l, fontsize=10)
    axes[1].set_title(title_r, fontsize=10)
    handles = [
        Line2D([0], [0], color=LIGHT, ls="--", lw=1.4, label="计划听点环"),
        Line2D([0], [0], color=BLUE, lw=1.6, label="实际轨迹"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=LIGHT, markeredgecolor=GREY, label="未发现"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=ORANGE, markeredgecolor=INK, label="已听待清"),
        Line2D([0], [0], marker="*", color="w", markerfacecolor=GREEN, markeredgecolor=INK, label="已清除"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=RED, markeredgecolor=RED, label="机器狗"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=6, frameon=False, fontsize=8)

    def _pts(chs: set[int]) -> list[tuple[float, float]]:
        pts = [src_by_ch[ch].xy for ch in chs if ch in src_by_ch]
        return pts if pts else [(1e9, 1e9)]

    def _apply_panel(idx: int, fr: dict, stats: dict) -> None:
        trail_line, unk, heard_sc, clr_sc, robot, arrow, status = arts[idx]
        trail_line.set_data([p[0] for p in fr["trail"]], [p[1] for p in fr["trail"]])
        u = set(src_by_ch) - fr["heard"] - fr["cleared"]
        h = fr["heard"] - fr["cleared"]
        unk.set_offsets(_pts(u))
        heard_sc.set_offsets(_pts(h))
        clr_sc.set_offsets(_pts(fr["cleared"]))
        robot.set_offsets([fr["xy"]])
        ang = _heading(fr["trail"])
        dx, dy = 80.0 * math.cos(ang), 80.0 * math.sin(ang)
        arrow.set_positions(fr["xy"], (fr["xy"][0] + dx, fr["xy"][1] + dy))
        status.set_text(
            f"{fr['action']}  |  {fr['vt']:.0f} s  |  已清 {len(fr['cleared'])}/{stats['cleared']}"
        )

    def update(i: int):
        _apply_panel(0, frames_l[min(i, len(frames_l) - 1)], stats_l)
        _apply_panel(1, frames_r[min(i, len(frames_r) - 1)], stats_r)
        return ()

    update(n - 1)
    fig.tight_layout(rect=(0.0, 0.06, 1.0, 0.94))
    fig.savefig(OUT_CMP_PNG, dpi=150, bbox_inches="tight", facecolor="white")
    anim = animation.FuncAnimation(fig, update, frames=n, interval=55, blit=False)
    anim.save(str(OUT_CMP_GIF), writer=animation.PillowWriter(fps=16))
    plt.close(fig)


def main() -> None:
    seed, n = 1, 12
    sources_a, stats_a, frames_a = build_run(seed, n, run_q3, "defer")
    sources_b, stats_b, frames_b = build_run(seed, n, run_q3_batch, "batch")
    if stats_a["cleared"] != n or stats_b["cleared"] != n:
        raise SystemExit(f"未全清 defer={stats_a['cleared']} batch={stats_b['cleared']}")
    title_a = (
        f"现行：环上顺路复测 / 延后清除\n"
        f"VT {stats_a['virtual_time_s']:.0f} s，行驶 {stats_a.get('travel_s', 0):.0f} s"
    )
    title_b = (
        f"新策略：正六边形听点 + 滚动时域最短路清除\n"
        f"VT {stats_b['virtual_time_s']:.0f} s，行驶 {stats_b.get('travel_s', 0):.0f} s"
    )
    render(
        sources_a, stats_a, frames_a,
        title_text="问题 3 现行策略（原点全扫 + 8×1200 m + 顺路复测 / 延后清除）",
        out_gif=OUT_GIF, out_png=OUT_PNG,
    )
    render(
        sources_b, stats_b, frames_b,
        title_text="问题 3 新策略（正六边形听点全覆盖，再滚动重解开放最短路）",
        out_gif=OUT_BATCH_GIF, out_png=OUT_BATCH_PNG,
        waypoints=q3_waypoints(),
    )
    render_compare(sources_a, (stats_a, frames_a, title_a), (stats_b, frames_b, title_b))
    print(
        f"defer  vt={stats_a['virtual_time_s']:.1f} travel={stats_a.get('travel_s'):.1f} frames={len(frames_a)}"
    )
    print(
        f"batch  vt={stats_b['virtual_time_s']:.1f} travel={stats_b.get('travel_s'):.1f} frames={len(frames_b)}"
    )
    print("wrote", OUT_GIF)
    print("wrote", OUT_BATCH_GIF)
    print("wrote", OUT_CMP_GIF)


if __name__ == "__main__":
    main()
