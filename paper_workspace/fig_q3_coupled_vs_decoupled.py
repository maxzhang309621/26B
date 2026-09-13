"""Figure 17: coupled star-like clearing versus decoupled cover-then-clear.

The original embedded raster had no retained generator.  Coordinates are
normalized schematic coordinates: the mechanism and node topology are kept,
while axes and a compact legend make every symbol explicit.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Microsoft YaHei", "SimHei", "Arial", "Helvetica"],
    "font.size": 8,
    "axes.titlesize": 6.2,
    "axes.labelsize": 5.4,
    "xtick.labelsize": 4.6,
    "ytick.labelsize": 4.6,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.linewidth": 0.6,
    "pdf.fonttype": 42,
    "svg.fonttype": "none",
    "savefig.dpi": 600,
    "savefig.bbox": None,
})
mpl.rcParams["axes.unicode_minus"] = False

OUT = Path(__file__).resolve().parent / "revised_assets" / "figure17_revised"
MM = 1 / 25.4
BLUE, RED, GREEN, ORANGE, INK, GRID = "#2166AC", "#C43A31", "#1B7837", "#F1A340", "#222222", "#E5E9EE"


def _axes_style(ax, title: str) -> None:
    ax.set_aspect("equal")
    ax.set_xlim(-1.15, 1.15)
    # The lowest hearing point must not visually touch the x-axis spine.
    ax.set_ylim(-1.16, 1.15)
    ax.set_xlabel("相对 x", labelpad=1)
    ax.set_ylabel("相对 y", labelpad=1)
    ax.tick_params(length=2)
    ax.grid(color=GRID, linewidth=0.45, zorder=0)
    ax.set_axisbelow(True)
    ax.set_title(title, loc="left", fontweight="bold", pad=5)


def _hexagon() -> np.ndarray:
    angles = np.deg2rad([90, 30, -30, -90, -150, 150, 90])
    return np.c_[np.cos(angles), np.sin(angles)]


def main() -> None:
    # Match the original Word container exactly: 4.77 in x 2.46 in.
    fig, axes = plt.subplots(1, 2, figsize=(4.77, 2.46), sharex=True, sharey=True)
    ring = _hexagon()
    hearing = ring[:-1]
    sources = np.array([[-0.42, 0.42], [0.16, 0.56], [-0.22, 0.22],
                        [0.52, -0.10], [-0.50, -0.36], [0.08, -0.55]])
    depot = np.array([0.0, 0.0])

    # Coupled policy: each newly heard source sends the robot away from the ring.
    ax = axes[0]
    _axes_style(ax, "a  耦合式边巡边清：星形折返")
    ax.plot(ring[:, 0], ring[:, 1], color=BLUE, lw=1.4, zorder=2)
    coupled = np.array([hearing[0], sources[0], hearing[1], sources[1], hearing[2],
                        sources[2], hearing[3], sources[3], hearing[4], sources[4],
                        hearing[5], sources[5]])
    ax.plot(coupled[:, 0], coupled[:, 1], color=INK, lw=1.1, zorder=3)
    ax.scatter(hearing[:, 0], hearing[:, 1], s=26, color=BLUE, edgecolors="white", linewidths=0.45, zorder=5)
    ax.scatter(sources[:, 0], sources[:, 1], s=29, color=RED, edgecolors="white", linewidths=0.45, zorder=6)
    ax.scatter(*depot, s=32, color=GREEN, edgecolors="white", linewidths=0.45, zorder=6)

    # Decoupled policy: finish the coverage ring, then solve a compact source tour.
    ax = axes[1]
    _axes_style(ax, "b  解耦式覆盖清除：先环后批")
    ax.plot(ring[:, 0], ring[:, 1], color=BLUE, lw=1.7, zorder=2)
    batch_order = sources[[2, 0, 1, 3, 5, 4, 2]]
    ax.plot(batch_order[:, 0], batch_order[:, 1], color=ORANGE, lw=1.25, ls=(0, (4, 2)), zorder=3)
    ax.scatter(hearing[:, 0], hearing[:, 1], s=26, color=BLUE, edgecolors="white", linewidths=0.45, zorder=5)
    ax.scatter(sources[:, 0], sources[:, 1], s=29, color=RED, edgecolors="white", linewidths=0.45, zorder=6)
    ax.scatter(*depot, s=32, color=GREEN, edgecolors="white", linewidths=0.45, zorder=6)

    handles = [
        Line2D([], [], color=BLUE, lw=1.5, label="覆盖听点环"),
        Line2D([], [], color=INK, lw=1.1, label="耦合式折返轨迹"),
        Line2D([], [], color=ORANGE, lw=1.2, ls=(0, (4, 2)), label="批量清除轨迹"),
        Line2D([], [], marker="o", color="none", markerfacecolor=BLUE, markeredgecolor="white", markersize=4.5, label="听点"),
        Line2D([], [], marker="o", color="none", markerfacecolor=RED, markeredgecolor="white", markersize=4.5, label="干扰源"),
        Line2D([], [], marker="o", color="none", markerfacecolor=GREEN, markeredgecolor="white", markersize=4.5, label="原点"),
    ]
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, 0.055),
               ncol=3, fontsize=4.2, frameon=False, handlelength=1.15,
               columnspacing=0.45, handletextpad=0.30, labelspacing=0.65)
    # Keep the lower margin exclusively for the legend; no explanatory grey text.
    fig.subplots_adjust(left=0.10, right=0.98, top=0.87, bottom=0.37, wspace=0.25)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(OUT) + ".png", facecolor="white", bbox_inches=None)
    fig.savefig(str(OUT) + ".pdf", facecolor="white", bbox_inches=None)
    fig.savefig(str(OUT) + ".svg", facecolor="white", bbox_inches=None)
    plt.close(fig)
    print("wrote", OUT.with_suffix(".png"))


if __name__ == "__main__":
    main()
