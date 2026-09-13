"""Two-panel Q3 algorithm schematic: ring-edge second look vs enroute ΔL."""
from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Polygon
from matplotlib.lines import Line2D

# Academic Figure Skill Typography Baseline — COPY VERBATIM, place at TOP of script
mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "Liberation Sans"],
    "font.size": 8,
    "axes.titlesize": 6.2,
    "axes.labelsize": 5.5,
    "xtick.labelsize": 4.7,
    "ytick.labelsize": 4.7,
    "legend.fontsize": 4.8,
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
    "savefig.bbox": None,
    "savefig.dpi": 300,
})
mpl.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial", "Helvetica"]
mpl.rcParams["axes.unicode_minus"] = False

OUT = Path(__file__).resolve().parent / "revised_assets" / "figure19_revised"
MM = 1 / 25.4
BLUE, RED, GREEN, ORANGE, PURPLE, GREY = CATEGORICAL
BLACK = "#222222"


def main() -> None:
    # Match the original Word container exactly: 6.30 in x 1.95 in.
    fig, axes = plt.subplots(1, 2, figsize=(6.30, 1.95))

    ax = axes[0]
    ax.set_aspect("equal")
    A, B = np.array([0.0, 0.0]), np.array([10.0, 0.0])
    ax.plot([A[0], B[0]], [A[1], B[1]], color=BLUE, lw=1.8, zorder=2)
    ax.scatter([A[0], B[0]], [A[1], B[1]], s=21, color=BLUE, zorder=3)
    ax.annotate("A", A, xytext=(-7, -13), textcoords="offset points", ha="right", fontsize=5.6)
    ax.annotate("B", B, xytext=(7, -13), textcoords="offset points", ha="left", fontsize=5.6)
    ts = (0.25, 0.4, 0.5, 0.6, 0.75)
    samples = np.array([(1 - t) * A + t * B for t in ts])
    ax.scatter(samples[:, 0], samples[:, 1], s=13, color=GREY, zorder=3)
    chosen = samples[3]
    ax.scatter([chosen[0]], [chosen[1]], s=30, color=RED, zorder=4, marker="s")
    s1 = np.array([2.2, -3.4])
    ax.scatter([s1[0]], [s1[1]], s=24, color=ORANGE, zorder=4)
    ax.annotate(r"$s_1$", s1, xytext=(-7, -13), textcoords="offset points", ha="right", fontsize=5.6)
    # candidate band as a parallelogram crossing the edge
    band = np.array([[3.2, 1.35], [8.6, 1.35], [7.4, -1.35], [2.0, -1.35]])
    ax.add_patch(Polygon(band, closed=True, facecolor="#2166AC", alpha=0.12, edgecolor=BLUE, lw=0.8, zorder=1))
    ax.annotate(
        "问题二候选带",
        xy=(3.3, 1.00),
        xytext=(-0.65, 2.38),
        fontsize=5.6,
        color=BLUE,
        arrowprops=dict(arrowstyle="->", color=BLUE, lw=0.7),
    )
    ax.plot([s1[0], chosen[0]], [s1[1], chosen[1]], color=ORANGE, ls=(0, (3, 2)), lw=0.8, zorder=2)
    ax.annotate(r"$P(t^{*})$", chosen, xytext=(0, 10), textcoords="offset points", ha="center", fontsize=5.6, color=RED)
    ax.set_xlim(-1.25, 11.2)
    ax.set_ylim(-3.85, 3.05)
    ax.set_xlabel("相对 x", labelpad=1)
    ax.set_ylabel("相对 y", labelpad=1)
    ax.tick_params(labelsize=4.7, length=2)
    ax.grid(color="#E5E9EE", linewidth=0.45, zorder=0)
    ax.set_axisbelow(True)
    ax.set_title("a  环边补测：边上合法第二站", loc="left", fontsize=6.2, fontweight="bold", pad=4)

    ax = axes[1]
    ax.set_aspect("equal")
    P, Q, C = np.array([0.0, 0.0]), np.array([10.0, 0.0]), np.array([4.6, 2.15])
    ax.plot([P[0], Q[0]], [P[1], Q[1]], color=BLUE, lw=1.8, zorder=2)
    ax.plot([P[0], C[0], Q[0]], [P[1], C[1], Q[1]], color=GREEN, ls=(0, (4, 2)), lw=1.4, zorder=2)
    ax.scatter([P[0], Q[0]], [P[1], Q[1]], s=21, color=BLUE, zorder=3)
    ax.scatter([C[0]], [C[1]], s=30, color=GREEN, zorder=4)
    ax.annotate("P", P, xytext=(-6, -13), textcoords="offset points", ha="right", fontsize=5.6)
    ax.annotate("Q", Q, xytext=(6, -13), textcoords="offset points", ha="left", fontsize=5.6)
    ax.annotate("C", C, xytext=(0, 9), textcoords="offset points", ha="center", fontsize=5.6, color=GREEN)
    ax.set_xlim(-1.25, 11.2)
    ax.set_ylim(-2.9, 3.15)
    ax.set_xlabel("相对 x", labelpad=1)
    ax.set_ylabel("相对 y", labelpad=1)
    ax.tick_params(labelsize=4.7, length=2)
    ax.grid(color="#E5E9EE", linewidth=0.45, zorder=0)
    ax.set_axisbelow(True)
    ax.set_title("b  顺路清除：增量路程门控", loc="left", fontsize=6.2, fontweight="bold", pad=4)

    handles = [
        Line2D([], [], color=BLUE, lw=1.4, label="环边 / 原路径"),
        Line2D([], [], marker="o", color="none", markerfacecolor=GREY, markeredgecolor=GREY,
               markersize=3.8, label="候选采样点"),
        Line2D([], [], marker="s", color="none", markerfacecolor=RED, markeredgecolor=RED,
               markersize=4.2, label="采用的补测点"),
        Line2D([], [], color=GREEN, ls=(0, (4, 2)), lw=1.2, label="顺路清除路径"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=4, fontsize=4.8, frameon=False,
               handlelength=1.35, columnspacing=0.85)
    fig.subplots_adjust(left=0.07, right=0.99, top=0.83, bottom=0.27, wspace=0.25)
    OUT.parent.mkdir(parents=True, exist_ok=True)

    fig.savefig(str(OUT) + ".png", facecolor="white", bbox_inches=None)
    fig.savefig(str(OUT) + ".pdf", facecolor="white", bbox_inches=None)
    plt.close(fig)
    print("wrote", OUT.with_suffix(".png"))


if __name__ == "__main__":
    main()
