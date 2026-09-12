"""Schematic: locked open TSP vs receding-horizon replan."""
from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

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

OUT = Path(r"D:\maxzhang\python files\Math-modeling\26B\output\figures\q3_rh_open_path")
MM = 1 / 25.4
BLUE, RED, GREEN, ORANGE, PURPLE, GREY = CATEGORICAL
BLACK = "#222222"


def _panel(ax, title, pos, cities, path, moved=None, new_path=None):
    ax.set_aspect("equal")
    xs, ys = zip(*cities)
    ax.scatter(xs, ys, s=36, color=ORANGE, zorder=3, edgecolors=BLACK, linewidths=0.3)
    for i, (x, y) in enumerate(cities, start=1):
        ax.text(x + 0.18, y + 0.18, f"c{i}", fontsize=7, color=BLACK)
    ax.scatter([pos[0]], [pos[1]], s=48, color=BLUE, zorder=4, marker="s")
    ax.text(pos[0] - 0.15, pos[1] - 0.45, "P", fontsize=8, color=BLUE, ha="center")
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
    ax.set_xlim(-0.6, 6.4)
    ax.set_ylim(-0.7, 4.6)
    ax.axis("off")
    ax.set_title(title, loc="left", fontsize=8, fontweight="bold", pad=2)


def main() -> None:
    pos = np.array([0.3, 0.4])
    c = [
        np.array([1.6, 3.2]),
        np.array([3.5, 1.1]),
        np.array([5.4, 3.4]),
        np.array([4.8, 0.3]),
    ]
    locked = [c[1], c[3], c[0], c[2]]
    fig, axes = plt.subplots(1, 2, figsize=(170 * MM, 68 * MM))
    _panel(axes[0], "a  一次锁定开放路", pos, c, locked)
    axes[0].text(3.2, -0.55, "服务点随后续示向移动时，整条锁定路失效", ha="center", fontsize=7, color=GREY)
    _panel(
        axes[1],
        "b  执行第一城后从新位姿重解",
        pos,
        c,
        locked,
        moved=c[1],
        new_path=[c[0], c[2], c[3]],
    )
    axes[1].text(3.2, -0.55, r"每步只执行 $\pi^\ast$ 的第一座城市，再滚动重规划", ha="center", fontsize=7, color=GREY)
    fig.savefig(str(OUT) + ".png", facecolor="white")
    fig.savefig(str(OUT) + ".pdf", facecolor="white")
    plt.close(fig)
    print("wrote", OUT.with_suffix(".png"))


if __name__ == "__main__":
    main()
