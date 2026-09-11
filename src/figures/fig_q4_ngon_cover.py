"""Q4 inner/outer regular n-gons: covering detection-tour time."""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Circle

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from coverage import (  # noqa: E402
    ARENA_R,
    COVER_R,
    q4_double_ring_search_time,
    q4_double_ring_waypoints,
    q4_opt_inner_r,
    q4_opt_search_waypoints,
)

OUT_PNG = ROOT.parent / "output" / "figures" / "q4_ngon_cover_time.png"
OUT_PDF = ROOT.parent / "output" / "figures" / "q4_ngon_cover_time.pdf"
BLUE = "#2166AC"
RED = "#B2182B"
GREEN = "#1B7837"
GREY = "#888888"
ORANGE = "#E08214"


def _setup_font() -> None:
    mpl.rcParams.update(
        {
            "font.size": 10,
            "axes.titlesize": 11,
            "axes.labelsize": 10,
            "legend.fontsize": 8,
            "axes.unicode_minus": False,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )
    for name in ("Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Source Han Sans SC"):
        if any(name.lower() in f.name.lower() for f in font_manager.fontManager.ttflist):
            mpl.rcParams["font.sans-serif"] = [name, "DejaVu Sans"]
            return
    mpl.rcParams["font.sans-serif"] = ["DejaVu Sans"]


def _row(n_in, inner_r, n_out, outer_r, align, enroute_r):
    return q4_double_ring_search_time(
        n_in,
        inner_r,
        n_out,
        outer_r,
        align=align,
        enroute_r=enroute_r,
        check_cover=False,
    )


def main() -> None:
    _setup_font()
    rho7 = q4_opt_inner_r()
    catalog = [
        ("7+12 同径向", _row(7, rho7, 12, 1865.0, "radial", None), BLUE, True),
        ("8+12 同径向", _row(8, 1000.0, 12, 1865.0, "radial", None), GREEN, True),
        ("8+12 交错", _row(8, 1000.0, 12, 1865.0, "stagger", None), "#A6DBA0", True),
        ("9+12 同径向", _row(9, 1000.0, 12, 1865.0, "radial", None), GREY, True),
        ("6+12+途听", _row(6, 1150.0, 12, 1865.0, "radial", 900.0), ORANGE, True),
        ("8+12×2100+途听", _row(8, 1200.0, 12, 2100.0, "radial", 900.0), RED, False),
    ]

    fig, axes = plt.subplots(1, 2, figsize=(10.8, 4.5), dpi=150)

    ax = axes[0]
    xs = list(range(len(catalog)))
    travel = [float(row["travel_s"]) for _, row, _, _ in catalog]
    dwell = [float(row["dwell_s"]) for _, row, _, _ in catalog]
    total = [float(row["total_s"]) for _, row, _, _ in catalog]
    ax.bar(xs, travel, color=BLUE, width=0.62, label="行驶")
    ax.bar(xs, dwell, bottom=travel, color=GREEN, width=0.62, label="检测+切频（每站满扫 20 信道）")
    ax.plot(xs, total, color="#222222", marker="o", ms=4.5, lw=1.2, label="总虚拟时间")
    ax.axhline(total[0], color=GREY, ls="--", lw=0.8)
    ax.set_xticks(xs)
    ax.set_xticklabels([name for name, *_ in catalog], rotation=22, ha="right")
    ax.set_ylabel("覆盖巡游虚拟时间 (s)")
    ax.set_title("全覆盖（密网格前瓣）下的检测巡游")
    ax.legend(loc="upper left")

    ax = axes[1]
    ax.set_aspect("equal")
    ax.add_patch(Circle((0, 0), ARENA_R, fill=False, ls="--", color=GREY, lw=1.0))
    ax.add_patch(Circle((0, 0), COVER_R, fill=False, color=GREEN, lw=0.9, alpha=0.7))
    opt = q4_opt_search_waypoints()
    inner = opt[1:8] + [opt[1]]
    outer = opt[8:] + [opt[8]]
    ax.plot([p[0] for p in inner], [p[1] for p in inner], color=BLUE, lw=1.8)
    ax.plot([p[0] for p in outer], [p[1] for p in outer], color=BLUE, lw=1.2)
    ax.scatter([p[0] for p in opt], [p[1] for p in opt], s=22, color=BLUE, zorder=3)
    old = q4_double_ring_waypoints(8, 1200.0, 12, 2100.0, align="radial", enroute_r=900.0)
    ax.scatter(
        [p[0] for p in old],
        [p[1] for p in old],
        s=16,
        facecolors="none",
        edgecolors=RED,
        lw=0.9,
        zorder=2,
        label="现行 8×1200+12×2100+8×900",
    )
    ax.plot([-50, 1865], [0, 0], color=BLUE, lw=0.7, ls=":", label="同径向（共享 0° 射线）")
    ax.set_xlim(-2300, 2300)
    ax.set_ylim(-2300, 2300)
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_title(f"最优：正7边形 ρ={rho7:.0f} m + 正12边形 1865 m")
    ax.legend(loc="lower left", fontsize=7.5)
    ax.text(0, 0, "原点\n1–20", ha="center", va="center", fontsize=8)

    fig.suptitle("问题 4 检测环：内/外正 n 边形与径向对齐的全覆盖耗时", fontsize=12)
    fig.tight_layout()
    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PNG, dpi=150, bbox_inches="tight", facecolor="white")
    fig.savefig(OUT_PDF, bbox_inches="tight")
    plt.close(fig)
    print("layout            n_in n_out  rin   rout  align    enr  stops  travel   dwell    total")
    for name, row, _color, _keep in catalog:
        print(
            f"{name:16s} {row['n_inner']:4d} {row['n_outer']:5d} "
            f"{row['inner_r']:6.0f} {row['outer_r']:6.0f} {row['align']:7s} "
            f"{str(row['enroute_r']):5s} {row['n_stops']:5d} "
            f"{row['travel_s']:7.1f} {row['dwell_s']:7.0f} {row['total_s']:7.1f}"
        )
    print("wrote", OUT_PNG)


if __name__ == "__main__":
    main()
