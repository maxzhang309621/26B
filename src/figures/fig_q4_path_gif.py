"""Animate the Q4 HuntPolicy full path on a local mock (no official simulator)."""

from __future__ import annotations

import math
import random
import sys
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import animation, font_manager
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, FancyArrowPatch, Wedge

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from coverage import covering_phases, q4_opt_search_waypoints
from mock_sim import MockSim, Source
from robot_client import FnTransport, RobotClient
from runner_q4 import run_q4_hexbatch

ARENA_R = 1800.0
BLUE = "#2166AC"
RED = "#B2182B"
GREEN = "#1B7837"
ORANGE = "#E08214"
PURPLE = "#762A83"
GREY = "#888888"
LIGHT = "#D0D0D0"
INK = "#222222"
OMNI_FILL = "#92C5DE"
DIR_FILL = "#F1A340"

OUT_GIF = ROOT.parent / "output" / "figures" / "q4_complete_path.gif"
OUT_PNG = ROOT.parent / "output" / "figures" / "q4_complete_path.png"
WEDGE_R = 240.0


def _setup_font() -> None:
    mpl.rcParams.update(
        {
            "font.size": 10,
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "legend.fontsize": 8.5,
            "axes.unicode_minus": False,
        }
    )
    for name in ("Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Source Han Sans SC"):
        if any(name.lower() in f.name.lower() for f in font_manager.fontManager.ttflist):
            mpl.rcParams["font.sans-serif"] = [name, "DejaVu Sans"]
            return
    mpl.rcParams["font.sans-serif"] = ["DejaVu Sans"]


def _mix_q4(seed: int, n: int, n_dir: int) -> list[Source]:
    rng = random.Random(seed)
    chs = rng.sample(range(1, 21), n)
    out: list[Source] = []
    for i, ch in enumerate(chs):
        r = 400.0 + math.sqrt(rng.random()) * 1300.0
        a = rng.random() * 2.0 * math.pi
        xy = (r * math.cos(a), r * math.sin(a))
        reff = rng.uniform(1000.0, 1500.0)
        heading = math.degrees(a) if i < n_dir else None
        out.append(Source(channel=ch, xy=xy, r_eff=reff, heading_deg=heading))
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


def _interpolate(stops: list[dict], step_m: float = 90.0) -> list[dict]:
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
    push(first["xy"], first["action"], first["vt"], pause=3)

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
                pause=2 if arriving else 1,
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


def _state_color(ch: int, heard: set[int], cleared: set[int], base: str) -> str:
    if ch in cleared:
        return GREEN
    if ch in heard:
        return ORANGE
    return base


def build_run(seed: int, n: int, n_dir: int) -> tuple[list[Source], dict, list[dict]]:
    sources = _mix_q4(seed, n, n_dir)
    sim = MockSim(robot_id="q4-path-gif", sources=sources)
    bot = RobotClient(robot_id="q4-path-gif", transport=FnTransport(sim.handle))
    stats = run_q4_hexbatch(bot)
    frames = _interpolate(_stops(_events(bot.log)))
    return sources, stats, frames


def _draw_static(ax, waypoints: list[tuple[float, float]]) -> None:
    origin, inner, outer = covering_phases(waypoints)
    ax.add_patch(Circle((0.0, 0.0), ARENA_R, fill=False, ls="--", lw=1.0, ec=GREY, zorder=0))
    if inner:
        ring = inner + [inner[0]]
        ax.plot(
            [p[0] for p in ring],
            [p[1] for p in ring],
            color="#92C5DE",
            lw=1.3,
            ls="--",
            zorder=1,
            label="计划内环（正七边形）",
        )
    if outer:
        ring = outer + [outer[0]]
        ax.plot(
            [p[0] for p in ring],
            [p[1] for p in ring],
            color="#B2ABD2",
            lw=1.3,
            ls="--",
            zorder=1,
            label="计划外环（正十二边形）",
        )
    ax.scatter(
        [p[0] for p in waypoints],
        [p[1] for p in waypoints],
        s=22,
        c="white",
        edgecolors=BLUE,
        linewidths=0.9,
        zorder=3,
    )
    ax.scatter([origin[0]], [origin[1]], s=42, c=BLUE, zorder=4)
    ax.set_aspect("equal")
    ax.set_xlim(-2300, 2300)
    ax.set_ylim(-2300, 2550)
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def render(sources: list[Source], stats: dict, frames: list[dict]) -> None:
    _setup_font()
    waypoints = q4_opt_search_waypoints()
    src_by_ch = {s.channel: s for s in sources}
    omni = [s for s in sources if s.heading_deg is None]
    directional = [s for s in sources if s.heading_deg is not None]
    OUT_GIF.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(7.6, 7.8), dpi=110)
    _draw_static(ax, waypoints)

    wedges: dict[int, Wedge] = {}
    for src in directional:
        heading = float(src.heading_deg)
        wedge = Wedge(
            src.xy,
            WEDGE_R,
            heading - 90.0,
            heading + 90.0,
            facecolor=DIR_FILL,
            edgecolor=PURPLE,
            lw=0.8,
            alpha=0.38,
            zorder=5,
        )
        ax.add_patch(wedge)
        wedges[src.channel] = wedge
        hx = src.xy[0] + 160.0 * math.cos(math.radians(heading))
        hy = src.xy[1] + 160.0 * math.sin(math.radians(heading))
        ax.annotate(
            "",
            xy=(hx, hy),
            xytext=src.xy,
            arrowprops={"arrowstyle": "->", "color": PURPLE, "lw": 1.1},
            zorder=6,
        )

    omni_sc = ax.scatter(
        [s.xy[0] for s in omni] or [1e9],
        [s.xy[1] for s in omni] or [1e9],
        s=68,
        c=OMNI_FILL,
        edgecolors=BLUE,
        linewidths=1.2,
        zorder=6,
        label="全向源（圆）",
    )
    dir_sc = ax.scatter(
        [s.xy[0] for s in directional] or [1e9],
        [s.xy[1] for s in directional] or [1e9],
        s=58,
        c=DIR_FILL,
        marker="^",
        edgecolors=PURPLE,
        linewidths=1.2,
        zorder=7,
        label="定向源（三角+前瓣）",
    )
    for src in omni:
        ax.annotate(
            f"全向 ch{src.channel}",
            xy=src.xy,
            xytext=(10, 8),
            textcoords="offset points",
            fontsize=7.5,
            color=BLUE,
            zorder=10,
        )
    for src in directional:
        back = math.radians(float(src.heading_deg) + 180.0)
        ax.annotate(
            f"定向 ch{src.channel}",
            xy=src.xy,
            xytext=(
                src.xy[0] + 210.0 * math.cos(back),
                src.xy[1] + 210.0 * math.sin(back),
            ),
            fontsize=7.5,
            color=PURPLE,
            ha="center",
            va="center",
            zorder=10,
        )
    trail_line, = ax.plot([], [], color=BLUE, lw=1.8, alpha=0.9, zorder=2, label="实际行驶轨迹")
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
    extra = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor=ORANGE, markeredgecolor=INK, label="已听待清"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=GREEN, markeredgecolor=INK, label="已清除"),
    ]
    ax.legend(
        handles=ax.get_legend_handles_labels()[0] + extra,
        loc="lower right",
        frameon=True,
        fancybox=False,
        edgecolor="#DDDDDD",
        fontsize=8,
    )

    omni_index = {s.channel: i for i, s in enumerate(omni)}
    dir_index = {s.channel: i for i, s in enumerate(directional)}

    def _recolor() -> None:
        fr = frames[0]
        # placeholder; real colors set in update
        del fr

    def update(i: int):
        fr = frames[i]
        trail_line.set_data([p[0] for p in fr["trail"]], [p[1] for p in fr["trail"]])
        if omni:
            omni_colors = [
                _state_color(s.channel, fr["heard"], fr["cleared"], OMNI_FILL) for s in omni
            ]
            omni_sc.set_facecolor(omni_colors)
        if directional:
            dir_colors = [
                _state_color(s.channel, fr["heard"], fr["cleared"], DIR_FILL) for s in directional
            ]
            dir_sc.set_facecolor(dir_colors)
            for src in directional:
                wedges[src.channel].set_facecolor(
                    _state_color(src.channel, fr["heard"], fr["cleared"], DIR_FILL)
                )
        robot.set_offsets([fr["xy"]])
        ang = _heading(fr["trail"])
        dx, dy = 90.0 * math.cos(ang), 90.0 * math.sin(ang)
        arrow.set_positions(fr["xy"], (fr["xy"][0] + dx, fr["xy"][1] + dy))
        n_omni = sum(s.heading_deg is None for s in sources)
        n_dir = len(sources) - n_omni
        title.set_text("问题 4 机器狗全路径（圆=全向源，三角+扇形=定向源 180° 前瓣）")
        status.set_text(
            f"动作：{fr['action']}\n"
            f"虚拟时间：{fr['vt']:.0f} s\n"
            f"已清除：{len(fr['cleared'])} / {stats['cleared']}\n"
            f"全向 {n_omni} · 定向 {n_dir}"
        )
        return trail_line, omni_sc, dir_sc, robot, arrow, title, status

    update(len(frames) - 1)
    fig.savefig(OUT_PNG, dpi=160, bbox_inches="tight", facecolor="white")
    anim = animation.FuncAnimation(fig, update, frames=len(frames), interval=55, blit=False)
    anim.save(str(OUT_GIF), writer=animation.PillowWriter(fps=16))
    plt.close(fig)
    del src_by_ch, omni_index, dir_index, _recolor


def main() -> None:
    seed, n, n_dir = 3, 12, 6
    sources, stats, frames = build_run(seed, n, n_dir)
    if stats["cleared"] != n:
        raise SystemExit(f"未全清 cleared={stats['cleared']} n={n}")
    render(sources, stats, frames)
    n_omni = sum(s.heading_deg is None for s in sources)
    print(
        f"seed={seed} n={n} omni={n_omni} dir={n_dir} "
        f"vt={stats['virtual_time_s']:.1f} travel={stats.get('travel_s'):.1f} "
        f"frames={len(frames)}"
    )
    print("wrote", OUT_GIF)
    print("wrote", OUT_PNG)


if __name__ == "__main__":
    main()
