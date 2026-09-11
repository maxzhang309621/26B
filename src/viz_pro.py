# -*- coding: utf-8 -*-
"""Publication-style preview figures. Does not rewrite Word or overwrite paper/figures."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = Path(__file__).resolve().parent
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from candidate import (  # noqa: E402
    H_COMPACT,
    RHO_COMPACT,
    candidate_region,
    from_body,
    recommend_second_sides_compact,
)
from coverage import (  # noqa: E402
    ARENA_R,
    COVER_R,
    ENROUTE_R,
    OMNI_RING_N,
    OMNI_RING_R,
    Q4_OUTER_FULL_N,
    Q4_OUTER_FULL_R,
    directional_waypoints,
    omni_waypoints,
    q4_listen_set,
)
from geometry import dist, locate_quality, unit  # noqa: E402

OUT = ROOT / "output" / "paper" / "figures" / "pro"

INK = "#1B2430"
MUTED = "#5C6778"
ARENA_FILL = "#EEF3F8"
INNER_C = "#1D4E89"
ENROUTE_C = "#2F9E6B"
OUTER_C = "#C05621"
REGION_C = "#4C51BF"
GOLD = "#B7791F"
DIR_C = "#C53030"
OMNI_C = "#2B6CB0"
PAPER = "#FBFCFD"


def _setup() -> None:
    import matplotlib as mpl
    import matplotlib.pyplot as plt
    from matplotlib import font_manager

    mpl.rcParams.update(
        {
            "figure.facecolor": PAPER,
            "axes.facecolor": PAPER,
            "axes.edgecolor": INK,
            "axes.labelcolor": INK,
            "xtick.color": INK,
            "ytick.color": INK,
            "text.color": INK,
            "axes.linewidth": 0.8,
            "xtick.direction": "in",
            "ytick.direction": "in",
            "xtick.major.size": 3.5,
            "ytick.major.size": 3.5,
            "font.size": 10,
            "axes.labelsize": 11,
            "legend.frameon": True,
            "legend.fancybox": False,
            "legend.edgecolor": "#D0D5DD",
            "legend.facecolor": "#FFFFFF",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "savefig.dpi": 320,
            "axes.unicode_minus": False,
        }
    )
    for name in ("Microsoft YaHei", "SimHei", "Noto Sans CJK SC"):
        if any(name.lower() in f.name.lower() for f in font_manager.fontManager.ttflist):
            mpl.rcParams["font.sans-serif"] = [name, "Times New Roman", "DejaVu Sans"]
            mpl.rcParams["font.family"] = "sans-serif"
            break
    plt.rcParams["mathtext.fontset"] = "stix"


def _halo(size: float = 9.0, color: str = INK, weight: str = "normal"):
    import matplotlib.patheffects as pe

    return {
        "fontsize": size,
        "color": color,
        "fontweight": weight,
        "path_effects": [pe.withStroke(linewidth=2.6, foreground="white")],
        "zorder": 20,
    }


def _save(fig, name: str) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    png = OUT / f"{name}.png"
    pdf = OUT / f"{name}.pdf"
    fc = fig.get_facecolor()
    fig.savefig(png, dpi=320, bbox_inches="tight", pad_inches=0.08, facecolor=fc)
    fig.savefig(pdf, bbox_inches="tight", pad_inches=0.08, facecolor=fc)
    return png


def _style_xy(ax, lim: float = 2100) -> None:
    ax.set_aspect("equal")
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.set_xlabel(r"$x$ / m")
    ax.set_ylabel(r"$y$ / m")
    ax.tick_params(top=True, right=True)
    for sp in ax.spines.values():
        sp.set_linewidth(0.8)


def _arena(ax, r: float = ARENA_R, fill: bool = True) -> None:
    import matplotlib.pyplot as plt

    if fill:
        ax.add_patch(
            plt.Circle((0, 0), r, facecolor=ARENA_FILL, edgecolor="none", zorder=0)
        )
    ax.add_patch(
        plt.Circle(
            (0, 0),
            r,
            fill=False,
            linestyle=(0, (5, 2.5)),
            color="#8A94A6",
            lw=1.15,
            zorder=2,
        )
    )


def _ring(ax, r: float, color: str, ls: str = "-", lw: float = 1.15, alpha: float = 0.95):
    import matplotlib.pyplot as plt

    ax.add_patch(
        plt.Circle((0, 0), r, fill=False, linestyle=ls, color=color, lw=lw, alpha=alpha, zorder=2)
    )


def _shadow_scatter(ax, xs, ys, **kw):
    kw = dict(kw)
    z = kw.pop("zorder", 6)
    shadow = {k: v for k, v in kw.items() if k not in {"c", "edgecolors", "linewidths", "label"}}
    ax.scatter(xs, ys, c="0.15", alpha=0.14, zorder=z - 1, linewidths=0, **shadow)
    ax.scatter(xs, ys, zorder=z, **kw)


def _wedge(ax, origin, theta_deg, half_deg, radius, facecolor, edgecolor, alpha=0.22):
    from matplotlib.patches import Wedge

    ax.add_patch(
        Wedge(
            origin,
            radius,
            theta_deg - half_deg,
            theta_deg + half_deg,
            facecolor=facecolor,
            edgecolor="none",
            lw=0,
            alpha=alpha,
            zorder=3,
        )
    )


def _dim_radius(ax, r: float, angle_deg: float, text: str, color: str) -> None:
    a = math.radians(angle_deg)
    x, y = r * math.cos(a), r * math.sin(a)
    ax.annotate(
        "",
        xy=(x, y),
        xytext=(0, 0),
        arrowprops=dict(arrowstyle="<->", color=color, lw=0.9),
        zorder=8,
    )
    tx, ty = 0.55 * r * math.cos(a), 0.55 * r * math.sin(a)
    ax.text(tx, ty, text, ha="center", va="center", **_halo(8.5, color))


def _ray(ax, origin, theta_deg, length, color, lw=1.15, ls="-", alpha=1.0, z=4):
    u = unit(theta_deg)
    ax.plot(
        [origin[0], origin[0] + length * u[0]],
        [origin[1], origin[1] + length * u[1]],
        color=color,
        lw=lw,
        ls=ls,
        alpha=alpha,
        zorder=z,
        solid_capstyle="round",
    )


def _angle_label(ax, origin, t0, t1, radius, text, color):
    from matplotlib.patches import Arc

    lo, hi = (t0, t1) if t0 <= t1 else (t1, t0)
    if hi - lo > 180:
        lo, hi = hi, lo + 360
    ax.add_patch(
        Arc(
            origin,
            2 * radius,
            2 * radius,
            angle=0,
            theta1=lo,
            theta2=hi,
            color=color,
            lw=1.35,
            zorder=12,
        )
    )
    mid = math.radians(0.5 * (lo + hi))
    ax.text(
        origin[0] + (radius + 18) * math.cos(mid),
        origin[1] + (radius + 18) * math.sin(mid),
        text,
        ha="center",
        va="center",
        **_halo(9.5, color),
    )


def fig_q1_intersection() -> Path:
    import matplotlib.pyplot as plt

    s1, s2 = (0.0, 0.0), (520.0, 0.0)
    g = (260.0, 310.0)
    th1 = math.degrees(math.atan2(g[1] - s1[1], g[0] - s1[0]))
    th2 = math.degrees(math.atan2(g[1] - s2[1], g[0] - s2[0]))
    vis_delta = 8.0
    q = locate_quality([s1, s2], [th1, th2], delta_deg=vis_delta)
    verts = q.region.vertices
    c1, c2 = "#3B5BDB", "#0B9B8A"
    fig, ax = plt.subplots(figsize=(7.1, 6.2))

    reach = 780
    for s, th, col in ((s1, th1, c1), (s2, th2, c2)):
        _wedge(ax, s, th, vis_delta, reach, col, col, alpha=0.13)
        _ray(ax, s, th, reach, col, lw=1.45)
        _ray(ax, s, th - vis_delta, reach, col, lw=0.85, ls=(0, (3.2, 1.8)), alpha=0.85)
        _ray(ax, s, th + vis_delta, reach, col, lw=0.85, ls=(0, (3.2, 1.8)), alpha=0.85)

    if verts:
        xs = [p[0] for p in verts] + [verts[0][0]]
        ys = [p[1] for p in verts] + [verts[0][1]]
        ax.fill(xs, ys, facecolor=REGION_C, alpha=0.42, zorder=6, label="定位区 $R$")
        ax.plot(xs, ys, color=REGION_C, lw=2.0, zorder=7)
        ax.scatter(
            [p[0] for p in verts],
            [p[1] for p in verts],
            s=26,
            c=REGION_C,
            zorder=8,
            edgecolors="white",
            linewidths=0.5,
        )

    if q.sec_center is not None:
        c, r = q.sec_center, q.sec_radius
        ax.add_patch(
            plt.Circle(c, r, fill=False, ls=(0, (3.4, 1.6)), color=GOLD, lw=1.55, zorder=9, label="最小包围圆")
        )
        ax.add_patch(
            plt.Circle(c, 20.0, fill=False, color=DIR_C, lw=1.05, alpha=0.85, zorder=9, label="清除半径 $20$ m")
        )
        ax.scatter([c[0]], [c[1]], s=28, c=GOLD, zorder=10, marker="x")

    _shadow_scatter(
        ax, [s1[0], s2[0]], [s1[1], s2[1]], s=92, c="#1A365D", edgecolors="white", linewidths=0.85, label="检测站"
    )
    ax.scatter(
        [g[0]],
        [g[1]],
        s=150,
        c=DIR_C,
        marker="*",
        edgecolors="white",
        linewidths=0.55,
        zorder=11,
        label="干扰源",
    )
    ax.text(s1[0] - 8, s1[1] - 38, r"$S_1$", ha="center", **_halo(11))
    ax.text(s2[0] + 8, s2[1] - 38, r"$S_2$", ha="center", **_halo(11))
    ax.text(g[0] + 22, g[1] + 28, r"$J$", **_halo(11, DIR_C))

    _angle_label(ax, s1, th1 - vis_delta, th1 + vis_delta, 118, r"$\pm 1^{\circ}$", c1)
    _angle_label(ax, s2, th2 - vis_delta, th2 + vis_delta, 118, r"$\pm 1^{\circ}$", c2)
    beta = abs(((th1 - th2 + 180) % 360) - 180)
    _angle_label(ax, g, th1 + 180, th2 + 180, 78, r"$\beta$", INK)

    ax.legend(
        loc="upper right",
        fontsize=8.6,
        borderpad=0.55,
        handlelength=1.6,
        title=rf"$\beta\approx {beta:.0f}^{{\circ}}$，角扇放大示意",
        title_fontsize=8.4,
    )
    ax.set_xlim(-90, 760)
    ax.set_ylim(-90, 620)
    ax.set_aspect("equal")
    ax.set_xlabel(r"$x$ / m")
    ax.set_ylabel(r"$y$ / m")
    ax.tick_params(top=True, right=True)
    fig.tight_layout()
    p = _save(fig, "pro_q1_intersection")
    plt.close(fig)
    return p


def fig_q2_candidate() -> Path:
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon

    s1 = (-280.0, 140.0)
    th = 35.0
    bands = candidate_region(s1, th)
    s2p, s2m = recommend_second_sides_compact(s1, th)
    ghat = from_body(s1, th, RHO_COMPACT, 0.0)
    fig, ax = plt.subplots(figsize=(6.6, 6.2))
    _arena(ax)
    u = unit(th)
    ax.plot(
        [s1[0], s1[0] + 1600 * u[0]],
        [s1[1], s1[1] + 1600 * u[1]],
        color="#4A5568",
        lw=1.05,
        ls=(0, (4, 2)),
        zorder=3,
        label="第一示向",
    )
    for i, band in enumerate(bands):
        poly = Polygon(
            band,
            closed=True,
            facecolor="#63B3ED" if i == 0 else "#F6AD55",
            edgecolor="#2B6CB0" if i == 0 else OUTER_C,
            alpha=0.28,
            lw=1.0,
            zorder=4,
            label="候选带" if i == 0 else None,
        )
        ax.add_patch(poly)
    ax.plot(
        [s1[0], ghat[0], s2p[0]],
        [s1[1], ghat[1], s2p[1]],
        color=INNER_C,
        lw=1.15,
        zorder=5,
    )
    ax.plot([ghat[0], s2m[0]], [ghat[1], s2m[1]], color=INNER_C, lw=1.15, ls="--", zorder=5)
    _shadow_scatter(ax, [s1[0]], [s1[1]], s=86, c=INK, edgecolors="white", linewidths=0.7, label=r"$S_1$")
    _shadow_scatter(
        ax, [s2p[0], s2m[0]], [s2p[1], s2m[1]], s=92, c=OUTER_C, edgecolors="white", linewidths=0.7, marker="D", label=r"$S_2^{\pm}$"
    )
    ax.scatter([ghat[0]], [ghat[1]], s=46, c=GOLD, zorder=8, marker="x", label=r"名义源 $\hat G$")
    ax.text(s1[0] - 70, s1[1] + 40, r"$S_1$", **_halo(10))
    ax.text(s2p[0] + 20, s2p[1] + 20, r"$S_2^{+}$", **_halo(10, OUTER_C))
    ax.text(s2m[0] + 20, s2m[1] - 40, r"$S_2^{-}$", **_halo(10, OUTER_C))
    ax.annotate(
        rf"$\rho={RHO_COMPACT:.0f}$ m",
        xy=((s1[0] + ghat[0]) / 2, (s1[1] + ghat[1]) / 2),
        textcoords="offset points",
        xytext=(8, 8),
        **_halo(8.5, MUTED),
    )
    ax.annotate(
        rf"$H={H_COMPACT:.0f}$ m",
        xy=((ghat[0] + s2p[0]) / 2, (ghat[1] + s2p[1]) / 2),
        textcoords="offset points",
        xytext=(6, -12),
        **_halo(8.5, MUTED),
    )
    ax.legend(loc="lower left", fontsize=8.5)
    _style_xy(ax, 1950)
    fig.tight_layout()
    p = _save(fig, "pro_q2_candidate")
    plt.close(fig)
    return p


def fig_q3_coverage() -> Path:
    import matplotlib.pyplot as plt

    omni = omni_waypoints()
    ring = omni[1:]
    fig, ax = plt.subplots(figsize=(6.4, 6.3))
    _arena(ax)
    for p in ring:
        ax.add_patch(
            plt.Circle(p, COVER_R, facecolor="#90CDF4", edgecolor=INNER_C, alpha=0.10, lw=0.55, zorder=1)
        )
    _ring(ax, OMNI_RING_R, INNER_C, lw=1.25)
    xs = [p[0] for p in ring] + [ring[0][0]]
    ys = [p[1] for p in ring] + [ring[0][1]]
    ax.plot(xs, ys, color=INNER_C, lw=1.35, zorder=4, label="内环访问边")
    _shadow_scatter(
        ax,
        [p[0] for p in ring],
        [p[1] for p in ring],
        s=64,
        c=INNER_C,
        edgecolors="white",
        linewidths=0.8,
        label="8×1200 m 听点",
    )
    ax.scatter([0], [0], s=90, c=INK, marker="s", edgecolors="white", linewidths=0.7, zorder=8, label="原点全扫")
    # worst-ish boundary sample between two ring points
    mid_a = math.pi / 8
    bx, by = ARENA_R * math.cos(mid_a), ARENA_R * math.sin(mid_a)
    nearest = min(ring, key=lambda p: dist((bx, by), p))
    dnear = dist((bx, by), nearest)
    ax.scatter([bx], [by], s=46, c=DIR_C, zorder=9, marker="o", edgecolors="white", linewidths=0.6)
    ax.plot([bx, nearest[0]], [by, nearest[1]], color=DIR_C, lw=0.9, ls=":", zorder=7)
    ax.text(
        bx * 0.70,
        by * 0.70,
        rf"最近听点 ${dnear:.0f}$ m",
        **_halo(8.5, DIR_C),
    )
    ax.text(0, -80, r"$O$", ha="center", **_halo(10))
    _dim_radius(ax, OMNI_RING_R, -32, r"$R=1200$ m", INNER_C)
    ax.legend(loc="lower left", fontsize=8.5)
    _style_xy(ax, 1950)
    fig.tight_layout()
    p = _save(fig, "pro_q3_coverage")
    plt.close(fig)
    return p


def fig_q3_residual() -> Path:
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap

    wps = omni_waypoints()
    n = 401
    lim = 1850
    xs = np.linspace(-lim, lim, n)
    ys = np.linspace(-lim, lim, n)
    xx, yy = np.meshgrid(xs, ys)
    dmin = np.full(xx.shape, np.inf)
    for px, py in wps:
        dmin = np.minimum(dmin, np.hypot(xx - px, yy - py))
    rr = np.hypot(xx, yy)
    dmin = np.ma.masked_where(rr > ARENA_R, dmin)
    cmap = LinearSegmentedColormap.from_list(
        "dmin",
        ["#1A365D", "#2B6CB0", "#63B3ED", "#C6F6D5", "#FAF089", "#DD6B20", "#9B2C2C"],
        N=256,
    )
    fig, ax = plt.subplots(figsize=(6.6, 6.05))
    im = ax.pcolormesh(xx, yy, dmin, cmap=cmap, shading="auto", vmin=0, vmax=1000, zorder=1)
    _arena(ax, fill=False)
    ax.contour(xx, yy, dmin.filled(9999), levels=[1000], colors=["#9B2C2C"], linewidths=1.1, zorder=4)
    ring = wps[1:]
    ax.scatter([p[0] for p in ring], [p[1] for p in ring], s=38, c="white", edgecolors=INK, linewidths=0.65, zorder=5)
    ax.scatter([0], [0], s=42, c="white", edgecolors=INK, linewidths=0.65, marker="s", zorder=5)
    cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.03)
    cb.set_label(r"到最近听点距离  / m")
    cb.outline.set_linewidth(0.6)
    _style_xy(ax, 1950)
    fig.tight_layout()
    p = _save(fig, "pro_q3_residual")
    plt.close(fig)
    return p


def fig_q4_layers() -> Path:
    import matplotlib.pyplot as plt

    inner = omni_waypoints()[1:]
    enroute = [
        (ENROUTE_R * math.cos(2 * math.pi * k / OMNI_RING_N), ENROUTE_R * math.sin(2 * math.pi * k / OMNI_RING_N))
        for k in range(OMNI_RING_N)
    ]
    outer = directional_waypoints(outer_r=Q4_OUTER_FULL_R, outer_n=Q4_OUTER_FULL_N)
    outer = [p for p in outer if dist(p, (0.0, 0.0)) > 1800]
    fig, ax = plt.subplots(figsize=(6.6, 6.4))
    _arena(ax)
    _ring(ax, ENROUTE_R, ENROUTE_C, ls=(0, (1.5, 1.5)), lw=1.0)
    _ring(ax, OMNI_RING_R, INNER_C, lw=1.2)
    _ring(ax, Q4_OUTER_FULL_R, OUTER_C, lw=1.25)
    for p in inner:
        ax.plot([0, p[0]], [0, p[1]], color="#CBD5E0", lw=0.7, zorder=2)
    ox = [p[0] for p in outer] + [outer[0][0]]
    oy = [p[1] for p in outer] + [outer[0][1]]
    ax.plot(ox, oy, color=OUTER_C, lw=1.15, alpha=0.9, zorder=3)
    ix = [p[0] for p in inner] + [inner[0][0]]
    iy = [p[1] for p in inner] + [inner[0][1]]
    ax.plot(ix, iy, color=INNER_C, lw=1.2, zorder=4)
    _shadow_scatter(ax, [p[0] for p in enroute], [p[1] for p in enroute], s=42, c=ENROUTE_C, marker="o", edgecolors="white", linewidths=0.55, label="途听 8×900 m")
    _shadow_scatter(ax, [p[0] for p in inner], [p[1] for p in inner], s=58, c=INNER_C, marker="o", edgecolors="white", linewidths=0.7, label="内环 8×1200 m")
    _shadow_scatter(ax, [p[0] for p in outer], [p[1] for p in outer], s=52, c=OUTER_C, marker="s", edgecolors="white", linewidths=0.6, label="外环 12×2100 m")
    ax.scatter([0], [0], s=86, c=INK, marker="s", edgecolors="white", linewidths=0.7, zorder=9, label="原点")
    ax.text(ENROUTE_R * 0.12, ENROUTE_R * 0.92, "900", **_halo(8, ENROUTE_C))
    ax.text(OMNI_RING_R * 0.22, OMNI_RING_R * 0.78, "1200", **_halo(8, INNER_C))
    ax.text(ARENA_R * 0.55, ARENA_R * 0.72, "1800", **_halo(8, MUTED))
    ax.text(Q4_OUTER_FULL_R * 0.62, Q4_OUTER_FULL_R * 0.55, "2100", **_halo(8.5, OUTER_C))
    ax.legend(loc="lower left", fontsize=8.3, ncol=1)
    _style_xy(ax, 2350)
    fig.tight_layout()
    p = _save(fig, "pro_q4_layers")
    plt.close(fig)
    return p


def fig_q4_outward() -> Path:
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyArrowPatch, Wedge

    src = (160.0, 40.0)
    phi = 18.0
    inner = omni_waypoints()[1:]
    # pick inner point roughly opposite to heading = backlobe
    back = min(inner, key=lambda p: math.cos(math.radians(phi)) * p[0] + math.sin(math.radians(phi)) * p[1])
    en_a = math.radians(phi)
    en = (ENROUTE_R * math.cos(en_a), ENROUTE_R * math.sin(en_a))
    outer_a = math.radians(phi)
    outer = (Q4_OUTER_FULL_R * math.cos(outer_a), Q4_OUTER_FULL_R * math.sin(outer_a))
    fig, ax = plt.subplots(figsize=(6.6, 6.3))
    _arena(ax)
    _ring(ax, OMNI_RING_R, INNER_C, lw=0.9, alpha=0.55)
    _ring(ax, Q4_OUTER_FULL_R, OUTER_C, lw=0.9, alpha=0.7)
    ax.add_patch(
        Wedge(
            src,
            COVER_R,
            phi - 90,
            phi + 90,
            facecolor=DIR_C,
            edgecolor=DIR_C,
            alpha=0.16,
            lw=0.8,
            zorder=3,
        )
    )
    ax.add_patch(
        plt.Circle(src, COVER_R, fill=False, color=DIR_C, lw=0.7, ls=(0, (3, 2)), alpha=0.7, zorder=3)
    )
    ax.add_patch(
        FancyArrowPatch(
            src,
            (src[0] + 420 * math.cos(math.radians(phi)), src[1] + 420 * math.sin(math.radians(phi))),
            arrowstyle="-|>",
            mutation_scale=14,
            color=DIR_C,
            lw=1.6,
            zorder=8,
        )
    )
    _shadow_scatter(ax, [back[0]], [back[1]], s=70, c=INNER_C, edgecolors="white", linewidths=0.7, label="内环点（后瓣）")
    _shadow_scatter(ax, [en[0]], [en[1]], s=86, c=ENROUTE_C, edgecolors="white", linewidths=0.8, label="途听 900 m（前瓣）")
    _shadow_scatter(ax, [outer[0]], [outer[1]], s=78, c=OUTER_C, marker="s", edgecolors="white", linewidths=0.7, label="外环 2100 m")
    ax.scatter([src[0]], [src[1]], s=160, c=DIR_C, marker="^", edgecolors="white", linewidths=0.8, zorder=10, label="近心朝外定向源")
    ax.plot([src[0], back[0]], [src[1], back[1]], color=MUTED, lw=0.8, ls=":", zorder=4)
    ax.text(src[0] - 30, src[1] + 55, r"$J$", **_halo(11, DIR_C))
    ax.text(en[0] + 30, en[1] + 20, "途听", **_halo(9, ENROUTE_C))
    ax.legend(loc="lower left", fontsize=8.3)
    _style_xy(ax, 2350)
    fig.tight_layout()
    p = _save(fig, "pro_q4_outward")
    plt.close(fig)
    return p


def fig_q4_frontcover() -> Path:
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap

    listens = q4_listen_set(directional_waypoints(outer_r=Q4_OUTER_FULL_R, outer_n=Q4_OUTER_FULL_N))
    n = 161
    lim = 1820
    xs = np.linspace(-lim, lim, n)
    ys = np.linspace(-lim, lim, n)
    xx, yy = np.meshgrid(xs, ys)
    headings = np.linspace(0.0, 360.0, 24, endpoint=False)
    worst = np.full(xx.shape, 0.0)
    for h in headings:
        nearest = np.full(xx.shape, np.inf)
        rad = math.radians(h)
        ux, uy = math.cos(rad), math.sin(rad)
        for px, py in listens:
            dx = px - xx
            dy = py - yy
            front = dx * ux + dy * uy >= -1e-9
            d = np.hypot(dx, dy)
            d = np.where(front, d, np.inf)
            nearest = np.minimum(nearest, d)
        worst = np.maximum(worst, nearest)
    rr = np.hypot(xx, yy)
    worst = np.ma.masked_where(rr > ARENA_R, worst)
    cmap = LinearSegmentedColormap.from_list(
        "front",
        ["#1A365D", "#2B6CB0", "#9AE6B4", "#FAF089", "#DD6B20", "#C53030"],
        N=256,
    )
    fig, ax = plt.subplots(figsize=(6.6, 6.05))
    im = ax.pcolormesh(xx, yy, worst, cmap=cmap, shading="auto", vmin=400, vmax=1200, zorder=1)
    _arena(ax, fill=False)
    _ring(ax, Q4_OUTER_FULL_R, OUTER_C, lw=0.95)
    ax.contour(xx, yy, worst.filled(9999), levels=[1000], colors=["#1A202C"], linewidths=0.85, zorder=4)
    ax.scatter(
        [p[0] for p in listens],
        [p[1] for p in listens],
        s=16,
        c="white",
        edgecolors=INK,
        linewidths=0.4,
        zorder=5,
    )
    cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.03)
    cb.set_label("最坏朝向下最近前瓣听点 / m")
    cb.outline.set_linewidth(0.6)
    _style_xy(ax, 2350)
    fig.tight_layout()
    p = _save(fig, "pro_q4_frontcover")
    plt.close(fig)
    return p


def fig_vt_structure() -> Path:
    import matplotlib.pyplot as plt

    # official practice means (seconds)
    labels = ["问题三\nround3", "问题四\n12×2100"]
    travel = np.array([4432.4, 7169.0])  # Q3 approx mean of table; Q4 given
    detect = np.array([755.8, 1246.0])
    other = np.array([5245.0, 8508.0]) - travel - detect
    other = np.clip(other, 0, None)
    fig, ax = plt.subplots(figsize=(5.6, 4.4))
    x = np.arange(len(labels))
    w = 0.46
    ax.bar(x, travel, w, color=INNER_C, label="行驶", zorder=3)
    ax.bar(x, detect, w, bottom=travel, color="#63B3ED", label="探测驻留", zorder=3)
    ax.bar(x, other, w, bottom=travel + detect, color="#E2E8F0", label="其余", zorder=3)
    for i, tot in enumerate([5245, 8508]):
        ax.text(i, tot + 120, f"{tot} s", ha="center", va="bottom", **_halo(9.5, INK))
    ax.axhline(5000, color=DIR_C, ls=(0, (4, 2)), lw=1.0, zorder=2, label="赛题期望 5000 s")
    ax.set_xticks(x, labels)
    ax.set_ylabel("虚拟时间 / s")
    ax.set_ylim(0, 9800)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(loc="upper left", fontsize=8.5)
    ax.yaxis.grid(True, ls=":", color="#E2E8F0", zorder=0)
    ax.set_axisbelow(True)
    fig.tight_layout()
    p = _save(fig, "pro_vt_structure")
    plt.close(fig)
    return p


def fig_q3_games() -> Path:
    import matplotlib.pyplot as plt

    vt = [5546, 4902, 5171, 4845, 5085, 5495, 4612, 4732, 6258, 5808]
    travel = [4767, 4074, 4373, 4011, 4159, 4621, 3765, 3894, 5469, 5191]
    detect = [724, 778, 748, 784, 873, 818, 794, 778, 724, 537]
    idx = np.arange(1, 11)
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.bar(idx, travel, color=INNER_C, width=0.72, label="行驶", zorder=3)
    ax.bar(idx, detect, bottom=travel, color="#90CDF4", width=0.72, label="探测", zorder=3)
    ax.plot(idx, vt, color=DIR_C, marker="o", ms=4.5, lw=1.15, label="虚拟时间", zorder=4)
    ax.axhline(5245, color=GOLD, ls=(0, (4, 2)), lw=1.05, label="10 局均值 5245 s")
    ax.set_xlabel("局号")
    ax.set_ylabel("时间 / s")
    ax.set_xticks(idx)
    ax.set_ylim(0, 7200)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(ncol=2, fontsize=8.3, loc="upper left")
    ax.yaxis.grid(True, ls=":", color="#E2E8F0")
    ax.set_axisbelow(True)
    fig.tight_layout()
    p = _save(fig, "pro_q3_games")
    plt.close(fig)
    return p


def main() -> None:
    _setup()
    writers = [
        fig_q1_intersection,
        fig_q2_candidate,
        fig_q3_coverage,
        fig_q3_residual,
        fig_q3_games,
        fig_q4_layers,
        fig_q4_outward,
        fig_q4_frontcover,
        fig_vt_structure,
    ]
    for fn in writers:
        path = fn()
        print("wrote", path)


if __name__ == "__main__":
    main()
