"""Figure 20: compact optical trial grid after tightening its activation gate."""
from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, Rectangle

mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Microsoft YaHei", "SimHei", "Arial", "Helvetica"],
    "font.size": 8,
    "axes.labelsize": 8,
    "axes.titlesize": 8,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.linewidth": 0.65,
    "pdf.fonttype": 42,
    "svg.fonttype": "none",
    "savefig.dpi": 600,
})
mpl.rcParams["axes.unicode_minus"] = False

OUT = Path(__file__).resolve().parent / "revised_assets" / "figure20_revised"
BLUE, GREEN, RED, GRID, INK = "#2166AC", "#1B7837", "#C43A31", "#DDE3EA", "#222222"


def main() -> None:
    fig, ax = plt.subplots(figsize=(104 / 25.4, 92 / 25.4))
    ax.add_patch(Circle((0, 0), 22, fill=True, facecolor="#DCE9F5", alpha=0.55,
                        edgecolor=BLUE, lw=1.35, zorder=1))
    ax.add_patch(Circle((0, 0), 20, fill=False, edgecolor=GREEN, lw=1.15,
                        ls=(0, (4, 2)), zorder=2))

    # Four disjoint trial cells keep the local grid explicit without obscuring the circles.
    cells = [(-14, 3), (-2, 3), (-14, -10), (-2, -10)]
    for x, y in cells:
        ax.add_patch(Rectangle((x, y), 10, 10, facecolor="#AAB7C4", alpha=0.10,
                               edgecolor="#647586", lw=0.9, zorder=3))
    candidates = [(-9, 8), (8, 3), (3, -6)]
    ax.scatter(*zip(*candidates), s=27, color=BLUE, zorder=5, edgecolors="white", linewidths=0.40)
    ax.scatter([-9], [-9], s=44, marker="x", color=RED, linewidths=1.25, zorder=6)

    ax.set_aspect("equal")
    ax.set_xlim(-32, 32)
    ax.set_ylim(-32, 32)
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.grid(color=GRID, linewidth=0.45, zorder=0)
    ax.set_axisbelow(True)
    ax.set_title("局部光学试清：越界或近共线即停", loc="left", fontweight="bold", pad=5)
    ax.legend(handles=[
        Line2D([], [], color=BLUE, lw=1.25, label="SEC 半径 ≤ 28 m"),
        Line2D([], [], color=GREEN, lw=1.15, ls=(0, (4, 2)), label="清除半径 20 m"),
        Rectangle((0, 0), 1, 1, fc="#AAB7C4", ec="#647586", alpha=0.35, label="受限试清网格"),
        Line2D([], [], marker="o", color="none", markerfacecolor=BLUE, markeredgecolor="white", markersize=4.4, label="候选试清点"),
        Line2D([], [], marker="x", color=RED, markersize=4.8, lw=0, label="试清 miss 即停"),
    ], loc="upper right", fontsize=4.8, frameon=True, fancybox=False,
       edgecolor="#D3D8DE", handlelength=1.25, labelspacing=0.25,
       borderpad=0.35, handletextpad=0.4)
    fig.tight_layout(pad=0.8)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(OUT) + ".png", facecolor="white")
    fig.savefig(str(OUT) + ".pdf", facecolor="white")
    fig.savefig(str(OUT) + ".svg", facecolor="white")
    plt.close(fig)
    print("wrote", OUT.with_suffix(".png"))


if __name__ == "__main__":
    main()
