"""Q1 paper figures (publication styling, Chinese labels).

Paper numbering (output/2026B-问题1(3).docx):
  fig1  single-station closed cone as two oriented half-planes (schematic, magnified)
  fig3  bounded convex localization region: vertices, diameter pair, SEC, diameter circle
  fig5  two-station intersection: cones, region, minimum enclosing circle, diameter circle
  fig7  equilateral triangle: Jung equality and diameter-circle counterexample

Values are computed with src/geometry.py; the fig3 multi-station example reproduces
the paper figure values d=10.73 m, r=5.36 m.
"""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Arc, Circle, FancyArrowPatch, Patch, Polygon, Wedge  # noqa: E402

from geometry import intersect_cones, polygon_diameter, smallest_enclosing_circle  # noqa: E402

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
            ha: str = "left", va: str = "center", zorder: int = 10,
            bg: bool = True) -> None:
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
        bbox=dict(boxstyle="round,pad=0.16", fc="white", ec="none", alpha=0.9) if bg else None,
    )


def _plain(ax, x, y, text: str, color: str = DARK, fs: float = 10, ha: str = "left",
           va: str = "center", zorder: int = 10) -> None:
    ax.text(x, y, text, fontsize=fs, color=color, ha=ha, va=va, zorder=zorder)


def fig1_single_station(outdir: Path) -> None:
    fig, ax = plt.subplots(figsize=(7.2, 6.4), layout="constrained")
    theta = 36.0
    delta = 13.0  # display exaggeration only
    r_edge = 5.0
    S = np.array([0.0, 0.0])

    ang = np.radians(np.linspace(theta - delta, theta + delta, 120))
    arc = np.column_stack([np.cos(ang), np.sin(ang)]) * r_edge
    ax.add_patch(
        Polygon(np.vstack([S, arc]), closed=True, facecolor=SKY, alpha=0.25,
                edgecolor="none", zorder=2)
    )
    for a in (theta - delta, theta + delta):
        u = math.radians(a)
        p = np.array([math.cos(u), math.sin(u)]) * (r_edge + 1.0)
        ax.plot([0.0, p[0]], [0.0, p[1]], color=BLUE, lw=1.8, zorder=3)
        ax.annotate(
            "",
            xy=p,
            xytext=np.array([math.cos(u), math.sin(u)]) * (r_edge + 0.62),
            arrowprops=dict(arrowstyle="-|>", color=BLUE, lw=1.8),
            zorder=3,
        )
    ax.plot(arc[:, 0], arc[:, 1], color=BLUE, lw=1.8, zorder=3)

    ang2 = np.radians(np.linspace(theta + 180 - delta, theta + 180 + delta, 120))
    arc2 = np.column_stack([np.cos(ang2), np.sin(ang2)]) * (r_edge * 0.42)
    ax.add_patch(
        Polygon(
            np.vstack([S, arc2]),
            closed=True,
            facecolor="none",
            edgecolor=GRAY,
            ls=(0, (4, 3)),
            lw=1.1,
            zorder=2,
        )
    )

    u = math.radians(theta)
    center_end = np.array([math.cos(u), math.sin(u)]) * (r_edge * 0.94)
    ax.plot(
        [0.0, center_end[0]],
        [0.0, center_end[1]],
        color="#4D4D4D",
        lw=1.2,
        ls=(0, (3, 2.4)),
        zorder=4,
    )

    ax.add_patch(
        Arc(
            (0.0, 0.0),
            3.8,
            3.8,
            angle=0.0,
            theta1=0.0,
            theta2=theta,
            color="#4D4D4D",
            lw=1.1,
            zorder=4,
        )
    )
    ax.text(
        2.28 * math.cos(math.radians(theta / 2)),
        2.28 * math.sin(math.radians(theta / 2)),
        r"$\theta$",
        fontsize=13,
        ha="center",
        va="center",
        zorder=4,
    )

    ax.add_patch(
        Arc(
            (0.0, 0.0),
            7.8,
            7.8,
            angle=0.0,
            theta1=theta - delta,
            theta2=theta + delta,
            color=VERM,
            lw=1.4,
            zorder=4,
        )
    )

    p_pt = np.array([math.cos(u), math.sin(u)]) * 3.0
    ax.plot([p_pt[0]], [p_pt[1]], marker="o", ms=7, color=PURPLE, zorder=5)
    _halo(ax, p_pt[0] + 0.32, p_pt[1], "$P$", fs=11, ha="left", va="center")

    ax.plot([0.0], [0.0], marker="o", ms=9, color=DARK, zorder=6)

    _halo(
        ax,
        (r_edge + 1.14) * math.cos(math.radians(theta + delta)),
        (r_edge + 1.14) * math.sin(math.radians(theta + delta)),
        r"$\theta+\delta$",
        color=BLUE,
        fs=10.5,
        ha="left",
        va="bottom",
    )
    _halo(
        ax,
        (r_edge + 1.0) * math.cos(math.radians(theta - delta)),
        (r_edge + 1.0) * math.sin(math.radians(theta - delta)),
        r"$\theta-\delta$",
        color=BLUE,
        fs=10.5,
        ha="left",
        va="top",
    )

    handles = [
        Patch(facecolor=SKY, edgecolor=BLUE, alpha=0.4,
              label="可接受闭角扇 $C(S,\\theta,\\delta)$"),
        Line2D([], [], color=VERM, lw=1.4, label="误差张角 $2\\delta$（示意放大）"),
        Line2D([], [], color=GRAY, lw=1.1, ls=(0, (4, 3)), label="对顶扇：不在模型内"),
        Line2D([], [], marker="o", ls="none", color=DARK, ms=8, label="检测站 $S$"),
    ]
    ax.legend(
        handles=handles,
        loc="upper left",
        fontsize=9.5,
        framealpha=0.96,
        title="定位区 = 两闭半平面之交（阴影楔形）",
        title_fontsize=9.5,
    )

    _corner_box(
        ax,
        "正文 $\\delta=1°$；本图为示意：角度放大、坐标为示意尺度",
        loc="lower right",
        fs=9,
    )

    ax.set_aspect("equal")
    ax.set_xlim(-2.3, 6.9)
    ax.set_ylim(-1.7, 5.7)
    ax.set_xticks([0, 2, 4, 6])
    ax.set_yticks([0, 2, 4])
    ax.set_xlabel("$x$（示意）")
    ax.set_ylabel("$y$（示意）")
    ax.grid(True, color="#EFEFEF", lw=0.7, zorder=0)
    _save(fig, outdir, "fig1_single_station_cone")


def fig2_flowchart(outdir: Path) -> None:
    fig, ax = plt.subplots(figsize=(12.2, 4.8), layout="constrained")
    ax.set_xlim(0.0, 11.2)
    ax.set_ylim(-0.25, 4.4)
    ax.axis("off")

    def box(cx, cy, w, h, text, *, edge=BLUE, fs=12.0, face="#F2F7FB"):
        ax.add_patch(
            matplotlib.patches.FancyBboxPatch(
                (cx - w / 2, cy - h / 2),
                w,
                h,
                boxstyle="round,pad=0.06,rounding_size=0.16",
                linewidth=1.6,
                edgecolor=edge,
                facecolor=face,
                zorder=2,
            )
        )
        ax.text(cx, cy, text, ha="center", va="center", fontsize=fs, zorder=3, linespacing=1.5)

    def arrow(p, q, color):
        ax.add_patch(
            FancyArrowPatch(
                p,
                q,
                arrowstyle="-|>",
                mutation_scale=17,
                color=color,
                lw=2.0,
                shrinkA=1.0,
                shrinkB=1.0,
                zorder=1,
            )
        )

    box(1.35, 2.0, 1.9, 1.15, "输入\n$(S_i,\\ \\theta_i)$")
    box(3.95, 2.0, 2.2, 1.15, "角扇半平面\n叉积不等式")
    box(6.55, 2.0, 2.2, 1.15, "半平面交\n空 / 无界 / 有界")
    box(9.55, 3.3, 2.5, 1.45, "定位质量核\n有界：直径 $d$\nWelzl $(c,\\ r)$", edge=GREEN, fs=11.5)
    box(9.55, 0.85, 2.5, 1.2, "空 / 无界\n触发补测", edge=VERM, fs=11.5)

    arrow((2.32, 2.0), (2.83, 2.0), "#4D4D4D")
    arrow((5.07, 2.0), (5.43, 2.0), "#4D4D4D")
    arrow((7.67, 2.15), (8.28, 3.05), GREEN)
    arrow((7.67, 1.85), (8.28, 1.00), VERM)

    ax.text(
        11.1, -0.12,
        "近共线标记 / 可清判定",
        fontsize=10.5, color="#6E6E6E", ha="right", va="bottom", zorder=3,
    )

    _save(fig, outdir, "fig2_flowchart")


def _region_data():
    stations = [(100.0, 300.0), (100.0, 400.0), (300.0, 200.0), (400.0, 400.0)]
    G = (200.0, 221.0)
    bearings = [
        math.degrees(math.atan2(G[1] - s[1], G[0] - s[0])) % 360.0 for s in stations
    ]
    region = intersect_cones(stations, bearings, delta_deg=1.0)
    verts = np.array(region.vertices, dtype=float)
    d = polygon_diameter(region.vertices)
    c, r = smallest_enclosing_circle(region.vertices)
    best = (0, 1, -1.0)
    for i in range(len(verts)):
        for j in range(i + 1, len(verts)):
            dd = float(np.hypot(*(verts[i] - verts[j])))
            if dd > best[2]:
                best = (i, j, dd)
    i, j, _ = best
    return stations, G, verts, d, c, r, (i, j)


def _draw_global_panel(ax, stations, G, c) -> None:
    label_layout = (
        (-18.0, 0.0, "right", "center"),
        (-20.0, 14.0, "right", "bottom"),
        (0.0, -24.0, "center", "top"),
        (22.0, -14.0, "left", "top"),
    )
    for idx, (s, col) in enumerate(zip(stations, (BLUE, GREEN, ORANGE, PURPLE))):
        th = math.degrees(math.atan2(G[1] - s[1], G[0] - s[0]))
        reach = math.hypot(G[0] - s[0], G[1] - s[1]) * 1.32
        ax.add_patch(
            Wedge(s, reach, th - 5.0, th + 5.0, facecolor=col, alpha=0.16,
                  edgecolor=col, lw=0.9, zorder=2)
        )
        ax.plot([s[0], G[0]], [s[1], G[1]], color=col, lw=1.0, zorder=3)
        ax.plot([s[0]], [s[1]], marker="o", ms=6.0, color=DARK, zorder=5)
        dx, dy, ha, va = label_layout[idx]
        _plain(ax, s[0] + dx, s[1] + dy, f"$S_{{{idx + 1}}}$", fs=10,
               ha=ha, va=va)
    ax.plot([G[0]], [G[1]], marker="*", ms=16, color=VERM, zorder=6)
    ax.add_patch(Circle(c, 7.0, facecolor="none", edgecolor=VERM, lw=1.2, zorder=6))
    _plain(ax, G[0] + 12, G[1] + 10, "$G$（真源）", color=VERM, fs=10, ha="left", va="bottom")
    _corner_box(
        ax,
        "4 站闭角扇交会（张角示意放大）\n"
        "正文 $\\delta=1°$；定位区放大见 (b)",
        loc="upper right",
        fs=9.2,
    )
    ax.set_xlabel("$x$ (m)")
    ax.set_ylabel("$y$ (m)")
    ax.set_aspect("equal")
    ax.grid(True, color="#EFEFEF", lw=0.7, zorder=0)
    ax.set_xlim(55, 445)
    ax.set_ylim(145, 435)


def _draw_zoom_panel(ax, verts, d, c, r, pair, G, x_half=None, y_half=None) -> None:
    i, j = pair
    ax.add_patch(
        Polygon(verts, closed=True, facecolor=SKY, alpha=0.30, edgecolor=BLUE, lw=1.7, zorder=2)
    )

    p_i, p_j = verts[i], verts[j]
    ax.plot([p_i[0], p_j[0]], [p_i[1], p_j[1]], color="#4D4D4D", lw=1.2,
            ls=(0, (6, 2, 1, 2)), zorder=4)
    ax.add_patch(Circle(c, r, facecolor="none", edgecolor=ORANGE, lw=2.4, zorder=5))
    ax.add_patch(Circle(c, d / 2.0, facecolor="none", edgecolor=PURPLE, lw=1.5,
                        ls=(0, (4, 3)), zorder=6))

    for k, v in enumerate(verts):
        ax.plot([v[0]], [v[1]], marker="o", ms=5.0, color=DARK, zorder=7)

    left = [k for k, v in enumerate(verts) if v[0] < c[0]]
    right = [k for k, v in enumerate(verts) if v[0] >= c[0]]
    min_x = float(verts[:, 0].min())
    max_x = float(verts[:, 0].max())
    for group, x_label in ((left, min_x - 3.4), (right, max_x + 3.4)):
        group = sorted(group, key=lambda k: verts[k][1])
        ys = [float(verts[k][1]) for k in group]
        mean_y = sum(ys) / len(ys)
        gap = 2.05
        start = mean_y - gap * (len(group) - 1) / 2.0
        for pos, k in enumerate(group):
            ly = start + gap * pos
            v = verts[k]
            ax.plot([x_label, v[0]], [ly, v[1]], color="#B8B8B8", lw=0.7,
                    zorder=6, solid_capstyle="round")
            _halo(ax, x_label, ly, f"$V_{{{k + 1}}}$", fs=9, ha="center", va="center",
                  zorder=9)

    ax.plot([p_i[0], p_j[0]], [p_i[1], p_j[1]], marker="o", ms=9, mfc="none",
            mec=ORANGE, mew=2.0, ls="none", zorder=8)

    ax.plot([G[0]], [G[1]], marker="*", ms=13, color=VERM, zorder=9)

    handles = [
        Patch(facecolor=SKY, edgecolor=BLUE, alpha=0.4, label="定位区 $R$（4 站半平面交）"),
        Line2D([], [], color="#4D4D4D", lw=1.2, ls=(0, (6, 2, 1, 2)),
               label=f"直径端点对 $d={d:.2f}$ m"),
        Line2D([], [], color=ORANGE, lw=2.4, label=f"最小包围圆 $r={r:.2f}$ m"),
        Line2D([], [], color=PURPLE, lw=1.5, ls=(0, (4, 3)),
               label=f"直径圆 $d/2={d / 2:.2f}$ m（重合）"),
    ]
    ax.legend(handles=handles, loc="lower right", fontsize=8.2, framealpha=0.96)

    _corner_box(
        ax,
        "多站半平面交 → 有界凸多边形（★ 真源示例）\n"
        f"$d={d:.2f}$ m，$r={r:.2f}$ m，$d/2={d / 2:.2f}$ m；本例 $r=d/2$（两圆重合）",
        loc="upper left",
        fs=8.4,
    )

    span = max(verts.max(axis=0) - verts.min(axis=0))
    pad = 0.55 * span
    xh = x_half if x_half is not None else span / 2 + pad
    yh = y_half if y_half is not None else span / 2 + pad
    ax.set_xlim(c[0] - xh, c[0] + xh)
    ax.set_ylim(c[1] - yh, c[1] + yh)
    ax.set_xlabel("$x$ (m)")
    ax.set_ylabel("$y$ (m)")
    ax.set_aspect("equal")
    ax.grid(True, color="#EFEFEF", lw=0.7, zorder=0)


def fig3_bounded_region(outdir: Path) -> None:
    stations, G, verts, d, c, r, pair = _region_data()
    fig, ax = plt.subplots(figsize=(7.6, 6.8), layout="constrained")
    _draw_zoom_panel(ax, verts, d, c, r, pair, G)

    axins = ax.inset_axes([0.025, 0.025, 0.31, 0.31])
    for idx, (s, col) in enumerate(zip(stations, (BLUE, GREEN, ORANGE, PURPLE))):
        th = math.degrees(math.atan2(G[1] - s[1], G[0] - s[0]))
        reach = math.hypot(G[0] - s[0], G[1] - s[1]) * 1.30
        axins.add_patch(
            Wedge(s, reach, th - 5.0, th + 5.0, facecolor=col, alpha=0.15,
                  edgecolor=col, lw=0.7, zorder=2)
        )
        axins.plot([s[0]], [s[1]], marker="o", ms=3.6, color=DARK, zorder=4)
        axins.text(s[0], s[1], f"$S_{{{idx + 1}}}$", fontsize=6.4, ha="center",
                   va="center", color=DARK, zorder=6,
                   bbox=dict(boxstyle="round,pad=0.1", fc="white", ec="none", alpha=0.75))
    axins.plot([G[0]], [G[1]], marker="o", ms=6.0, mfc="none", mec=VERM, mew=1.5, zorder=5)
    axins.text(0.02, 0.98, "全局：4 站闭角扇（张角示意放大）", transform=axins.transAxes,
               fontsize=7.4, color="#4D4D4D", ha="left", va="top", zorder=6,
               bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="#E0E0E0", lw=0.6, alpha=0.9))
    axins.set_aspect("equal")
    axins.axis("off")
    _save(fig, outdir, "fig3_bounded_region")


def fig3_bounded_region_2panel(outdir: Path) -> None:
    stations, G, verts, d, c, r, pair = _region_data()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.6, 5.9), layout="constrained",
                                   width_ratios=[1.12, 1.0])
    _draw_global_panel(ax1, stations, G, c)
    ax1.set_title("(a) 多站角扇交会全局（张角示意放大）", fontsize=12, pad=8)
    _draw_zoom_panel(ax2, verts, d, c, r, pair, G, x_half=10.7, y_half=8.8)
    ax2.set_title("(b) 定位区放大（$\\delta=1°$）", fontsize=12, pad=8)
    _save(fig, outdir, "fig3_bounded_region_2panel")


def fig5_two_station(outdir: Path) -> None:
    S1 = (0.0, 0.0)
    S2 = (400.0, 0.0)
    G = (200.0, 300.0)
    b1 = math.degrees(math.atan2(G[1] - S1[1], G[0] - S1[0])) % 360.0
    b2 = math.degrees(math.atan2(G[1] - S2[1], G[0] - S2[0])) % 360.0

    region = intersect_cones([S1, S2], [b1, b2], delta_deg=1.0)
    verts = np.array(region.vertices, dtype=float)
    d = polygon_diameter(region.vertices)
    c, r = smallest_enclosing_circle(region.vertices)
    best = (0, 1, -1.0)
    for i in range(len(verts)):
        for j in range(i + 1, len(verts)):
            dd = float(np.hypot(*(verts[i] - verts[j])))
            if dd > best[2]:
                best = (i, j, dd)
    i, j, _ = best

    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(12.8, 6.0), layout="constrained", width_ratios=[1.12, 1.0]
    )

    L = 470.0
    for S, b, col in ((S1, b1, BLUE), (S2, b2, GREEN)):
        ends = []
        for a in (b - 1.0, b + 1.0):
            u = math.radians(a)
            ends.append((S[0] + L * math.cos(u), S[1] + L * math.sin(u)))
        ax1.add_patch(
            Polygon([S, ends[0], ends[1]], closed=True, facecolor=col, alpha=0.12,
                    edgecolor="none", zorder=1)
        )
        for e in ends:
            ax1.plot([S[0], e[0]], [S[1], e[1]], color=col, lw=1.0, alpha=0.75, zorder=2)
        ax1.plot([S[0], G[0]], [S[1], G[1]], color="#4D4D4D", lw=1.1, ls=(0, (3, 2.4)), zorder=3)

    ax1.plot([S1[0]], [S1[1]], marker="o", ms=8, color=DARK, zorder=5)
    ax1.plot([S2[0]], [S2[1]], marker="o", ms=8, color=DARK, zorder=5)
    _plain(ax1, S1[0] - 12, S1[1] - 40, "$S_1$", fs=13, ha="center", va="top")
    _plain(ax1, S2[0] + 12, S2[1] - 40, "$S_2$", fs=13, ha="center", va="top")
    ax1.plot([G[0]], [G[1]], marker="*", ms=15, color=VERM, zorder=5)
    zb = 42.0
    _leader(ax1, (G[0] + 4, G[1]), (G[0] + zb + 14, G[1] + 2), "真源（示例）",
            color=VERM, fs=9.5, ha="left", va="center", bg=False)

    ax1.add_patch(
        Polygon(
            [
                (G[0] - zb, G[1] - zb),
                (G[0] + zb, G[1] - zb),
                (G[0] + zb, G[1] + zb),
                (G[0] - zb, G[1] + zb),
            ],
            closed=True,
            facecolor="none",
            edgecolor=PURPLE,
            lw=1.3,
            ls=(0, (4, 2.6)),
            zorder=4,
        )
    )
    _plain(ax1, G[0] - zb + 6, G[1] + zb - 6, "(b)", color=PURPLE, fs=10,
           ha="left", va="top")
    _corner_box(ax1, "两站角扇半宽 $\\delta=1°$（全局视图下张角很小）", loc="upper left", fs=9.5)
    ax1.set_title("(a) 两站交会全局", fontsize=12.5, pad=8)
    ax1.set_xlabel("$x$ (m)")
    ax1.set_ylabel("$y$ (m)")
    ax1.set_aspect("equal")
    ax1.set_xlim(-70, 470)
    ax1.set_ylim(-70, 470)
    ax1.grid(True, color="#EFEFEF", lw=0.7, zorder=0)

    ax2.add_patch(
        Polygon(verts, closed=True, facecolor=SKY, alpha=0.30, edgecolor=BLUE, lw=1.6, zorder=2)
    )
    ax2.add_patch(Circle(c, r, facecolor="none", edgecolor=ORANGE, lw=2.4, zorder=5))
    ax2.add_patch(
        Circle(c, d / 2.0, facecolor="none", edgecolor=PURPLE, lw=1.5, ls=(0, (4, 3)), zorder=6)
    )
    ax2.add_patch(Circle(c, 20.0, facecolor="none", edgecolor=GREEN, lw=1.3,
                         ls=(0, (1.6, 1.8)), zorder=4))

    p_i, p_j = verts[i], verts[j]
    ax2.plot([p_i[0], p_j[0]], [p_i[1], p_j[1]], color="#4D4D4D", lw=1.1, zorder=4)
    ax2.annotate(
        "",
        xy=p_j,
        xytext=p_i,
        arrowprops=dict(arrowstyle="<|-|>", color="#4D4D4D", lw=1.1, mutation_scale=9),
        zorder=4,
    )

    ax2.plot([G[0]], [G[1]], marker="*", ms=14, color=VERM, zorder=9)

    ax2.plot([G[0] - 30, G[0] - 30 + 10], [G[1] - 34, G[1] - 34], color=DARK, lw=2.4, zorder=7)
    for x in (G[0] - 30, G[0] - 30 + 10):
        ax2.plot([x, x], [G[1] - 35.2, G[1] - 32.8], color=DARK, lw=1.4, zorder=7)
    _plain(ax2, G[0] - 30 + 5, G[1] - 37.5, "10 m", fs=9.5, ha="center", va="top")

    _corner_box(
        ax2,
        f"$d={d:.2f}$ m，$r={r:.2f}$ m，$d/2={d / 2:.2f}$ m（两圆重合）\n"
        "$r\\leq 20$ m：可清；$r=d/2$：直径圆覆盖成立\n"
        "★ 真源（示例）",
        loc="upper left",
        fs=8.8,
    )
    ax2.set_title("(b) 定位区放大（$\\delta=1°$）", fontsize=12.5, pad=8)
    ax2.set_xlabel("$x$ (m)")
    ax2.set_ylabel("$y$ (m)")
    ax2.set_aspect("equal")
    ax2.set_xlim(G[0] - 44, G[0] + 44)
    ax2.set_ylim(G[1] - 44, G[1] + 44)
    ax2.grid(True, color="#EFEFEF", lw=0.7, zorder=0)

    handles = [
        Patch(facecolor=SKY, edgecolor=BLUE, alpha=0.4, label="定位区 $R$（凸四边形）"),
        Line2D([], [], color="#4D4D4D", lw=1.1, label=f"直径端点对 $d={d:.2f}$ m"),
        Line2D([], [], color=ORANGE, lw=2.4, label=f"最小包围圆 $r={r:.2f}$ m"),
        Line2D([], [], color=PURPLE, lw=1.5, ls=(0, (4, 3)),
               label=f"直径圆 $d/2={d / 2:.2f}$ m（本例重合）"),
        Line2D([], [], color=GREEN, lw=1.3, ls=(0, (1.6, 1.8)), label="清除界 $20$ m"),
    ]
    ax2.legend(handles=handles, loc="lower right", fontsize=9, framealpha=0.96)

    _save(fig, outdir, "fig5_two_station_intersection")


def fig7_equilateral_jung(outdir: Path) -> None:
    d = 100.0
    h = d * math.sqrt(3.0) / 2.0
    tri = [(0.0, 0.0), (d, 0.0), (d / 2.0, h)]
    dd = polygon_diameter(tri)
    c, r = smallest_enclosing_circle(tri)
    c_diam = (d / 2.0, 0.0)

    fig, ax = plt.subplots(figsize=(7.2, 6.6), layout="constrained")
    ax.add_patch(
        Polygon(tri, closed=True, facecolor=SKY, alpha=0.28, edgecolor=BLUE, lw=1.8, zorder=2)
    )
    ax.add_patch(Circle(c, r, facecolor="none", edgecolor=ORANGE, lw=2.4, zorder=5))
    ax.add_patch(Circle(c_diam, d / 2.0, facecolor="none", edgecolor=PURPLE, lw=1.6,
                        ls=(0, (4, 3)), zorder=6))

    for v in tri:
        ax.plot([v[0]], [v[1]], marker="o", ms=6.5, color=DARK, zorder=7)

    ax.plot([c[0], d / 2.0], [c[1], h], color=ORANGE, lw=1.3, ls=(0, (2.5, 2.0)), zorder=4)
    _plain(ax, c[0] + 4.5, (c[1] + h) / 2.0, "$r$", color=ORANGE, fs=10.5, ha="left")

    ax.plot([c_diam[0]], [c_diam[1]], marker="o", ms=9, mfc="none", mec=PURPLE,
            mew=1.8, zorder=8)
    ax.plot([c[0]], [c[1]], marker="o", ms=9, mfc="none", mec=ORANGE, mew=1.8, zorder=8)
    _plain(ax, c_diam[0] - 3.0, c_diam[1] - 3.0, "直径圆心", color=PURPLE, fs=9,
           ha="right", va="top")
    _plain(ax, c[0] + 4.5, c[1] + 0.8, "包围圆心 $c$", color=ORANGE, fs=9,
           ha="left", va="bottom")

    ax.annotate(
        "",
        xy=(0.0, -9.0),
        xytext=(d, -9.0),
        arrowprops=dict(arrowstyle="<|-|>", color="#4D4D4D", lw=1.0, mutation_scale=9),
        zorder=4,
    )
    _plain(ax, d / 2.0, -11.0, "$d=100.00$ m", fs=9.5, ha="center", va="top")

    _leader(ax, (d / 2.0, h), (d * 0.66, h * 1.08), "顶点在直径圆外：$r>d/2$",
            color=VERM, fs=9.5, ha="left", va="center", bg=False)

    _corner_box(
        ax,
        f"$d={dd:.2f}$ m；$r={r:.2f}$ m；$d/2={d / 2:.2f}$ m\n"
        "$r=d/\\sqrt{3}$：荣格不等式取等\n"
        "$r>d/2$：直径圆不能覆盖",
        loc="upper left",
        fs=9.5,
    )

    handles = [
        Patch(facecolor=SKY, edgecolor=BLUE, alpha=0.4, label="等边三角形顶点集"),
        Line2D([], [], color=ORANGE, lw=2.4, label=f"最小包围圆 $r={r:.2f}$ m"),
        Line2D([], [], color=PURPLE, lw=1.6, ls=(0, (4, 3)), label=f"直径圆 $d/2={d / 2:.2f}$ m"),
    ]
    ax.legend(handles=handles, loc="lower right", fontsize=9.2, framealpha=0.96)

    ax.set_aspect("equal")
    ax.set_xlim(-32, 132)
    ax.set_ylim(-72, 118)
    ax.set_xlabel("$x$ (m)")
    ax.set_ylabel("$y$ (m)")
    ax.grid(True, color="#EFEFEF", lw=0.7, zorder=0)
    _save(fig, outdir, "fig7_equilateral_jung")


def main() -> int:
    outdir = Path(__file__).resolve().parents[1] / "output" / "figures" / "q1_paper"
    fig1_single_station(outdir)
    fig2_flowchart(outdir)
    fig3_bounded_region(outdir)
    fig3_bounded_region_2panel(outdir)
    fig5_two_station(outdir)
    fig7_equilateral_jung(outdir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
