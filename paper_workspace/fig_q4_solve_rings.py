"""Q4 dual-ring geometry, ranked covering-tour times, and Q3-to-Q4 algorithm schematic."""
from __future__ import annotations

import math
import sys
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, FancyBboxPatch, FancyArrowPatch, Wedge

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from coverage import (  # noqa: E402
    ARENA_R,
    COVER_R,
    q4_double_ring_search_time,
    q4_opt_inner_r,
    q4_opt_search_waypoints,
)

# Academic Figure Skill Typography Baseline — COPY VERBATIM
mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "Liberation Sans"],
    "font.size": 8,
    "axes.titlesize": 8,
    "axes.labelsize": 8,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 8,
    "figure.titlesize": 9,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.linewidth": 0.6,
    "xtick.direction": "out",
    "ytick.direction": "out",
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "legend.frameon": False,
})
CATEGORICAL = ["#2166AC", "#B2182B", "#1B7837", "#F1A340", "#762A83", "#666666"]
mpl.rcParams.update({
    "pdf.fonttype": 42,
    "svg.fonttype": "none",
    "savefig.bbox": "tight",
    "savefig.dpi": 300,
})
mpl.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial", "Helvetica"]
mpl.rcParams["axes.unicode_minus"] = False

BLUE, RED, GREEN, ORANGE, PURPLE, GREY = CATEGORICAL
BLACK = "#222222"
MM = 1 / 25.4
FIG_DIR = ROOT / "output" / "figures"


def _row(n_in, inner_r, n_out, outer_r, align, enroute_r):
    return q4_double_ring_search_time(
        n_in, inner_r, n_out, outer_r,
        align=align, enroute_r=enroute_r, check_cover=False,
    )


def fig_geometry() -> None:
    rho = q4_opt_inner_r()
    opt = q4_opt_search_waypoints()
    origin, inner, outer = opt[0], opt[1:8], opt[8:]
    fig, axes = plt.subplots(1, 2, figsize=(183 * MM, 84 * MM))

    ax = axes[0]
    ax.set_aspect("equal")
    ax.add_patch(Circle((0, 0), ARENA_R, fill=False, ls="--", color=GREY, lw=0.8, zorder=1))
    ax.add_patch(Circle(inner[0], COVER_R, fill=True, facecolor=BLUE, alpha=0.10,
                        edgecolor=BLUE, lw=0.7, ls=(0, (3, 2)), zorder=1))
    ax.plot([origin[0], inner[0][0], outer[0][0]], [origin[1], inner[0][1], outer[0][1]],
            color=GREY, lw=0.7, ls=(0, (3, 2)), zorder=2)
    ax.plot([p[0] for p in inner + [inner[0]]], [p[1] for p in inner + [inner[0]]],
            color=BLUE, lw=1.3, zorder=2)
    ax.plot([p[0] for p in outer + [outer[0]]], [p[1] for p in outer + [outer[0]]],
            color=ORANGE, lw=1.1, zorder=2)
    # angular bisector of first two inner vertices: farthest omni gap
    ang = math.pi / 7.0
    far = (ARENA_R * math.cos(ang), ARENA_R * math.sin(ang))
    ax.plot([0, far[0]], [0, far[1]], color=RED, lw=0.8, ls=(0, (4, 2)), zorder=3)
    ax.scatter([far[0]], [far[1]], s=26, c=RED, marker="x", zorder=5, linewidths=0.9)
    ax.plot([far[0], inner[0][0]], [far[1], inner[0][1]], color=RED, lw=0.6, alpha=0.7, zorder=3)
    ax.annotate("角平分线最远点", far, textcoords="offset points",
                xytext=(6, 4), fontsize=6.5, color=RED)
    ax.scatter([p[0] for p in inner], [p[1] for p in inner], s=22, c=BLUE, zorder=4,
               edgecolors="white", linewidths=0.4)
    ax.scatter([p[0] for p in outer], [p[1] for p in outer], s=20, c=ORANGE, zorder=4,
               marker="s", edgecolors="white", linewidths=0.4)
    ax.scatter([0], [0], s=36, c=PURPLE, marker="D", zorder=5, edgecolors="white", linewidths=0.4)
    mid = (900.0, 0.0)
    ax.scatter([mid[0]], [mid[1]], s=22, c=GREEN, marker="^", zorder=5, edgecolors="white", linewidths=0.4)
    ax.annotate(r"$r_{\mathrm{eff}}=1000\,\mathrm{m}$", inner[0], textcoords="offset points",
                xytext=(8, -18), fontsize=6.5, color=BLUE)
    ax.set_xlim(-2350, 2350)
    ax.set_ylim(-2350, 2350)
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_title("a  原点 + 正七边形 + 正十二边形（同径向）", loc="left", fontsize=8, fontweight="bold")
    ax.legend(
        handles=[
            Line2D([0], [0], marker="D", color="w", markerfacecolor=PURPLE, markersize=6, label="原点全扫"),
            Line2D([0], [0], marker="o", color="w", markerfacecolor=BLUE, markersize=6,
                   label=rf"内环 $7\times{rho:.0f}\,\mathrm{{m}}$"),
            Line2D([0], [0], marker="s", color="w", markerfacecolor=ORANGE, markersize=6,
                   label=r"外环 $12\times 1865\,\mathrm{m}$"),
            Line2D([0], [0], marker="^", color="w", markerfacecolor=GREEN, markersize=6,
                   label="出发途听 900 m（不计入核验点集）"),
        ],
        loc="lower left",
        fontsize=6.0,
        handletextpad=0.35,
        borderaxespad=0.15,
        labelspacing=0.25,
    )

    ax = axes[1]
    ax.set_aspect("equal")
    ax.add_patch(Circle((0, 0), ARENA_R, fill=False, ls="--", color=GREY, lw=0.8, zorder=1))
    g = (1550.0, 0.0)
    ax.add_patch(Wedge(g, COVER_R, -90.0, 90.0, facecolor=RED, alpha=0.14,
                       edgecolor=RED, lw=0.7, zorder=1))
    ax.scatter([g[0]], [g[1]], s=42, c=RED, marker="^", zorder=5, edgecolors="white", linewidths=0.4)
    ax.annotate("朝外定向源", g, textcoords="offset points", xytext=(-22, 14), fontsize=7, color=RED)
    ax.plot([p[0] for p in inner + [inner[0]]], [p[1] for p in inner + [inner[0]]],
            color=BLUE, lw=1.0, alpha=0.7, zorder=2)
    ax.plot([p[0] for p in outer + [outer[0]]], [p[1] for p in outer + [outer[0]]],
            color=ORANGE, lw=1.1, zorder=2)
    ax.scatter([inner[0][0]], [inner[0][1]], s=28, c=BLUE, zorder=4, edgecolors="white", linewidths=0.4)
    ax.scatter([outer[0][0]], [outer[0][1]], s=28, c=ORANGE, marker="s", zorder=4, edgecolors="white", linewidths=0.4)
    ax.annotate("内顶点：后瓣静默", inner[0], textcoords="offset points",
                xytext=(-92, 8), fontsize=6.5, color=BLUE)
    ax.annotate("外顶点：前瓣可听", outer[0], textcoords="offset points",
                xytext=(-28, 12), fontsize=6.5, color=ORANGE)
    ax.scatter([0], [0], s=28, c=PURPLE, marker="D", zorder=5, edgecolors="white", linewidths=0.4)
    ax.annotate("", xy=(g[0] + 380, g[1]), xytext=(g[0] + 40, g[1]),
                arrowprops=dict(arrowstyle="->", color=RED, lw=0.9))
    ax.set_xlim(-400, 2750)
    ax.set_ylim(-1550, 1550)
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_title("b  朝外源迫使圆外听点", loc="left", fontsize=8, fontweight="bold")

    fig.savefig(FIG_DIR / "q4_double_ring_geometry.png", facecolor="white")
    fig.savefig(FIG_DIR / "q4_double_ring_geometry.pdf")
    plt.close(fig)


def fig_times() -> None:
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

    fig, ax = plt.subplots(figsize=(150 * MM, 96 * MM))
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
            note += "  前瓣未过"
        ax.text(total[i] + 50, i, note, va="center", ha="left", fontsize=6.5,
                color=GREY if feasible else RED)
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlabel("覆盖巡游虚拟时间 (s)")
    ax.set_xlim(0, max(total) * 1.38)
    best = next(t for t, f in zip(total, ok) if f)
    ax.axvline(best, color=RED, ls=(0, (3, 2)), lw=0.7, alpha=0.75)
    ax.legend(
        handles=[
            plt.Rectangle((0, 0), 1, 1, color=BLUE, label="行驶"),
            plt.Rectangle((0, 0), 1, 1, color=GREEN, label="检测与换频驻留"),
            plt.Rectangle((0, 0), 1, 1, facecolor="#C8C8C8", hatch="////", edgecolor=GREY,
                          label="前瓣核验未通过"),
        ],
        loc="lower center",
        bbox_to_anchor=(0.42, 1.02),
        ncol=3,
        fontsize=6.5,
        handlelength=1.4,
        columnspacing=0.9,
    )
    fig.savefig(FIG_DIR / "q4_ngon_time_ranked.png", facecolor="white")
    fig.savefig(FIG_DIR / "q4_ngon_time_ranked.pdf")
    plt.close(fig)


def fig_algo() -> None:
    fig, axes = plt.subplots(1, 2, figsize=(183 * MM, 88 * MM))

    ax = axes[0]
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_xlim(-0.15, 11.35)
    ax.set_ylim(-0.55, 6.45)
    ax.add_patch(FancyBboxPatch((0.15, 3.55), 5.2, 2.55, boxstyle="round,pad=0.08",
                                facecolor="#F4F7FB", edgecolor=BLUE, lw=0.8))
    ax.text(2.75, 5.72, "问题三：等圆可听", ha="center", fontsize=8, color=BLUE, fontweight="bold")
    ax.add_patch(Circle((2.75, 4.58), 0.88, fill=True, facecolor=BLUE, alpha=0.16, edgecolor=BLUE, lw=0.9))
    ax.scatter([2.75], [4.58], s=28, c=BLUE, zorder=3)
    ax.text(2.75, 3.72, r"$\|P-G\|\leq r_{\mathrm{eff}}$", ha="center", fontsize=7.5)

    ax.add_patch(FancyBboxPatch((5.85, 3.55), 5.25, 2.55, boxstyle="round,pad=0.08",
                                facecolor="#FDF6F2", edgecolor=RED, lw=0.8))
    ax.text(8.48, 5.72, "问题四：前瓣可听", ha="center", fontsize=8, color=RED, fontweight="bold")
    ax.add_patch(Wedge((8.48, 4.58), 0.98, -90, 90, facecolor=RED, alpha=0.16, edgecolor=RED, lw=0.9))
    ax.scatter([8.48], [4.58], s=28, c=RED, marker="^", zorder=3)
    ax.annotate("", xy=(9.58, 4.58), xytext=(8.62, 4.58),
                arrowprops=dict(arrowstyle="->", color=RED, lw=0.9))
    ax.text(8.48, 3.72, r"$P\in\mathbb{D}(G)\cap H_{\psi}$", ha="center", fontsize=7.5)

    ax.add_patch(Circle((2.35, 1.55), 1.05, fill=True, facecolor=BLUE, alpha=0.10, edgecolor=BLUE, lw=0.8))
    poly = np.array([[1.70, 1.05], [2.90, 0.92], [3.05, 1.78], [2.20, 2.12], [1.50, 1.62]])
    ax.fill(poly[:, 0], poly[:, 1], color=GREEN, alpha=0.30, zorder=2)
    ax.plot(np.append(poly[:, 0], poly[0, 0]), np.append(poly[:, 1], poly[0, 1]),
            color=GREEN, lw=0.8, zorder=3)
    ax.text(2.35, 0.18, "校正器：朝向可行点", ha="center", fontsize=6.8, color=GREEN)
    ax.text(2.35, -0.22, "留在角扇外包络内", ha="center", fontsize=6.8, color=GREEN)

    ax.plot([5.55, 9.35], [1.15, 1.15], color=BLUE, lw=1.6)
    ax.plot([5.55, 7.45, 9.35], [1.15, 2.28, 1.15], color=GREEN, ls=(0, (4, 2)), lw=1.2)
    ax.scatter([5.55, 9.35], [1.15, 1.15], s=22, c=BLUE, zorder=4)
    ax.scatter([7.45], [2.28], s=32, c=GREEN, zorder=4)
    ax.text(5.55, 0.72, "P", ha="center", fontsize=7, color=BLUE)
    ax.text(9.35, 0.72, "Q", ha="center", fontsize=7, color=BLUE)
    ax.text(7.45, 2.62, r"$C=c_{\mathrm{SEC}}$", ha="center", fontsize=7, color=GREEN)
    ax.text(7.45, 0.18, r"$\Delta L\leq 280\,\mathrm{m}$", ha="center", fontsize=6.8, color=GREEN)
    ax.text(7.45, -0.22, "且仅清除可清圆心", ha="center", fontsize=6.8, color=GREEN)
    ax.set_title("a  可听条件与覆盖期内服务门控", loc="left", fontsize=8, fontweight="bold")

    ax = axes[1]
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_xlim(-0.4, 10.6)
    ax.set_ylim(-0.45, 6.2)
    s1 = np.array([1.85, 3.05])
    th = 22.0 * math.pi / 180.0
    ax.scatter([s1[0]], [s1[1]], s=40, c=BLUE, zorder=4)
    ax.text(s1[0], s1[1] - 0.42, r"$s_1$", ha="center", fontsize=8)
    ax.annotate("", xy=s1 + np.array([3.55 * math.cos(th), 3.55 * math.sin(th)]),
                xytext=s1, arrowprops=dict(arrowstyle="->", color=ORANGE, lw=1.05))
    ax.text(4.55, 4.72, r"示向 $\theta$", fontsize=7.5, color=ORANGE)
    ax.add_patch(Wedge(tuple(s1), 3.9, math.degrees(th) - 90, math.degrees(th) + 90,
                       facecolor=ORANGE, alpha=0.10, edgecolor=ORANGE, lw=0.6))
    p_ok = s1 + np.array([2.45 * math.cos(th + 0.52), 2.45 * math.sin(th + 0.52)])
    p_bad = s1 + np.array([2.05 * math.cos(th + math.pi), 2.05 * math.sin(th + math.pi)])
    ax.scatter([p_ok[0]], [p_ok[1]], s=46, c=GREEN, marker="s", zorder=5)
    ax.scatter([p_bad[0]], [p_bad[1]], s=42, c=RED, marker="x", zorder=5, linewidths=1.2)
    ax.text(p_ok[0] + 0.12, p_ok[1] + 0.32, r"$S_2$（前瓣、只一侧）", fontsize=7, color=GREEN)
    ax.text(p_bad[0] - 2.05, p_bad[1] - 0.42, "背面正交：不采用", fontsize=6.8, color=RED)
    proxy = s1 + np.array([2.15 * math.cos(th), 2.15 * math.sin(th)])
    ax.scatter([proxy[0]], [proxy[1]], s=32, facecolors="none", edgecolors=PURPLE, linewidths=1.15, zorder=5)
    ax.text(proxy[0] + 0.18, proxy[1] - 0.40, r"代理 $\rho\approx 380\,\mathrm{m}$", fontsize=6.8, color=PURPLE)
    ax.text(5.1, 0.12, "无合法紧凑点时沿示向前瓣代理，不走双侧。", ha="center", fontsize=6.8, color=GREY)
    ax.set_title("b  第二站：前瓣兼容、只走一侧", loc="left", fontsize=8, fontweight="bold")

    fig.savefig(FIG_DIR / "q4_q3_vs_q4_algo.png", facecolor="white")
    fig.savefig(FIG_DIR / "q4_q3_vs_q4_algo.pdf")
    plt.close(fig)


if __name__ == "__main__":
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig_geometry()
    fig_times()
    fig_algo()
    print("wrote geometry / ranked times / algo")
