# -*- coding: utf-8 -*-
"""Q2 residual simulation and paper figures.

Question: after the orthogonal second station is fixed from S1 and the first
bearing, how large are the intersection-angle and SEC-radius residuals when
the true source is not at the nominal range, and when it sits inside the
±1° cone? Reasonableness = residuals stay far from collinear degeneracy.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import matplotlib as mpl
import numpy as np

mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Microsoft YaHei", "SimHei", "Arial", "Helvetica"],
    "font.size": 8,
    "axes.titlesize": 8,
    "axes.labelsize": 8,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 7.5,
    "figure.titlesize": 9,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.linewidth": 0.6,
    "xtick.direction": "out",
    "ytick.direction": "out",
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "legend.frameon": True,
    "legend.fancybox": False,
    "legend.edgecolor": "#D0D5DD",
    "legend.facecolor": "#FFFFFF",
    "pdf.fonttype": 42,
    "svg.fonttype": "none",
    "savefig.bbox": "tight",
    "savefig.dpi": 300,
    "axes.unicode_minus": False,
    "mathtext.fontset": "stix",
})

import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, Polygon

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from candidate import (  # noqa: E402
    ARENA_R,
    H_DEFAULT,
    X_MAX,
    X_MIN,
    Y_MAX,
    Y_MIN,
    candidate_region,
    from_body,
    in_candidate_region,
    intersection_angle_deg,
    recommend_second,
    to_body,
)
from geometry import COLLINEAR_SIN, Q3_ANGLE_HALF_WIDTH_DEG, dist, locate_quality, unit  # noqa: E402

OUT = ROOT.parent / "output" / "figures" / "q2_paper"
OUT.mkdir(parents=True, exist_ok=True)
JSON_OUT = ROOT.parent / "output" / "q2_residual_summary.json"

BLUE = "#2166AC"
RED = "#B2182B"
GREEN = "#1B7837"
GOLD = "#6B3FA0"
GREY = "#7A8694"
BLACK = "#222222"
BAND = "#C5D9ED"
BAND_EDGE = "#3D6B99"
S1C = "#2D7A4F"
S2C = "#C0392B"

TH_DEG = 35.0
S1 = (0.0, 0.0)
DELTA = Q3_ANGLE_HALF_WIDTH_DEG
CLEAR_R = 20.0
SEED = 20260912


def save(fig, stem: str) -> Path:
    path = OUT / stem
    fig.savefig(f"{path}.pdf", bbox_inches="tight", dpi=300)
    fig.savefig(f"{path}.png", bbox_inches="tight", dpi=300)
    plt.close(fig)
    return path


def bearing_deg(a, b) -> float:
    return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 360.0


def angle_residual(s1, s2, g) -> float:
    return intersection_angle_deg(s1, s2, g) - 90.0


def sec_residual(s1, s2, g, th1_meas: float) -> tuple[float, bool, bool]:
    if dist(g, s1) < 5.0 or dist(g, s2) < 5.0:
        return float("inf"), False, True
    th2 = bearing_deg(s2, g)
    q = locate_quality([s1, s2], [th1_meas, th2], delta_deg=DELTA)
    er = q.sec_radius - CLEAR_R if math.isfinite(q.sec_radius) else float("inf")
    return er, bool(q.can_clear_20), bool(q.near_collinear)


def finite_stats(vals: np.ndarray) -> dict:
    x = np.asarray(vals, dtype=float)
    x = x[np.isfinite(x)]
    if x.size == 0:
        return {"n": 0}
    return {
        "n": int(x.size),
        "mean": float(np.mean(x)),
        "median": float(np.median(x)),
        "p90": float(np.percentile(np.abs(x), 90)),
        "max_abs": float(np.max(np.abs(x))),
        "min": float(np.min(x)),
        "max": float(np.max(x)),
    }


def simulate() -> dict:
    s2 = recommend_second(S1, TH_DEG, now=S1)
    xb, yb = to_body(S1, TH_DEG, s2)
    ghat = from_body(S1, TH_DEG, xb, 0.0)
    rho_hat = xb
    beta_hat = intersection_angle_deg(S1, s2, ghat)
    e_beta_hat = beta_hat - 90.0
    e_r_hat, clear_hat, col_hat = sec_residual(S1, s2, ghat, TH_DEG)

    rhos = np.arange(250.0, 1600.0 + 1e-9, 10.0)
    ray = []
    for rho in rhos:
        g = from_body(S1, TH_DEG, float(rho), 0.0)
        if dist(g, (0.0, 0.0)) > ARENA_R:
            continue
        eb = angle_residual(S1, s2, g)
        er, can, col = sec_residual(S1, s2, g, TH_DEG)
        sinb = abs(math.sin(math.radians(eb + 90.0)))
        ray.append({
            "rho": float(rho),
            "e_beta_deg": float(eb),
            "e_r_m": None if not math.isfinite(er) else float(er),
            "can_clear_20": can,
            "near_collinear": col,
            "sin_beta": float(sinb),
            "in_long_band": bool(X_MIN - 1e-9 <= rho <= X_MAX + 1e-9),
        })

    s2_col = from_body(S1, TH_DEG, 800.0, 0.0)
    ray_col = []
    for rho in rhos:
        g = from_body(S1, TH_DEG, float(rho), 0.0)
        if dist(g, (0.0, 0.0)) > ARENA_R or dist(g, s2_col) < 5.0:
            continue
        eb = angle_residual(S1, s2_col, g)
        ray_col.append({"rho": float(rho), "e_beta_deg": float(eb)})

    rng = np.random.default_rng(SEED)
    n_mc = 400
    mc = []
    for _ in range(n_mc):
        rho = float(rng.uniform(400.0, 1300.0))
        eps = float(rng.uniform(-1.0, 1.0))
        g = from_body(S1, TH_DEG + eps, rho, 0.0)
        if dist(g, (0.0, 0.0)) > ARENA_R:
            continue
        eb = angle_residual(S1, s2, g)
        er, can, col = sec_residual(S1, s2, g, TH_DEG)
        sinb = abs(math.sin(math.radians(eb + 90.0)))
        mc.append({
            "rho": rho,
            "eps_deg": eps,
            "delta_rho": rho - rho_hat,
            "e_beta_deg": float(eb),
            "e_r_m": None if not math.isfinite(er) else float(er),
            "can_clear_20": can,
            "near_collinear": col,
            "sin_beta": float(sinb),
        })

    in_band = [r for r in ray if r["in_long_band"]]
    e_beta_band = np.array([r["e_beta_deg"] for r in in_band])
    e_r_band = np.array([r["e_r_m"] if r["e_r_m"] is not None else np.nan for r in in_band], dtype=float)
    sin_band = np.array([r["sin_beta"] for r in in_band])
    e_beta_mc = np.array([r["e_beta_deg"] for r in mc])
    e_r_mc = np.array([r["e_r_m"] if r["e_r_m"] is not None else np.nan for r in mc], dtype=float)
    sin_mc = np.array([r["sin_beta"] for r in mc])

    summary = {
        "s1": list(S1),
        "theta_deg": TH_DEG,
        "delta_deg": DELTA,
        "s2_xy": [float(s2[0]), float(s2[1])],
        "s2_body": [float(xb), float(yb)],
        "rho_hat_m": float(rho_hat),
        "h_m": float(abs(yb)),
        "s2_in_band": bool(in_candidate_region(S1, TH_DEG, s2)),
        "s2_in_arena": bool(dist(s2, (0.0, 0.0)) <= ARENA_R + 1e-6),
        "nominal": {
            "beta_deg": float(beta_hat),
            "e_beta_deg": float(e_beta_hat),
            "e_r_m": None if not math.isfinite(e_r_hat) else float(e_r_hat),
            "can_clear_20": clear_hat,
            "near_collinear": col_hat,
            "sin_beta": abs(math.sin(math.radians(beta_hat))),
        },
        "ray_in_band": {
            "n": len(in_band),
            "rho_min": X_MIN,
            "rho_max": X_MAX,
            "e_beta": finite_stats(e_beta_band),
            "e_r": finite_stats(e_r_band),
            "sin_beta_min": float(np.min(sin_band)),
            "frac_abs_e_beta_le_30": float(np.mean(np.abs(e_beta_band) <= 30.0)),
            "frac_sin_ge_collinear": float(np.mean(sin_band >= COLLINEAR_SIN)),
            "frac_e_r_le_0": float(np.mean(np.isfinite(e_r_band) & (e_r_band <= 0.0))),
            "frac_can_clear": float(np.mean([r["can_clear_20"] for r in in_band])),
            "n_near_collinear": int(sum(r["near_collinear"] for r in in_band)),
        },
        "mc_pm1deg": {
            "n": len(mc),
            "seed": SEED,
            "rho_range": [400.0, 1300.0],
            "eps_range_deg": [-1.0, 1.0],
            "e_beta": finite_stats(e_beta_mc),
            "e_r": finite_stats(e_r_mc),
            "sin_beta_min": float(np.min(sin_mc)),
            "frac_abs_e_beta_le_30": float(np.mean(np.abs(e_beta_mc) <= 30.0)),
            "frac_sin_ge_collinear": float(np.mean(sin_mc >= COLLINEAR_SIN)),
            "frac_e_r_le_0": float(np.mean(np.isfinite(e_r_mc) & (e_r_mc <= 0.0))),
            "frac_can_clear": float(np.mean([r["can_clear_20"] for r in mc])),
            "n_near_collinear": int(sum(r["near_collinear"] for r in mc)),
        },
        "h_default": H_DEFAULT,
        "collinear_sin": COLLINEAR_SIN,
    }
    payload = {"summary": summary, "ray": ray, "ray_col": ray_col, "mc": mc}
    JSON_OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def fig4_range(data: dict) -> Path:
    ray = data["ray"]
    rho_hat = data["summary"]["rho_hat_m"]
    rho = np.array([r["rho"] for r in ray])
    eb = np.array([r["e_beta_deg"] for r in ray])
    er = np.array([np.nan if r["e_r_m"] is None else r["e_r_m"] for r in ray])

    fig, axes = plt.subplots(1, 2, figsize=(7.28, 2.92), gridspec_kw={"wspace": 0.32})

    ax = axes[0]
    ax.axhspan(-30.0, 30.0, color=BLUE, alpha=0.08, zorder=0)
    ax.axvspan(X_MIN, X_MAX, color="#5AAE61", alpha=0.08, zorder=0)
    ax.axhline(0.0, color=GREY, lw=0.7, zorder=1)
    ax.axvline(rho_hat, color=GOLD, lw=1.0, ls=(0, (3, 2)), zorder=2)
    ax.plot(rho, eb, color=BLUE, lw=1.5, zorder=4)
    ax.scatter([rho_hat], [0.0], s=38, c=GOLD, marker="*", zorder=5, edgecolors="white", linewidths=0.3)
    ax.set_xlim(250, 1600)
    ax.set_ylim(-55, 50)
    ax.set_xlabel(r"真源纵向距离 $\rho$ / m")
    ax.set_ylabel(r"交会角残差 $e_{\beta}$ / °")
    ax.set_title(r"(a) $e_{\beta}(\rho)$", loc="left", fontsize=8)

    ax = axes[1]
    ax.axvspan(X_MIN, X_MAX, color="#5AAE61", alpha=0.08, zorder=0)
    ax.axhspan(-5, 0.0, color=GREEN, alpha=0.08, zorder=0)
    ax.axhline(0.0, color=GREEN, lw=0.85, zorder=1)
    ax.axvline(rho_hat, color=GOLD, lw=1.0, ls=(0, (3, 2)), zorder=2)
    ax.plot(rho, er, color=RED, lw=1.5, zorder=4)
    ax.scatter([rho_hat], [data["summary"]["nominal"]["e_r_m"]], s=38, c=GOLD,
               marker="*", zorder=5, edgecolors="white", linewidths=0.3)
    ax.set_xlim(250, 1600)
    ax.set_ylim(-5, 55)
    ax.set_xlabel(r"真源纵向距离 $\rho$ / m")
    ax.set_ylabel(r"包围圆半径残差 $e_{r}$ / m")
    ax.set_title(r"(b) $e_{r}(\rho)$", loc="left", fontsize=8)

    fig.subplots_adjust(left=0.08, right=0.99, top=0.90, bottom=0.18)
    return save(fig, "q2_fig4_range_residual")


def fig5_mc(data: dict) -> Path:
    mc = data["mc"]
    eb = np.array([r["e_beta_deg"] for r in mc])
    er = np.array([r["e_r_m"] for r in mc], dtype=float)

    fig, axes = plt.subplots(1, 2, figsize=(7.28, 2.92), gridspec_kw={"wspace": 0.32})

    ax = axes[0]
    ax.axvspan(-30.0, 30.0, color=BLUE, alpha=0.10, zorder=0)
    ax.axvline(0.0, color=GREY, lw=0.7, zorder=1)
    ax.axvline(-30.0, color=BLUE, lw=0.7, ls=(0, (3, 2)), zorder=1)
    ax.axvline(30.0, color=BLUE, lw=0.7, ls=(0, (3, 2)), zorder=1)
    edges = np.linspace(-42, 42, 22)
    ax.hist(eb, bins=edges, color=BLUE, edgecolor="white", linewidth=0.4, zorder=3)
    ax.plot(eb, np.full_like(eb, 0.35), "|", color=BLACK, ms=5, mew=0.6, zorder=4, clip_on=False)
    ax.set_xlim(-42, 42)
    ax.set_xlabel(r"交会角残差 $e_{\beta}$ / °")
    ax.set_ylabel("频数")
    ax.set_title(r"(a) $e_{\beta}$ 分布", loc="left", fontsize=8)

    ax = axes[1]
    ax.axvline(0.0, color=GREEN, lw=0.85, zorder=1)
    edges_r = np.linspace(-3, 23, 22)
    ax.hist(er, bins=edges_r, color=RED, edgecolor="white", linewidth=0.4, zorder=3)
    ax.plot(er, np.full_like(er, 0.35), "|", color=BLACK, ms=5, mew=0.6, zorder=4, clip_on=False)
    ax.set_xlim(-3, 23)
    ax.set_xlabel(r"包围圆半径残差 $e_{r}$ / m")
    ax.set_ylabel("频数")
    ax.set_title(r"(b) $e_{r}$ 分布", loc="left", fontsize=8)

    fig.subplots_adjust(left=0.08, right=0.99, top=0.90, bottom=0.18)
    return save(fig, "q2_fig5_mc_residual")


def fig6_spatial(data: dict) -> Path:
    s2 = tuple(data["summary"]["s2_xy"])
    rho_hat = data["summary"]["rho_hat_m"]
    u = np.array(unit(TH_DEG))
    n = np.array([-u[1], u[0]])
    ghat = rho_hat * u

    xs = np.linspace(-150, 1550, 220)
    ys = np.linspace(-750, 1400, 220)
    xx, yy = np.meshgrid(xs, ys)
    eb = np.full(xx.shape, np.nan)
    for i in range(xx.shape[0]):
        for j in range(xx.shape[1]):
            g = (float(xx[i, j]), float(yy[i, j]))
            if dist(g, (0.0, 0.0)) > ARENA_R or dist(g, S1) < 25.0 or dist(g, s2) < 25.0:
                continue
            eb[i, j] = angle_residual(S1, s2, g)

    fig, ax = plt.subplots(figsize=(6.5, 5.55))
    ax.set_facecolor("#F7F9FC")
    for sp in ax.spines.values():
        sp.set_visible(True)
        sp.set_color("#2C3E50")
        sp.set_linewidth(0.6)
    ax.spines["top"].set_visible(True)
    ax.spines["right"].set_visible(True)

    norm = TwoSlopeNorm(vmin=-60, vcenter=0.0, vmax=60)
    mesh = ax.pcolormesh(xx, yy, eb, cmap="RdBu_r", norm=norm, shading="auto", zorder=1)
    ax.contour(xx, yy, eb, levels=[-30, 30], colors=["#1B2430"], linewidths=0.7, zorder=2)
    cb = fig.colorbar(mesh, ax=ax, fraction=0.046, pad=0.03)
    cb.set_label(r"$e_{\beta}$ / °")

    for poly in candidate_region(S1, TH_DEG):
        ax.add_patch(Polygon(poly, closed=True, facecolor="none", edgecolor=BAND_EDGE,
                             lw=1.15, zorder=3))
    ax.plot([0, 1550 * u[0]], [0, 1550 * u[1]], color=GREY, lw=1.0, ls=(0, (3, 2)), zorder=4)
    mid = (0.5 * (S1[0] + s2[0]), 0.5 * (S1[1] + s2[1]))
    ax.add_patch(Circle(mid, 0.5 * dist(S1, s2), fill=False, ls=(0, (4, 2.5)),
                        lw=1.05, color=GOLD, zorder=4))
    ax.scatter([0], [0], s=48, c=S1C, zorder=6, edgecolors="white", linewidths=0.4)
    ax.scatter([s2[0]], [s2[1]], s=48, c=S2C, marker="D", zorder=6, edgecolors="white", linewidths=0.4)
    ax.scatter([ghat[0]], [ghat[1]], s=70, c=GOLD, marker="*", zorder=6, edgecolors="white", linewidths=0.3)
    ax.annotate(r"$S_1$", (0, 0), textcoords="offset points", xytext=(-16, -14), fontsize=9, color=S1C)
    ax.annotate(r"$S_2$", s2, textcoords="offset points", xytext=(7, 6), fontsize=9, color=S2C)
    ax.annotate(r"$\hat{G}$", ghat, textcoords="offset points", xytext=(8, -12), fontsize=9, color=GOLD)

    ax.set_aspect("equal")
    ax.set_xlim(-150, 1550)
    ax.set_ylim(-750, 1400)
    ax.set_xlabel(r"$x$ / m")
    ax.set_ylabel(r"$y$ / m")
    ax.legend(
        handles=[
            Line2D([0], [0], color=GREY, ls=(0, (3, 2)), label="第一示向"),
            Line2D([0], [0], color=GOLD, ls=(0, (4, 2.5)), label=r"直角轨迹（直径 $S_1S_2$）"),
            Line2D([0], [0], color=BAND_EDGE, lw=1.15, label="候选带边界"),
            Line2D([0], [0], color="#1B2430", lw=0.7, label=r"$|e_{\beta}|=30^{\circ}$"),
        ],
        loc="lower right", framealpha=0.95, edgecolor="#D0D5DD",
    )
    return save(fig, "q2_fig6_spatial_residual")


if __name__ == "__main__":
    data = simulate()
    s = data["summary"]
    print(json.dumps(s, ensure_ascii=False, indent=2))
    print(fig4_range(data))
    print(fig5_mc(data))
    print(fig6_spatial(data))
