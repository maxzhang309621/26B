# -*- coding: utf-8 -*-
"""Q2 inversion validation: two-station cone containment after orthogonal siting."""
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
    "savefig.bbox": "tight",
    "savefig.dpi": 300,
    "axes.unicode_minus": False,
    "mathtext.fontset": "stix",
})

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from candidate import (  # noqa: E402
    ARENA_R,
    from_body,
    in_candidate_region,
    intersection_angle_deg,
    lecture_second_sides,
    recommend_second,
    to_body,
)
from geometry import add, dist, locate_quality, scale, sub  # noqa: E402
from inversion import truth_in_cones  # noqa: E402
from validation import RESIDUAL_BAND_DEG, bearing_residuals_deg, true_bearing_deg  # noqa: E402

OUT = ROOT.parent / "output" / "figures" / "q2_paper"
OUT.mkdir(parents=True, exist_ok=True)
JSON_OUT = ROOT.parent / "output" / "q2_inversion_summary.json"

BLUE = "#2166AC"
RED = "#B2182B"
GREY = "#7A8694"
GREEN = "#1B7837"
BLACK = "#222222"

TH_DEG = 35.0
S1 = (0.0, 0.0)
DELTA = 1.01
SEED = 20260912
N = 400


def save(fig, stem: str) -> Path:
    path = OUT / stem
    fig.savefig(f"{path}.pdf", bbox_inches="tight", dpi=300)
    fig.savefig(f"{path}.png", bbox_inches="tight", dpi=300)
    plt.close(fig)
    return path


def _clip_arena(p):
    r = dist(p, (0.0, 0.0))
    if r > ARENA_R:
        return scale(p, ARENA_R / r)
    return p


def _perp(p):
    n = dist(p, (0.0, 0.0))
    if n < 1e-9:
        return (0.0, 1.0)
    return (-p[1] / n, p[0] / n)


def third_station(vertices, now):
    dmax = -1.0
    a = b = vertices[0]
    for i, u in enumerate(vertices):
        for v in vertices[i + 1 :]:
            d = dist(u, v)
            if d > dmax:
                dmax, a, b = d, u, v
    mid = ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)
    axis = sub(b, a)
    n = _perp(axis)
    step = max(80.0, 0.5 * dmax)
    p1 = add(mid, scale(n, step))
    p2 = add(mid, scale(n, -step))
    p = p1 if dist(p1, now) <= dist(p2, now) else p2
    return _clip_arena(p)


def _round_brg(th: float) -> float:
    return round(th % 360.0, 2)


def evaluate(s2, g, th1_meas: float, eps2: float, eps3: float) -> dict:
    th2 = _round_brg(true_bearing_deg(s2, g) + eps2)
    th1 = _round_brg(th1_meas)
    q = locate_quality([S1, s2], [th1, th2], delta_deg=DELTA)
    inside = bool(truth_in_cones([S1, s2], [th1, th2], g, delta_deg=DELTA))
    res = bearing_residuals_deg([S1, s2], [th1, th2], g)
    within = bool(res) and all(abs(r) <= RESIDUAL_BAND_DEG + 1e-9 for r in res)
    rec3 = False
    if (not q.can_clear_20) and q.region.vertices and len(q.region.vertices) >= 2:
        s3 = third_station(q.region.vertices, s2)
        if dist(s3, S1) > 5.0 and dist(s3, s2) > 5.0:
            th3 = _round_brg(true_bearing_deg(s3, g) + eps3)
            q3 = locate_quality([S1, s2, s3], [th1, th2, th3], delta_deg=DELTA)
            rec3 = bool(q3.can_clear_20)
    sec = q.sec_radius if math.isfinite(q.sec_radius) else None
    beta = intersection_angle_deg(S1, s2, g)
    return {
        "inside": inside,
        "residual_ok": within,
        "can_clear_20": bool(q.can_clear_20),
        "near_collinear": bool(q.near_collinear),
        "sec_radius": sec,
        "beta_deg": float(beta),
        "recover3": bool(q.can_clear_20 or rec3),
        "res_max_abs": max(abs(r) for r in res) if res else None,
    }


def rate(rows, key) -> float:
    return float(np.mean([bool(r[key]) for r in rows])) if rows else float("nan")


def median_finite(vals) -> float | None:
    x = [v for v in vals if v is not None and math.isfinite(v)]
    return float(np.median(x)) if x else None


def simulate() -> dict:
    s2o = recommend_second(S1, TH_DEG, now=S1)
    s2c = from_body(S1, TH_DEG, 800.0, 0.0)
    xb, yb = to_body(S1, TH_DEG, s2o)
    ghat = from_body(S1, TH_DEG, xb, 0.0)
    along = from_body(S1, TH_DEG, 800.0, 0.0)
    lec = lecture_second_sides(S1, TH_DEG)[0]

    geom = {
        "s2_body": [float(xb), float(yb)],
        "s2_in_band": bool(in_candidate_region(S1, TH_DEG, s2o)),
        "s2_in_arena": bool(dist(s2o, (0.0, 0.0)) <= ARENA_R + 1e-6),
        "beta_at_ghat_deg": float(intersection_angle_deg(S1, s2o, ghat)),
        "along_800_in_band": bool(in_candidate_region(S1, TH_DEG, along)),
        "lecture_in_band": bool(in_candidate_region(S1, TH_DEG, lec)),
    }

    rng = np.random.default_rng(SEED)
    rhos = rng.uniform(400.0, 1300.0, N)
    eps1 = rng.uniform(-1.0, 1.0, N)
    eps2 = rng.uniform(-1.0, 1.0, N)
    eps3 = rng.uniform(-1.0, 1.0, N)

    ortho, col = [], []
    for i in range(N):
        g = from_body(S1, TH_DEG + float(eps1[i]), float(rhos[i]), 0.0)
        if dist(g, (0.0, 0.0)) > ARENA_R:
            continue
        ortho.append(evaluate(s2o, g, TH_DEG, float(eps2[i]), float(eps3[i])))
        col.append(evaluate(s2c, g, TH_DEG, float(eps2[i]), float(eps3[i])))

    def pack(rows):
        secs = [r["sec_radius"] for r in rows]
        betas = [r["beta_deg"] for r in rows]
        rmax = [r["res_max_abs"] for r in rows if r["res_max_abs"] is not None]
        return {
            "n": len(rows),
            "containment": rate(rows, "inside"),
            "residual_band": rate(rows, "residual_ok"),
            "can_clear_20": rate(rows, "can_clear_20"),
            "near_collinear": rate(rows, "near_collinear"),
            "recover3": rate(rows, "recover3"),
            "sec_median_m": median_finite(secs),
            "beta_median_deg": float(np.median(betas)) if betas else None,
            "residual_max_abs_p90": float(np.percentile(rmax, 90)) if rmax else None,
            "residual_max_abs_max": float(np.max(rmax)) if rmax else None,
        }

    summary = {
        "theta_deg": TH_DEG,
        "delta_deg": DELTA,
        "n_draw": N,
        "seed": SEED,
        "geometry": geom,
        "ortho": pack(ortho),
        "collinear": pack(col),
    }
    JSON_OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def fig7(summary: dict) -> Path:
    o, c = summary["ortho"], summary["collinear"]
    labels = ["真值包含", r"残差落在 $\pm 1.01^\circ$", "两站可清", "近共线", "补第三站后可清"]
    ovals = [o["containment"], o["residual_band"], o["can_clear_20"], o["near_collinear"], o["recover3"]]
    cvals = [c["containment"], c["residual_band"], c["can_clear_20"], c["near_collinear"], c["recover3"]]
    ovals = [100.0 * v for v in ovals]
    cvals = [100.0 * v for v in cvals]

    fig, ax = plt.subplots(figsize=(7.28, 3.15))
    x = np.arange(len(labels))
    w = 0.36
    ax.bar(x - w / 2, ovals, w, color=BLUE, label="正交推荐站", zorder=3)
    ax.bar(x + w / 2, cvals, w, color=GREY, label="共线延伸站", zorder=3)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("比例 / %")
    ax.set_ylim(0, 112)
    ax.axhline(100.0, color=GREY, lw=0.6, ls=(0, (3, 2)), zorder=1)
    ax.legend(loc="upper right", framealpha=0.95, edgecolor="#D0D5DD")
    for i, (a, b) in enumerate(zip(ovals, cvals)):
        ax.text(i - w / 2, a + 1.5, f"{a:.1f}", ha="center", va="bottom", fontsize=6.5, color=BLACK)
        ax.text(i + w / 2, b + 1.5, f"{b:.1f}", ha="center", va="bottom", fontsize=6.5, color=BLACK)
    fig.subplots_adjust(left=0.08, right=0.98, top=0.96, bottom=0.16)
    return save(fig, "q2_fig7_inversion")


if __name__ == "__main__":
    s = simulate()
    print(json.dumps(s, ensure_ascii=False, indent=2))
    print(fig7(s))
