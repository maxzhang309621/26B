"""Redraw Q4 manuscript figures 1, 2, 3, 4, 6, 9 with overlap-free layouts.

Bases:
- 图3/图4/图9: adapted from paper_workspace/fig_q4_solve_rings.py
- 图6:        adapted from paper_workspace/fig_q4_open_path_dp.py
- 图1/图2:    redrawn schematics (data from src/coverage.py and manuscript text)

Outputs: output/figures/q4_final/*.png (300 dpi, PNG only)
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Circle, FancyBboxPatch, Patch, Wedge  # noqa: E402
from matplotlib.text import Text  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from coverage import (  # noqa: E402
    ARENA_R,
    COVER_R,
    q4_double_ring_search_time,
    q4_opt_inner_r,
    q4_opt_search_waypoints,
)

mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Microsoft YaHei", "SimHei", "Arial", "Helvetica"],
        "font.size": 8,
        "axes.titlesize": 8,
        "axes.labelsize": 8,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "legend.fontsize": 7,
        "axes.unicode_minus": False,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.linewidth": 0.6,
        "legend.frameon": False,
        "savefig.bbox": "tight",
        "savefig.dpi": 300,
    }
)

BLUE, RED, GREEN, ORANGE, PURPLE, GREY = ["#2166AC", "#B2182B", "#1B7837", "#E08214", "#762A83", "#666666"]
BLACK = "#222222"
MM = 1 / 25.4
OUT = ROOT / "output" / "figures" / "q4_final"


def _overlap_report(fig, stem: str, tol: float = 1.5) -> None:
    """Print text-text, text-line and text-patch overlaps in display coords."""
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    items = []
    for ax in fig.axes:
        for t in list(ax.texts) + ([ax.title] if ax.get_title().strip() else []):
            if t.get_text().strip() and t.get_visible():
                items.append((ax, t))
        leg = ax.get_legend()
        if leg is not None:
            items.extend((ax, t) for t in leg.get_texts())
    boxes = []
    for ax, t in items:
        try:
            boxes.append((ax, t, Text.get_window_extent(t, renderer)))
        except Exception:
            continue
    issues: list[str] = []
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            a, b = boxes[i][2], boxes[j][2]
            dx = min(a.x1, b.x1) - max(a.x0, b.x0)
            dy = min(a.y1, b.y1) - max(a.y0, b.y0)
            if dx > tol and dy > tol:
                issues.append(f"text-text  [{boxes[i][1].get_text()}] x [{boxes[j][1].get_text()}] {dx:.0f}x{dy:.0f}px")
    for ax, t, bb in boxes:
        if ax is None:
            continue
        arts = []
        for ln in ax.lines:
            xy = ln.get_xydata()
            if len(xy) < 2:
                continue
            disp = ax.transData.transform(xy)
            for k in range(len(disp) - 1):
                a, b = disp[k], disp[k + 1]
                n = max(2, int(np.hypot(*(b - a)) / 2.0) + 1)
                for tt in np.linspace(0.0, 1.0, n):
                    arts.append((a + tt * (b - a), "line"))
        for p in ax.patches:
            try:
                verts = p.get_path().vertices
                if len(verts) == 0:
                    continue
                disp = p.get_transform().transform(verts)
                for k in range(len(disp)):
                    a, b = disp[k], disp[(k + 1) % len(disp)]
                    n = max(2, int(np.hypot(*(b - a)) / 2.0) + 1)
                    for tt in np.linspace(0.0, 1.0, n):
                        arts.append((a + tt * (b - a), type(p).__name__))
            except Exception:
                continue
        if not arts:
            continue
        pts = np.array([a[0] for a in arts])
        kinds = [a[1] for a in arts]
        inside = ((pts[:, 0] > bb.x0 + tol) & (pts[:, 0] < bb.x1 - tol)
                  & (pts[:, 1] > bb.y0 + tol) & (pts[:, 1] < bb.y1 - tol))
        if int(inside.sum()) > 0:
            hit = int(np.argmax(inside))
            data = ax.transData.inverted().transform(pts[hit])
            issues.append(f"text-curve [{t.get_text()}] {int(inside.sum())}px "
                          f"@data({data[0]:.0f},{data[1]:.0f}) by {kinds[hit]}")
    # legend frames vs curves
    for ax in fig.axes:
        leg = ax.get_legend()
        if leg is None:
            continue
        lb = leg.get_window_extent(renderer)
        pts = []
        for ln in ax.lines:
            xy = ln.get_xydata()
            if len(xy) < 2:
                continue
            disp = ax.transData.transform(xy)
            for k in range(len(disp) - 1):
                a, b = disp[k], disp[k + 1]
                n = max(2, int(np.hypot(*(b - a)) / 2.0) + 1)
                for tt in np.linspace(0.0, 1.0, n):
                    pts.append(a + tt * (b - a))
        for p in ax.patches:
            try:
                verts = p.get_path().vertices
                if len(verts) == 0:
                    continue
                disp = p.get_transform().transform(verts)
                for k in range(len(disp)):
                    a, b = disp[k], disp[(k + 1) % len(disp)]
                    n = max(2, int(np.hypot(*(b - a)) / 2.0) + 1)
                    for tt in np.linspace(0.0, 1.0, n):
                        pts.append(a + tt * (b - a))
            except Exception:
                continue
        if not pts:
            continue
        arr = np.array(pts)
        inside = ((arr[:, 0] > lb.x0) & (arr[:, 0] < lb.x1)
                  & (arr[:, 1] > lb.y0) & (arr[:, 1] < lb.y1))
        if int(inside.sum()) > 2:
            issues.append(f"legend-frame {int(inside.sum())}px curve points")
    tag = "OK " if not issues else "!! "
    print(f"{tag}{stem}: {len(issues)} issue(s)")
    report_path = OUT / "_overlap_report.txt"
    with report_path.open("a", encoding="utf-8") as fh:
        fh.write(f"{tag}{stem}: {len(issues)} issue(s)\n")
        for line in issues:
            fh.write(f"      {line}\n")
            print("     ", line)


def _save(fig, stem: str) -> None:
    _overlap_report(fig, stem)
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / f"{stem}.png"
    for attempt in range(3):
        try:
            fig.savefig(target, facecolor="white")
            break
        except OSError:
            import time
            time.sleep(2.5)
    else:
        target = OUT / f"{stem}_new.png"
        fig.savefig(target, facecolor="white")
        print("WARN: target locked, saved as", target)
    plt.close(fig)
    print(target)


# ---------------------------------------------------------------------------
# 图 1  hexbatch 听点
# ---------------------------------------------------------------------------

def fig1_hexbatch() -> None:
    opt = q4_opt_search_waypoints()
    inner, outer = opt[1:8], opt[8:]
    rho = q4_opt_inner_r()

    fig, ax = plt.subplots(figsize=(5.4, 5.4), layout="constrained")
    ax.set_aspect("equal")
    ax.add_patch(Circle((0, 0), ARENA_R, fill=False, ls=(0, (5, 3)), color="#9AA5AB", lw=0.9, zorder=1))
    for p in inner:
        ang = math.atan2(p[1], p[0])
        ax.plot([0, ARENA_R * math.cos(ang)], [0, ARENA_R * math.sin(ang)],
                color="#D8DEE2", lw=0.6, ls=(0, (1, 3)), zorder=0)

    ax.plot([p[0] for p in inner + [inner[0]]], [p[1] for p in inner + [inner[0]]],
            color=BLUE, lw=1.5, zorder=2)
    ax.plot([p[0] for p in outer + [outer[0]]], [p[1] for p in outer + [outer[0]]],
            color=ORANGE, lw=1.1, zorder=2)
    ax.scatter([p[0] for p in inner], [p[1] for p in inner], s=22, c=BLUE, zorder=4)
    ax.scatter([p[0] for p in outer], [p[1] for p in outer], s=20, c=ORANGE, marker="s", zorder=4)
    ax.scatter([0], [0], s=46, c=PURPLE, marker="D", zorder=5)
    ax.scatter([900.0], [0.0], s=34, c=GREEN, marker="^", zorder=5)

    ax.legend(
        handles=[
            Line2D([], [], marker="D", ls="none", color=PURPLE, ms=6, label="原点全扫"),
            Line2D([], [], marker="o", ls="none", color=BLUE, ms=6, label=f"内环 $7\\times{rho:.0f}$ m"),
            Line2D([], [], marker="s", ls="none", color=ORANGE, ms=6, label="外环 $12\\times1865$ m"),
            Line2D([], [], marker="^", ls="none", color=GREEN, ms=6, label="出发途听 900 m（不计入核验点集）"),
        ],
        loc="lower left", fontsize=6.2, handletextpad=0.4, borderaxespad=0.2, labelspacing=0.3,
    )
    ax.set_xlim(-2350, 2350)
    ax.set_ylim(-2350, 2350)
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_title("原点 + 内七边形 + 外十二边形（同径向）", loc="left", fontsize=8, fontweight="bold")
    _save(fig, "fig1_hexbatch_waypoints")


# ---------------------------------------------------------------------------
# 图 2  近心朝外源示意（带双环场景）
# ---------------------------------------------------------------------------

def fig2_near_center() -> None:
    opt = q4_opt_search_waypoints()
    inner, outer = opt[1:8], opt[8:]
    src = (550.0, 0.0)
    lobe_r = 1000.0

    fig, ax = plt.subplots(figsize=(5.8, 5.6), layout="constrained")
    ax.set_aspect("equal")
    ax.add_patch(Circle((0, 0), ARENA_R, fill=False, ls=(0, (5, 3)), color="#9AA5AB", lw=0.9, zorder=1))
    ax.plot([p[0] for p in inner + [inner[0]]], [p[1] for p in inner + [inner[0]]],
            color=BLUE, lw=0.9, alpha=0.40, zorder=2)
    ax.plot([p[0] for p in outer + [outer[0]]], [p[1] for p in outer + [outer[0]]],
            color=ORANGE, lw=0.8, alpha=0.40, zorder=2)
    ax.scatter([p[0] for p in inner], [p[1] for p in inner], s=12, c=BLUE, alpha=0.55, zorder=3)
    ax.scatter([p[0] for p in outer], [p[1] for p in outer], s=11, c=ORANGE, marker="s",
               alpha=0.55, zorder=3)

    ax.add_patch(Wedge(src, lobe_r, 90, 270, facecolor="#B8BFC4", alpha=0.12,
                       edgecolor="#9AA5AB", lw=0.7, ls=(0, (3, 2)), zorder=1))
    ax.add_patch(Wedge(src, lobe_r, -90, 90, facecolor=RED, alpha=0.13,
                       edgecolor=RED, lw=0.8, zorder=1))
    for sign in (1.0, -1.0):
        ax.plot([src[0], src[0]], [0, sign * 1950], color=RED, lw=0.6, ls=(0, (2, 3)),
                alpha=0.55, zorder=1)
    ax.annotate("", xy=(1960, 0), xytext=(0, 0),
                arrowprops=dict(arrowstyle="->", color=GREY, lw=0.9, ls=(0, (4, 2))), zorder=3)
    ax.annotate("", xy=(src[0] + 300, 0), xytext=(src[0] + 60, 0),
                arrowprops=dict(arrowstyle="->", color=RED, lw=1.2), zorder=6)

    ax.scatter([0], [0], s=46, c=BLUE, marker="s", zorder=6)
    ax.scatter([src[0]], [src[1]], s=52, c=RED, zorder=6)
    ax.scatter([900.0], [0.0], s=34, c=ORANGE, marker="D", zorder=6)
    ax.scatter([997.2], [0.0], s=38, c=GREEN, zorder=6)
    ax.scatter([1865.0], [0.0], s=38, c="#7F2704", zorder=6)

    handles = [
        Line2D([], [], marker="s", ls="none", color=BLUE, ms=5.5, label="原点"),
        Line2D([], [], marker="o", ls="none", color=RED, ms=5.5, label="近心朝外源"),
        Line2D([], [], marker="D", ls="none", color=ORANGE, ms=5.5, label="900 m 途听"),
        Line2D([], [], marker="o", ls="none", color=GREEN, ms=5.5, label="内环听点"),
        Line2D([], [], marker="o", ls="none", color="#7F2704", ms=5.5, label="外环听点"),
        Patch(facecolor=RED, alpha=0.15, edgecolor=RED, lw=0.6, label="前瓣（可听）"),
        Patch(facecolor="#B8BFC4", alpha=0.18, edgecolor="#9AA5AB", lw=0.6, ls=(0, (3, 2)),
              label="后瓣（静默）"),
    ]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.02), ncol=2,
              frameon=False, fontsize=6.0, columnspacing=2.2, handletextpad=0.4,
              labelspacing=0.5)
    ax.set_xlim(-2000, 2050)
    ax.set_ylim(-2000, 2000)
    ax.axis("off")
    ax.set_title("近心朝外源：前瓣与听点分工", loc="left", fontsize=8, fontweight="bold")
    _save(fig, "fig2_near_center_source")


# ---------------------------------------------------------------------------
# 图 3  双环覆盖几何
# ---------------------------------------------------------------------------

def fig3_geometry() -> None:
    rho = q4_opt_inner_r()
    opt = q4_opt_search_waypoints()
    inner, outer = opt[1:8], opt[8:]
    fig, axes = plt.subplots(1, 2, figsize=(183 * MM, 84 * MM))

    ax = axes[0]
    ax.set_aspect("equal")
    ax.add_patch(Circle((0, 0), ARENA_R, fill=False, ls="--", color=GREY, lw=0.8, zorder=1))
    ax.add_patch(Circle(inner[0], COVER_R, fill=True, facecolor=BLUE, alpha=0.10,
                        edgecolor=BLUE, lw=0.7, ls=(0, (3, 2)), zorder=1))
    ax.plot([0, inner[0][0], outer[0][0]], [0, inner[0][1], outer[0][1]],
            color=GREY, lw=0.7, ls=(0, (3, 2)), zorder=2)
    ax.plot([p[0] for p in inner + [inner[0]]], [p[1] for p in inner + [inner[0]]],
            color=BLUE, lw=1.3, zorder=2)
    ax.plot([p[0] for p in outer + [outer[0]]], [p[1] for p in outer + [outer[0]]],
            color=ORANGE, lw=1.1, zorder=2)
    ang = math.pi / 7.0
    far = (ARENA_R * math.cos(ang), ARENA_R * math.sin(ang))
    ax.plot([0, far[0]], [0, far[1]], color=RED, lw=0.8, ls=(0, (4, 2)), zorder=3)
    ax.scatter([far[0]], [far[1]], s=26, c=RED, marker="x", zorder=5, linewidths=0.9)
    ax.plot([far[0], inner[0][0]], [far[1], inner[0][1]], color=RED, lw=0.6, alpha=0.7, zorder=3)
    ax.scatter([p[0] for p in inner], [p[1] for p in inner], s=22, c=BLUE, zorder=4)
    ax.scatter([p[0] for p in outer], [p[1] for p in outer], s=20, c=ORANGE, zorder=4, marker="s")
    ax.scatter([0], [0], s=36, c=PURPLE, marker="D", zorder=5)
    ax.scatter([900.0], [0.0], s=22, c=GREEN, marker="^", zorder=5)
    ax.set_xlim(-2700, 2700)
    ax.set_ylim(-2700, 2700)
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_title("a  原点 + 正七边形 + 正十二边形（同径向）", loc="left", fontsize=8, fontweight="bold")
    ax.legend(
        handles=[
            Line2D([], [], marker="D", ls="none", color=PURPLE, ms=5.2, label="原点全扫"),
            Line2D([], [], marker="o", ls="none", color=BLUE, ms=5.2, label=rf"内环 {rho:.0f} m"),
            Line2D([], [], marker="s", ls="none", color=ORANGE, ms=5.2, label="外环 1865 m"),
            Line2D([], [], marker="^", ls="none", color=GREEN, ms=5.2, label="出发途听 900 m"),
        ],
        loc="upper left", fontsize=5.6, handletextpad=0.35, borderaxespad=0.12, labelspacing=0.25,
        frameon=True, facecolor="white", edgecolor="none", framealpha=1.0,
    )

    ax = axes[1]
    ax.set_aspect("equal")
    ax.add_patch(Circle((0, 0), ARENA_R, fill=False, ls="--", color=GREY, lw=0.8, zorder=1))
    g = (1550.0, 0.0)
    ax.add_patch(Wedge(g, COVER_R, -90.0, 90.0, facecolor=RED, alpha=0.14, edgecolor=RED, lw=0.7, zorder=1))
    ax.plot([p[0] for p in inner + [inner[0]]], [p[1] for p in inner + [inner[0]]],
            color=BLUE, lw=1.0, alpha=0.7, zorder=2)
    ax.plot([p[0] for p in outer + [outer[0]]], [p[1] for p in outer + [outer[0]]],
            color=ORANGE, lw=1.1, zorder=2)
    ax.scatter([g[0]], [g[1]], s=42, c=RED, marker="^", zorder=5)
    ax.annotate("", xy=(g[0] + 330, g[1]), xytext=(g[0] + 60, g[1]),
                arrowprops=dict(arrowstyle="->", color=RED, lw=0.9), zorder=6)
    ax.scatter([inner[0][0]], [inner[0][1]], s=28, c=BLUE, zorder=4)
    ax.scatter([outer[0][0]], [outer[0][1]], s=28, c=ORANGE, marker="s", zorder=4)
    ax.scatter([0], [0], s=28, c=PURPLE, marker="D", zorder=5)
    ax.text(930.0, 60.0, "内顶点（后瓣）", fontsize=6.5, color=BLUE, ha="right", va="bottom", zorder=8)
    ax.text(1830.0, 300.0, "外顶点可听", fontsize=6.0, color=ORANGE, ha="left", va="bottom", zorder=8)
    ax.text(1500, -450, "朝外定向源", fontsize=6.8, color=RED, ha="right", va="center", zorder=8)
    ax.annotate("", xy=(1545, 25), xytext=(1505, -420),
                arrowprops=dict(arrowstyle="-", color=RED, lw=0.7, alpha=0.8), zorder=8)
    ax.set_xlim(-400, 2750)
    ax.set_ylim(-1575, 1575)
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_title("b  朝外源迫使圆外听点", loc="left", fontsize=8, fontweight="bold")
    _save(fig, "fig3_double_ring_geometry")


# ---------------------------------------------------------------------------
# 图 4  问题三→问题四算法改动（精简文字）
# ---------------------------------------------------------------------------

def fig4_algo() -> None:
    fig, axes = plt.subplots(1, 2, figsize=(183 * MM, 84 * MM))

    ax = axes[0]
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_xlim(-0.2, 11.4)
    ax.set_ylim(-0.9, 6.3)
    ax.add_patch(FancyBboxPatch((0.15, 3.55), 5.2, 2.60, boxstyle="round,pad=0.08",
                                facecolor="#F4F7FB", edgecolor=BLUE, lw=0.8))
    ax.text(2.75, 5.85, "问题三：等圆可听", ha="center", fontsize=6.2, color=BLUE, fontweight="bold")
    ax.add_patch(Circle((2.75, 4.90), 0.70, fill=True, facecolor=BLUE, alpha=0.16, edgecolor=BLUE, lw=0.9))
    ax.scatter([2.75], [4.90], s=26, c=BLUE, zorder=3)
    ax.text(2.75, 3.80, r"$\|P-G\|\leq r_{\mathrm{eff}}$", ha="center", fontsize=6.2)

    ax.add_patch(FancyBboxPatch((5.85, 3.55), 5.25, 2.60, boxstyle="round,pad=0.08",
                                facecolor="#FDF6F2", edgecolor=RED, lw=0.8))
    ax.text(8.48, 5.85, "问题四：前瓣可听", ha="center", fontsize=6.2, color=RED, fontweight="bold")
    ax.add_patch(Wedge((8.48, 4.90), 0.80, -90, 90, facecolor=RED, alpha=0.16, edgecolor=RED, lw=0.9))
    ax.scatter([8.48], [4.90], s=26, c=RED, marker="^", zorder=3)
    ax.annotate("", xy=(9.40, 4.90), xytext=(8.60, 4.90),
                arrowprops=dict(arrowstyle="->", color=RED, lw=0.9))
    ax.text(8.48, 3.80, r"$P\in\mathbb{D}(G)\cap H_{\psi}$", ha="center", fontsize=6.2)

    ax.add_patch(Circle((2.35, 1.85), 1.0, fill=True, facecolor=BLUE, alpha=0.10, edgecolor=BLUE, lw=0.8))
    poly = np.array([[1.72, 1.37], [2.88, 1.24], [3.02, 2.06], [2.20, 2.39], [1.53, 1.92]])
    ax.fill(poly[:, 0], poly[:, 1], color=GREEN, alpha=0.30, zorder=2)
    ax.plot(np.append(poly[:, 0], poly[0, 0]), np.append(poly[:, 1], poly[0, 1]),
            color=GREEN, lw=0.8, zorder=3)
    ax.text(2.35, 0.66, "校正器：角扇外包络内", ha="center", va="top", fontsize=6.0, color=GREEN)

    ax.plot([5.55, 9.35], [1.35, 1.35], color=BLUE, lw=1.6)
    ax.plot([5.55, 7.45, 9.35], [1.35, 2.42, 1.35], color=GREEN, ls=(0, (4, 2)), lw=1.2)
    ax.scatter([5.55, 9.35], [1.35, 1.35], s=22, c=BLUE, zorder=4)
    ax.scatter([7.45], [2.42], s=32, c=GREEN, zorder=4)
    ax.text(5.55, 0.95, "P", ha="center", va="top", fontsize=6.6, color=BLUE)
    ax.text(9.35, 0.95, "Q", ha="center", va="top", fontsize=6.6, color=BLUE)
    ax.text(7.45, 2.72, r"$C=c_{\mathrm{SEC}}$", ha="center", fontsize=6.6, color=GREEN)
    ax.text(7.45, 0.80, r"$\Delta L\leq 280$ m", ha="center", va="top", fontsize=6.0, color=GREEN)
    ax.set_title("a  可听条件与顺路清除门控", loc="left", fontsize=7.2, fontweight="bold")

    ax = axes[1]
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_xlim(-0.2, 11.4)
    ax.set_ylim(-0.9, 6.3)
    s1 = np.array([1.85, 3.05])
    th = 22.0 * math.pi / 180.0
    ax.scatter([s1[0]], [s1[1]], s=40, c=BLUE, zorder=4)
    ax.text(s1[0] - 0.30, s1[1] - 0.30, r"$s_1$", ha="right", va="top", fontsize=7.0)
    ax.annotate("", xy=s1 + np.array([3.55 * math.cos(th), 3.55 * math.sin(th)]),
                xytext=s1, arrowprops=dict(arrowstyle="->", color=ORANGE, lw=1.05))
    ax.text(s1[0] + 1.55, s1[1] + 1.15, r"示向 $\theta$", fontsize=6.2, color=ORANGE, ha="left")
    ax.add_patch(Wedge(tuple(s1), 3.9, math.degrees(th) - 90, math.degrees(th) + 90,
                       facecolor=ORANGE, alpha=0.10, edgecolor=ORANGE, lw=0.6))
    p_ok = s1 + np.array([2.45 * math.cos(th + 0.52), 2.45 * math.sin(th + 0.52)])
    p_bad = s1 + np.array([2.05 * math.cos(th + math.pi), 2.05 * math.sin(th + math.pi)])
    ax.scatter([p_ok[0]], [p_ok[1]], s=46, c=GREEN, marker="s", zorder=5)
    ax.scatter([p_bad[0]], [p_bad[1]], s=42, c=RED, marker="x", zorder=5, linewidths=1.2)
    ax.text(p_ok[0] + 0.25, p_ok[1] + 0.42, r"$S_2$", fontsize=7.0, color=GREEN, ha="left", zorder=8)
    ax.text(p_bad[0] - 0.25, p_bad[1] - 0.30, "背面正交：不采用", fontsize=6.0, color=RED,
            ha="right", va="top", zorder=8)
    proxy = s1 + np.array([2.15 * math.cos(th), 2.15 * math.sin(th)])
    ax.scatter([proxy[0]], [proxy[1]], s=32, facecolors="none", edgecolors=PURPLE, linewidths=1.15, zorder=5)
    ax.text(3.00, 2.60, r"代理 $\rho\approx 380$ m", fontsize=6.0,
            color=PURPLE, ha="left", va="center", zorder=8)
    ax.set_title("b  第二站：前瓣兼容、只走一侧", loc="left", fontsize=7.2, fontweight="bold")
    _save(fig, "fig4_algo_changes")


# ---------------------------------------------------------------------------
# 图 6  无跳点分层 + 开放路 DP（去掉公式框，完整显示虚线圈）
# ---------------------------------------------------------------------------

def fig6_open_path_dp() -> None:
    fig, axes = plt.subplots(1, 2, figsize=(183 * MM, 80 * MM))

    ax = axes[0]
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_xlim(-2.05, 5.05)
    ax.set_ylim(-2.15, 2.85)
    p = np.array([0.0, 0.0])
    loc = [np.array([1.15, 0.85]), np.array([0.35, 1.45]), np.array([1.55, -0.15])]
    far = [np.array([3.55, 1.35]), np.array([4.15, -0.55])]
    ax.add_patch(Circle(tuple(p), 1.85, fill=False, ls=(0, (4, 2)), color=GREY, lw=0.9, zorder=1))
    ax.scatter([p[0]], [p[1]], s=52, color=BLUE, marker="s", zorder=5)
    ax.text(p[0] - 0.30, p[1] - 0.22, "P", fontsize=8, color=BLUE, ha="right", va="center")
    ax.scatter([c[0] for c in loc], [c[1] for c in loc], s=40, color=ORANGE, zorder=4)
    ax.scatter([c[0] for c in far], [c[1] for c in far], s=40, color=PURPLE, marker="D", zorder=4)
    for i, c in enumerate(loc, 1):
        if i == 1:
            ax.text(c[0], c[1] + 0.20, f"c{i}", fontsize=7, ha="center", va="bottom")
        elif i == 2:
            ax.text(c[0], c[1] - 0.28, f"c{i}", fontsize=7, ha="center", va="top")
        else:
            ax.text(c[0] - 0.20, c[1] - 0.30, f"c{i}", fontsize=7, ha="right", va="top")
    ax.text(far[0][0] + 0.14, far[0][1] + 0.16, "c4", fontsize=7)
    ax.text(far[1][0] + 0.14, far[1][1] - 0.30, "c5", fontsize=7)
    skip = [p, far[0], far[1], loc[0]]
    ax.plot([q[0] for q in skip], [q[1] for q in skip], color=RED, ls=(0, (3, 2)), lw=1.15, zorder=2)
    good = [p, loc[2], loc[0], loc[1], far[0], far[1]]
    ax.plot([q[0] for q in good], [q[1] for q in good], color=GREEN, lw=1.55, zorder=3)
    ax.legend(
        handles=[
            Line2D([], [], color=RED, ls=(0, (3, 2)), lw=1.2, label="欧氏开放路（远簇优先）"),
            Line2D([], [], color=GREEN, lw=1.4, label="无跳点：局部簇优先"),
        ],
        loc="lower right", fontsize=6.4, handlelength=1.6, borderaxespad=0.2, labelspacing=0.35,
    )
    ax.set_title("a  分层无跳点约束（虚线圈出 650 m 局部簇）", loc="left", fontsize=8, fontweight="bold")

    ax = axes[1]
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_xlim(-0.3, 6.6)
    ax.set_ylim(-0.95, 3.91)
    p = np.array([0.35, 0.55])
    c1 = np.array([2.05, 3.15])
    c2 = np.array([3.35, 0.85])
    c3 = np.array([5.35, 2.55])
    ax.scatter([p[0]], [p[1]], s=52, color=BLUE, marker="s", zorder=5)
    ax.text(p[0] - 0.28, p[1] - 0.16, "P", ha="right", va="center", fontsize=8, color=BLUE)
    for lab, q in (("c1", c1), ("c2", c2), ("c3", c3)):
        ax.scatter([q[0]], [q[1]], s=42, color=ORANGE, zorder=4)
        if lab == "c2":
            ax.text(q[0] + 0.16, q[1] - 0.26, lab, fontsize=7, ha="left", va="top")
        else:
            ax.text(q[0] + 0.15, q[1] + 0.17, lab, fontsize=7)
    ax.plot([p[0], c2[0], c1[0], c3[0]], [p[1], c2[1], c1[1], c3[1]],
            color=BLUE, ls=(0, (4, 2)), lw=1.25, zorder=2)
    ax.annotate("", xy=c2, xytext=p, arrowprops=dict(arrowstyle="->", color=GREEN, lw=1.7))
    ax.plot([c2[0], c3[0], c1[0]], [c2[1], c3[1], c1[1]], color=GREEN, lw=1.45, zorder=3)
    ax.text(3.45, -0.62, r"只执行 $\pi^*$ 第一城，服务点随示向移动后再解",
            ha="center", va="top", fontsize=6.6, color=GREY)
    ax.set_title("b  开放路 Held–Karp 动态规划", loc="left", fontsize=8, fontweight="bold")
    _save(fig, "fig6_open_path_dp")


# ---------------------------------------------------------------------------
# 图 9  覆盖巡游时间对照
# ---------------------------------------------------------------------------

def _row(n_in, inner_r, n_out, outer_r, align, enroute_r):
    return q4_double_ring_search_time(
        n_in, inner_r, n_out, outer_r, align=align, enroute_r=enroute_r, check_cover=False,
    )


def fig9_times() -> None:
    rho7 = q4_opt_inner_r()
    catalog = [
        ("正七 + 十二，同径向（本文）", _row(7, rho7, 12, 1865.0, "radial", None), True),
        ("正七 + 十二，交错相位", _row(7, rho7, 12, 1865.0, "stagger", None), True),
        ("正八 + 十二，同径向", _row(8, 995.0, 12, 1865.0, "radial", None), True),
        ("正九 + 十二，同径向", _row(9, 1000.0, 12, 1865.0, "radial", None), True),
        ("正七 + 十四，同径向", _row(7, rho7, 14, 1865.0, "radial", None), True),
        ("正六 + 十二 + 途听环", _row(6, 1150.0, 12, 1865.0, "radial", 900.0), True),
        ("正八 + 十二×2100 + 途听", _row(8, 1200.0, 12, 2100.0, "radial", 900.0), True),
        ("正七 + 十一×1900", _row(7, rho7, 11, 1900.0, "radial", None), False),
        ("正六 + 十二，无途听", _row(6, 1150.0, 12, 1865.0, "radial", None), False),
    ]
    catalog.sort(key=lambda c: (not c[2], float(c[1]["total_s"])))
    labels = [c[0] for c in catalog]
    travel = np.array([float(c[1]["travel_s"]) for c in catalog])
    dwell = np.array([float(c[1]["dwell_s"]) for c in catalog])
    total = travel + dwell
    ok = [c[2] for c in catalog]
    y = np.arange(len(catalog))

    fig, ax = plt.subplots(figsize=(150 * MM, 96 * MM), layout="constrained")
    for i, feasible in enumerate(ok):
        hatch = "" if feasible else "////"
        tc = BLUE if feasible else "#A0A0A0"
        dc = GREEN if feasible else "#C8C8C8"
        ax.barh(y[i], travel[i], color=tc, height=0.62, hatch=hatch, edgecolor="white", linewidth=0.3)
        ax.barh(y[i], dwell[i], left=travel[i], color=dc, height=0.62, hatch=hatch,
                edgecolor="white", linewidth=0.3)
        note = f"{total[i]:.0f} s"
        if i == 0:
            note += "（最短可行）"
        if not feasible:
            note += "　前瓣未过"
        ax.text(total[i] + 70, i, note, va="center", ha="left", fontsize=6.5,
                color=GREY if feasible else RED,
                bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.85))
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlabel("覆盖巡游虚拟时间 (s)")
    ax.set_xlim(0, max(total) * 1.38)
    best = next(t for t, f in zip(total, ok) if f)
    ax.axvline(best, color=RED, ls=(0, (3, 2)), lw=0.7, alpha=0.75, zorder=1)
    ax.legend(
        handles=[
            Patch(color=BLUE, label="行驶"),
            Patch(color=GREEN, label="检测与换频驻留"),
            Patch(facecolor="#C8C8C8", hatch="////", edgecolor=GREY, label="前瓣核验未通过"),
        ],
        loc="lower center", bbox_to_anchor=(0.42, 1.02), ncol=3, fontsize=6.5,
        handlelength=1.4, columnspacing=0.9,
    )
    _save(fig, "fig9_cover_time_ranked")


def main() -> None:
    fig1_hexbatch()
    fig2_near_center()
    fig3_geometry()
    fig4_algo()
    fig6_open_path_dp()
    fig9_times()


if __name__ == "__main__":
    main()
