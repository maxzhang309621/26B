"""Sorted stacked bar chart of feasible regular n-gon covering-tour times."""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from coverage import regular_ring_search_time  # noqa: E402

# Academic Figure Skill Typography Baseline — COPY VERBATIM
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

OUT = ROOT / "output" / "figures" / "q3_ngon_time_ranked"
BLUE = CATEGORICAL[0]
GREEN = CATEGORICAL[2]
ACCENT = CATEGORICAL[1]
GREY = "#666666"
MM = 1 / 25.4


def main() -> None:
    rows = [regular_ring_search_time(n) for n in range(6, 13)]
    rows.sort(key=lambda r: float(r["total_s"]))
    labels = [
        f"正{['六','七','八','九','十','十一','十二'][int(r['n'])-6]}边形"
        for r in rows
    ]
    travel = np.array([float(r["travel_s"]) for r in rows])
    dwell = np.array([float(r["dwell_s"]) for r in rows])
    total = travel + dwell
    y = np.arange(len(rows))

    fig, ax = plt.subplots(figsize=(140 * MM, 78 * MM))
    ax.barh(y, travel, color=BLUE, height=0.62, label="行驶")
    ax.barh(y, dwell, left=travel, color=GREEN, height=0.62, label="检测与换频驻留")
    for i, tot in enumerate(total):
        note = f"{tot:.0f} s"
        if int(rows[i]["n"]) == 6:
            note += "（最短）"
        ax.text(tot + 25, i, note, va="center", ha="left", fontsize=7, color=GREY)
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlabel("覆盖巡游虚拟时间 (s)")
    ax.set_xlim(0, max(total) * 1.28)
    ax.legend(loc="lower center", bbox_to_anchor=(0.45, 1.02), ncol=2, fontsize=7)
    ax.axvline(total[0], color=ACCENT, ls=(0, (3, 2)), lw=0.7, alpha=0.7)
    fig.savefig(str(OUT) + ".png", facecolor="white")
    fig.savefig(str(OUT) + ".pdf", facecolor="white")
    plt.close(fig)
    print("wrote", OUT.with_suffix(".png"))
    for r in rows:
        print(int(r["n"]), round(float(r["travel_s"]), 1), round(float(r["dwell_s"]), 1), round(float(r["total_s"]), 1))


if __name__ == "__main__":
    main()
