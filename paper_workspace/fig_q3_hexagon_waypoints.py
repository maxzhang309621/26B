"""Single-panel Q3 hexagon listen-point figure for the paper."""
from __future__ import annotations

import math
import sys
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from coverage import (  # noqa: E402
    ARENA_R,
    COVER_R,
    Q3_RING_PHASE_DEG,
    q3_waypoints,
)

OUT = ROOT / "output" / "figures" / "q3_hexagon_waypoints"
COL = "#2166AC"
GREY = "#888888"
BLACK = "#222222"
ORIGIN = "#B2182B"


def main() -> None:
    mpl.rcParams.update(
        {
            "font.sans-serif": ["Microsoft YaHei", "SimHei", "Arial", "DejaVu Sans"],
            "font.size": 9,
            "axes.unicode_minus": False,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "pdf.fonttype": 42,
            "savefig.dpi": 300,
            "savefig.bbox": "tight",
        }
    )
    wps = q3_waypoints()
    origin, ring = wps[0], wps[1:]
    closed = ring + [ring[0]]

    fig, ax = plt.subplots(figsize=(5.6, 5.4))
    ax.set_aspect("equal")
    ax.add_patch(Circle((0, 0), ARENA_R, fill=False, ls="--", color=GREY, lw=1.0, zorder=1))
    ax.add_patch(
        Circle(
            ring[0],
            COVER_R,
            fill=True,
            facecolor=COL,
            alpha=0.10,
            edgecolor=COL,
            lw=0.8,
            ls=(0, (3, 2)),
            zorder=1,
        )
    )
    ax.plot([origin[0], ring[0][0]], [origin[1], ring[0][1]], color=COL, lw=1.0, alpha=0.7, zorder=2)
    ax.plot([p[0] for p in closed], [p[1] for p in closed], color=COL, lw=1.4, zorder=2)
    ax.scatter([p[0] for p in ring], [p[1] for p in ring], s=42, c=COL, zorder=4, edgecolors="white", linewidths=0.5)
    ax.scatter([0], [0], s=58, c=ORIGIN, marker="D", zorder=5, edgecolors="white", linewidths=0.5)
    for i, p in enumerate(ring, start=1):
        ax.annotate(str(i), p, textcoords="offset points", xytext=(7, 6), fontsize=9, color=BLACK)
    ax.annotate("原点\n全扫 1–20", (0, 0), textcoords="offset points", xytext=(10, -22), fontsize=8, color=ORIGIN)
    ax.annotate(
        rf"$r_{{\mathrm{{eff}}}}=1000\,\mathrm{{m}}$",
        ring[0],
        textcoords="offset points",
        xytext=(12, -28),
        fontsize=8,
        color=COL,
    )
    ax.annotate(
        rf"$\rho=1150\,\mathrm{{m}},\ \varphi={Q3_RING_PHASE_DEG:.0f}^\circ$",
        (0, -ARENA_R),
        textcoords="offset points",
        xytext=(0, -16),
        fontsize=8,
        color=BLACK,
        ha="center",
    )
    ax.set_xlim(-2050, 2050)
    ax.set_ylim(-2150, 2050)
    ax.set_xlabel(r"$x$ (m)")
    ax.set_ylabel(r"$y$ (m)")
    ax.legend(
        handles=[
            Line2D([0], [0], marker="D", color="w", markerfacecolor=ORIGIN, markersize=7, label="原点检测点"),
            Line2D([0], [0], marker="o", color="w", markerfacecolor=COL, markersize=7, label="正六边形检测点"),
            Line2D([0], [0], color=GREY, ls="--", lw=1.0, label="工作圆 1800 m"),
        ],
        loc="upper right",
        frameon=False,
        fontsize=8,
    )
    fig.savefig(str(OUT) + ".png", facecolor="white")
    fig.savefig(str(OUT) + ".pdf", facecolor="white")
    plt.close(fig)
    print("wrote", OUT.with_suffix(".png"))


if __name__ == "__main__":
    main()
