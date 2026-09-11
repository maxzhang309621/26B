"""Publication-style figures for inversion validation."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Sequence

from geometry import Q3_ANGLE_HALF_WIDTH_DEG, Point, add, dist, scale, unit
from inversion import InvertResult
from log_parse import ChannelObs
from validation import TruthMetrics
from viz import _setup_font

# Colorblind-friendly (muted teal / navy / vermillion / sand).
C_STATION = "#1f4e79"
C_CONE = "#f4a261"
C_REGION = "#2a9d8f"
C_EST = "#264653"
C_TRUTH = "#c1121f"
C_ARENA = "#8d99ae"
C_HIST = "#457b9d"
C_BAND = "#d62828"
C_GRID = "#d9dde3"


def _style() -> None:
    import matplotlib.pyplot as plt

    _setup_font()
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": "#333333",
            "axes.linewidth": 0.8,
            "axes.labelsize": 11,
            "axes.titlesize": 12,
            "axes.titleweight": "medium",
            "xtick.labelsize": 9.5,
            "ytick.labelsize": 9.5,
            "legend.fontsize": 8.5,
            "legend.framealpha": 0.95,
            "legend.edgecolor": "#c5c9ce",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "savefig.dpi": 300,
            "axes.unicode_minus": False,
        }
    )


def _polish(ax, grid: str | None = "y") -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(direction="out", length=3.2, width=0.7, color="#333333")
    ax.set_axisbelow(True)
    if grid == "y":
        ax.yaxis.grid(True, linestyle=":", linewidth=0.7, color=C_GRID)
    elif grid == "both":
        ax.grid(True, linestyle=":", linewidth=0.6, color=C_GRID)
    ax.spines["left"].set_color("#333333")
    ax.spines["bottom"].set_color("#333333")


def _save(fig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=300, bbox_inches="tight", pad_inches=0.08, facecolor="white")
    pdf = path.with_suffix(".pdf")
    fig.savefig(pdf, dpi=300, bbox_inches="tight", pad_inches=0.08, facecolor="white")


def _textbox(ax, lines: Sequence[str], loc: str = "upper left") -> None:
    text = "\n".join(lines)
    va, ha = "top", "left"
    x, y = 0.03, 0.97
    if "right" in loc:
        ha, x = "right", 0.97
    if "lower" in loc:
        va, y = "bottom", 0.03
    ax.text(
        x,
        y,
        text,
        transform=ax.transAxes,
        ha=ha,
        va=va,
        fontsize=8,
        family="sans-serif",
        linespacing=1.35,
        bbox={
            "boxstyle": "round,pad=0.35",
            "facecolor": "white",
            "edgecolor": "#c5c9ce",
            "alpha": 0.92,
        },
        zorder=8,
    )


def _draw_cones(ax, obs: ChannelObs, focus: Point | None, delta: float, z: int = 2) -> None:
    from matplotlib.patches import Wedge

    for i, (s, th) in enumerate(zip(obs.stations, obs.bearings_deg), start=1):
        reach = dist(s, focus) * 1.18 if focus is not None else 900.0
        reach = max(reach, 250.0)
        wedge = Wedge(
            s,
            reach,
            th - delta,
            th + delta,
            facecolor=C_CONE,
            edgecolor=C_CONE,
            linewidth=0.4,
            alpha=0.18,
            zorder=z,
        )
        ax.add_patch(wedge)
        tip = add(s, scale(unit(th), reach))
        ax.plot([s[0], tip[0]], [s[1], tip[1]], color=C_STATION, lw=1.05, zorder=z + 1)
        ax.annotate(
            f"$S_{{{i}}}$",
            xy=s,
            xytext=(6, 6),
            textcoords="offset points",
            fontsize=8,
            color=C_STATION,
            zorder=6,
        )


def _draw_region(ax, verts: list[Point], lw: float = 1.15) -> None:
    if not verts:
        return
    xs = [p[0] for p in verts] + [verts[0][0]]
    ys = [p[1] for p in verts] + [verts[0][1]]
    ax.fill(xs, ys, facecolor=C_REGION, alpha=0.45, zorder=3, label="可行域 $R$")
    ax.plot(xs, ys, color=C_REGION, lw=lw, zorder=3.2)


def _markers(
    ax,
    obs: ChannelObs,
    result: InvertResult,
    truth: Point | None,
    *,
    draw_sec: bool = True,
) -> None:
    from matplotlib.patches import Circle

    if obs.stations:
        ax.scatter(
            [p[0] for p in obs.stations],
            [p[1] for p in obs.stations],
            c=C_STATION,
            s=42,
            marker="o",
            edgecolors="white",
            linewidths=0.6,
            zorder=5,
            label="测站",
        )
    if result.point_est is not None:
        if draw_sec and math.isfinite(result.sec_radius) and result.sec_radius < 1e5:
            ax.add_patch(
                Circle(
                    result.point_est,
                    result.sec_radius,
                    fill=False,
                    ls="--",
                    lw=0.9,
                    color=C_EST,
                    zorder=4,
                    label="最小包围圆",
                )
            )
        ax.scatter(
            [result.point_est[0]],
            [result.point_est[1]],
            c=C_EST,
            marker="+",
            s=90,
            linewidths=1.4,
            zorder=6,
            label="点估计 $\\hat{G}$",
        )
    if truth is not None:
        ax.scatter(
            [truth[0]],
            [truth[1]],
            facecolors="none",
            edgecolors=C_TRUTH,
            s=64,
            linewidths=1.4,
            marker="o",
            zorder=7,
            label="真值 $G$",
        )


def plot_channel_intersection(
    obs: ChannelObs,
    result: InvertResult,
    out: Path,
    truth: Point | None = None,
    delta_deg: float = Q3_ANGLE_HALF_WIDTH_DEG,
) -> None:
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    _style()
    fig, (ax0, ax1) = plt.subplots(
        1, 2, figsize=(10.6, 5.15), gridspec_kw={"width_ratios": [1.22, 1.0], "wspace": 0.22}
    )
    ax0.add_patch(plt.Circle((0, 0), 1800, fill=False, ls=(0, (4, 2.5)), lw=0.8, color=C_ARENA, zorder=0))
    ax0.axhline(0, color=C_GRID, lw=0.5, zorder=0)
    ax0.axvline(0, color=C_GRID, lw=0.5, zorder=0)

    verts = result.region.vertices or []
    focus = truth if truth is not None else result.point_est
    _draw_cones(ax0, obs, focus, delta_deg)
    _draw_region(ax0, verts)
    _markers(ax0, obs, result, truth, draw_sec=False)

    pts = list(obs.stations)
    if focus is not None:
        pts.append(focus)
    if pts:
        xs0 = [p[0] for p in pts]
        ys0 = [p[1] for p in pts]
        span = max(max(xs0) - min(xs0), max(ys0) - min(ys0), 1.0)
        pad = max(80.0, 0.10 * span)
        ax0.set_xlim(min(xs0) - pad, max(xs0) + pad)
        ax0.set_ylim(min(ys0) - pad, max(ys0) + pad)
    ax0.set_aspect("equal")
    _polish(ax0, grid=None)
    ax0.set_xlabel("$x$ (m)")
    ax0.set_ylabel("$y$ (m)")
    ax0.set_title(f"(a) 频道 {obs.channel}：测站与角扇")
    h, lab = ax0.get_legend_handles_labels()
    seen: set[str] = set()
    uniq_h, uniq_l = [], []
    for handle, label in zip(h, lab):
        if label in seen or label == "最小包围圆":
            continue
        seen.add(label)
        uniq_h.append(handle)
        uniq_l.append(label)
    uniq_h.insert(0, Patch(facecolor=C_CONE, edgecolor=C_CONE, alpha=0.35))
    uniq_l.insert(0, r"角扇 $\pm 1.01^\circ$")
    ax0.legend(uniq_h, uniq_l, loc="best", fancybox=False, borderpad=0.4, framealpha=0.96)

    _draw_region(ax1, verts, lw=1.5)
    _markers(ax1, ChannelObs(obs.channel), result, truth, draw_sec=True)
    if result.point_est is not None:
        cx, cy = result.point_est
        rad = result.sec_radius if math.isfinite(result.sec_radius) else 20.0
        m = max(22.0, 2.6 * rad)
        ax1.set_xlim(cx - m, cx + m)
        ax1.set_ylim(cy - m, cy + m)
    elif verts:
        xs = [p[0] for p in verts]
        ys = [p[1] for p in verts]
        pad = 8.0
        ax1.set_xlim(min(xs) - pad, max(xs) + pad)
        ax1.set_ylim(min(ys) - pad, max(ys) + pad)
    ax1.set_aspect("equal")
    _polish(ax1, grid=None)
    ax1.set_xlabel("$x$ (m)")
    ax1.set_ylabel("$y$ (m)")
    ax1.set_title("(b) 可行域与包围圆")
    notes = [f"频道  {obs.channel}", f"测向次数  {len(obs.stations)}"]
    if math.isfinite(result.sec_radius):
        notes.append(f"包围圆半径  {result.sec_radius:.2f} m")
    if truth is not None and result.point_est is not None:
        notes.append(f"定位误差  {dist(result.point_est, truth):.2f} m")
    notes.append(f"角扇半宽  {delta_deg:.2f}°")
    _textbox(ax1, notes, "upper left")

    fig.tight_layout()
    _save(fig, out)
    plt.close(fig)


def plot_est_vs_truth(rows: Sequence[tuple[Point, Point]], out: Path) -> None:
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    _style()
    fig, ax = plt.subplots(figsize=(6.6, 6.2))
    ax.add_patch(plt.Circle((0, 0), 1800, fill=False, ls=(0, (4, 2.5)), lw=0.85, color=C_ARENA, label="工作圆 1800 m"))
    ax.axhline(0, color=C_GRID, lw=0.5)
    ax.axvline(0, color=C_GRID, lw=0.5)
    errs = [dist(t, e) for t, e in rows]
    gx = [t[0] for t, _ in rows]
    gy = [t[1] for t, _ in rows]
    ex = [e[0] for _, e in rows]
    ey = [e[1] for _, e in rows]
    for t, e in rows:
        ax.plot([t[0], e[0]], [t[1], e[1]], color="#9aa5b1", lw=0.7, zorder=2)
    ax.scatter(
        gx,
        gy,
        facecolors="none",
        edgecolors=C_TRUTH,
        s=46,
        linewidths=1.15,
        zorder=4,
        label="真值 $G$",
    )
    sc = ax.scatter(
        ex,
        ey,
        c=errs,
        cmap="cividis",
        s=36,
        marker="s",
        edgecolors="white",
        linewidths=0.4,
        zorder=5,
        label="点估计 $\\hat{G}$",
    )
    cb = fig.colorbar(sc, ax=ax, fraction=0.046, pad=0.03)
    cb.set_label("定位误差 (m)", fontsize=10)
    cb.outline.set_linewidth(0.6)
    ax.set_aspect("equal")
    _polish(ax, grid=None)
    ax.set_xlabel("$x$ (m)")
    ax.set_ylabel("$y$ (m)")
    ax.set_title("点估计与真值对照")
    rmse = math.sqrt(sum(e * e for e in errs) / len(errs)) if errs else float("nan")
    _textbox(
        ax,
        [
            f"$n$  = {len(rows)}",
            f"RMSE  = {rmse:.2f} m",
            f"均值  = {sum(errs) / len(errs):.2f} m" if errs else "",
            f"最大  = {max(errs):.2f} m" if errs else "",
        ],
        "upper left",
    )
    extra = [
        Line2D([0], [0], color=C_ARENA, ls=(0, (4, 2.5)), lw=0.85, label="工作圆 1800 m"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="none", markeredgecolor=C_TRUTH, markersize=7, label="真值 $G$"),
        Line2D(
            [0],
            [0],
            marker="s",
            color="w",
            markerfacecolor="#5c6b73",
            markeredgecolor="white",
            markersize=7,
            label=r"点估计 $\hat{G}$（颜色=误差）",
        ),
    ]
    ax.legend(handles=extra, loc="lower left", fancybox=False)
    lim = 1900
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    _save(fig, out)
    plt.close(fig)


def plot_error_hist(err_m: Sequence[float], out: Path) -> None:
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator

    _style()
    vals = list(err_m)
    fig, ax = plt.subplots(figsize=(6.5, 4.55))
    vmax = max(vals) if vals else 1.0
    width = 2.0
    edges = [i * width for i in range(int(math.ceil((vmax + 1e-9) / width)) + 1)]
    if len(edges) < 3:
        edges = [0.0, 2.0, 4.0]
    ax.hist(vals, bins=edges, color=C_HIST, edgecolor="white", linewidth=0.8, alpha=0.92, zorder=3)
    if vals:
        mean = sum(vals) / len(vals)
        rmse = math.sqrt(sum(v * v for v in vals) / len(vals))
        ax.axvline(mean, color=C_EST, lw=1.3, ls="--", label=f"均值 {mean:.2f} m", zorder=4)
        ax.axvline(rmse, color=C_CONE, lw=1.3, ls="-.", label=f"RMSE {rmse:.2f} m", zorder=4)
        ax.plot(vals, [0.12] * len(vals), "|", color=C_EST, ms=10, mew=1.1, zorder=5, clip_on=False)
    ax.set_xlabel(r"定位误差 $\|\hat{G}-G\|_2$ (m)")
    ax.set_ylabel("频数")
    ax.set_title("点估计误差分布")
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    _polish(ax, "y")
    ax.legend(loc="upper right", fancybox=False)
    if vals:
        _textbox(ax, [f"$n$ = {len(vals)}", f"最大 {max(vals):.2f} m"], "upper left")
    _save(fig, out)
    plt.close(fig)


def plot_residual_hist(residuals_deg: Sequence[float], out: Path) -> None:
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator

    _style()
    vals = list(residuals_deg)
    fig, ax = plt.subplots(figsize=(6.5, 4.55))
    ax.axvspan(-1.0, 1.0, color=C_BAND, alpha=0.08, zorder=0, label="赛题误差带 $\\pm 1^\\circ$")
    ax.axvline(-1.0, color=C_BAND, ls="--", lw=1.05, zorder=2)
    ax.axvline(1.0, color=C_BAND, ls="--", lw=1.05, zorder=2)
    ax.axvline(0.0, color="#6c757d", ls=":", lw=0.9, zorder=2)
    edges = [i / 10.0 - 1.2 for i in range(25)]
    ax.hist(vals, bins=edges, color=C_HIST, edgecolor="white", linewidth=0.7, alpha=0.92, zorder=3)
    if vals:
        ax.plot(vals, [0.12] * len(vals), "|", color=C_EST, ms=9, mew=1.0, zorder=5, clip_on=False)
        mabs = max(abs(v) for v in vals)
        _textbox(
            ax,
            [
                f"$n$ = {len(vals)}",
                f"均值 {sum(vals) / len(vals):+.3f}°",
                f"$\\max|\\tilde{{\\theta}}|$ = {mabs:.3f}°",
            ],
            "upper left",
        )
    ax.set_xlabel(r"示向残差 $\tilde{\theta}=\theta_{\mathrm{true}}-\mathrm{svd}$ (deg)")
    ax.set_ylabel("频数")
    ax.set_title("示向残差分布")
    ax.set_xlim(-1.25, 1.25)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    _polish(ax, "y")
    ax.legend(loc="upper right", fancybox=False)
    _save(fig, out)
    plt.close(fig)


def write_truth_figures(
    out_dir: Path,
    sample: tuple[ChannelObs, InvertResult, Point] | None,
    metrics: Sequence[TruthMetrics],
    pairs: Sequence[tuple[Point, Point]],
) -> list[Path]:
    _style()
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    if sample is not None:
        p = out_dir / "inversion_intersection.png"
        plot_channel_intersection(sample[0], sample[1], p, truth=sample[2])
        paths.append(p)
    if pairs:
        p = out_dir / "est_vs_truth.png"
        plot_est_vs_truth(pairs, p)
        paths.append(p)
    errs = [m.err_m for m in metrics if m.err_m is not None]
    if errs:
        p = out_dir / "error_hist.png"
        plot_error_hist(errs, p)
        paths.append(p)
    res = [r for m in metrics for r in m.residuals_deg]
    if res:
        p = out_dir / "residual_hist.png"
        plot_residual_hist(res, p)
        paths.append(p)
    return paths
