"""Q3 边扫边清演进图：时间压缩与账本、均值—尾部对照。数据来自探索素材，非正式测试。"""
from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

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

# Academic Figure Skill Nature/Cell/Science Color Palette -- COPY VERBATIM
CATEGORICAL = ["#2166AC", "#B2182B", "#1B7837", "#F1A340", "#762A83", "#666666"]
CATEGORICAL_EXTENDED = [
    "#2166AC", "#B2182B", "#1B7837", "#F1A340", "#762A83", "#666666",
    "#4393C3", "#D6604D", "#5AAE61", "#B35806", "#9970AB", "#999999",
]
DIVERGING   = ["#2166AC", "#F7F7F7", "#B2182B"]
SEQUENTIAL  = ["#F7FBFF", "#6BAED6", "#08306B"]
ACCENT_RED  = "#B2182B"
GREY        = "#999999"
BLACK       = "#222222"

# Academic Figure Skill Export Baseline — COPY VERBATIM
mpl.rcParams.update({
    "pdf.fonttype": 42,
    "svg.fonttype": "none",
    "savefig.bbox": None,
    "savefig.dpi": 300,
})

mpl.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial", "Helvetica"]
mpl.rcParams["axes.unicode_minus"] = False

OUT = Path(__file__).resolve().parent / "revised_assets"
MM = 1 / 25.4
BLUE, RED, GREEN, ORANGE, PURPLE, GREY6 = CATEGORICAL


def save_cns_figure(fig, filename: Path) -> None:
    # Keep the canvas ratio identical to its Word drawing box.  ``tight``
    # crops each side differently and causes visible squashing on replacement.
    fig.savefig(f"{filename}.pdf", bbox_inches=None, dpi=300, facecolor="white")
    fig.savefig(f"{filename}.png", bbox_inches=None, dpi=600, facecolor="white")


def fig_cost() -> None:
    """左：在线路线内部压缩；右：严格基线时间账本。"""
    rounds = ["局部试探", "交会优先", "增量调度"]
    means = np.array([8844.80, 6293.90, 5347.74])
    # travel ledger of later strict mock (80/80, mean 5156.596 s)
    parts = [
        ("清除绕行", 36.62, RED),
        ("主干规划", 28.39, BLUE),
        ("定位移动", 15.32, ORANGE),
        ("协议驻留", 14.13, GREY6),
        ("主干回接", 5.55, PURPLE),
    ]
    assert abs(sum(p[1] for p in parts) - 100.01) < 0.1 or abs(sum(p[1] for p in parts) - 100) < 0.05

    # Match the original Word container exactly: 5.10 in x 2.54 in.
    fig, axes = plt.subplots(1, 2, figsize=(5.10, 2.54), gridspec_kw={"width_ratios": [1.0, 1.05]})

    ax = axes[0]
    y = np.arange(len(rounds))
    colors = [GREY6, BLUE, GREEN]
    ax.barh(y, means, color=colors, height=0.62, zorder=2)
    labels = ["8845 s", "6294 s  (−28.8%)", "5348 s  (−15.0%)"]
    for i, (v, lab) in enumerate(zip(means, labels)):
        ax.text(v + 90, i, lab, va="center", ha="left", fontsize=6.5, color=BLACK)
    ax.set_yticks(y, rounds)
    ax.invert_yaxis()
    ax.set_xlabel("本地 Mock 平均虚拟时间 (s)")
    ax.set_xlim(0, 14500)
    ax.text(0.0, 1.07, "a  在线路线内部压缩", transform=ax.transAxes, fontsize=8, color=BLACK, fontweight="bold")
    ax.grid(axis="x", color="#E5E9EE", linewidth=0.45, zorder=0)
    ax.set_axisbelow(True)

    ax = axes[1]
    left = 0.0
    for name, pct, color in parts:
        ax.barh([0], [pct], left=left, color=color, height=0.42, zorder=2)
        mid = left + pct / 2
        if pct >= 10:
            ax.text(mid, 0.0, f"{pct:.1f}%", ha="center", va="center", fontsize=6.5, color="white")
        left += pct
    ax.set_yticks([])
    ax.set_xlabel("占总虚拟时间的比例 (%)")
    ax.set_xlim(0, 100)
    ax.set_ylim(-0.72, 0.88)
    ax.text(0.0, 1.07, "b  后续严格基线账本（移动 85.9%）", transform=ax.transAxes, fontsize=8, color=BLACK, fontweight="bold")
    handles = [
        plt.Rectangle((0, 0), 1, 1, color=c, label=n) for n, _, c in parts
    ]
    ax.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, 0.02),
              ncol=3, fontsize=3.5, handlelength=0.7, columnspacing=0.42,
              handletextpad=0.22, labelspacing=0.30)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.annotate(
        "清除绕行最大",
        xy=(36.62 / 2, 0.22),
        xytext=(18, 0.60),
        fontsize=7,
        color=RED,
        ha="center",
        arrowprops=dict(arrowstyle="->", color=RED, lw=0.7),
    )

    fig.subplots_adjust(wspace=0.40, bottom=0.20)
    save_cns_figure(fig, OUT / "q3_scan_clear_cost")
    plt.close(fig)


def fig_tail() -> None:
    """均值改善（正=变快）对配对 P90 回退。全部为本地 Mock。"""
    pts = [
        dict(name="六点环 1150 m", mean=-4.090, p90=17.413, color=GREY6, dx=0.05, dy=1.05),
        dict(name="首段入口自适应", mean=0.927, p90=6.620, color=BLUE, dx=0.15, dy=0.95),
        dict(name="八点环 1150 m 扩展", mean=3.804, p90=2.600, color=PURPLE, dx=0.1, dy=-1.45),
        dict(name="服务驱动外扩", mean=5.754, p90=4.569, color=GREEN, dx=-0.15, dy=0.95),
    ]
    fig, ax = plt.subplots(figsize=(140 * MM, 88 * MM))
    ax.axvline(0.0, color=GREY, lw=0.7, ls=(0, (3, 2)), zorder=1)
    ax.axhline(0.0, color=GREY, lw=0.7, ls=(0, (3, 2)), zorder=1)
    ax.fill_between([-8, 0], 0, 20, color="#F7F7F7", zorder=0)
    ax.fill_between([0, 8], 0, 20, color="#FDECEC", zorder=0, alpha=0.55)

    for p in pts:
        ax.scatter(p["mean"], p["p90"], s=38, color=p["color"], zorder=3, edgecolors=BLACK, linewidths=0.3)
        ax.annotate(
            p["name"],
            xy=(p["mean"], p["p90"]),
            xytext=(p["mean"] + p["dx"], p["p90"] + p["dy"]),
            fontsize=7,
            color=BLACK,
            ha="center",
        )

    ax.set_xlabel("均值相对改善（%，正值表示变快）")
    ax.set_ylabel("配对 P90 相对回退（%）")
    ax.set_xlim(-7.2, 7.6)
    ax.set_ylim(-1.2, 20.5)
    ax.text(3.8, 18.6, "均值变快，尾部仍回退", fontsize=7, color=RED, ha="center")
    ax.text(-3.8, 1.2, "均值未改善", fontsize=7, color=GREY6, ha="center")
    save_cns_figure(fig, OUT / "q3_scan_clear_tail")
    plt.close(fig)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    fig_cost()
    fig_tail()
    print("wrote", OUT / "q3_scan_clear_cost.png")
    print("wrote", OUT / "q3_scan_clear_tail.png")
