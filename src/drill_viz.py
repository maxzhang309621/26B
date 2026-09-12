"""Rebuild a practice-drill map: robot path + reconstructed jammer positions.

Official result JSON does not include ground-truth coordinates.  Source
locations are taken from successful /clear points (must be ≤20 m) and, if
needed, from AOA inversion of the same action log.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, Wedge

from coverage import (
    directional_waypoints,
    omni_waypoints,
    q3_waypoints,
    q4_opt_search_waypoints,
)
from geometry import Point, Q3_ARENA_R, add, dist, scale, unit
from inversion import invert_channel
from log_parse import ChannelObs, extract_log, parse_action_log

ARENA_R = Q3_ARENA_R
BLUE = "#2166AC"
RED = "#B2182B"
GREEN = "#1B7837"
ORANGE = "#E08214"
PURPLE = "#762A83"
GREY = "#888888"
INK = "#222222"
OMNI_FILL = "#92C5DE"
DIR_FILL = "#F1A340"
WEDGE_R = 240.0
DEFAULT_DRILL_DIR = Path(__file__).resolve().parent.parent / "output" / "drill"
DEFAULT_FIG_DIR = Path(__file__).resolve().parent.parent / "output" / "figures"


@dataclass
class PathEvent:
    xy: Point
    kind: str
    channel: int | None
    result: str | None
    vt: float


@dataclass
class ReconstructedSource:
    channel: int
    xy: Point
    origin: str
    cleared: bool
    directional: bool | None
    heading_deg: float | None


@dataclass
class DrillScene:
    problem: str
    stats: dict[str, Any]
    events: list[PathEvent]
    sources: list[ReconstructedSource]
    waypoints: list[Point] = field(default_factory=list)
    path: Path | None = None


def _setup_font() -> None:
    mpl.rcParams.update(
        {
            "font.size": 10,
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "legend.fontsize": 8.5,
            "axes.unicode_minus": False,
            "pdf.fonttype": 42,
            "savefig.bbox": "tight",
        }
    )
    for name in ("Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Source Han Sans SC"):
        if any(name.lower() in f.name.lower() for f in font_manager.fontManager.ttflist):
            mpl.rcParams["font.sans-serif"] = [name, "DejaVu Sans"]
            return
    mpl.rcParams["font.sans-serif"] = ["DejaVu Sans"]


def _clip_arena(p: Point, radius: float = ARENA_R) -> Point:
    r = dist(p, (0.0, 0.0))
    if r > radius:
        return scale(p, (radius - 1e-6) / r)
    return p


def _xy(payload: dict[str, Any]) -> Point | None:
    pos = payload.get("position")
    if not isinstance(pos, dict):
        return None
    try:
        return (float(pos["x"]), float(pos["y"]))
    except (KeyError, TypeError, ValueError):
        return None


def extract_path(log: Iterable[dict[str, Any]]) -> list[PathEvent]:
    """Accepted /measure and /clear poses in time order, including start at origin."""
    out: list[PathEvent] = [PathEvent((0.0, 0.0), "start", None, None, 0.0)]
    for rec in log:
        if not isinstance(rec, dict):
            continue
        path = rec.get("path")
        if path not in ("/measure", "/clear"):
            continue
        body = rec.get("response") or {}
        if body.get("accepted") is not True:
            continue
        req = rec.get("request") or {}
        xy = _xy(req)
        if xy is None:
            continue
        ch = req.get("channel")
        try:
            channel = int(ch) if ch is not None else None
        except (TypeError, ValueError):
            channel = None
        vt = float(body.get("virtual_time_s") or 0.0)
        if path == "/measure":
            out.append(
                PathEvent(xy, "measure", channel, body.get("measure_result"), vt)
            )
        else:
            out.append(
                PathEvent(xy, "clear", channel, body.get("clear_result"), vt)
            )
    collapsed: list[PathEvent] = []
    for ev in out:
        if collapsed and dist(collapsed[-1].xy, ev.xy) < 1.0:
            collapsed[-1] = ev
        else:
            collapsed.append(ev)
    return collapsed


def _along_ray(obs: ChannelObs, rho: float = 400.0) -> Point | None:
    if not obs.stations:
        return None
    return _clip_arena(add(obs.stations[0], scale(unit(obs.bearings_deg[0]), rho)))


def _infer_directional(obs: ChannelObs, src: Point) -> tuple[bool | None, float | None]:
    if not obs.stations:
        return None, None
    hear_d = min(dist(p, src) for p in obs.stations)
    behind = [p for p in obs.silence if dist(p, src) + 80.0 < hear_d]
    directional = bool(behind)
    ux = uy = 0.0
    for p in obs.stations:
        dx, dy = p[0] - src[0], p[1] - src[1]
        n = math.hypot(dx, dy)
        if n < 1e-9:
            continue
        ux += dx / n
        uy += dy / n
    if abs(ux) < 1e-12 and abs(uy) < 1e-12:
        heading = None
    else:
        heading = math.degrees(math.atan2(uy, ux))
    if not directional:
        heading = None
    return directional, heading


def reconstruct_sources(
    grouped: dict[int, ChannelObs],
    *,
    problem: str = "4",
) -> list[ReconstructedSource]:
    """One marker per heard/cleared channel. Prefer successful clear, else invert."""
    out: list[ReconstructedSource] = []
    for ch, obs in sorted(grouped.items()):
        cleared = any(obs.clear_ok)
        xy: Point | None = None
        origin = "none"
        if cleared:
            for p, ok in zip(obs.clear_xy, obs.clear_ok):
                if ok:
                    xy, origin = p, "clear"
                    break
        if xy is None and obs.near:
            xy, origin = obs.near[-1], "near"
        if xy is None:
            inv = invert_channel(obs)
            if inv.point_est is not None:
                xy, origin = inv.point_est, "invert"
        if xy is None:
            xy = _along_ray(obs)
            origin = "along_ray" if xy is not None else "none"
        if xy is None:
            continue
        if str(problem) == "3":
            directional, heading = False, None
        else:
            directional, heading = _infer_directional(obs, xy)
        out.append(
            ReconstructedSource(
                channel=ch,
                xy=_clip_arena(xy, ARENA_R + 50.0),
                origin=origin,
                cleared=cleared,
                directional=directional,
                heading_deg=heading,
            )
        )
    return out


def _ring(n: int, radius: float) -> list[Point]:
    if n <= 0 or radius <= 0:
        return []
    return [
        (radius * math.cos(2.0 * math.pi * k / n), radius * math.sin(2.0 * math.pi * k / n))
        for k in range(n)
    ]


def planned_waypoints(stats: dict[str, Any], problem: str) -> list[Point]:
    """Same listen set the hunt actually used, including Q3's 10° ring phase."""
    if str(problem) == "3":
        n = stats.get("q3_ring_n")
        r = stats.get("q3_ring_r")
        profile = stats.get("q3_path_profile")
        if profile == "batch" or n == 6:
            if isinstance(r, (int, float)) and r > 0:
                return q3_waypoints(ring_r=float(r))
            return q3_waypoints()
        if isinstance(n, int) and isinstance(r, (int, float)) and n > 0:
            return omni_waypoints(ring_r=float(r), n=n)
        return omni_waypoints()

    profile = stats.get("q4_path_profile")
    inner_n = stats.get("q4_inner_n")
    inner_r = stats.get("q4_inner_r")
    outer_n = stats.get("q4_outer_n")
    outer_r = stats.get("q4_outer_r")
    if profile == "hexbatch" or inner_n == 7:
        kwargs: dict[str, Any] = {}
        if isinstance(outer_r, (int, float)):
            kwargs["outer_r"] = float(outer_r)
        if isinstance(outer_n, int):
            kwargs["outer_n"] = outer_n
        return q4_opt_search_waypoints(**kwargs)
    if profile == "pathopt":
        return directional_waypoints()
    pts: list[Point] = [(0.0, 0.0)]
    if isinstance(inner_n, int) and isinstance(inner_r, (int, float)) and inner_n > 0:
        pts.extend(_ring(inner_n, float(inner_r)))
    if isinstance(outer_n, int) and isinstance(outer_r, (int, float)) and outer_n > 0:
        pts.extend(_ring(outer_n, float(outer_r)))
    if len(pts) > 1:
        return pts
    return directional_waypoints()


def load_drill(path: Path | str) -> DrillScene:
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} 不是含 stats/log 的演练 JSON")
    log = extract_log(data)
    stats = data.get("stats") if isinstance(data.get("stats"), dict) else {}
    problem = str(data.get("problem") or "4")
    if problem not in ("3", "4"):
        problem = "4"
    grouped = parse_action_log(log)
    return DrillScene(
        problem=problem,
        stats=stats,
        events=extract_path(log),
        sources=reconstruct_sources(grouped, problem=problem),
        waypoints=planned_waypoints(stats, problem),
        path=path,
    )


def latest_drill(problem: str | None = None, drill_dir: Path | None = None) -> Path:
    folder = drill_dir or DEFAULT_DRILL_DIR
    if problem in ("3", "4"):
        files = list(folder.glob(f"p{problem}-*.json"))
    else:
        files = list(folder.glob("p3-*.json")) + list(folder.glob("p4-*.json"))
    files = [p for p in files if p.is_file()]
    if not files:
        raise FileNotFoundError(f"{folder} 里没有 p3-/p4- 演练日志")
    return max(files, key=lambda p: p.stat().st_mtime)


def _polyline(events: Sequence[PathEvent]) -> list[Point]:
    pts: list[Point] = []
    for ev in events:
        if not pts or dist(pts[-1], ev.xy) >= 1.0:
            pts.append(ev.xy)
    return pts


def render_drill_map(
    scene: DrillScene,
    out_png: Path,
    out_pdf: Path | None = None,
) -> Path:
    """Static full-path map with reconstructed jammer markers."""
    _setup_font()
    out_png = Path(out_png)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    trail = _polyline(scene.events)
    omni = [s for s in scene.sources if not s.directional]
    directional = [s for s in scene.sources if s.directional]
    fig, ax = plt.subplots(figsize=(7.6, 7.8), dpi=120)
    ax.add_patch(Circle((0.0, 0.0), ARENA_R, fill=False, ls="--", lw=1.0, ec=GREY, zorder=0))
    wps = scene.waypoints
    if len(wps) > 1:
        ax.scatter(
            [p[0] for p in wps],
            [p[1] for p in wps],
            s=18,
            c="white",
            edgecolors=BLUE,
            linewidths=0.8,
            zorder=3,
            label="计划听点",
        )
    if trail:
        ax.plot(
            [p[0] for p in trail],
            [p[1] for p in trail],
            color=BLUE,
            lw=1.7,
            alpha=0.9,
            zorder=2,
            label="实际行驶轨迹",
        )
        ax.scatter([trail[0][0]], [trail[0][1]], s=42, c=BLUE, zorder=5, label="起点")
        ax.scatter([trail[-1][0]], [trail[-1][1]], s=70, c=RED, zorder=8, label="终点")

    for src in directional:
        heading = float(src.heading_deg or 0.0)
        face = GREEN if src.cleared else DIR_FILL
        ax.add_patch(
            Wedge(
                src.xy,
                WEDGE_R,
                heading - 90.0,
                heading + 90.0,
                facecolor=face,
                edgecolor=PURPLE,
                lw=0.7,
                alpha=0.35,
                zorder=5,
            )
        )
        hx = src.xy[0] + 160.0 * math.cos(math.radians(heading))
        hy = src.xy[1] + 160.0 * math.sin(math.radians(heading))
        ax.annotate(
            "",
            xy=(hx, hy),
            xytext=src.xy,
            arrowprops={"arrowstyle": "->", "color": PURPLE, "lw": 1.05},
            zorder=6,
        )
        ax.annotate(
            f"定向 ch{src.channel}",
            xy=src.xy,
            xytext=(8, 8),
            textcoords="offset points",
            fontsize=7.5,
            color=PURPLE,
            zorder=10,
        )
    if omni:
        ax.scatter(
            [s.xy[0] for s in omni],
            [s.xy[1] for s in omni],
            s=64,
            c=[GREEN if s.cleared else OMNI_FILL for s in omni],
            edgecolors=BLUE,
            linewidths=1.1,
            zorder=6,
            label="全向源（圆）",
        )
        for src in omni:
            ax.annotate(
                f"全向 ch{src.channel}",
                xy=src.xy,
                xytext=(8, 8),
                textcoords="offset points",
                fontsize=7.5,
                color=BLUE,
                zorder=10,
            )
    if directional:
        ax.scatter(
            [s.xy[0] for s in directional],
            [s.xy[1] for s in directional],
            s=56,
            c=[GREEN if s.cleared else DIR_FILL for s in directional],
            marker="^",
            edgecolors=PURPLE,
            linewidths=1.1,
            zorder=7,
            label="定向源（三角+前瓣）",
        )

    n_clear = int(scene.stats.get("cleared") or sum(1 for s in scene.sources if s.cleared))
    vt = scene.stats.get("virtual_time_s")
    vt_txt = f"{float(vt):.0f} s" if isinstance(vt, (int, float)) else "—"
    title_p = "问题 3" if scene.problem == "3" else "问题 4"
    ax.set_title(f"{title_p} 演练全路径（圆=全向源，三角+扇形=定向源；位置由清除点/反演还原）")
    ax.text(
        0.02,
        0.98,
        f"已清除：{n_clear}\n虚拟时间：{vt_txt}\n源点数：{len(scene.sources)}",
        transform=ax.transAxes,
        va="top",
        ha="left",
        fontsize=9,
        color=INK,
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.82, "pad": 3.5},
    )
    ax.set_aspect("equal")
    ax.set_xlim(-2300, 2300)
    ax.set_ylim(-2300, 2550)
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    extra = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor=GREEN, markeredgecolor=INK, label="已清除"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=OMNI_FILL, markeredgecolor=INK, label="未清除估计"),
    ]
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(
        handles + extra,
        labels + [e.get_label() for e in extra],
        loc="lower right",
        frameon=True,
        fancybox=False,
        edgecolor="#DDDDDD",
        fontsize=8,
    )
    fig.savefig(out_png, dpi=160, facecolor="white")
    if out_pdf is not None:
        fig.savefig(out_pdf, facecolor="white")
    plt.close(fig)
    return out_png


def render_drill_gif(scene: DrillScene, out_gif: Path, step_m: float = 110.0) -> Path:
    """Optional animation of the reconstructed path."""
    from matplotlib import animation

    _setup_font()
    out_gif = Path(out_gif)
    out_gif.parent.mkdir(parents=True, exist_ok=True)
    trail_pts = _polyline(scene.events)
    if len(trail_pts) < 2:
        raise ValueError("轨迹点不足，无法生成动图")
    frames: list[list[Point]] = []
    acc: list[Point] = [trail_pts[0]]
    for i in range(1, len(trail_pts)):
        a, b = trail_pts[i - 1], trail_pts[i]
        gap = dist(a, b)
        n = max(1, int(round(gap / step_m)))
        for k in range(1, n + 1):
            t = k / n
            xy = (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))
            acc.append(xy)
            frames.append(list(acc))
    fig, ax = plt.subplots(figsize=(7.2, 7.4), dpi=100)
    ax.add_patch(Circle((0.0, 0.0), ARENA_R, fill=False, ls="--", lw=1.0, ec=GREY, zorder=0))
    for src in scene.sources:
        color = GREEN if src.cleared else (DIR_FILL if src.directional else OMNI_FILL)
        marker = "^" if src.directional else "o"
        ax.scatter([src.xy[0]], [src.xy[1]], s=50, c=color, marker=marker, edgecolors=INK, zorder=6)
        if src.directional and src.heading_deg is not None:
            ax.add_patch(
                Wedge(
                    src.xy,
                    WEDGE_R,
                    float(src.heading_deg) - 90.0,
                    float(src.heading_deg) + 90.0,
                    facecolor=color,
                    edgecolor=PURPLE,
                    lw=0.6,
                    alpha=0.32,
                    zorder=5,
                )
            )
    (line,) = ax.plot([], [], color=BLUE, lw=1.7, zorder=2)
    robot = ax.scatter([], [], s=64, c=RED, zorder=8)
    ax.set_aspect("equal")
    ax.set_xlim(-2300, 2300)
    ax.set_ylim(-2300, 2400)
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    title_p = "问题 3" if scene.problem == "3" else "问题 4"
    ax.set_title(f"{title_p} 演练全路径动图")

    def update(i: int):
        fr = frames[i]
        line.set_data([p[0] for p in fr], [p[1] for p in fr])
        robot.set_offsets([fr[-1]])
        return line, robot

    anim = animation.FuncAnimation(fig, update, frames=len(frames), interval=50, blit=False)
    anim.save(str(out_gif), writer=animation.PillowWriter(fps=16))
    plt.close(fig)
    return out_gif


def _default_stems(scene: DrillScene) -> tuple[Path, Path, Path]:
    stem = scene.path.stem if scene.path is not None else f"p{scene.problem}-drill"
    base = DEFAULT_FIG_DIR / stem
    return base.with_name(f"{stem}_path.png"), base.with_name(f"{stem}_path.pdf"), base.with_name(f"{stem}_path.gif")


def main(argv: Sequence[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="由演练动作日志绘制机器狗全路径与干扰源位置。")
    p.add_argument("--drill", type=Path, default=None, help="output/drill/p4-*.json")
    p.add_argument("--latest", choices=("3", "4"), default=None, help="使用最新一局问题3/4日志")
    p.add_argument("--out", type=Path, default=None, help="输出 PNG 路径")
    p.add_argument("--gif", action="store_true", help="额外输出 GIF 动图")
    args = p.parse_args(argv)
    if args.drill is None and args.latest is None:
        args.latest = "4"
    path = args.drill if args.drill is not None else latest_drill(args.latest)
    scene = load_drill(path)
    png, pdf, gif = _default_stems(scene)
    if args.out is not None:
        png = args.out
        pdf = args.out.with_suffix(".pdf")
        gif = args.out.with_suffix(".gif")
    render_drill_map(scene, png, pdf)
    print("drill", path)
    print("sources", len(scene.sources), "cleared", sum(1 for s in scene.sources if s.cleared))
    print("wrote", png)
    print("wrote", pdf)
    if args.gif:
        render_drill_gif(scene, gif)
        print("wrote", gif)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()
