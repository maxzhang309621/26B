"""Two-panel Q3 algorithm schematic: ring-edge second look vs enroute ΔL."""
from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Polygon

# Academic Figure Skill Typography Baseline — COPY VERBATIM, place at TOP of script
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

OUT = Path(r"D:\maxzhang\python files\Math-modeling\26B\output\figures\q3_edge_enroute_algo")
MM = 1 / 25.4
BLUE, RED, GREEN, ORANGE, PURPLE, GREY = CATEGORICAL
BLACK = "#222222"


def main() -> None:
    fig, axes = plt.subplots(1, 2, figsize=(170 * MM, 72 * MM))

    ax = axes[0]
    ax.set_aspect("equal")
    A, B = np.array([0.0, 0.0]), np.array([10.0, 0.0])
    ax.plot([A[0], B[0]], [A[1], B[1]], color=BLUE, lw=1.8, zorder=2)
    ax.scatter([A[0], B[0]], [A[1], B[1]], s=28, color=BLUE, zorder=3)
    ax.text(A[0], A[1] - 0.55, "A", ha="center", fontsize=8)
    ax.text(B[0], B[1] - 0.55, "B", ha="center", fontsize=8)
    ts = (0.25, 0.4, 0.5, 0.6, 0.75)
    samples = np.array([(1 - t) * A + t * B for t in ts])
    ax.scatter(samples[:, 0], samples[:, 1], s=18, color=GREY, zorder=3)
    chosen = samples[3]
    ax.scatter([chosen[0]], [chosen[1]], s=42, color=RED, zorder=4, marker="s")
    s1 = np.array([2.2, -3.4])
    ax.scatter([s1[0]], [s1[1]], s=32, color=ORANGE, zorder=4)
    ax.text(s1[0] - 0.15, s1[1] - 0.55, r"$s_1$", ha="center", fontsize=8)
    # candidate band as a parallelogram crossing the edge
    band = np.array([[3.2, 1.35], [8.6, 1.35], [7.4, -1.35], [2.0, -1.35]])
    ax.add_patch(Polygon(band, closed=True, facecolor="#2166AC", alpha=0.12, edgecolor=BLUE, lw=0.8, zorder=1))
    ax.annotate(
        "问题二候选带",
        xy=(5.4, 1.15),
        xytext=(6.6, 2.35),
        fontsize=7,
        color=BLUE,
        arrowprops=dict(arrowstyle="->", color=BLUE, lw=0.7),
    )
    ax.plot([s1[0], chosen[0]], [s1[1], chosen[1]], color=ORANGE, ls=(0, (3, 2)), lw=0.8, zorder=2)
    ax.text(chosen[0], chosen[1] + 0.45, r"$P(t^{*})$", ha="center", fontsize=7, color=RED)
    ax.text(5.0, -2.55, r"$P(t)=(1-t)A+tB$", ha="center", fontsize=7, color=BLACK)
    ax.text(5.0, -3.15, r"$t\in\{0.25,0.40,0.50,0.60,0.75\}$", ha="center", fontsize=7, color=GREY)
    ax.set_xlim(-1.2, 11.2)
    ax.set_ylim(-3.7, 3.0)
    ax.axis("off")
    ax.set_title("a  环边补测：边上合法第二站", loc="left", fontsize=8, fontweight="bold", pad=2)

    ax = axes[1]
    ax.set_aspect("equal")
    P, Q, C = np.array([0.0, 0.0]), np.array([10.0, 0.0]), np.array([4.6, 2.15])
    ax.plot([P[0], Q[0]], [P[1], Q[1]], color=BLUE, lw=1.8, zorder=2)
    ax.plot([P[0], C[0], Q[0]], [P[1], C[1], Q[1]], color=GREEN, ls=(0, (4, 2)), lw=1.4, zorder=2)
    ax.scatter([P[0], Q[0]], [P[1], Q[1]], s=28, color=BLUE, zorder=3)
    ax.scatter([C[0]], [C[1]], s=42, color=GREEN, zorder=4)
    ax.text(P[0], P[1] - 0.55, "P", ha="center", fontsize=8)
    ax.text(Q[0], Q[1] - 0.55, "Q", ha="center", fontsize=8)
    ax.text(C[0], C[1] + 0.42, "C", ha="center", fontsize=8, color=GREEN)
    ax.text(5.0, -1.55, r"$\Delta L=d(P,C)+d(C,Q)-d(P,Q)$", ha="center", fontsize=7)
    ax.text(5.0, -2.2, r"门控：$\Delta L\leq 280\,\mathrm{m}$ 且示向 $\geq 2$", ha="center", fontsize=7, color=GREY)
    ax.set_xlim(-1.2, 11.2)
    ax.set_ylim(-2.9, 3.15)
    ax.axis("off")
    ax.set_title("b  顺路清除：增量路程门控", loc="left", fontsize=8, fontweight="bold", pad=2)

    fig.savefig(str(OUT) + ".png", facecolor="white")
    fig.savefig(str(OUT) + ".pdf", facecolor="white")
    plt.close(fig)
    print("wrote", OUT.with_suffix(".png"))


if __name__ == "__main__":
    main()
