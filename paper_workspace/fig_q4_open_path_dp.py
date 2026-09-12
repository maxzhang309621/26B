"""Q4 path-opt schematic: no-skip local cluster + Held–Karp open DP."""
from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, FancyBboxPatch
from matplotlib.lines import Line2D

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
    "legend.frameon": False,
    "pdf.fonttype": 42,
    "svg.fonttype": "none",
    "savefig.bbox": "tight",
    "savefig.dpi": 300,
})
mpl.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial", "Helvetica"]
mpl.rcParams["axes.unicode_minus"] = False

CATEGORICAL = ["#2166AC", "#B2182B", "#1B7837", "#F1A340", "#762A83", "#666666"]
BLUE, RED, GREEN, ORANGE, PURPLE, GREY = CATEGORICAL
BLACK = "#222222"
MM = 1 / 25.4
OUT = Path(r"D:\maxzhang\python files\Math-modeling\26B\output\figures\q4_open_path_dp")


def main() -> None:
    fig, axes = plt.subplots(1, 2, figsize=(183 * MM, 78 * MM))

    ax = axes[0]
    ax.set_aspect("equal")
    ax.axis("off")
    p = np.array([0.0, 0.0])
    loc = [np.array([1.15, 0.85]), np.array([0.35, 1.45]), np.array([1.55, -0.15])]
    far = [np.array([3.55, 1.35]), np.array([4.15, -0.55])]
    ax.add_patch(Circle(tuple(p), 1.85, fill=False, ls=(0, (4, 2)), color=GREY, lw=0.9, zorder=1))
    ax.text(0.15, 1.95, r"$650\,\mathrm{m}$ 局部簇", fontsize=7, color=GREY)
    ax.scatter([p[0]], [p[1]], s=52, color=BLUE, marker="s", zorder=5)
    ax.text(p[0] - 0.22, p[1] - 0.38, "P", fontsize=8, color=BLUE, ha="center")
    ax.scatter([c[0] for c in loc], [c[1] for c in loc], s=40, color=ORANGE, zorder=4,
               edgecolors=BLACK, linewidths=0.3)
    ax.scatter([c[0] for c in far], [c[1] for c in far], s=40, color=PURPLE, zorder=4,
               marker="D", edgecolors=BLACK, linewidths=0.3)
    for i, c in enumerate(loc, 1):
        ax.text(c[0] + 0.12, c[1] + 0.14, f"c{i}", fontsize=7)
    ax.text(far[0][0] + 0.12, far[0][1] + 0.14, "c4", fontsize=7)
    ax.text(far[1][0] + 0.12, far[1][1] - 0.32, "c5", fontsize=7)
    skip = [p, far[0], far[1], loc[0]]
    ax.plot([q[0] for q in skip], [q[1] for q in skip], color=RED, ls=(0, (3, 2)), lw=1.15, zorder=2)
    good = [p, loc[2], loc[0], loc[1], far[0], far[1]]
    ax.plot([q[0] for q in good], [q[1] for q in good], color=GREEN, lw=1.55, zorder=3)
    ax.set_xlim(-1.15, 5.05)
    ax.set_ylim(-1.35, 2.45)
    ax.legend(
        handles=[
            Line2D([0], [0], color=RED, ls=(0, (3, 2)), lw=1.2, label="欧氏开放路：远簇优先，近源留到最后"),
            Line2D([0], [0], color=GREEN, lw=1.4, label="无跳点：局部簇走完再接远簇"),
        ],
        loc="lower left",
        fontsize=6.3,
        handlelength=1.8,
        borderaxespad=0.1,
    )
    ax.set_title("a  分层无跳点约束", loc="left", fontsize=8, fontweight="bold")

    ax = axes[1]
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_xlim(-0.3, 6.6)
    ax.set_ylim(-0.85, 4.55)
    p = np.array([0.35, 0.55])
    c1 = np.array([2.05, 3.15])
    c2 = np.array([3.35, 0.85])
    c3 = np.array([5.35, 2.55])
    ax.scatter([p[0]], [p[1]], s=52, color=BLUE, marker="s", zorder=5)
    ax.text(p[0], p[1] - 0.38, "P", ha="center", fontsize=8, color=BLUE)
    for lab, q in (("c1", c1), ("c2", c2), ("c3", c3)):
        ax.scatter([q[0]], [q[1]], s=42, color=ORANGE, zorder=4, edgecolors=BLACK, linewidths=0.3)
        ax.text(q[0] + 0.16, q[1] + 0.16, lab, fontsize=7)
    ax.plot([p[0], c2[0], c1[0], c3[0]], [p[1], c2[1], c1[1], c3[1]],
            color=BLUE, ls=(0, (4, 2)), lw=1.25, zorder=2)
    ax.annotate("", xy=c2, xytext=p, arrowprops=dict(arrowstyle="->", color=GREEN, lw=1.7))
    ax.plot([c2[0], c3[0], c1[0]], [c2[1], c3[1], c1[1]], color=GREEN, lw=1.45, zorder=3)
    ax.add_patch(FancyBboxPatch((0.15, 3.55), 6.2, 0.88, boxstyle="round,pad=0.04",
                                facecolor="#F4F7FB", edgecolor=BLUE, lw=0.6))
    ax.text(
        3.25, 4.12,
        r"$f(S,j)=\min_{i\in S\setminus\{j\}}[f(S\setminus\{j\},i)+d(i,j)],\ \ f(\{j\},j)=d(P,j)$",
        ha="center", va="center", fontsize=7, color=BLACK,
    )
    ax.text(3.25, -0.55, r"只执行 $\pi^*$ 第一城，服务点随示向移动后再解", ha="center", fontsize=7, color=GREY)
    ax.set_title("b  开放路 Held–Karp 动态规划", loc="left", fontsize=8, fontweight="bold")

    fig.savefig(str(OUT) + ".png", facecolor="white")
    fig.savefig(str(OUT) + ".pdf", facecolor="white")
    plt.close(fig)
    print("wrote", OUT.with_suffix(".png"))


if __name__ == "__main__":
    main()
