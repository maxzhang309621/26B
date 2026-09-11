"""Static figures for inversion validation."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from geometry import Point, add, dist, scale, unit
from inversion import InvertResult
from log_parse import ChannelObs
from validation import TruthMetrics
from viz import _save, _setup_font


def plot_channel_intersection(
    obs: ChannelObs,
    result: InvertResult,
    out: Path,
    truth: Point | None = None,
) -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6.2, 5.4))
    ax.add_patch(plt.Circle((0, 0), 1800, fill=False, linestyle="--", color="0.6"))
    verts = result.region.vertices
    if verts:
        xs = [p[0] for p in verts] + [verts[0][0]]
        ys = [p[1] for p in verts] + [verts[0][1]]
        ax.fill(xs, ys, alpha=0.35, color="C0", label="反演可行域")
        ax.plot(xs, ys, color="C0")
    focus = truth if truth is not None else result.point_est
    for s, th in zip(obs.stations, obs.bearings_deg):
        reach = dist(s, focus) * 1.2 if focus is not None else 800.0
        reach = max(reach, 200.0)
        tip = add(s, scale(unit(th), reach))
        ax.plot([s[0], tip[0]], [s[1], tip[1]], color="C1", lw=0.9)
    if obs.stations:
        ax.scatter(
            [p[0] for p in obs.stations],
            [p[1] for p in obs.stations],
            c="C1",
            s=28,
            label="测站",
            zorder=3,
        )
    if result.point_est is not None:
        ax.scatter(
            [result.point_est[0]],
            [result.point_est[1]],
            c="C2",
            marker="x",
            s=50,
            label="点估计",
            zorder=4,
        )
    if truth is not None:
        ax.scatter([truth[0]], [truth[1]], c="C3", s=40, label="真值", zorder=5)
    pts = list(obs.stations)
    if verts:
        pts.extend(verts)
    if result.point_est is not None:
        pts.append(result.point_est)
    if truth is not None:
        pts.append(truth)
    if pts:
        xs0 = [p[0] for p in pts]
        ys0 = [p[1] for p in pts]
        pad = max(80.0, 0.15 * max(max(xs0) - min(xs0), max(ys0) - min(ys0), 1.0))
        ax.set_xlim(min(xs0) - pad, max(xs0) + pad)
        ax.set_ylim(min(ys0) - pad, max(ys0) + pad)
    ax.set_aspect("equal")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_title(f"频道 {obs.channel} 交会反演")
    ax.legend(loc="best", fontsize=8)
    _save(fig, out)
    plt.close(fig)


def plot_est_vs_truth(rows: Sequence[tuple[Point, Point]], out: Path) -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(5.6, 5.6))
    gx = [t[0] for t, _ in rows]
    gy = [t[1] for t, _ in rows]
    ex = [e[0] for _, e in rows]
    ey = [e[1] for _, e in rows]
    ax.scatter(gx, gy, c="C3", s=28, label="真值")
    ax.scatter(ex, ey, c="C2", marker="x", s=36, label="估计")
    for t, e in rows:
        ax.plot([t[0], e[0]], [t[1], e[1]], color="0.7", lw=0.6)
    ax.set_aspect("equal")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_title("点估计 vs 真值")
    ax.legend()
    _save(fig, out)
    plt.close(fig)


def plot_error_hist(err_m: Sequence[float], out: Path) -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6.0, 4.4))
    ax.hist(list(err_m), bins=min(12, max(5, len(err_m))), color="C0", edgecolor="white")
    ax.set_xlabel("定位误差 (m)")
    ax.set_ylabel("频数")
    ax.set_title("点估计误差直方图")
    _save(fig, out)
    plt.close(fig)


def plot_residual_hist(residuals_deg: Sequence[float], out: Path) -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6.0, 4.4))
    ax.hist(list(residuals_deg), bins=min(16, max(8, len(residuals_deg))), color="C1", edgecolor="white")
    ax.axvline(-1.0, color="C3", ls="--", lw=1, label="±1° 误差带")
    ax.axvline(1.0, color="C3", ls="--", lw=1)
    ax.set_xlabel("示向残差 (deg)")
    ax.set_ylabel("频数")
    ax.set_title("示向残差（真方位 − 测量）")
    ax.legend()
    _save(fig, out)
    plt.close(fig)


def write_truth_figures(
    out_dir: Path,
    sample: tuple[ChannelObs, InvertResult, Point] | None,
    metrics: Sequence[TruthMetrics],
    pairs: Sequence[tuple[Point, Point]],
) -> list[Path]:
    _setup_font()
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
