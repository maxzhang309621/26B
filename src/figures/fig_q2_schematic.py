# -*- coding: utf-8 -*-
"""Q2 paper schematics: nominal source, orthogonal candidates, and a separate omni siting flow."""
import matplotlib as mpl

mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Microsoft YaHei", "SimHei", "Arial", "Helvetica"],
    "font.size": 9,
    "axes.labelsize": 10,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 8,
    "axes.linewidth": 0.8,
    "legend.frameon": True,
    "legend.fancybox": False,
    "legend.edgecolor": "#D0D5DD",
    "legend.facecolor": "#FFFFFF",
    "pdf.fonttype": 42,
    "savefig.dpi": 300,
    "axes.unicode_minus": False,
    "mathtext.fontset": "stix",
})

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import (
    Circle,
    FancyArrowPatch,
    FancyBboxPatch,
    Rectangle,
    Patch,
    Polygon,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / "output" / "figures" / "q2_paper"
OUT.mkdir(parents=True, exist_ok=True)

BAND = "#C5D9ED"
BAND_EDGE = "#3D6B99"
S1C = "#2D7A4F"
S2C = "#C0392B"
GOLD = "#6B3FA0"
GREY = "#7A8694"
BLACK = "#1B2430"
OK = "#1B7837"
BOX = "#D6E4F0"
BOX_EDGE = "#2B6CB0"
ARENA_R = 1800.0
TH = np.deg2rad(35.0)


def save(fig, stem):
    path = OUT / stem
    fig.savefig(f"{path}.pdf", bbox_inches="tight", dpi=300)
    fig.savefig(f"{path}.png", bbox_inches="tight", dpi=300)
    plt.close(fig)
    return path


def _axes_style(ax):
    ax.set_facecolor("#F7F9FC")
    ax.grid(True, color="#E4E8EE", lw=0.6)
    ax.set_aspect("equal")
    for sp in ax.spines.values():
        sp.set_color("#2C3E50")


def fig1_nominal():
    u = np.array([np.cos(TH), np.sin(TH)])
    n = np.array([-u[1], u[0]])
    s1 = np.array([0.0, 0.0])
    rho = 850.0
    ghat = rho * u
    xmin, xmax = 400.0, 1300.0

    fig, ax = plt.subplots(figsize=(6.5, 5.6))
    _axes_style(ax)
    ax.add_patch(Circle((0, 0), ARENA_R, fill=False, ls=(0, (5, 3)), lw=0.9, color=GREY, zorder=0))

    ray_end = 1550 * u
    ax.plot([0, ray_end[0]], [0, ray_end[1]], color=GREY, lw=1.05, ls=(0, (3, 2.2)), zorder=2)
    # candidate longitudinal interval on the ray
    ax.plot(
        [xmin * u[0], xmax * u[0]],
        [xmin * u[1], xmax * u[1]],
        color="#5AAE61", lw=7.5, alpha=0.28, solid_capstyle="butt", zorder=2,
    )
    ax.plot([0, rho * u[0]], [0, rho * u[1]], color=GOLD, lw=3.0, solid_capstyle="butt", zorder=3)

    exit_pt = ARENA_R * u
    ax.scatter(*exit_pt, s=18, c=GREY, zorder=4)
    ax.annotate("射线出圆", exit_pt, textcoords="offset points", xytext=(8, -12),
                fontsize=8, color=GREY)

    # body axes
    ax.annotate(
        "", xy=380 * u, xytext=s1,
        arrowprops=dict(arrowstyle="-|>", color=S1C, lw=1.6, mutation_scale=12),
    )
    ax.annotate(
        "", xy=280 * n, xytext=s1,
        arrowprops=dict(arrowstyle="-|>", color="#4A5568", lw=1.4, mutation_scale=12),
    )
    ax.text(*(200 * u + 55 * n), r"$\mathbf{u}$", color=S1C, fontsize=11, fontweight="bold")
    ax.text(*(160 * n + 40 * u), r"$\mathbf{n}$", color="#4A5568", fontsize=11)

    ax.scatter([0], [0], s=78, c=S1C, zorder=6, edgecolors="white", linewidths=0.7)
    ax.annotate(r"$S_1$", s1, textcoords="offset points", xytext=(-22, -18),
                fontsize=11, color=S1C, fontweight="bold")
    ax.scatter([ghat[0]], [ghat[1]], s=90, c=GOLD, marker="*", zorder=6, edgecolors="white", linewidths=0.4)
    ax.annotate(r"$\hat{G}$", ghat, textcoords="offset points", xytext=(10, -16),
                fontsize=11, color=GOLD)

    ax.annotate(r"$x_{\min}$", xmin * u, textcoords="offset points", xytext=(-18, 10),
                fontsize=8, color=S1C)
    ax.annotate(r"$x_{\max}$", xmax * u, textcoords="offset points", xytext=(-6, 12),
                fontsize=8, color=S1C)
    ax.annotate(r"$\hat{\rho}$", 0.52 * ghat + 35 * n, fontsize=10, color=GOLD)

    ax.set_xlim(-220, 2050)
    ax.set_ylim(-520, 1750)
    ax.set_xlabel(r"$x$ / m")
    ax.set_ylabel(r"$y$ / m")
    ax.legend(
        handles=[
            Line2D([0], [0], color=GREY, ls=(0, (5, 3)), label="工作圆 1800 m"),
            Line2D([0], [0], color=GREY, ls=(0, (3, 2)), label="第一示向"),
            Line2D([0], [0], color=GOLD, lw=3.0, label=r"名义纵向 $\hat{\rho}=850$ m"),
            Line2D([0], [0], color="#5AAE61", lw=6, alpha=0.45, label=r"纵向允许 $x\in[400,1300]$"),
            Line2D([0], [0], marker="o", color="w", markerfacecolor=S1C, markersize=8, linestyle="none", label=r"第一站 $S_1$"),
            Line2D([0], [0], marker="*", color="w", markerfacecolor=GOLD, markersize=11, linestyle="none", label=r"名义源 $\hat{G}$"),
        ],
        loc="upper left", framealpha=0.96, edgecolor="#D0D5DD",
    )
    return save(fig, "q2_fig1_nominal")


def _right_angle(ax, origin, v1, v2, size=58.0):
    a = v1 / np.hypot(*v1)
    b = v2 / np.hypot(*v2)
    bis = a + b
    bis = bis / np.hypot(*bis)
    o = origin + 18.0 * bis
    p1 = o + size * a
    p2 = o + size * a + size * b
    p3 = o + size * b
    ax.plot([p1[0], p2[0], p3[0]], [p1[1], p2[1], p3[1]], color=BLACK, lw=1.05, zorder=5)
    return origin + 155.0 * bis


def fig2_ortho():
    u = np.array([np.cos(TH), np.sin(TH)])
    n = np.array([-u[1], u[0]])
    s1 = np.array([0.0, 0.0])
    rho, h = 850.0, 600.0
    ghat = rho * u
    pp = ghat + h * n
    pm = ghat - h * n

    fig, ax = plt.subplots(figsize=(6.5, 5.8))
    _axes_style(ax)
    for sign in (1.0, -1.0):
        corners = np.array([
            400 * u + sign * 400 * n,
            1300 * u + sign * 400 * n,
            1300 * u + sign * 800 * n,
            400 * u + sign * 800 * n,
        ])
        ax.add_patch(Polygon(corners, closed=True, facecolor=BAND, edgecolor=BAND_EDGE,
                             lw=1.0, alpha=0.85, zorder=1))

    ax.plot([0, 1500 * u[0]], [0, 1500 * u[1]], color=GREY, lw=1.05, ls=(0, (3, 2.2)), zorder=2)
    ax.plot([s1[0], ghat[0]], [s1[1], ghat[1]], color=GOLD, lw=2.2, zorder=3)
    ax.plot([pp[0], pm[0]], [pp[1], pm[1]], color=S2C, lw=1.45, zorder=3)
    ang_pos = _right_angle(ax, ghat, s1 - ghat, pp - ghat, size=62.0)

    ax.scatter([0], [0], s=72, c=S1C, zorder=6, edgecolors="white", linewidths=0.5)
    ax.scatter([ghat[0]], [ghat[1]], s=86, c=GOLD, marker="*", zorder=6)
    ax.scatter([pp[0]], [pp[1]], s=70, c=S2C, marker="D", zorder=6, edgecolors="white", linewidths=0.5)
    ax.scatter([pm[0]], [pm[1]], s=70, c="#C05621", marker="D", zorder=6, edgecolors="white", linewidths=0.5)
    ax.scatter([pp[0]], [pp[1]], s=175, facecolors="none", edgecolors=S2C, linewidths=1.4, zorder=7)

    ax.annotate(r"$S_1$", s1, textcoords="offset points", xytext=(-18, -16), fontsize=11, color=S1C)
    ax.annotate(r"$\hat{G}$", ghat, textcoords="offset points", xytext=(16, -18), fontsize=11, color=GOLD)
    ax.annotate(r"$P_+$", pp, textcoords="offset points", xytext=(8, 8), fontsize=11, color=S2C)
    ax.annotate(r"$P_-$", pm, textcoords="offset points", xytext=(8, -12), fontsize=11, color="#C05621")
    ax.annotate(r"$h$", 0.55 * (ghat + pp) + 18 * u, fontsize=11, color=S2C)
    ax.annotate(r"$90^{\circ}$", ang_pos, fontsize=10, color=BLACK, ha="center", va="center")

    ax.set_xlim(-180, 1400)
    ax.set_ylim(-650, 1350)
    ax.set_xlabel(r"$x$ / m")
    ax.set_ylabel(r"$y$ / m")
    ax.legend(
        handles=[
            Patch(facecolor=BAND, edgecolor=BAND_EDGE, label="候选带"),
            Line2D([0], [0], color=GREY, ls=(0, (3, 2)), label="第一示向"),
            Line2D([0], [0], color=S2C, lw=1.4, label=r"侧向 $\pm h=600$ m"),
            Line2D([0], [0], marker="o", color="w", markerfacecolor="none",
                   markeredgecolor=S2C, markersize=9, linestyle="none", label=r"择近 $S_2$"),
        ],
        loc="lower right", framealpha=0.96, edgecolor="#D0D5DD",
    )
    return save(fig, "q2_fig2_ortho")


def fig3_flow():
    fig, ax = plt.subplots(figsize=(7.8, 3.25))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3.15)
    ax.axis("off")
    boxes = [
        (0.18, 1.12, 1.72, 1.12, "输入\n第一站与示向"),
        (2.10, 1.12, 1.82, 1.12, "与工作圆求交\n得名义纵向距离"),
        (4.12, 1.12, 1.82, 1.12, "左右正交候选\n裁剪到工作圆"),
        (6.14, 1.12, 1.62, 1.12, "候选带筛选\n就近择侧"),
        (8.00, 2.02, 1.72, 0.88, "可清：\n回代问题一"),
        (8.00, 0.28, 1.72, 0.88, "不可清：\n补第三站"),
    ]
    for x, y, w, h, txt in boxes:
        ax.add_patch(FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.04,rounding_size=0.10",
            facecolor=BOX, edgecolor=BOX_EDGE, lw=1.15, zorder=2,
        ))
        ax.text(x + w / 2, y + h / 2, txt, ha="center", va="center", fontsize=8.2,
                color=BLACK, zorder=3, linespacing=1.35)

    def arr(x0, y0, x1, y1):
        ax.add_patch(FancyArrowPatch(
            (x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=10,
            lw=1.15, color=BOX_EDGE, zorder=4,
        ))

    arr(1.90, 1.68, 2.10, 1.68)
    arr(3.92, 1.68, 4.12, 1.68)
    arr(5.94, 1.68, 6.14, 1.68)
    arr(7.76, 1.88, 8.00, 2.35)
    arr(7.76, 1.48, 8.00, 0.85)
    ax.text(8.86, 3.00, r"$r_{\mathrm{SEC}}\leq 20$", fontsize=7.3, color=OK, ha="center")
    ax.text(8.86, 0.08, "强制再测", fontsize=7.3, color=S2C, ha="center")
    fig.subplots_adjust(left=0.01, right=0.99, top=0.96, bottom=0.06)
    return save(fig, "q2_fig3_flow")


if __name__ == "__main__":
    print(fig1_nominal())
    print(fig2_ortho())
    print(fig3_flow())
