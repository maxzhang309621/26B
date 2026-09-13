"""Redraw Q2 manuscript figures 5-7 (2026B-问题2-修改(2).docx).

Data provenance
---------------
fig5  400-sample residual histograms. The 400-row sample vectors are not in the
      workspace; bin counts are transcribed from the manuscript figure
      (both panels sum to 400).
fig6  Analytical angle-residual field. S1=(0,0), first bearing 35 deg,
      second station at body coordinates (850 m, 600 m); candidate bands from
      src/candidate.py.
fig7  Inversion comparison metrics exactly as reported in the manuscript text
      and Table 1 (same batch of 400 true sources).

Outputs go to output/figures/q2_final/ (PNG 300 dpi + SVG).
"""

from __future__ import annotations

import math
import os
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch, Polygon  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from candidate import candidate_region, from_body  # noqa: E402

OUT = ROOT / "output" / "figures" / "q2_final"

plt.rcParams.update(
    {
        "font.sans-serif": ["Microsoft YaHei", "SimHei"],
        "axes.unicode_minus": False,
        "font.size": 10.5,
        "axes.linewidth": 0.8,
        "axes.edgecolor": "#4D4D4D",
        "text.color": "#1A1A1A",
        "axes.labelcolor": "#1A1A1A",
        "xtick.color": "#4D4D4D",
        "ytick.color": "#4D4D4D",
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
    }
)

BLUE = "#0072B2"
SKY = "#56B4E9"
ORANGE = "#E69F00"
GREEN = "#009E73"
VERM = "#D55E00"
PURPLE = "#CC79A7"
GRAY = "#8C8C8C"
DARK = "#1A1A1A"
TEAL = "#2A9D8F"
BOX_FC = "#F7F7F7"
BOX_EC = "#CFCFCF"


def _save(fig, stem: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "svg"):
        target = OUT / f"{stem}.{ext}"
        staging = target.with_name(target.stem + ".staging" + target.suffix)
        fig.savefig(staging, dpi=300)
        os.replace(staging, target)
    plt.close(fig)
    print(OUT / f"{stem}.png")


def _corner_box(ax, text: str, loc: str = "upper left", fs: float = 8.8) -> None:
    x = 0.02 if "left" in loc else 0.98
    y = 0.97 if "upper" in loc else 0.03
    ax.text(
        x, y, text, transform=ax.transAxes, fontsize=fs,
        ha="left" if "left" in loc else "right",
        va="top" if "upper" in loc else "bottom",
        zorder=10, linespacing=1.5,
        bbox=dict(boxstyle="round,pad=0.34", fc=BOX_FC, ec=BOX_EC, lw=0.7, alpha=0.95),
    )


def _label(ax, x, y, text: str, color: str = DARK, fs: float = 10, ha: str = "left",
           va: str = "center", halo: bool = True, zorder: int = 10) -> None:
    ax.text(
        x, y, text, fontsize=fs, color=color, ha=ha, va=va, zorder=zorder,
        bbox=dict(boxstyle="round,pad=0.14", fc="white", ec="none", alpha=0.85) if halo else None,
    )


def _smooth(counts: np.ndarray, sigma: float = 0.9) -> np.ndarray:
    half = int(3 * sigma)
    k = np.exp(-0.5 * (np.arange(-half, half + 1) / sigma) ** 2)
    k /= k.sum()
    padded = np.pad(counts.astype(float), half, mode="edge")
    return np.convolve(padded, k, mode="same")[half:-half]


# ---------------------------------------------------------------------------
# Figure 5
# ---------------------------------------------------------------------------

def fig5_residual_distribution() -> None:
    beta_counts = np.array([22, 21, 18, 20, 22, 18, 17, 17, 21, 14, 27, 18, 17, 25, 26, 26, 20, 29, 22])
    radius_counts = np.array([120, 62, 56, 40, 9, 10, 15, 9, 9, 10, 9, 4, 6, 6, 7, 10, 7, 7, 4])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.6, 4.4), layout="constrained",
                                   gridspec_kw={"wspace": 0.30})

    # ---- (a) e_beta ----
    edges_b = np.linspace(-38, 38, len(beta_counts) + 1)
    centers_b = 0.5 * (edges_b[:-1] + edges_b[1:])
    ax1.axvspan(-30, 30, color="#DFF0EC", zorder=0)
    ax1.bar(edges_b[:-1], beta_counts, width=np.diff(edges_b), align="edge",
            color=BLUE, alpha=0.88, edgecolor="white", linewidth=0.8, zorder=2)
    ax1.plot(centers_b, _smooth(beta_counts), color="#0B3C5D", lw=1.5, zorder=3)
    for x in (-30, 30):
        ax1.axvline(x, color=TEAL, ls=(0, (4, 2.5)), lw=1.1, zorder=3)
    ax1.axvline(0, color="#9AA5AB", lw=0.8, zorder=3)
    ax1.set_xlim(-42, 42)
    ax1.set_ylim(0, 40)
    ax1.set_xticks([-40, -20, 0, 20, 40])
    ax1.set_xlabel("交会角残差 $e_\\beta$（°）")
    ax1.set_ylabel("频数")
    ax1.set_title("(a) 交会角残差分布", loc="left", fontsize=11.5, pad=8)
    ax1.grid(True, axis="y", color="#EFEFEF", lw=0.7, zorder=0)
    _corner_box(ax1, "阴影：直角邻域 $|e_\\beta|\\leq 30°$\n"
                     "$|e_\\beta|$ 中位 20.1°｜90% 分位 34.1°\n最大 37.7°｜近共线 0", "upper left")

    # ---- (b) e_r ----
    edges_r = np.linspace(-2, 22, len(radius_counts) + 1)
    centers_r = 0.5 * (edges_r[:-1] + edges_r[1:])
    ax2.axvspan(-3.4, 0, color="#E4F1E8", zorder=0)
    ax2.bar(edges_r[:-1], radius_counts, width=np.diff(edges_r), align="edge",
            color=VERM, alpha=0.85, edgecolor="white", linewidth=0.8, zorder=2)
    ax2.plot(centers_r, _smooth(radius_counts), color="#7A2E12", lw=1.5, zorder=3)
    ax2.axvline(0, color=TEAL, lw=1.3, zorder=3)
    ax2.set_xlim(-3.4, 23.4)
    ax2.set_ylim(0, 165)
    ax2.set_xticks([0, 5, 10, 15, 20])
    ax2.set_xlabel("包围圆半径残差 $e_r$（m）")
    ax2.set_ylabel("频数")
    ax2.set_title("(b) 包围圆半径残差分布", loc="left", fontsize=11.5, pad=8)
    ax2.grid(True, axis="y", color="#EFEFEF", lw=0.7, zorder=0)
    _corner_box(ax2, "绿线：$e_r=0$；$e_r\\leq 0$ 占 38.3%\n中位 1.11 m", "upper left")

    _save(fig, "fig5_residual_distribution")


# ---------------------------------------------------------------------------
# Figure 6
# ---------------------------------------------------------------------------

def _intersection_angle(x, y, s1, s2):
    v1x, v1y = s1[0] - x, s1[1] - y
    v2x, v2y = s2[0] - x, s2[1] - y
    den = np.hypot(v1x, v1y) * np.hypot(v2x, v2y)
    cos_b = np.divide(v1x * v2x + v1y * v2y, den, out=np.zeros_like(x), where=den > 1e-9)
    return np.degrees(np.arccos(np.clip(cos_b, -1.0, 1.0)))


def fig6_residual_field() -> None:
    s1 = (0.0, 0.0)
    theta = 35.0
    g_hat = from_body(s1, theta, 850.0, 0.0)
    s2 = from_body(s1, theta, 850.0, 600.0)

    xv = np.linspace(-850, 1550, 440)
    yv = np.linspace(-800, 1450, 420)
    x, y = np.meshgrid(xv, yv)
    residual = _intersection_angle(x, y, s1, s2) - 90.0
    near = (np.hypot(x - s1[0], y - s1[1]) < 15) | (np.hypot(x - s2[0], y - s2[1]) < 15)
    residual[near] = np.nan

    fig, ax = plt.subplots(figsize=(6.6, 6.2), layout="constrained")
    cmap = LinearSegmentedColormap.from_list("res", ["#2C6FA8", "#F5F5F0", "#B23A3A"])
    field = ax.pcolormesh(x, y, residual, shading="auto", cmap=cmap,
                          norm=TwoSlopeNorm(vmin=-60, vcenter=0, vmax=60), zorder=0)
    ax.contour(x, y, residual, levels=[-30, 30], colors="#333333", linewidths=1.2,
               linestyles="solid", zorder=3)

    for band in candidate_region(s1, theta):
        ax.add_patch(Polygon(band, closed=True, facecolor=SKY, alpha=0.22,
                             edgecolor=BLUE, lw=1.1, zorder=2))

    center = ((s1[0] + s2[0]) / 2.0, (s1[1] + s2[1]) / 2.0)
    radius = math.dist(s1, s2) / 2.0
    ax.add_patch(plt.Circle(center, radius, fill=False, color=PURPLE, lw=1.7,
                            ls=(0, (5, 2.6)), zorder=4))

    ax.scatter(*s1, marker="o", s=58, color=GREEN, zorder=6)
    ax.scatter(*s2, marker="D", s=64, color=VERM, zorder=6)
    ax.scatter(*g_hat, marker="*", s=180, color=PURPLE, zorder=7)

    _label(ax, s1[0] - 55, s1[1] - 60, "$S_1$", fs=11, ha="right", va="top", halo=False)
    _label(ax, s2[0] + 18, s2[1] + 6, "$S_2$", fs=11, ha="left", va="bottom", halo=False)

    handles = [
        Patch(facecolor=SKY, edgecolor=BLUE, alpha=0.45, label="候选带"),
        Line2D([], [], color=PURPLE, lw=1.7, ls=(0, (5, 2.6)), label="直角轨迹（直径 $S_1S_2$）"),
        Line2D([], [], color="#333333", lw=1.2, label="$|e_\\beta|=30°$ 边界"),
        Line2D([], [], marker="*", ls="none", color=PURPLE, ms=13, label="名义源（设计点）"),
    ]
    ax.legend(handles=handles, loc="lower left", fontsize=8.6, framealpha=0.96,
              borderaxespad=0.6)

    ax.set_xlim(-850, 1550)
    ax.set_ylim(-800, 1450)
    ax.set_aspect("equal")
    ax.set_xlabel("$x$（m）")
    ax.set_ylabel("$y$（m）")
    cb = fig.colorbar(field, ax=ax, fraction=0.046, pad=0.03, ticks=[-60, -30, 0, 30, 60])
    cb.set_label("$e_\\beta$（°）")
    cb.outline.set_linewidth(0.6)
    _save(fig, "fig6_residual_field")


# ---------------------------------------------------------------------------
# Figure 7
# ---------------------------------------------------------------------------

def fig7_inversion_comparison() -> None:
    rows = [
        ("真值包含率", 100.0, 100.0),
        ("示向残差带通过率", 100.0, 100.0),
        ("两站可清", 33.2, 4.0),
        ("补第三站后可清", 100.0, 65.5),
        ("近共线比例（越低越好）", 0.0, 81.2),
    ]
    n = len(rows)
    h = 0.32

    fig, ax = plt.subplots(figsize=(9.8, 4.9), layout="constrained")
    for idx, (label, ortho, coll) in enumerate(rows):
        y = n - 1 - idx
        if ortho > 0:
            ax.barh(y + h / 2 + 0.03, ortho, height=h, color=BLUE, zorder=3)
        ax.barh(y - h / 2 - 0.03, coll, height=h, color=VERM, zorder=3)
        ax.text(ortho + 2.0, y + h / 2 + 0.03, f"{ortho:.1f}%", va="center", ha="left",
                fontsize=9.5, color=BLUE, zorder=4)
        ax.text(coll + 2.0, y - h / 2 - 0.03, f"{coll:.1f}%", va="center", ha="left",
                fontsize=9.5, color=VERM, zorder=4)

    ax.set_yticks(range(n))
    ax.set_yticklabels([r[0] for r in reversed(rows)], fontsize=10.5)
    ax.set_ylim(-0.65, n - 0.35)
    ax.set_xlim(0, 118)
    ax.set_xticks([0, 20, 40, 60, 80, 100])
    ax.set_xlabel("比例（%）")
    ax.grid(True, axis="x", color="#EFEFEF", lw=0.7, zorder=0)
    ax.axhline(n - 2.5, color="#D9D9D9", lw=0.9, zorder=1)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    handles = [
        Patch(facecolor=BLUE, label="正交推荐站"),
        Patch(facecolor=VERM, label="共线延伸站"),
    ]
    ax.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.0, 1.01), ncol=2,
              frameon=False, fontsize=10)
    ax.text(1.0, 1.03, "同一批 400 个真源；交会角中位 86.7° / 4.9°", transform=ax.transAxes,
            ha="right", va="bottom", fontsize=9, color=GRAY)

    _save(fig, "fig7_inversion_comparison")


def main() -> None:
    fig5_residual_distribution()
    fig6_residual_field()
    fig7_inversion_comparison()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
