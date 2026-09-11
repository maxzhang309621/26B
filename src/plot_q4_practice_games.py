"""Plot real Q4 practice paths and inferred jammer positions from drill logs."""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

from coverage import ARENA_R, ENROUTE_R, OMNI_RING_N, directional_waypoints
from geometry import Point, dist

ROOT = Path(__file__).resolve().parents[1]
DRILL = ROOT / "output" / "drill"
OUT = ROOT / "output" / "q4-results"


def v_nofar_waypoints() -> list[Point]:
    """Baseline cover set: inner 8×1200 + outer 12×2100 + 900 enroute."""
    wps = directional_waypoints(outer_r=2100.0, outer_n=12)
    for k in range(OMNI_RING_N):
        a = 2.0 * math.pi * k / OMNI_RING_N
        wps.append((ENROUTE_R * math.cos(a), ENROUTE_R * math.sin(a)))
    return wps


def _setup_font() -> None:
    import matplotlib.pyplot as plt
    from matplotlib import font_manager

    for name in ("Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Source Han Sans SC"):
        if any(name.lower() in f.name.lower() for f in font_manager.fontManager.ttflist):
            plt.rcParams["font.sans-serif"] = [name, "DejaVu Sans"]
            plt.rcParams["axes.unicode_minus"] = False
            return


@dataclass
class ChannelTrace:
    channel: int
    events: list[tuple[Point, str, float | None]] = field(default_factory=list)
    clear_xy: Point | None = None


@dataclass
class GameTrace:
    label: str
    log_path: Path
    virtual_time_s: float
    cleared: int
    jammer_count: int | None
    omni_n: int | None
    dir_n: int | None
    case_code: str | None
    path: list[Point] = field(default_factory=list)
    cover_stops: list[Point] = field(default_factory=list)
    channels: dict[int, ChannelTrace] = field(default_factory=dict)


def _xy(req: dict) -> Point:
    p = req.get("position") or {}
    return (float(p.get("x", 0.0)), float(p.get("y", 0.0)))


def _angle_span(angles: list[float]) -> float:
    if len(angles) < 2:
        return 0.0
    angles = sorted(a % (2.0 * math.pi) for a in angles)
    gaps = [angles[i + 1] - angles[i] for i in range(len(angles) - 1)]
    gaps.append(angles[0] + 2.0 * math.pi - angles[-1])
    return max(gaps)


def classify_source(ch: ChannelTrace, source: Point) -> str:
    """Heuristic omni vs directional from listen geometry."""
    hears = [(xy, b) for xy, kind, b in ch.events if kind in ("direction", "near")]
    if len(hears) < 2:
        return "dir"
    angles = [math.atan2(xy[1] - source[1], xy[0] - source[0]) for xy, _ in hears]
    # Narrow angular sector from listen points ⇒ directional lobe.
    if _angle_span(angles) < math.radians(140.0):
        return "dir"
    no_sigs = [xy for xy, kind, _ in ch.events if kind == "no_signal"]
    for xy in no_sigs:
        if 120.0 < dist(xy, source) < 1100.0:
            return "dir"
    return "omni"


def parse_game(log_path: Path, label: str, meta: dict | None = None) -> GameTrace:
    data = json.loads(log_path.read_text(encoding="utf-8"))
    stats = data.get("stats") or {}
    off = (meta or {}).get("official") or {}
    gt = GameTrace(
        label=label,
        log_path=log_path,
        virtual_time_s=float(stats.get("virtual_time_s") or 0.0),
        cleared=int(stats.get("cleared") or 0),
        jammer_count=off.get("jammer_count"),
        omni_n=off.get("omnidirectional_jammer_count"),
        dir_n=off.get("directional_jammer_count"),
        case_code=off.get("case_code"),
    )
    cover_wps = v_nofar_waypoints()
    pos: Point | None = None
    scan_bucket: dict[Point, set[int]] = {}

    for rec in data.get("log") or []:
        path = rec.get("path")
        if path not in ("/measure", "/clear"):
            continue
        body = rec.get("response") or {}
        if body.get("accepted") is not True:
            continue
        req = rec.get("request") or {}
        xy = _xy(req)
        ch = int(req.get("channel") or 0)
        if pos is not None:
            gt.path.append(xy)
        else:
            gt.path.append(xy)
        pos = xy

        if path == "/measure":
            kind = str(body.get("measure_result") or "")
            bearing = float(body["svd_deg"]) if kind == "direction" else None
            ct = gt.channels.setdefault(ch, ChannelTrace(channel=ch))
            ct.events.append((xy, kind, bearing))
            key = (round(xy[0], 1), round(xy[1], 1))
            scan_bucket.setdefault(key, set()).add(ch)
        else:
            if body.get("clear_result") == "success":
                ct = gt.channels.setdefault(ch, ChannelTrace(channel=ch))
                ct.clear_xy = xy

    for key, chs in scan_bucket.items():
        xy = key
        p: Point = (xy[0], xy[1])
        near_cover = any(dist(p, wp) <= 150.0 for wp in cover_wps)
        if len(chs) >= 8 or (near_cover and len(chs) >= 3) or dist(p, (0.0, 0.0)) < 30.0:
            gt.cover_stops.append(p)

    return gt


def load_meta(log_path: Path) -> dict | None:
    name = log_path.name
    for batch in (DRILL / "overnight_v_nofar_10.json", DRILL / "q4-batch-summary.json"):
        if not batch.exists():
            continue
        rows = json.loads(batch.read_text(encoding="utf-8"))
        for row in rows:
            lp = row.get("log_path") or ""
            if lp.replace("\\", "/").endswith(name):
                return row
    return None


def plot_game(ax, gt: GameTrace, *, show_cover_only: bool) -> None:
    import matplotlib.pyplot as plt

    ax.add_patch(plt.Circle((0, 0), ARENA_R, fill=False, linestyle="--", color="#888", lw=1.0))
    wps = v_nofar_waypoints()
    ax.scatter(
        [p[0] for p in wps if dist(p, (0, 0)) > 2000],
        [p[1] for p in wps if dist(p, (0, 0)) > 2000],
        s=18,
        c="#9ecae1",
        alpha=0.7,
        label="外环2100参考",
        zorder=1,
    )
    ax.scatter(
        [p[0] for p in wps if 1100 < dist(p, (0, 0)) < 1300],
        [p[1] for p in wps if 1100 < dist(p, (0, 0)) < 1300],
        s=22,
        c="#6baed6",
        alpha=0.7,
        label="内环1200参考",
        zorder=1,
    )

    if gt.path:
        xs = [p[0] for p in gt.path]
        ys = [p[1] for p in gt.path]
        if show_cover_only and gt.cover_stops:
            stops = gt.cover_stops
            ax.plot([p[0] for p in stops], [p[1] for p in stops], "-", color="#fdae6b", lw=1.8, alpha=0.9, zorder=2)
            ax.scatter([p[0] for p in stops], [p[1] for p in stops], s=28, c="#e6550d", zorder=3)
        else:
            ax.plot(xs, ys, "-", color="#bdbdbd", lw=0.8, alpha=0.85, zorder=2)
            ax.plot(xs, ys, "-", color="#636363", lw=1.4, alpha=0.55, zorder=3)

    omni_pts: list[Point] = []
    dir_pts: list[Point] = []
    for ch, trace in sorted(gt.channels.items()):
        if trace.clear_xy is None:
            continue
        kind = classify_source(trace, trace.clear_xy)
        (omni_pts if kind == "omni" else dir_pts).append(trace.clear_xy)

    if omni_pts:
        ax.scatter(
            [p[0] for p in omni_pts],
            [p[1] for p in omni_pts],
            s=120,
            marker="o",
            c="#2ca25f",
            edgecolors="white",
            linewidths=0.8,
            label=f"全向源({len(omni_pts)})",
            zorder=5,
        )
    if dir_pts:
        ax.scatter(
            [p[0] for p in dir_pts],
            [p[1] for p in dir_pts],
            s=140,
            marker="^",
            c="#de2d26",
            edgecolors="white",
            linewidths=0.8,
            label=f"定向源({len(dir_pts)})",
            zorder=5,
        )

    ax.scatter([0], [0], s=50, c="black", marker="+", zorder=6)
    n_txt = gt.jammer_count if gt.jammer_count is not None else "?"
    omni_txt = gt.omni_n if gt.omni_n is not None else "?"
    dir_txt = gt.dir_n if gt.dir_n is not None else "?"
    title = (
        f"{gt.label}\n"
        f"VT={gt.virtual_time_s:.0f}s  清除 {gt.cleared}/{n_txt}  "
        f"官方 全向{omni_txt}+定向{dir_txt}"
    )
    ax.set_title(title, fontsize=11)
    ax.set_aspect("equal")
    ax.set_xlim(-1950, 1950)
    ax.set_ylim(-1950, 1950)
    ax.grid(True, alpha=0.25)
    ax.legend(loc="upper right", fontsize=8)


def save_figure(fig, path: Path) -> None:
    _setup_font()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=170, bbox_inches="tight")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=OUT)
    args = parser.parse_args()

    cases = [
        ("慢局 v_nofar #9", DRILL / "p4-20260911-031051.json"),
        ("快局 v_nofar #5", DRILL / "p4-20260911-030938.json"),
        ("快局 v_nofar #3 全定向16", DRILL / "p4-20260911-030902.json"),
        ("慢局 outer11+q12 #8", DRILL / "p4-20260911-131424.json"),
    ]
    games: list[GameTrace] = []
    for label, path in cases:
        if not path.exists():
            print("missing", path)
            continue
        games.append(parse_game(path, label, load_meta(path)))

    import matplotlib.pyplot as plt

    _setup_font()

    # 2×2 full path
    fig, axes = plt.subplots(2, 2, figsize=(13, 13))
    for ax, gt in zip(axes.ravel(), games):
        plot_game(ax, gt, show_cover_only=False)
    fig.suptitle("Q4 官方演练：慢局 vs 快局（完整行走路径 + 推断源位置）", fontsize=14, y=0.98)
    save_figure(fig, args.out_dir / "fig6_real_games_full_path.png")
    plt.close(fig)

    # 2×2 cover-only path
    fig, axes = plt.subplots(2, 2, figsize=(13, 13))
    for ax, gt in zip(axes.ravel(), games):
        plot_game(ax, gt, show_cover_only=True)
    fig.suptitle("Q4 官方演练：覆盖停靠连线（橙）+ 源位置", fontsize=14, y=0.98)
    save_figure(fig, args.out_dir / "fig7_real_games_cover_path.png")
    plt.close(fig)

    # slow vs fast pair (v_nofar only)
    fig, axes = plt.subplots(1, 2, figsize=(13, 6.5))
    for ax, gt in zip(axes, games[:2]):
        plot_game(ax, gt, show_cover_only=False)
    fig.suptitle("v_nofar 基线：慢局 #9 (10283s) vs 快局 #5 (6162s)", fontsize=13)
    save_figure(fig, args.out_dir / "fig8_v_nofar_slow_vs_fast.png")
    plt.close(fig)

    summary = []
    for gt in games:
        sources = []
        for ch, tr in sorted(gt.channels.items()):
            if tr.clear_xy is None:
                continue
            sources.append(
                {
                    "channel": ch,
                    "x": tr.clear_xy[0],
                    "y": tr.clear_xy[1],
                    "r": dist(tr.clear_xy, (0.0, 0.0)),
                    "inferred_type": classify_source(tr, tr.clear_xy),
                }
            )
        summary.append(
            {
                "label": gt.label,
                "log": str(gt.log_path.relative_to(ROOT)),
                "virtual_time_s": gt.virtual_time_s,
                "cleared": gt.cleared,
                "jammer_count": gt.jammer_count,
                "official_omni": gt.omni_n,
                "official_dir": gt.dir_n,
                "case_code": gt.case_code,
                "path_points": len(gt.path),
                "cover_stops": len(gt.cover_stops),
                "sources": sources,
            }
        )
    (args.out_dir / "real_games_path_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("wrote", args.out_dir / "fig6_real_games_full_path.png")
    print("wrote", args.out_dir / "fig7_real_games_cover_path.png")
    print("wrote", args.out_dir / "fig8_v_nofar_slow_vs_fast.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
