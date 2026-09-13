"""Schematic: locked open TSP vs receding-horizon replan."""
from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

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
    "savefig.bbox": "tight",
    "savefig.dpi": 300,
})
mpl.rcParams["savefig.bbox"] = None
mpl.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial", "Helvetica"]
mpl.rcParams["axes.unicode_minus"] = False

OUT = Path(__file__).resolve().parent / "revised_assets" / "figure18_revised"
MM = 1 / 25.4
BLUE, RED, GREEN, ORANGE, PURPLE, GREY = CATEGORICAL
BLACK = "#222222"


def _panel(ax, title, pos, cities, path, moved=None, new_path=None):
    ax.set_aspect("equal")
    xs, ys = zip(*cities)
    ax.scatter(xs, ys, s=27, color=ORANGE, zorder=3, edgecolors=BLACK, linewidths=0.25)
    offsets = [(0.16, 0.18), (0.74, 0.56), (0.16, 0.18), (0.18, 0.18)]
    for i, ((x, y), (dx, dy)) in enumerate(zip(cities, offsets), start=1):
        ax.text(x + dx, y + dy, f"c{i}", fontsize=5.6, color=BLACK)
    ax.scatter([pos[0]], [pos[1]], s=36, color=BLUE, zorder=4, marker="s")
    ax.text(pos[0] - 0.14, pos[1] - 0.38, "P", fontsize=5.6, color=BLUE, ha="right", va="top")
    seq = [pos, *path]
    ax.plot([p[0] for p in seq], [p[1] for p in seq], color=BLUE, ls=(0, (4, 2)), lw=1.3, zorder=2)
    if moved is not None:
        ax.annotate(
            "",
            xy=moved,
            xytext=pos,
            arrowprops=dict(arrowstyle="->", color=GREEN, lw=1.6),
        )
    if new_path is not None:
        seq2 = [moved, *new_path]
        ax.plot([p[0] for p in seq2], [p[1] for p in seq2], color=GREEN, lw=1.5, zorder=2)
    ax.set_xlim(-0.35, 6.15)
    ax.set_ylim(-0.55, 4.15)
    ax.set_xlabel("相对 x", labelpad=1)
    ax.set_ylabel("相对 y", labelpad=1)
    ax.tick_params(labelsize=4.7, length=2)
    ax.grid(color="#E5E9EE", linewidth=0.45, zorder=0)
    ax.set_axisbelow(True)
    ax.set_title(title, loc="left", fontsize=6.2, fontweight="bold", pad=4)


def main() -> None:
    pos = np.array([0.3, 0.4])
    c = [
        np.array([1.6, 3.2]),
        np.array([3.5, 1.1]),
        np.array([5.4, 3.4]),
        np.array([4.8, 0.3]),
    ]
    locked = [c[1], c[3], c[0], c[2]]
    # Match the original Word container exactly: 4.87 in x 1.90 in.
    fig, axes = plt.subplots(1, 2, figsize=(4.87, 1.90))
    _panel(axes[0], "a  一次锁定开放路", pos, c, locked)
    _panel(
        axes[1],
        "b  执行第一城后从新位姿重解",
        pos,
        c,
        locked,
        moved=c[1],
        new_path=[c[0], c[2], c[3]],
    )
    handles = [
        Line2D([], [], marker="s", color="none", markerfacecolor=BLUE, markeredgecolor=BLUE,
               markersize=4.2, label="当前位置"),
        Line2D([], [], marker="o", color="none", markerfacecolor=ORANGE, markeredgecolor=BLACK,
               markersize=4.2, label="服务点"),
        Line2D([], [], color=BLUE, ls=(0, (4, 2)), lw=1.1, label="一次锁定开放路"),
        Line2D([], [], color=GREEN, lw=1.3, label="执行首点后重解"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=4, fontsize=4.8,
               frameon=False, handlelength=1.4, columnspacing=0.9)
    fig.subplots_adjust(left=0.09, right=0.99, top=0.84, bottom=0.25, wspace=0.32)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(OUT) + ".png", facecolor="white", bbox_inches=None)
    fig.savefig(str(OUT) + ".pdf", facecolor="white", bbox_inches=None)
    plt.close(fig)
    print("wrote", OUT.with_suffix(".png"))


if __name__ == "__main__":
    main()
