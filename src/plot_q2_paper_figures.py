"""Q2 paper figures (publication styling, Chinese labels).

Paper numbering (output/2026B-问题2(4).docx):
  fig1  orthogonal second-station construction (world frame)
  fig4  lecture point vs candidate bands and default recommendation (body frame)
  fig5  inversion check bars: clear ratio and median intersection angle
  fig6  cross-check bars: coarse grid, orthogonal construction, lecture point

Geometry comes from src/candidate.py; bar values come from the paper text
(sections 6.4.1/6.4.2, tables 1-2).
"""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Circle, Patch, Polygon  # noqa: E402

from candidate import (  # noqa: E402
    ARENA_R,
    X_MAX,
    X_MIN,
    Y_MAX,
    Y_MIN,
    candidate_region,
    from_body,
    lecture_second_sides,
    recommend_second,
    to_body,
)
from geometry import unit  # noqa: E402

plt.rcParams.update(
    {
        "font.sans-serif": ["Microsoft YaHei", "SimHei"],
        "axes.unicode_minus": False,
        "font.size": 11,
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
BOX_FC = "#F7F7F7"
BOX_EC = "#CFCFCF"

THETA = 35.0
S1 = (0.0, 0.0)


def _save(fig, outdir: Path, stem: str) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "svg"):
        fig.savefig(outdir / f"{stem}.{ext}", dpi=300)
    plt.close(fig)
    print(outdir / f"{stem}.png")


def _corner_box(ax, text: str, loc: str = "upper left", fs: float = 9.5) -> None:
    x = 0.02 if "left" in loc else 0.98
    y = 0.98 if "upper" in loc else 0.02
    ax.text(
        x,
        y,
        text,
        transform=ax.transAxes,
        fontsize=fs,
        ha="left" if "left" in loc else "right",
        va="top" if "upper" in loc else "bottom",
        zorder=10,
        bbox=dict(boxstyle="round,pad=0.34", fc=BOX_FC, ec=BOX_EC, lw=0.7, alpha=0.96),
    )


def _halo(ax, x, y, text: str, color: str = DARK, fs: float = 10, ha: str = "left",
          va: str = "center", zorder: int = 10) -> None:
    ax.text(
        x,
        y,
        text,
        fontsize=fs,
        color=color,
        ha=ha,
        va=va,
        zorder=zorder,
        bbox=dict(boxstyle="round,pad=0.16", fc="white", ec="none", alpha=0.85),
    )


def _leader(ax, xy, xytext, text: str, color: str = DARK, fs: float = 9.5,
            ha: str = "left", va: str = "center", zorder: int = 10) -> None:
    ax.annotate(
        text,
        xy=xy,
        xytext=xytext,
        fontsize=fs,
        color=color,
        ha=ha,
        va=va,
        zorder=zorder,
        arrowprops=dict(arrowstyle="-", color=GRAY, lw=0.9, shrinkA=1.5, shrinkB=1.5),
        bbox=dict(boxstyle="round,pad=0.16", fc="white", ec="none", alpha=0.9),
    )


def fig1_orthogonal_construction(outdir: Path) -> None:
    u = np.array(unit(THETA))
    n = np.array([-u[1], u[0]])
    g_hat = np.array(from_body(S1, THETA, 850.0, 0.0))
    p_plus = np.array(from_body(S1, THETA, 850.0, 600.0))
    p_minus = np.array(from_body(S1, THETA, 850.0, -600.0))
    bands = candidate_region(S1, THETA)

    fig, ax = plt.subplots(figsize=(8.6, 7.8), layout="constrained")

    for band in bands:
        ax.add_patch(
            Polygon(band, closed=True, facecolor=SKY, alpha=0.16, edgecolor=BLUE,
                    lw=1.0, zorder=1)
        )

    ray_tip = np.array(S1) + 1500.0 * u
    ax.plot([S1[0], ray_tip[0]], [S1[1], ray_tip[1]], color=GRAY, lw=1.1,
            ls=(0, (4, 3)), zorder=3)

    ax.plot([S1[0], g_hat[0]], [S1[1], g_hat[1]], color=PURPLE, lw=2.4, zorder=5)
    ax.plot([g_hat[0], p_plus[0]], [g_hat[1], p_plus[1]], color=VERM, lw=2.0, zorder=5)
    ax.plot([g_hat[0], p_minus[0]], [g_hat[1], p_minus[1]], color=ORANGE, lw=2.0, zorder=5)

    s = 30.0
    m1 = g_hat - s * u
    m2 = g_hat - s * u + s * n
    m3 = g_hat + s * n
    ax.plot([m1[0], m2[0], m3[0]], [m1[1], m2[1], m3[1]], color="#4D4D4D", lw=1.1, zorder=6)
    _halo(ax, g_hat[0] - 0.55 * s * u[0] + 0.45 * s * n[0],
          g_hat[1] - 0.55 * s * u[1] + 0.45 * s * n[1], "$90°$", fs=8.5,
          ha="center", va="center")

    rho_mid = (np.array(S1) + g_hat) / 2.0 + 16.0 * n
    _halo(ax, rho_mid[0], rho_mid[1], r"$\hat\rho$", color=PURPLE, fs=11, ha="center")

    h_plus_mid = (g_hat + p_plus) / 2.0 + 26.0 * u
    _halo(ax, h_plus_mid[0], h_plus_mid[1], "$h$", color=VERM, fs=11, ha="center")
    h_minus_mid = (g_hat + p_minus) / 2.0 + 26.0 * u
    _halo(ax, h_minus_mid[0], h_minus_mid[1], "$h$", color=ORANGE, fs=11, ha="center")

    ax.plot([S1[0]], [S1[1]], marker="o", ms=9, color=DARK, zorder=7)
    _halo(ax, S1[0] - 18, S1[1] - 42, "$S_1$（第一站）", fs=10.5, ha="center", va="top")

    ax.plot([g_hat[0]], [g_hat[1]], marker="*", ms=17, color=PURPLE, zorder=7)
    _halo(ax, g_hat[0] + 62 * math.cos(math.radians(80.0)),
          g_hat[1] + 62 * math.sin(math.radians(80.0)),
          r"$\hat{G}$（名义源）", color=PURPLE, fs=10, ha="left", va="bottom")

    ax.plot([p_plus[0]], [p_plus[1]], marker="D", ms=10, color=VERM, zorder=7)
    _halo(ax, p_plus[0] - 45, p_plus[1] + 40, "$P_+$", color=VERM, fs=10.5,
          ha="right", va="bottom")
    ax.plot([p_minus[0]], [p_minus[1]], marker="D", ms=10, color=ORANGE, zorder=7)
    _halo(ax, p_minus[0] + 45, p_minus[1] - 40, "$P_-$", color=ORANGE, fs=10.5,
          ha="left", va="top")

    ax.annotate("", xy=(S1[0] + 300 * u[0], S1[1] + 300 * u[1]), xytext=S1,
                arrowprops=dict(arrowstyle="-|>", color=GREEN, lw=2.0), zorder=6)
    _halo(ax, S1[0] + 320 * u[0], S1[1] + 320 * u[1] + 10, r"$\mathbf{u}_\rho$（示向）",
          color=GREEN, fs=10, ha="left", va="center")
    ax.annotate("", xy=(S1[0] + 230 * n[0], S1[1] + 230 * n[1]), xytext=S1,
                arrowprops=dict(arrowstyle="-|>", color=GRAY, lw=1.8), zorder=6)
    _halo(ax, S1[0] + 245 * n[0] + 12, S1[1] + 245 * n[1] + 8, r"$\mathbf{u}_h$（侧向）",
          color="#6E6E6E", fs=10, ha="left", va="center")

    handles = [
        Patch(facecolor=SKY, edgecolor=BLUE, alpha=0.35,
              label=f"候选带：$\\rho\\in[{X_MIN:.0f},{X_MAX:.0f}]$，"
                    f"$|h|\\in[{Y_MIN:.0f},{Y_MAX:.0f}]$"),
        Line2D([], [], color=GRAY, lw=1.1, ls=(0, (4, 3)), label="第一示向（$35°$）"),
        Line2D([], [], color=PURPLE, lw=2.4, label=r"名义纵向 $\hat\rho=850$ m"),
        Line2D([], [], color=VERM, lw=2.0, label="侧向 $h=600$ m（取满）"),
        Line2D([], [], marker="D", ls="none", color=VERM, ms=8,
               label="$P_\\pm$：左右候选（对名义源 $90°$）"),
    ]
    ax.legend(handles=handles, loc="upper right", fontsize=9.0, framealpha=0.96,
              title="正交第二站构造（默认档）", title_fontsize=9.5)

    _corner_box(ax, "随体坐标：$\\mathbf{u}_\\rho$ 沿示向，$\\mathbf{u}_h$ 由 $\\mathbf{u}_\\rho$ 逆时针转 $90°$",
                loc="lower right", fs=9)

    ax.set_aspect("equal")
    ax.set_xlim(-260, 1600)
    ax.set_ylim(-260, 1480)
    ax.set_xlabel("$x$ (m)")
    ax.set_ylabel("$y$ (m)")
    ax.grid(True, color="#EFEFEF", lw=0.7, zorder=0)
    _save(fig, outdir, "fig1_orthogonal_construction")


def fig4_lecture_band_compare(outdir: Path) -> None:
    s2_default = recommend_second(S1, THETA)
    s2_body = to_body(S1, THETA, s2_default)
    lecture = lecture_second_sides(S1, THETA)
    lecture_body = [to_body(S1, THETA, p) for p in lecture]

    fig, ax = plt.subplots(figsize=(8.4, 6.6), layout="constrained")

    ax.add_patch(Circle((0.0, 0.0), ARENA_R, facecolor="none", edgecolor=GRAY,
                        lw=1.0, ls=(0, (5, 4)), zorder=1))
    for sign in (1.0, -1.0):
        y0, y1 = sign * Y_MIN, sign * Y_MAX
        rect = [(X_MIN, y0), (X_MAX, y0), (X_MAX, y1), (X_MIN, y1)]
        ax.add_patch(
            Polygon(rect, closed=True, facecolor=SKY, alpha=0.22, edgecolor=BLUE,
                    lw=1.1, zorder=2)
        )

    ax.plot([0.0], [0.0], marker="o", ms=9, color=GREEN, zorder=6)
    _halo(ax, -30, -60, "$S_1$（第一站）", color=GREEN, fs=10, ha="left", va="top")

    ax.plot([s2_body[0]], [s2_body[1]], marker="o", ms=10, color=VERM, zorder=7)
    _halo(ax, s2_body[0] + 40, s2_body[1] + 55,
          f"$S_2$（默认推荐，{s2_body[0]:.0f}, {s2_body[1]:.0f}）",
          color=VERM, fs=9.5, ha="left", va="bottom")

    for p, va in zip(lecture_body, ("top", "bottom")):
        ax.plot([p[0]], [p[1]], marker="D", ms=9, color=ORANGE, zorder=7)
        _halo(ax, p[0] + 40, p[1] + (18 if va == "bottom" else -18),
              f"对照点（{p[0]:.0f}, {p[1]:+.0f}）", color=ORANGE, fs=9.5,
              ha="left", va=va)

    _halo(ax, 1520, 30, "示向线 $h=0$", color=GRAY, fs=9.5, ha="left", va="bottom")

    handles = [
        Patch(facecolor=SKY, edgecolor=BLUE, alpha=0.35,
              label=f"候选带：$\\rho\\in[{X_MIN:.0f},{X_MAX:.0f}]$，"
                    f"$|h|\\in[{Y_MIN:.0f},{Y_MAX:.0f}]$"),
        Line2D([], [], marker="o", ls="none", color=GREEN, ms=8, label="第一站 $S_1$"),
        Line2D([], [], marker="o", ls="none", color=VERM, ms=8,
               label=f"默认推荐站 $S_2$（${s2_body[0]:.0f}$, ${s2_body[1]:.0f}$）"),
        Line2D([], [], marker="D", ls="none", color=ORANGE, ms=7,
               label="对照示意点（$600$, $\\pm350$）"),
        Line2D([], [], color=GRAY, lw=1.0, ls=(0, (5, 4)), label=f"工作圆 $R={ARENA_R:.0f}$ m"),
    ]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.13),
              ncol=3, fontsize=9.0, frameon=False, title="随体坐标（$\\rho$ 沿示向，$h$ 垂直示向）",
              title_fontsize=9.5)

    _corner_box(
        ax,
        "对照示意点侧向 $|h|=350<400$：落在候选带外、更靠近示向线\n"
        "默认推荐取满 $|h|=600$：离开共线退化",
        loc="lower right",
        fs=9,
    )

    ax.set_aspect("equal")
    ax.set_xlim(-250, 1900)
    ax.set_ylim(-1150, 1150)
    ax.set_xlabel(r"纵向 $\rho$ (m)")
    ax.set_ylabel(r"侧向 $h$ (m)")
    ax.grid(True, color="#EFEFEF", lw=0.7, zorder=0)
    _save(fig, outdir, "fig4_lecture_band_compare")


def fig5_inversion_bars(outdir: Path) -> None:
    labels = ["正交推荐", "共线延伸"]
    colors = [GREEN, GRAY]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.2, 4.4), layout="constrained")

    vals = [32.3, 0.0]
    bars = ax1.bar(labels, vals, color=colors, width=0.55, zorder=3)
    for rect, v in zip(bars, vals):
        ax1.text(rect.get_x() + rect.get_width() / 2, max(v, 0.0) + 2.0,
                 f"{v:.1f}%", ha="center", va="bottom", fontsize=11, color="#333333")
    ax1.set_ylim(0, 100)
    ax1.set_ylabel("两站可清比例 (%)")
    ax1.set_title("(a) 两站可清比例", fontsize=12)
    _corner_box(ax1, "样本 $n=198$", loc="upper right", fs=9)

    vals2 = [62.2, 0.0]
    bars2 = ax2.bar(labels, vals2, color=colors, width=0.55, zorder=3)
    for rect, v in zip(bars2, vals2):
        ax2.text(rect.get_x() + rect.get_width() / 2, max(v, 0.0) + 2.0,
                 f"{v:.1f}°", ha="center", va="bottom", fontsize=11, color="#333333")
    ax2.set_ylim(0, 100)
    ax2.set_ylabel("示向夹角中位 (°)")
    ax2.set_title("(b) 示向夹角中位", fontsize=12)

    for ax in (ax1, ax2):
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.grid(True, axis="y", color="#EFEFEF", lw=0.8, zorder=0)
        ax.tick_params(axis="x", labelsize=10.5)

    _save(fig, outdir, "fig5_inversion_bars")


def fig6_crossval_bars(outdir: Path) -> None:
    labels = ["粗网格", "正交构造", "对照示意点"]
    vals = [51.7, 55.8, 95.8]
    colors = [BLUE, GREEN, ORANGE]

    fig, ax = plt.subplots(figsize=(7.4, 4.9), layout="constrained")
    bars = ax.bar(labels, vals, color=colors, width=0.55, zorder=3)
    for rect, v in zip(bars, vals):
        ax.text(rect.get_x() + rect.get_width() / 2, v + 1.8, f"{v:.1f}",
                ha="center", va="bottom", fontsize=11, color="#333333")

    ax.axhline(vals[0], color=GRAY, lw=0.9, ls=(0, (5, 4)), zorder=2)
    ax.annotate(
        "",
        xy=(1.42, vals[1]),
        xytext=(1.42, vals[0]),
        arrowprops=dict(arrowstyle="<|-|>", color="#4D4D4D", lw=1.0, mutation_scale=12),
        zorder=4,
    )
    ax.text(1.48, (vals[0] + vals[1]) / 2, "+4.1 m", fontsize=9.5, color="#333333",
            ha="left", va="center", zorder=5,
            bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.9))

    ax.set_ylim(0, 110)
    ax.set_ylabel("平均最坏交会直径 (m)")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(True, axis="y", color="#EFEFEF", lw=0.8, zorder=0)
    ax.tick_params(axis="x", labelsize=10.5)
    _corner_box(ax, "40 组随机第一站与示向\n柱高为平均最坏交会直径", loc="upper left", fs=9)

    _save(fig, outdir, "fig6_crossval_bars")


def main() -> int:
    outdir = Path(__file__).resolve().parents[1] / "output" / "figures" / "q2_paper"
    fig1_orthogonal_construction(outdir)
    fig4_lecture_band_compare(outdir)
    fig5_inversion_bars(outdir)
    fig6_crossval_bars(outdir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
