# Academic Figure Skill Asset Confirmation (verified against assets/figures/)
# (a) geometric schematic (AOA cones) → assets/figures/ missing (sparse install)
#     → cross-type inherit from Scatter (point size, spine, legend outside)
# (b) feasible-region zoom → no matching dir → param inherit from (a)
# (c) spatial scatter (estimate vs truth) → Scatter → param inherit
# (d) residual histogram (±1° band) → BarDistribution / KernelDensity → param inherit
# RULE: "native run" = load pre-rendered PNG via Image.open().ax.imshow().
#       "param inherit" = drawing function below that copies Class A/B/C values.
#       If a panel says "native run" and you write a drawing function, you broke the contract.
#
# Journal: CUMCM paper using Nature-family dimensions (double column 183 mm).
# Archetype: asymmetric mixed-modality (mechanism + spatial accuracy + residual check).

# Academic Figure Skill Typography Baseline — COPY VERBATIM, place at TOP of script
import matplotlib as mpl
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
    "pdf.fonttype": 42,         # TrueType font embedding
    "svg.fonttype": "none",     # editable text in SVG
    "savefig.bbox": "tight",    # trim whitespace
    "savefig.dpi": 300,
})

def save_cns_figure(fig, filename):
    """Standard Academic Figure Skill export: vector PDF + 300dpi PNG preview."""
    fig.savefig(f"{filename}.pdf", bbox_inches="tight", dpi=300)
    fig.savefig(f"{filename}.png", bbox_inches="tight", dpi=300)

# CUMCM Chinese glyphs (does not replace Arial for Latin/math)
mpl.rcParams["font.sans-serif"] = [
    "Microsoft YaHei", "SimHei", "Arial", "Helvetica", "Liberation Sans"
]
mpl.rcParams["axes.unicode_minus"] = False
mpl.rcParams["mathtext.fontset"] = "stix"

import math
import random
import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, Patch, Wedge
from matplotlib.ticker import MaxNLocator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from geometry import Q3_ANGLE_HALF_WIDTH_DEG, Point, add, dist, scale, unit
from invert_cli import _random_omni, _run_mock_case
from inversion import InvertResult
from log_parse import ChannelObs
from validation import TruthMetrics

MM = 1.0 / 25.4
SEQ_CMAP = LinearSegmentedColormap.from_list("afs_seq", SEQUENTIAL)
OUT_STEM = ROOT.parent / "output" / "inversion" / "fig_inversion_validation"


def _panel_label(ax, letter: str) -> None:
    ax.text(
        -0.14,
        1.08,
        letter,
        transform=ax.transAxes,
        fontsize=9,
        fontweight="bold",
        va="top",
        ha="left",
        color=BLACK,
        clip_on=False,
    )


def _draw_a(ax, obs: ChannelObs, result: InvertResult, truth: Point) -> None:
    ax.axhline(0, color="#E0E0E0", lw=0.3, zorder=0)
    ax.axvline(0, color="#E0E0E0", lw=0.3, zorder=0)
    focus = truth
    for i, (s, th) in enumerate(zip(obs.stations, obs.bearings_deg), start=1):
        reach = max(dist(s, focus) * 1.12, 200.0)
        ax.add_patch(
            Wedge(
                s,
                reach,
                th - Q3_ANGLE_HALF_WIDTH_DEG,
                th + Q3_ANGLE_HALF_WIDTH_DEG,
                facecolor=CATEGORICAL[3],
                edgecolor="none",
                alpha=0.22,
                zorder=1,
            )
        )
        tip = add(s, scale(unit(th), reach))
        ax.plot([s[0], tip[0]], [s[1], tip[1]], color=CATEGORICAL[0], lw=0.9, zorder=2)
        ax.annotate(
            f"$S_{{{i}}}$",
            s,
            textcoords="offset points",
            xytext=(4, 4),
            fontsize=7,
            color=CATEGORICAL[0],
        )
    ax.scatter(
        [p[0] for p in obs.stations],
        [p[1] for p in obs.stations],
        s=18,
        c=CATEGORICAL[0],
        zorder=4,
        edgecolors="white",
        linewidths=0.3,
    )
    if result.point_est is not None:
        ax.plot(
            result.point_est[0],
            result.point_est[1],
            marker="+",
            color=BLACK,
            markersize=7,
            markeredgewidth=1.0,
            zorder=5,
            linestyle="none",
        )
    ax.scatter(
        [truth[0]],
        [truth[1]],
        s=28,
        facecolors="none",
        edgecolors=ACCENT_RED,
        linewidths=0.9,
        zorder=6,
    )
    xs = [p[0] for p in obs.stations] + [truth[0]]
    ys = [p[1] for p in obs.stations] + [truth[1]]
    pad = 80.0
    ax.set_xlim(min(xs) - pad, max(xs) + pad)
    ax.set_ylim(min(ys) - pad, max(ys) + pad)
    ax.set_aspect("equal")
    ax.set_xlabel("$x$ (m)")
    ax.set_ylabel("$y$ (m)")
    handles = [
        Patch(facecolor=CATEGORICAL[3], edgecolor="none", alpha=0.45, label="角扇 ±1.01°"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=CATEGORICAL[0], markersize=5, label="测站"),
        Line2D([0], [0], marker="+", color=BLACK, markersize=7, markeredgewidth=1.0, linestyle="none", label="估计"),
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor="none",
            markeredgecolor=ACCENT_RED,
            markersize=6,
            label="真值",
        ),
    ]
    ax.legend(handles=handles, loc="lower left", fontsize=7)
    _panel_label(ax, "a")


def _draw_b(ax, result: InvertResult, truth: Point) -> None:
    verts = result.region.vertices or []
    if verts:
        xs = [p[0] for p in verts] + [verts[0][0]]
        ys = [p[1] for p in verts] + [verts[0][1]]
        ax.fill(xs, ys, facecolor=CATEGORICAL[2], alpha=0.35, zorder=2)
        ax.plot(xs, ys, color=CATEGORICAL[2], lw=0.9, zorder=3)
    if result.point_est is not None and math.isfinite(result.sec_radius):
        ax.add_patch(
            Circle(
                result.point_est,
                result.sec_radius,
                fill=False,
                ls=(0, (3, 1.6)),
                lw=0.7,
                color=BLACK,
                zorder=4,
            )
        )
        ax.plot(
            result.point_est[0],
            result.point_est[1],
            marker="+",
            color=BLACK,
            markersize=8,
            markeredgewidth=1.1,
            zorder=5,
            linestyle="none",
        )
        cx, cy = result.point_est
        m = max(22.0, 2.5 * result.sec_radius)
        ax.set_xlim(cx - m, cx + m)
        ax.set_ylim(cy - m, cy + m)
    ax.scatter(
        [truth[0]],
        [truth[1]],
        s=36,
        facecolors="none",
        edgecolors=ACCENT_RED,
        linewidths=1.0,
        zorder=6,
    )
    ax.set_aspect("equal")
    ax.set_xlabel("$x$ (m)")
    ax.set_ylabel("$y$ (m)")
    if result.point_est is not None:
        err = dist(result.point_est, truth)
        ax.text(
            0.04,
            0.96,
            f"频道 {result.channel}\n"
            f"包围圆 {result.sec_radius:.1f} m\n"
            f"误差 {err:.1f} m",
            transform=ax.transAxes,
            va="top",
            ha="left",
            fontsize=7,
            color=BLACK,
            linespacing=1.35,
        )
    _panel_label(ax, "b")


def _draw_c(ax, pairs: list[tuple[Point, Point]], errs: list[float]) -> None:
    ax.add_patch(plt.Circle((0, 0), 1800, fill=False, ls=(0, (4, 2)), lw=0.6, color=GREY, zorder=0))
    ax.axhline(0, color="#E0E0E0", lw=0.3, zorder=0)
    ax.axvline(0, color="#E0E0E0", lw=0.3, zorder=0)
    gx = [t[0] for t, _ in pairs]
    gy = [t[1] for t, _ in pairs]
    ex = [e[0] for _, e in pairs]
    ey = [e[1] for _, e in pairs]
    for t, e in pairs:
        ax.plot([t[0], e[0]], [t[1], e[1]], color=GREY, lw=0.45, zorder=1)
    ax.scatter(
        gx,
        gy,
        s=22,
        facecolors="none",
        edgecolors=ACCENT_RED,
        linewidths=0.7,
        zorder=3,
    )
    sc = ax.scatter(
        ex,
        ey,
        c=errs,
        cmap=SEQ_CMAP,
        s=20,
        marker="s",
        edgecolors="white",
        linewidths=0.25,
        zorder=4,
    )
    cb = plt.colorbar(sc, ax=ax, fraction=0.046, pad=0.02)
    cb.set_label("定位误差 (m)", fontsize=7)
    cb.ax.tick_params(labelsize=6, width=0.5, length=2.5)
    cb.outline.set_linewidth(0.4)
    ax.set_aspect("equal")
    ax.set_xlim(-1900, 1900)
    ax.set_ylim(-1900, 1900)
    ax.set_xlabel("$x$ (m)")
    ax.set_ylabel("$y$ (m)")
    rmse = math.sqrt(sum(v * v for v in errs) / len(errs))
    mean = sum(errs) / len(errs)
    ax.text(
        0.04,
        0.96,
        f"$n$ = {len(errs)}\nRMSE = {rmse:.2f} m\n均值 = {mean:.2f} m",
        transform=ax.transAxes,
        va="top",
        fontsize=7,
        color=BLACK,
        linespacing=1.35,
    )
    _panel_label(ax, "c")


def _draw_d(ax, residuals: list[float]) -> None:
    ax.axvspan(-1.0, 1.0, color=ACCENT_RED, alpha=0.08, zorder=0)
    ax.axvline(-1.0, color=ACCENT_RED, ls="--", lw=0.7, zorder=2)
    ax.axvline(1.0, color=ACCENT_RED, ls="--", lw=0.7, zorder=2)
    ax.axvline(0.0, color=GREY, ls=":", lw=0.5, zorder=2)
    edges = [i / 10.0 - 1.2 for i in range(25)]
    ax.hist(residuals, bins=edges, color=CATEGORICAL[0], edgecolor="white", linewidth=0.4, zorder=3)
    ax.plot(residuals, [0.08] * len(residuals), "|", color=BLACK, ms=6, mew=0.7, zorder=4, clip_on=False)
    ax.set_xlim(-1.25, 1.25)
    ax.set_xlabel("示向残差 (deg)")
    ax.set_ylabel("频数")
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    mabs = max(abs(v) for v in residuals)
    mean = sum(residuals) / len(residuals)
    ax.text(
        0.04,
        0.96,
        f"$n$ = {len(residuals)}\n"
        f"均值 = {mean:+.3f} deg\n"
        f"最大绝对值 = {mabs:.3f} deg\n"
        f"浅红带: ±1°",
        transform=ax.transAxes,
        va="top",
        fontsize=7,
        color=BLACK,
        linespacing=1.35,
    )
    _panel_label(ax, "d")


def main() -> None:
    report = _run_mock_case("q3-seed0-n10", _random_omni(10, random.Random(0)), False)
    plot = report["_plot"]
    sample = plot["sample"]
    metrics: list[TruthMetrics] = plot["metrics"]
    pairs = plot["pairs"]
    if sample is None or not pairs:
        raise SystemExit("mock 反演未得到可绘图样本")
    obs, inv, truth = sample
    errs = [m.err_m for m in metrics if m.err_m is not None]
    residuals = [r for m in metrics for r in m.residuals_deg]
    if abs(max(errs) - min(errs)) / max(errs) <= 0.05:
        raise SystemExit("误差跨度过小，直方图无信息量")
    fig = plt.figure(figsize=(183 * MM, 142 * MM))
    gs = fig.add_gridspec(2, 2, wspace=0.34, hspace=0.28, left=0.07, right=0.97, top=0.94, bottom=0.08)
    _draw_a(fig.add_subplot(gs[0, 0]), obs, inv, truth)
    _draw_b(fig.add_subplot(gs[0, 1]), inv, truth)
    _draw_c(fig.add_subplot(gs[1, 0]), pairs, errs)
    _draw_d(fig.add_subplot(gs[1, 1]), residuals)
    OUT_STEM.parent.mkdir(parents=True, exist_ok=True)
    save_cns_figure(fig, str(OUT_STEM))
    plt.close(fig)
    print(str(OUT_STEM) + ".pdf")
    print(str(OUT_STEM) + ".png")
    print(f"n_channels={len(metrics)} n_pairs={len(pairs)} n_residuals={len(residuals)}")


if __name__ == "__main__":
    main()
