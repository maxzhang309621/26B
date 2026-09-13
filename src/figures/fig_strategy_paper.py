# Academic Figure Skill Asset Confirmation (verified against assets/figures/)
# assets/figures/ absent in this sparse install -> every panel is cross-type inherit.
# F1 a/b path-schematic  -> cross-type inherit (Scatter)        -> param inherit
# F1 c/d scalar field    -> cross-type inherit (Heatmap)        -> param inherit
# F2 a/b/c geometry      -> cross-type inherit (Scatter)        -> param inherit
# F3 a/b trajectory      -> cross-type inherit (Scatter)        -> param inherit
# F3 c step curve        -> cross-type inherit (Line)           -> param inherit
# F4 a strip + mean      -> cross-type inherit (BarComparison)  -> param inherit
# F4 b regression        -> cross-type inherit (Scatter)        -> param inherit
# F4 c stacked bar       -> cross-type inherit (BarComposition) -> param inherit
# F4 d grouped bar       -> cross-type inherit (BarComparison)  -> param inherit
# F5 tables              -> cross-type inherit (Table)          -> param inherit

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
    "pdf.fonttype": 42,
    "svg.fonttype": "none",
    "savefig.bbox": "tight",
    "savefig.dpi": 300,
})

def save_cns_figure(fig, filename):
    """Standard Academic Figure Skill export: vector PDF + 300dpi PNG preview."""
    fig.savefig(f"{filename}.pdf", bbox_inches="tight", dpi=300)
    fig.savefig(f"{filename}.png", bbox_inches="tight", dpi=300)

# CUMCM Chinese labels: put a CJK face ahead of Arial, keep Arial in the stack.
mpl.rcParams["font.sans-serif"] = [
    "Microsoft YaHei", "SimHei", "Arial", "Helvetica", "Liberation Sans"
]
mpl.rcParams["axes.unicode_minus"] = False
mpl.rcParams["mathtext.fontset"] = "stix"

import glob
import json
import math
import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, Patch, Wedge

ROOT = Path(__file__).resolve().parents[1]
PROJ = ROOT.parent
sys.path.insert(0, str(ROOT))

import coverage as C
from candidate import X_MAX, X_MIN, Y_MAX, Y_MIN, candidate_region, recommend_second_sides_compact
from geometry import (
    CLEAR_R,
    Q3_ANGLE_HALF_WIDTH_DEG,
    add,
    dist,
    intersect_cones,
    scale,
    smallest_enclosing_circle,
    unit,
)

MM = 1.0 / 25.4
OUT = PROJ / "output" / "figures"
ARENA_R = C.ARENA_R
R_EFF = C.COVER_R

SEQ_CMAP = LinearSegmentedColormap.from_list("cns_seq", SEQUENTIAL)

# Semantic roles fixed across the whole figure set.
COL_Q3 = CATEGORICAL[0]        # 问题3
COL_Q4 = ACCENT_RED            # 问题4
COL_COVER = CATEGORICAL[0]     # 覆盖搜索段
COL_FIX = CATEGORICAL[3]       # 定位清除段
COL_OK = CATEGORICAL[2]        # 清除成功
COL_MISS = ACCENT_RED          # 清除失败
LAYER_COLORS = {
    "origin": CATEGORICAL[4],
    "enroute": CATEGORICAL[2],
    "inner": CATEGORICAL[0],
    "outer": CATEGORICAL[3],
}


def _label(ax, letter):
    ax.text(-0.17, 1.0, letter, transform=ax.transAxes, fontsize=9,
            fontweight="bold", va="bottom", ha="left", color=BLACK)


def _title(ax, text):
    """Panel caption above the axes: keeps the data area free of text."""
    ax.set_title(text, loc="left", fontsize=6.8, pad=5, linespacing=1.5,
                 color=BLACK)


def _arena(ax, lw=0.7):
    ax.add_patch(Circle((0, 0), ARENA_R, fill=False, ls=(0, (5, 3)), lw=lw,
                        color=GREY, zorder=0))


def _square(ax, lim):
    ax.set_aspect("equal")
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.set_xlabel("$x$ (m)")
    ax.set_ylabel("$y$ (m)")


# --------------------------------------------------------------------------
# data loaders
# --------------------------------------------------------------------------

def load_q3_official():
    """Current Q3 default: hexagon 6×1150, search-first, edge-second, RH batch."""
    p = PROJ / "output" / "q3-results" / "official_edge_second_20260912_15.json"
    return json.loads(p.read_text(encoding="utf-8"))["rounds"]


def load_q4_current():
    """Current Q4 default hexbatch drills (7×ρ_min + 12×1865), not the 8×995 lock."""
    p = PROJ / "output" / "drill" / "q4-batch-summary.json"
    return json.loads(p.read_text(encoding="utf-8"))


def drill_files(problem):
    if problem == 3:
        return sorted((PROJ / "output" / "drill").glob("p3-20260912-13*.json"))
    return sorted((PROJ / "output" / "drill").glob("p4-20260912-135*.json"))


def q4_enroute_on_inner(inner):
    pts = []
    for p in inner:
        rd = dist(p, (0.0, 0.0))
        if rd < 1e-9:
            continue
        pts.append((C.ENROUTE_R * p[0] / rd, C.ENROUTE_R * p[1] / rd))
    return pts


def read_actions(path):
    """Accepted /measure and /clear records with position, channel, result, time."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    out = []
    for rec in data["log"]:
        if rec.get("path") not in ("/measure", "/clear"):
            continue
        body = rec.get("response") or {}
        if body.get("accepted") is not True:
            continue
        req = rec.get("request") or {}
        pos = req.get("position") or {}
        if "x" not in pos:
            continue
        out.append({
            "path": rec["path"],
            "xy": (float(pos["x"]), float(pos["y"])),
            "channel": req.get("channel"),
            "measure_result": body.get("measure_result"),
            "clear_result": body.get("clear_result"),
            "vt": float(body.get("virtual_time_s") or 0.0),
        })
    return data, out


def listen_set(problem):
    if problem == 3:
        return C.q3_waypoints()
    wps = C.q4_opt_search_waypoints()
    _origin, inner, _outer = C.covering_phases(wps)
    return list(wps) + q4_enroute_on_inner(inner)


def split_phases(actions, problem, tol=1.0):
    """Label each action as a covering listen or a localize/clear manoeuvre.

    The policy scans covering waypoints at their exact coordinates, so an exact
    match against the listen set separates the search phase from the fix phase.
    """
    listens = listen_set(problem)
    for a in actions:
        a["cover"] = a["path"] == "/measure" and any(
            dist(a["xy"], w) <= tol for w in listens
        )
    return actions


# --------------------------------------------------------------------------
# F1  strategy layout + coverage certificate
# --------------------------------------------------------------------------

def _min_dist_field(points, lim, n=240):
    g = np.linspace(-lim, lim, n)
    gx, gy = np.meshgrid(g, g)
    px = np.array([p[0] for p in points])
    py = np.array([p[1] for p in points])
    d = np.sqrt((gx[..., None] - px) ** 2 + (gy[..., None] - py) ** 2)
    return gx, gy, d.min(axis=-1)


def _front_margin_field(points, lim, n=170, n_head=36):
    """Worst-heading margin r_eff - max_h min{|g-w|: w in 180 deg front lobe}."""
    g = np.linspace(-lim, lim, n)
    gx, gy = np.meshgrid(g, g)
    px = np.array([p[0] for p in points])
    py = np.array([p[1] for p in points])
    dx = px - gx[..., None]
    dy = py - gy[..., None]
    dd = np.sqrt(dx * dx + dy * dy)
    brg = np.degrees(np.arctan2(dy, dx))
    worst = np.zeros_like(gx)
    for k in range(n_head):
        h = 360.0 * k / n_head
        rel = (brg - h + 180.0) % 360.0 - 180.0
        masked = np.where(np.abs(rel) <= 90.0, dd, np.inf)
        worst = np.maximum(worst, masked.min(axis=-1))
    return gx, gy, R_EFF - worst


def fig1_strategy_coverage():
    q3 = load_q3_official()
    n_enroute = sum(g["q3_cover_enroute_clears"] for g in q3)
    n_recheck = sum(g["route_rechecks"] for g in q3)
    hex_wps = C.q3_waypoints()
    q4_wps = C.q4_opt_search_waypoints()
    origin, inner, outer = C.covering_phases(q4_wps)
    enroute = q4_enroute_on_inner(inner)
    inner_r = C.q4_opt_inner_r()

    fig, axes = plt.subplots(2, 2, figsize=(183 * MM, 178 * MM))

    ax = axes[0][0]
    _arena(ax)
    ring = hex_wps[1:]
    ax.plot([hex_wps[0][0], ring[0][0]], [hex_wps[0][1], ring[0][1]],
            color=COL_Q3, lw=0.7, alpha=0.55, zorder=2)
    ax.plot([p[0] for p in ring] + [ring[0][0]], [p[1] for p in ring] + [ring[0][1]],
            color=COL_Q3, lw=0.7, alpha=0.55, zorder=2)
    ax.add_patch(Circle(ring[0], R_EFF, fill=True, facecolor=COL_Q3, alpha=0.10,
                        edgecolor=COL_Q3, lw=0.6, ls=(0, (3, 2)), zorder=1))
    ax.scatter([p[0] for p in ring], [p[1] for p in ring], s=34, c=COL_Q3,
               zorder=4, edgecolors="white", linewidths=0.4)
    ax.scatter([0], [0], s=46, c=LAYER_COLORS["origin"], marker="D", zorder=5,
               edgecolors="white", linewidths=0.4)
    for i, p in enumerate(ring, start=1):
        ax.annotate(str(i), p, textcoords="offset points", xytext=(6, 5),
                    fontsize=6.5, color=BLACK)
    ax.annotate("$r_{\\rm eff}=1000$ m", ring[0], textcoords="offset points",
                xytext=(8, -56), fontsize=6.5, color=COL_Q3, ha="left")
    _square(ax, 2050)
    _title(ax, "问题3：原点全扫 → 正六边形 6×1150 m（相位 10°）先搜后清\n"
               f"官方 15 局环边补二测 {n_recheck} 次，顺路清 {n_enroute} 次")
    ax.legend(handles=[
        Line2D([0], [0], marker="D", color="w", markerfacecolor=LAYER_COLORS["origin"],
               markersize=6, label="原点全扫"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=COL_Q3,
               markersize=6, label="内环 6×1150 m"),
    ], loc="lower left", fontsize=6.5, handletextpad=0.4, borderaxespad=0.3)
    _label(ax, "a")

    ax = axes[0][1]
    _arena(ax)
    ax.add_patch(Wedge(inner[0], R_EFF, -90.0, 90.0, facecolor=COL_FIX, alpha=0.14,
                       edgecolor=COL_FIX, lw=0.6, ls=(0, (3, 2)), zorder=1))
    ax.plot([p[0] for p in inner] + [inner[0][0]], [p[1] for p in inner] + [inner[0][1]],
            color=LAYER_COLORS["inner"], lw=0.7, alpha=0.5, zorder=2)
    ax.plot([p[0] for p in outer] + [outer[0][0]], [p[1] for p in outer] + [outer[0][1]],
            color=LAYER_COLORS["outer"], lw=0.7, alpha=0.5, zorder=2)
    ax.plot([0, inner[0][0]], [0, inner[0][1]], color=GREY, lw=0.6, ls=(0, (3, 2)),
            zorder=1)
    ax.annotate("同径向", (inner_r * 0.55, 80), fontsize=6.5, color=GREY)
    for pts, key, lab, mk, sz in (
        ([origin], "origin", "原点全扫", "D", 46),
        (enroute, "enroute", "出发停听 7×900 m", "^", 28),
        (inner, "inner", f"内环 7×{inner_r:.0f} m", "o", 34),
        (outer, "outer", "外环 12×1865 m", "s", 30),
    ):
        ax.scatter([p[0] for p in pts], [p[1] for p in pts], s=sz,
                   c=LAYER_COLORS[key], marker=mk, zorder=4, label=lab,
                   edgecolors="white", linewidths=0.4)
    _square(ax, 2300)
    _title(ax, "问题4 hexbatch：证书听点 7×ρ_min + 12×1865，先搜后清\n"
               "证书不含途听环；从原点去内环时仍可在 900 m 停听")
    ax.legend(loc="lower left", fontsize=6.5, handletextpad=0.4, borderaxespad=0.3)
    _label(ax, "b")

    ax = axes[1][0]
    gx, gy, fld = _min_dist_field(hex_wps, ARENA_R, n=260)
    mask = gx ** 2 + gy ** 2 > ARENA_R ** 2
    fld_in = np.where(mask, np.nan, fld)
    worst3 = float(np.nanmax(fld_in))
    im = ax.pcolormesh(gx, gy, np.ma.array(fld, mask=mask), cmap=SEQ_CMAP,
                       vmin=0, vmax=R_EFF, shading="auto", rasterized=True)
    cs = ax.contour(gx, gy, fld_in, levels=[worst3 - 1.0], colors=[ACCENT_RED],
                    linewidths=0.8)
    ax.clabel(cs, fmt=f"{worst3:.0f} m", fontsize=6, inline=True)
    ax.scatter([p[0] for p in hex_wps], [p[1] for p in hex_wps], s=12, c="white",
               zorder=4, edgecolors=BLACK, linewidths=0.4)
    _arena(ax, lw=0.6)
    _square(ax, 1900)
    cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cb.ax.set_title("到最近\n听点 (m)", fontsize=6.5, pad=4, linespacing=1.3)
    cb.ax.tick_params(labelsize=6.5)
    cb.outline.set_linewidth(0.4)
    _title(ax, f"六边形全向覆盖：最坏 {worst3:.0f} m < 1000 m\n"
               f"余量 {R_EFF - worst3:.0f} m，解析证书通过")
    _label(ax, "c")

    ax = axes[1][1]
    wps = q4_wps
    gx, gy, marg = _front_margin_field(wps, ARENA_R, n=190)
    mask = gx ** 2 + gy ** 2 > ARENA_R ** 2
    marg_in = np.where(mask, np.nan, marg)
    mmin = float(np.nanmin(marg_in))
    mmax = float(np.nanmax(marg_in))
    div = LinearSegmentedColormap.from_list("cns_div", [ACCENT_RED, "#F7F7F7",
                                                        CATEGORICAL[0]])
    norm = mpl.colors.TwoSlopeNorm(vmin=min(mmin, -1.0), vcenter=0.0, vmax=max(mmax, 1.0))
    im = ax.pcolormesh(gx, gy, np.ma.array(marg, mask=mask), cmap=div, norm=norm,
                       shading="auto", rasterized=True)
    neg = np.isfinite(marg_in) & (marg_in < 0)
    if np.any(neg):
        radii = np.hypot(gx, gy)[neg]
        r_lo, r_hi = float(radii.min()), float(radii.max())
        ax.contour(gx, gy, np.where(mask, np.nan, marg), levels=[0.0],
                   colors=[ACCENT_RED], linewidths=0.7)
        frac = float(neg.sum()) / float(np.isfinite(marg_in).sum()) * 100.0
        cap = f"最差 {mmin:.0f} m，负余量格点 {frac:.2f}%"
    else:
        r_lo, r_hi, frac = None, None, 0.0
        cap = f"密网格下最差余量 {mmin:.0f} m，全场为正"
    ax.scatter([p[0] for p in wps], [p[1] for p in wps], s=8, c="white",
               zorder=4, edgecolors=BLACK, linewidths=0.35)
    _arena(ax, lw=0.6)
    _square(ax, 2100)
    cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cb.ax.set_title("余量 (m)", fontsize=6.5, pad=4)
    cb.ax.tick_params(labelsize=6.5)
    cb.outline.set_linewidth(0.4)
    _title(ax, "定向覆盖判据（证书听点，不含 900 m 途听）\n" + cap)
    _label(ax, "d")

    fig.subplots_adjust(wspace=0.42, hspace=0.30)
    stem = OUT / "F1_strategy_coverage"
    save_cns_figure(fig, str(stem))
    plt.close(fig)
    return stem, {
        "q3_worst_m": worst3,
        "q4_inner_r": inner_r,
        "q4_min_margin_m": mmin,
        "q4_weak_band_m": [r_lo, r_hi],
        "q4_neg_fraction_pct": frac,
        "q3_enroute_clears": n_enroute,
        "q3_rechecks": n_recheck,
    }


# --------------------------------------------------------------------------
# F2  localization geometry (problems 1 and 2)
# --------------------------------------------------------------------------

def fig2_localization_geometry():
    s1, s2 = (0.0, 0.0), (400.0, 0.0)
    src = (200.0, 300.0)
    bearings = [math.degrees(math.atan2(src[1] - s[1], src[0] - s[0])) for s in (s1, s2)]
    region = intersect_cones([s1, s2], bearings, delta_deg=Q3_ANGLE_HALF_WIDTH_DEG)
    verts = region.vertices
    cen, rad = smallest_enclosing_circle(verts)

    fig, axes = plt.subplots(1, 3, figsize=(183 * MM, 84 * MM))

    # (a) two-station bearing cones -----------------------------------------
    ax = axes[0]
    for station, th, name in ((s1, bearings[0], "$S_1$"), (s2, bearings[1], "$S_2$")):
        reach = 480.0
        ax.add_patch(Wedge(station, reach, th - Q3_ANGLE_HALF_WIDTH_DEG,
                           th + Q3_ANGLE_HALF_WIDTH_DEG, facecolor=CATEGORICAL[3],
                           alpha=0.45, edgecolor="none", zorder=1))
        tip = add(station, scale(unit(th), reach))
        ax.plot([station[0], tip[0]], [station[1], tip[1]], color=COL_Q3, lw=0.7,
                zorder=2)
        ax.annotate(name, station, textcoords="offset points", xytext=(6, -12),
                    fontsize=7, color=COL_Q3)
    ax.scatter([s1[0], s2[0]], [s1[1], s2[1]], s=26, c=COL_Q3, zorder=4,
               edgecolors="white", linewidths=0.4)
    ax.scatter([src[0]], [src[1]], s=30, facecolors="none", edgecolors=ACCENT_RED,
               linewidths=1.0, zorder=5)
    box = 30.0
    ax.plot([cen[0] - box, cen[0] + box, cen[0] + box, cen[0] - box, cen[0] - box],
            [cen[1] - box, cen[1] - box, cen[1] + box, cen[1] + box, cen[1] - box],
            color=GREY, lw=0.6)
    ax.set_aspect("equal")
    ax.set_xlim(-70, 480)
    ax.set_ylim(-120, 560)
    ax.set_xlabel("$x$ (m)")
    ax.set_ylabel("$y$ (m)")
    ax.annotate("示向锥 ±1.01°", (95, 210), fontsize=6.5, color="#B35806",
                ha="right")
    ax.annotate("真实源", src, textcoords="offset points", xytext=(26, 26),
                fontsize=6.5, color=ACCENT_RED)
    _title(ax, "问题1：两站示向锥各带 ±1.01°\n（±1° 测角误差 + svd 两位小数取整）")
    _label(ax, "a")

    # (b) zoom on the feasible set ------------------------------------------
    ax = axes[1]
    xs = [p[0] for p in verts] + [verts[0][0]]
    ys = [p[1] for p in verts] + [verts[0][1]]
    ax.fill(xs, ys, color=COL_Q3, alpha=0.30, zorder=2)
    ax.plot(xs, ys, color=COL_Q3, lw=1.0, zorder=3)
    ax.add_patch(Circle(cen, rad, fill=False, ls=(0, (3, 1.5)), lw=0.9,
                        color=BLACK, zorder=4))
    ax.add_patch(Circle(cen, CLEAR_R, fill=False, lw=0.9, color=COL_OK, zorder=4))
    ax.scatter([src[0]], [src[1]], s=34, facecolors="none", edgecolors=ACCENT_RED,
               linewidths=1.0, zorder=5)
    ax.scatter([cen[0]], [cen[1]], s=18, c=BLACK, marker="+", zorder=5)
    ax.set_aspect("equal")
    pad = 32.0
    ax.set_xlim(cen[0] - pad, cen[0] + pad)
    ax.set_ylim(cen[1] - pad, cen[1] + pad)
    ax.set_xlabel("$x$ (m)")
    ax.set_ylabel("$y$ (m)")
    ax.annotate("可行定位区", (cen[0] - 9, cen[1] - 8), fontsize=6.5, color=COL_Q3,
                ha="right")
    ax.annotate(f"最小包围圆 {rad:.1f} m", (cen[0], cen[1] + rad),
                textcoords="offset points", xytext=(0, 4), fontsize=6.5,
                color=BLACK, ha="center")
    ax.annotate("20 m 清除判据", (cen[0], cen[1] - CLEAR_R),
                textcoords="offset points", xytext=(0, -11), fontsize=6.5,
                color=COL_OK, ha="center")
    _title(ax, f"面板 a 交会区放大：直径 {region.diameter:.1f} m\n"
               f"最小包围圆 {rad:.1f} m ≤ 20 m，可直接清除")
    _label(ax, "b")

    # (c) second-station band ------------------------------------------------
    ax = axes[2]
    th = 35.0
    _arena(ax)
    for band in candidate_region(s1, th):
        bx = [p[0] for p in band] + [band[0][0]]
        by = [p[1] for p in band] + [band[0][1]]
        ax.fill(bx, by, color=COL_Q3, alpha=0.22, zorder=1)
        ax.plot(bx, by, color=COL_Q3, lw=0.7, zorder=2)
    ray_tip = add(s1, scale(unit(th), 1750.0))
    ax.plot([s1[0], ray_tip[0]], [s1[1], ray_tip[1]], color=GREY,
            ls=(0, (4, 2)), lw=0.7, zorder=2)
    picks = recommend_second_sides_compact(s1, th)
    ax.scatter([p[0] for p in picks], [p[1] for p in picks], s=34, c=COL_OK,
               marker="s", zorder=5, edgecolors="white", linewidths=0.4)
    ax.scatter([s1[0]], [s1[1]], s=30, c=COL_Q3, zorder=5, edgecolors="white",
               linewidths=0.4)
    ax.annotate("$S_1$", s1, textcoords="offset points", xytext=(-6, -20), fontsize=7)
    ax.annotate("候选带", (-60, 980), fontsize=6.5, color=COL_Q3, ha="right")
    ax.annotate("紧凑二站 $\\rho$=450, $h$=±400", picks[1],
                textcoords="offset points", xytext=(6, -34), fontsize=6.5,
                color=COL_OK, ha="left")
    ax.annotate("示向射线", (1180, 880), fontsize=6.5, color=GREY, ha="left")
    _square(ax, 1900)
    _title(ax, f"问题2：第二站候选带 $x\\in$[{X_MIN:.0f}, {X_MAX:.0f}]，\n"
               f"$|y|\\in$[{Y_MIN:.0f}, {Y_MAX:.0f}]（示向体坐标系）")
    _label(ax, "c")

    fig.subplots_adjust(wspace=0.42)
    stem = OUT / "F2_localization_geometry"
    save_cns_figure(fig, str(stem))
    plt.close(fig)
    return stem, {"diameter_m": region.diameter, "sec_r_m": rad}


# --------------------------------------------------------------------------
# F3  executed drills
# --------------------------------------------------------------------------

def _draw_run(ax, actions, problem, lim):
    _arena(ax)
    pts = [(0.0, 0.0)] + [a["xy"] for a in actions]
    flags = [True] + [a.get("cover", False) for a in actions]
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        if dist(a, b) < 1e-6:
            continue
        col = COL_COVER if flags[i + 1] else COL_FIX
        ax.plot([a[0], b[0]], [a[1], b[1]], color=col, lw=0.6, alpha=0.85,
                zorder=2, solid_capstyle="round")
    cover_pts = [a["xy"] for a in actions if a.get("cover")]
    ax.scatter([p[0] for p in cover_pts], [p[1] for p in cover_pts], s=9,
               c=COL_COVER, zorder=3, edgecolors="none")
    ok = [a["xy"] for a in actions if a["path"] == "/clear" and a["clear_result"] == "success"]
    miss = [a["xy"] for a in actions if a["path"] == "/clear" and a["clear_result"] != "success"]
    ax.scatter([p[0] for p in miss], [p[1] for p in miss], s=22, c=COL_MISS,
               marker="x", linewidths=0.8, zorder=5)
    ax.scatter([p[0] for p in ok], [p[1] for p in ok], s=24, c=COL_OK,
               marker="o", zorder=6, edgecolors="white", linewidths=0.4)
    _square(ax, lim)


def fig3_execution():
    f3 = PROJ / "output" / "drill" / "p3-20260912-130508.json"
    f4 = PROJ / "output" / "drill" / "p4-20260912-135326.json"
    d3, a3 = read_actions(f3)
    d4, a4 = read_actions(f4)
    split_phases(a3, 3)
    split_phases(a4, 4)

    fig, axes = plt.subplots(1, 3, figsize=(183 * MM, 80 * MM))

    ax = axes[0]
    _draw_run(ax, a3, 3, 2050)
    s = d3["stats"]
    _title(ax, f"问题3 hexagon：清 {s['cleared']}，{s['virtual_time_s']:.0f} s\n"
               f"测量 {s['n_measure']}，失败 {s['clear_miss']}")
    _label(ax, "a")

    ax = axes[1]
    _draw_run(ax, a4, 4, 2200)
    s = d4["stats"]
    _title(ax, f"问题4 hexbatch：清 {s['cleared']}，{s['virtual_time_s']:.0f} s\n"
               f"测量 {s['n_measure']}，失败 {s['clear_miss']}")
    _label(ax, "b")

    fig.legend(handles=[
        Line2D([0], [0], color=COL_COVER, lw=1.2, label="覆盖搜索段"),
        Line2D([0], [0], color=COL_FIX, lw=1.2, label="定位清除段"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=COL_OK,
               markersize=5, label="清除成功"),
        Line2D([0], [0], marker="x", color=COL_MISS, lw=0, markersize=5,
               markeredgewidth=0.9, label="清除失败"),
    ], loc="lower center", bbox_to_anchor=(0.37, -0.04), ncol=4, fontsize=6.8,
        handletextpad=0.4, columnspacing=1.4)

    # (c) clearing progress --------------------------------------------------
    ax = axes[2]
    for problem, color, lab in ((3, COL_Q3, "问题3"), (4, COL_Q4, "问题4")):
        curves = []
        for path in drill_files(problem):
            _d, acts = read_actions(path)
            t = [0.0]
            n = [0]
            for a in acts:
                if a["path"] == "/clear" and a["clear_result"] == "success":
                    t.append(a["vt"])
                    n.append(n[-1] + 1)
            ax.step(np.array(t) / 60.0, n, where="post", color=color, lw=0.5,
                    alpha=0.35, zorder=2)
            curves.append((np.array(t) / 60.0, np.array(n)))
        grid = np.linspace(0, max(c[0][-1] for c in curves), 200)
        stacked = np.vstack([np.interp(grid, c[0], c[1]) for c in curves])
        ax.plot(grid, stacked.mean(axis=0), color=color, lw=1.6, zorder=4, label=lab)
    ax.set_xlabel("虚拟时间 (min)")
    ax.set_ylabel("累计清除源数")
    ax.legend(loc="upper left", fontsize=7)
    _title(ax, "清除进度：细线单局，粗线均值\nQ3 先搜后清，Q4 外环后再批量清")
    _label(ax, "c")

    fig.subplots_adjust(wspace=0.40)
    stem = OUT / "F3_execution"
    save_cns_figure(fig, str(stem))
    plt.close(fig)
    return stem, {"q3_log": f3.name, "q4_log": f4.name}


# --------------------------------------------------------------------------
# F4  outcome analysis
# --------------------------------------------------------------------------

def fig4_outcome_analysis():
    q3 = load_q3_official()
    q4 = load_q4_current()
    t3 = np.array([g["virtual_time_s"] for g in q3]) / 60.0
    t4 = np.array([g["stats"]["virtual_time_s"] for g in q4]) / 60.0

    fig, axes = plt.subplots(2, 2, figsize=(183 * MM, 136 * MM))

    ax = axes[0][0]
    rng = np.random.default_rng(0)
    for i, (vals, color) in enumerate(((t3, COL_Q3), (t4, COL_Q4))):
        jitter = rng.uniform(-0.10, 0.10, size=vals.size)
        ax.scatter(np.full(vals.size, i) + jitter, vals, s=26, c=color, alpha=0.85,
                   zorder=3, edgecolors="white", linewidths=0.4)
        ax.plot([i - 0.26, i + 0.26], [vals.mean()] * 2, color=color, lw=1.8, zorder=4)
        ax.annotate(f"{vals.mean():.1f} min", (i + 0.30, vals.mean()), fontsize=6.8,
                    color=color, va="center")
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["问题3", "问题4"])
    ax.set_xlim(-0.55, 1.75)
    ax.set_ylabel("虚拟时间 (min)")
    n3c = sum(1 for g in q3 if g["ratio"] >= 1)
    n4c = sum(1 for g in q4 if g["ratio"] >= 1)
    _title(ax, f"问题3 官方 {len(q3)} 局 {n3c}/{len(q3)} 全清；问题4 hexbatch {len(q4)} 局 {n4c}/{len(q4)} 全清\n"
               "每点一局，横线为均值")
    _label(ax, "a")

    ax = axes[0][1]
    n3 = np.array([g["jammer_count"] for g in q3], float)
    p3 = np.array([g["virtual_time_s"] for g in q3]) / n3
    n4 = np.array([g["official"]["jammer_count"] for g in q4], float)
    p4 = np.array([g["stats"]["virtual_time_s"] for g in q4]) / n4
    stats_b = {}
    for nn, pp, color, mk, lab in ((n3, p3, COL_Q3, "o", "问题3"),
                                   (n4, p4, COL_Q4, "s", "问题4")):
        ax.scatter(nn, pp, s=28, c=color, marker=mk, zorder=3, label=lab,
                   edgecolors="white", linewidths=0.4)
        k, b = np.polyfit(nn, pp, 1)
        xs = np.linspace(nn.min() - 0.4, nn.max() + 0.4, 40)
        ax.plot(xs, k * xs + b, color=color, lw=0.9, ls=(0, (4, 2)), zorder=2)
        stats_b[lab] = {"r": float(np.corrcoef(nn, pp)[0, 1]), "slope": float(k)}
    ax.set_xlabel("干扰源个数")
    ax.set_ylabel("单源平均耗时 (s)")
    ax.legend(loc="upper right", fontsize=6.8)
    _title(ax, f"覆盖主干是固定成本，源越多摊得越薄\n"
               f"问题3 $r$={stats_b['问题3']['r']:.2f}（{stats_b['问题3']['slope']:.0f} s/源），"
               f"问题4 $r$={stats_b['问题4']['r']:.2f}（{stats_b['问题4']['slope']:.0f} s/源）")
    _label(ax, "b")

    ax = axes[1][0]
    idx = np.arange(1, len(q4) + 1)
    tot = np.array([g["stats"]["virtual_time_s"] for g in q4])
    travel = np.array([g["stats"]["travel_s"] for g in q4]) / tot * 100.0
    detect = np.array([g["stats"]["detect_s"] for g in q4]) / tot * 100.0
    rest = 100.0 - travel - detect
    r_tt = float(np.corrcoef([g["stats"]["travel_s"] for g in q4], tot)[0, 1])
    ax.bar(idx, travel, color=COL_Q3, width=0.68, label="行驶")
    ax.bar(idx, detect, bottom=travel, color=CATEGORICAL[3], width=0.68, label="探测驻留")
    ax.bar(idx, rest, bottom=travel + detect, color=GREY, width=0.68, label="清除等其他")
    ax.set_xticks(idx)
    ax.set_xlabel("问题4 局序号")
    ax.set_ylabel("时间占比 (%)")
    ax.set_ylim(0, 100)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.40), ncol=3, fontsize=6.8,
              handletextpad=0.4, columnspacing=1.4)
    _title(ax, f"问题4 hexbatch 时间构成：行驶占 {travel.min():.0f}–{travel.max():.0f}%\n"
               f"行驶与总时间 $r$={r_tt:.2f}")
    _label(ax, "c")

    ax = axes[1][1]
    idx3 = np.arange(1, len(q3) + 1)
    bb = np.array([g["backbone_scan_s"] for g in q3])
    cd = np.array([g["clear_detour_s"] for g in q3])
    loc = np.array([g["localization_s"] for g in q3])
    move = bb + cd + loc
    ax.bar(idx3, 100.0 * bb / move, color=COL_Q3, width=0.72, label="主干扫描")
    ax.bar(idx3, 100.0 * loc / move, bottom=100.0 * bb / move, color=CATEGORICAL[3],
           width=0.72, label="定位补测")
    ax.bar(idx3, 100.0 * cd / move, bottom=100.0 * (bb + loc) / move, color=GREY,
           width=0.72, label="清除折返")
    ax.set_xticks([1, 5, 10, 15])
    ax.set_xlabel("问题3 局序号")
    ax.set_ylabel("行驶结构占比 (%)")
    ax.set_ylim(0, 100)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.40), ncol=3, fontsize=6.8,
              handletextpad=0.4, columnspacing=1.4)
    _title(ax, f"问题3 行驶结构：清除折返均 {cd.mean():.0f} s，主干均 {bb.mean():.0f} s\n"
               "边补二测后折返仍是时间大头")
    _label(ax, "d")

    fig.subplots_adjust(wspace=0.34, hspace=0.62)
    stem = OUT / "F4_outcome_analysis"
    save_cns_figure(fig, str(stem))
    plt.close(fig)
    return stem, {
        "q3_mean_min": float(t3.mean()), "q4_mean_min": float(t4.mean()),
        "source_vs_cost": stats_b,
        "r_travel_total": r_tt,
        "q3_mean_clear_detour_s": float(cd.mean()),
        "q3_mean_backbone_s": float(bb.mean()),
    }


# --------------------------------------------------------------------------
# F5  result tables
# --------------------------------------------------------------------------

def _style_table(tbl, fontsize=6.4, row_scale=1.5):
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(fontsize)
    tbl.scale(1.0, row_scale)
    for (r, _c), cell in tbl.get_celld().items():
        cell.set_linewidth(0.3)
        cell.set_edgecolor("#DDDDDD")
        if r == 0:
            cell.set_facecolor(CATEGORICAL[0])
            cell.set_text_props(color="white", fontweight="bold")
        elif r % 2 == 0:
            cell.set_facecolor("#F4F7FA")


def _wrap_code(code, width=11):
    parts = code.split("-")
    lines, cur = [], ""
    for p in parts:
        cand = p if not cur else f"{cur}-{p}"
        if cur and len(cand) > width:
            lines.append(cur)
            cur = p
        else:
            cur = cand
    if cur:
        lines.append(cur)
    return "\n".join(lines)


def fig5_result_tables():
    q3 = load_q3_official()
    q4 = load_q4_current()
    fig, axes = plt.subplots(2, 1, figsize=(183 * MM, 210 * MM),
                             height_ratios=[1.15, 0.95])

    ax = axes[0]
    ax.axis("off")
    ax.text(0.0, 1.02, "表1  问题3 官方演练 15 局（hexagon 6×1150 + 边补二测 + RH）",
            transform=ax.transAxes, fontsize=8, ha="left", va="bottom")
    cols = ["局", "源数", "清除", "虚拟时间 (s)", "秒/源", "顺路清", "复测", "全清"]
    rows = [[
        str(g["index"]), str(g["jammer_count"]), str(g["cleared"]),
        f"{g['virtual_time_s']:.1f}", f"{g['s_per_src']:.0f}",
        str(g["q3_cover_enroute_clears"]), str(g["route_rechecks"]),
        "是" if g["ratio"] >= 1 else "否",
    ] for g in q3]
    mean3 = sum(g["virtual_time_s"] for g in q3) / len(q3)
    mean_sps = sum(g["s_per_src"] for g in q3) / len(q3)
    rows.append([
        "均值", f"{sum(g['jammer_count'] for g in q3)/len(q3):.1f}", "—",
        f"{mean3:.1f}", f"{mean_sps:.0f}",
        str(sum(g["q3_cover_enroute_clears"] for g in q3)),
        str(sum(g["route_rechecks"] for g in q3)),
        f"{sum(1 for g in q3 if g['ratio'] >= 1)}/{len(q3)}",
    ])
    t1 = ax.table(cellText=rows, colLabels=cols, loc="center", cellLoc="center",
                  bbox=[0.0, 0.0, 1.0, 0.95])
    _style_table(t1, fontsize=6.2, row_scale=1.18)
    _label(ax, "a")

    ax = axes[1]
    ax.axis("off")
    ax.text(0.0, 1.02, "表2  问题4 hexbatch 演练 10 局（当前默认 7×997 + 12×1865）",
            transform=ax.transAxes, fontsize=8, ha="left", va="bottom")
    cols4 = ["局", "案例编码", "源数", "定向", "虚拟时间 (s)", "秒/源",
             "行驶 (s)", "探测 (s)", "清除失败", "全清"]
    rows4 = []
    for g in q4:
        o, s = g["official"], g["stats"]
        rows4.append([
            str(g["index"]), _wrap_code(o["case_code"]), str(o["jammer_count"]),
            str(o["directional_jammer_count"]), f"{s['virtual_time_s']:.1f}",
            f"{s['virtual_time_s']/o['jammer_count']:.0f}",
            f"{s['travel_s']:.0f}", f"{s['detect_s']:.0f}",
            str(s["clear_miss"]), "是" if g["ratio"] >= 1 else "否",
        ])
    n = len(q4)
    mean4 = sum(g["stats"]["virtual_time_s"] for g in q4) / n
    mean4_sps = sum(g["stats"]["virtual_time_s"] / g["official"]["jammer_count"] for g in q4) / n
    rows4.append([
        "均值", "—", "—", "—", f"{mean4:.1f}", f"{mean4_sps:.0f}",
        f"{sum(g['stats']['travel_s'] for g in q4) / n:.0f}",
        f"{sum(g['stats']['detect_s'] for g in q4) / n:.0f}",
        f"{sum(g['stats']['clear_miss'] for g in q4) / n:.1f}",
        f"{sum(1 for g in q4 if g['ratio'] >= 1)}/{n}",
    ])
    t2 = ax.table(cellText=rows4, colLabels=cols4, loc="center", cellLoc="center",
                  bbox=[0.0, 0.0, 1.0, 0.94],
                  colWidths=[0.05, 0.16, 0.07, 0.07, 0.13, 0.09, 0.10, 0.10, 0.12, 0.07])
    _style_table(t2, fontsize=6.0, row_scale=1.45)
    _label(ax, "b")

    fig.subplots_adjust(hspace=0.14)
    stem = OUT / "F5_result_tables"
    save_cns_figure(fig, str(stem))
    plt.close(fig)
    return stem, {"q3_mean_s": mean3, "q4_mean_s": mean4, "q3_mean_s_per_src": mean_sps,
                  "q4_mean_s_per_src": mean4_sps}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    facts = {}
    for fn in (fig1_strategy_coverage, fig2_localization_geometry, fig3_execution,
               fig4_outcome_analysis, fig5_result_tables):
        stem, info = fn()
        facts[stem.name] = info
        print(stem.with_suffix(".pdf"))
    print(json.dumps(facts, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
