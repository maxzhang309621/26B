"""Compare origin + regular n-gon coverage tours, including stop/sweep time."""

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
    omni_waypoints,
    regular_ring_search_time,
)

OUT_PNG = ROOT.parent / "output" / "figures" / "q3_ngon_cover_time.png"
OUT_PDF = ROOT.parent / "output" / "figures" / "q3_ngon_cover_time.pdf"
BLUE = "#2166AC"
RED = "#B2182B"
GREEN = "#1B7837"
GREY = "#888888"


def _setup_font() -> None:
    mpl.rcParams.update(
        {
            "font.size": 10,
            "axes.titlesize": 11,
            "axes.labelsize": 10,
            "legend.fontsize": 9,
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


def main() -> None:
    _setup_font()
    rows = [regular_ring_search_time(n) for n in range(3, 13)]
    feasible = [row for row in rows if row["feasible"]]
    ns = [int(row["n"]) for row in feasible]
    travel = [float(row["travel_s"]) for row in feasible]
    detect = [float(row["detect_s"]) for row in feasible]
    switch = [float(row["switch_s"]) for row in feasible]
    total = [float(row["total_s"]) for row in feasible]
    best_n = ns[total.index(min(total))]

    fig, axes = plt.subplots(1, 2, figsize=(10.6, 4.4), dpi=150)

    ax = axes[0]
    ax.bar(ns, travel, color=BLUE, width=0.72, label="行驶")
    ax.bar(ns, detect, bottom=travel, color=GREEN, width=0.72, label="检测 5 s × 信道")
    ax.bar(
        ns,
        switch,
        bottom=[a + b for a, b in zip(travel, detect)],
        color=RED,
        width=0.72,
        label="切频 1 s × 信道",
    )
    ax.plot(ns, total, color="#222222", marker="o", ms=4.5, lw=1.2, label="总虚拟时间")
    ax.axvline(best_n, color=GREY, ls="--", lw=0.8)
    ax.set_xlabel("正 n 边形顶点数 n")
    ax.set_ylabel("覆盖巡游虚拟时间 (s)")
    ax.set_xticks(ns)
    ax.set_title("全覆盖约束下：原点 + 最小可行环半径")
    ax.legend(loc="upper left")

    ax = axes[1]
    hex_r = float(regular_ring_search_time(6)["ring_r"])
    oct_r = float(regular_ring_search_time(8)["ring_r"])
    ax.set_aspect("equal")
    ax.add_patch(Circle((0, 0), ARENA_R, fill=False, ls="--", color=GREY, lw=1.0))
    ax.add_patch(Circle((0, 0), COVER_R, fill=False, color=GREEN, lw=0.9, alpha=0.7))
    for n, rho, color, lw in ((6, hex_r, BLUE, 1.8), (8, oct_r, RED, 1.2)):
        wps = omni_waypoints(ring_r=rho, n=n)
        ring = wps[1:] + [wps[1]]
        ax.plot([p[0] for p in ring], [p[1] for p in ring], color=color, lw=lw)
        ax.scatter(
            [p[0] for p in wps],
            [p[1] for p in wps],
            s=28,
            color=color,
            zorder=3,
            label=f"正{n}边形  ρ={rho:.0f} m",
        )
    ax.set_xlim(-2000, 2000)
    ax.set_ylim(-2000, 2000)
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_title("最小可行环：正六边形比正八边形更靠外、停站更少")
    ax.legend(loc="lower left", fontsize=8)
    ax.text(0, 0, "原点全扫\n1–20", ha="center", va="center", fontsize=8, color="#222222")

    fig.suptitle("问题 3 检测环：保证最坏接收半径 1000 m 全覆盖的正 n 边形耗时", fontsize=12)
    fig.tight_layout()
    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PNG, dpi=150, bbox_inches="tight", facecolor="white")
    fig.savefig(OUT_PDF, bbox_inches="tight")
    plt.close(fig)
    print("n  feasible  rho_min  path_m  travel  detect  switch  dwell   total")
    for row in rows:
        if not row["feasible"]:
            print(f"{int(row['n']):2d}  no")
            continue
        print(
            f"{int(row['n']):2d}  yes   {row['ring_r']:7.1f} {row['path_m']:7.0f} "
            f"{row['travel_s']:7.1f} {row['detect_s']:7.0f} {row['switch_s']:7.0f} "
            f"{row['dwell_s']:7.0f} {row['total_s']:7.1f}"
        )
    print("wrote", OUT_PNG)


if __name__ == "__main__":
    main()
