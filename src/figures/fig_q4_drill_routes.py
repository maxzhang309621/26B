"""Q4 drill route maps with collision-avoiding source labels.

Renders the three manuscript route figures (16 / 12 / 10 sources) from the
same drill logs used in the paper.  Also renders one combined three-panel
figure (no overall title) with a shared legend.

Outputs: output/figures/q4_final/fig7_drill_16src.png,
         fig7b_drill_12src.png, fig8_drill_10src.png,
         fig7_8_drill_combined.png (plus overlap reports).
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Circle, Wedge  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "paper_workspace"))

from fig_q4_redraw import _overlap_report  # noqa: E402

from drill_viz import (  # noqa: E402
    ARENA_R,
    BLUE,
    DIR_FILL,
    GREEN,
    GREY,
    INK,
    OMNI_FILL,
    PURPLE,
    RED,
    WEDGE_R,
    _polyline,
    _setup_font,
    load_drill,
)

OUT = ROOT / "output" / "figures" / "q4_final"
DRILL = ROOT / "output" / "drill"
CASES = [
    ("fig7_drill_16src", "p4-20260912-210603.json", "a"),
    ("fig7b_drill_12src", "p4-20260912-210518.json", "b"),
    ("fig8_drill_10src", "p4-20260912-205941.json", "c"),
]


def _bbox(x: float, y: float, text: str, ha: str, va: str, cw: float, ch: float):
    w = cw * max(len(text), 1)
    if ha == "left":
        x0 = x
    elif ha == "right":
        x0 = x - w
    else:
        x0 = x - w / 2.0
    if va == "bottom":
        y0 = y
    elif va == "top":
        y0 = y - ch
    else:
        y0 = y - ch / 2.0
    return (x0, y0, x0 + w, y0 + ch)


def _overlap(a, b) -> float:
    dx = min(a[2], b[2]) - max(a[0], b[0])
    dy = min(a[3], b[3]) - max(a[1], b[1])
    return dx * dy if dx > 0 and dy > 0 else 0.0


def _place_labels(ax, items, fig, obstacles, fontsize=7.0):
    """Greedy non-overlapping label placement in data coordinates."""
    fig.canvas.draw()
    extent = ax.get_window_extent(fig.canvas.get_renderer())
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    data_per_px_x = (x1 - x0) / extent.width
    data_per_px_y = (y1 - y0) / extent.height
    px_per_pt = fig.dpi / 72.0
    cw = 0.62 * fontsize * px_per_pt * data_per_px_x
    ch = 1.5 * fontsize * px_per_pt * data_per_px_y
    gap_x = 10.0 * px_per_pt * data_per_px_x
    gap_y = 10.0 * px_per_pt * data_per_px_y

    offsets = [
        (gap_x, gap_y, "left", "bottom"),
        (-gap_x, gap_y, "right", "bottom"),
        (gap_x, -gap_y, "left", "top"),
        (-gap_x, -gap_y, "right", "top"),
        (0.0, gap_y * 1.4, "center", "bottom"),
        (0.0, -gap_y * 1.4, "center", "top"),
        (gap_x * 1.2, 0.0, "left", "center"),
        (-gap_x * 1.2, 0.0, "right", "center"),
    ]

    obst = np.array(obstacles) if obstacles else np.zeros((0, 2))
    placed = []
    for x, y, _text, _color in items:
        placed.append((x - 40.0, y - 40.0, x + 40.0, y + 40.0))
    out = []
    for x, y, text, color in sorted(items, key=lambda it: -it[1]):
        best = None
        for dx, dy, ha, va in offsets:
            lx, ly = x + dx, y + dy
            box = _bbox(lx, ly, text, ha, va, cw, ch)
            score = sum(_overlap(box, b) for b in placed)
            score += 0.0005 * (dx * dx + dy * dy)
            if len(obst):
                inside = ((obst[:, 0] > box[0]) & (obst[:, 0] < box[2])
                          & (obst[:, 1] > box[1]) & (obst[:, 1] < box[3]))
                score += 4.0e4 * float(inside.sum())
            if best is None or score < best[0]:
                best = (score, lx, ly, ha, va, box)
        _, lx, ly, ha, va, box = best
        placed.append(box)
        out.append((x, y, lx, ly, ha, va, text, color))
    return out


def _draw_panel(ax, scene, fig, label: str | None = None) -> None:
    trail = _polyline(scene.events)
    omni = [s for s in scene.sources if not s.directional]
    directional = [s for s in scene.sources if s.directional]

    ax.add_patch(Circle((0.0, 0.0), ARENA_R, fill=False, ls="--", lw=1.0, ec=GREY, zorder=0))
    wps = scene.waypoints
    if len(wps) > 1:
        ax.scatter([p[0] for p in wps], [p[1] for p in wps], s=14, c="white",
                   edgecolors=BLUE, linewidths=0.8, zorder=3)
    if trail:
        ax.plot([p[0] for p in trail], [p[1] for p in trail], color=BLUE, lw=1.5,
                alpha=0.9, zorder=2)
        ax.scatter([trail[0][0]], [trail[0][1]], s=36, c=BLUE, zorder=5)
        ax.scatter([trail[-1][0]], [trail[-1][1]], s=58, c=RED, zorder=8)

    labels = []
    for src in directional:
        heading = float(src.heading_deg or 0.0)
        face = GREEN if src.cleared else DIR_FILL
        ax.add_patch(Wedge(src.xy, WEDGE_R, heading - 90.0, heading + 90.0, facecolor=face,
                           edgecolor=PURPLE, lw=0.7, alpha=0.35, zorder=5))
        hx = src.xy[0] + 160.0 * math.cos(math.radians(heading))
        hy = src.xy[1] + 160.0 * math.sin(math.radians(heading))
        ax.annotate("", xy=(hx, hy), xytext=src.xy,
                    arrowprops={"arrowstyle": "->", "color": PURPLE, "lw": 1.0}, zorder=6)
        labels.append((src.xy[0], src.xy[1], f"{src.channel}", PURPLE))
    if omni:
        ax.scatter([s.xy[0] for s in omni], [s.xy[1] for s in omni], s=54,
                   c=[GREEN if s.cleared else OMNI_FILL for s in omni],
                   edgecolors=BLUE, linewidths=1.0, zorder=6)
        for src in omni:
            labels.append((src.xy[0], src.xy[1], f"{src.channel}", BLUE))
    if directional:
        ax.scatter([s.xy[0] for s in directional], [s.xy[1] for s in directional], s=48,
                   c=[GREEN if s.cleared else DIR_FILL for s in directional], marker="^",
                   edgecolors=PURPLE, linewidths=1.0, zorder=7)

    ax.set_aspect("equal")
    ax.set_xlim(-2300, 2300)
    ax.set_ylim(-2300, 2550)

    obstacles: list[tuple[float, float]] = []
    if trail:
        for i in range(len(trail) - 1):
            a, b = trail[i], trail[i + 1]
            n = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) / 18.0))
            for k in range(n + 1):
                t = k / n
                obstacles.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
    for radius in sorted({round(math.hypot(p[0], p[1]), 0) for p in scene.waypoints} | {ARENA_R}):
        if radius < 100:
            continue
        for k in range(96):
            a = 2.0 * math.pi * k / 96
            obstacles.append((radius * math.cos(a), radius * math.sin(a)))
    for src in directional:
        heading = math.radians(float(src.heading_deg or 0.0))
        for ang in (heading - math.pi / 2, heading + math.pi / 2):
            for r in np.linspace(0.0, WEDGE_R, 10):
                obstacles.append((src.xy[0] + r * math.cos(ang), src.xy[1] + r * math.sin(ang)))
        for th in np.linspace(heading - math.pi / 2, heading + math.pi / 2, 20):
            obstacles.append((src.xy[0] + WEDGE_R * math.cos(th), src.xy[1] + WEDGE_R * math.sin(th)))

    for x, y, lx, ly, ha, va, text, color in _place_labels(ax, labels, fig, obstacles):
        ax.plot([x, lx], [y, ly], color="#B9C2C8", lw=0.6, zorder=9)
        ax.text(lx, ly, text, fontsize=7.0, color=color, ha=ha, va=va, zorder=10,
                bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.85))

    n_clear = int(scene.stats.get("cleared") or sum(1 for s in scene.sources if s.cleared))
    vt = scene.stats.get("virtual_time_s")
    vt_txt = f"{float(vt):.0f} s" if isinstance(vt, (int, float)) else "—"
    ax.text(0.02, 0.98, f"已清除：{n_clear}\n虚拟时间：{vt_txt}\n源点数：{len(scene.sources)}",
            transform=ax.transAxes, va="top", ha="left", fontsize=8.5, color=INK,
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.82, "pad": 3.0})
    if label:
        ax.text(0.98, 0.98, f"({label})", transform=ax.transAxes, va="top", ha="right",
                fontsize=10, color=INK)
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def _legend_handles() -> list:
    return [
        Line2D([], [], marker="o", color="w", markerfacecolor="white", markeredgecolor=BLUE,
               markersize=6, label="计划听点"),
        Line2D([], [], color=BLUE, lw=1.6, label="实际行驶轨迹"),
        Line2D([], [], marker="o", ls="none", color=BLUE, ms=7, label="起点"),
        Line2D([], [], marker="o", ls="none", color=RED, ms=7, label="终点"),
        Line2D([], [], marker="o", ls="none", color=GREEN, ms=7, label="全向源（圆）"),
        Line2D([], [], marker="^", ls="none", color=DIR_FILL, ms=7, label="定向源（三角+前瓣）"),
        Line2D([], [], marker="o", ls="none", color=GREEN, ms=7, label="已清除"),
        Line2D([], [], marker="o", ls="none", color=OMNI_FILL, ms=7, label="未清除估计"),
    ]


def _save_png(fig, target: Path) -> Path:
    import time
    for _ in range(4):
        try:
            fig.savefig(target, dpi=300, facecolor="white")
            return target
        except OSError:
            time.sleep(2.5)
    target = target.with_name(target.stem + "_new" + target.suffix)
    fig.savefig(target, dpi=300, facecolor="white")
    print("WARN: target locked, saved as", target)
    return target


def render_combined(stem: str, cases: list[tuple[str, str, str]]) -> None:
    _setup_font()
    fig, axes = plt.subplots(1, 3, figsize=(15.6, 6.0), dpi=150, layout="constrained")
    for ax, (_stem, name, label) in zip(axes, cases):
        scene = load_drill(DRILL / name)
        _draw_panel(ax, scene, fig, label)
    fig.legend(handles=_legend_handles(), loc="lower center", ncol=8, frameon=False,
               fontsize=8, bbox_to_anchor=(0.5, -0.01), columnspacing=1.2, handletextpad=0.4)
    OUT.mkdir(parents=True, exist_ok=True)
    _overlap_report(fig, stem)
    _save_png(fig, OUT / f"{stem}.png")
    plt.close(fig)
    print(OUT / f"{stem}.png")


def render_case(stem: str, drill_name: str) -> None:
    _setup_font()
    scene = load_drill(DRILL / drill_name)
    fig, ax = plt.subplots(figsize=(7.6, 7.8), dpi=150, layout="constrained")
    _draw_panel(ax, scene, fig, None)
    fig.legend(handles=_legend_handles(), loc="lower center", ncol=4, frameon=False,
               fontsize=8, bbox_to_anchor=(0.5, -0.01), columnspacing=1.4, handletextpad=0.5)
    OUT.mkdir(parents=True, exist_ok=True)
    _overlap_report(fig, stem)
    _save_png(fig, OUT / f"{stem}.png")
    plt.close(fig)
    print(OUT / f"{stem}.png", "sources:", len(scene.sources))


def main() -> None:
    for stem, name, _label in CASES:
        render_case(stem, name)
    render_combined("fig7_8_drill_combined", CASES)


if __name__ == "__main__":
    main()
