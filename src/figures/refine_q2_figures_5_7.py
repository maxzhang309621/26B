"""Redraw the three Q2 paper figures that had readability defects.

The numerical labels below are deliberately limited to the frozen values already
reported around Figures 5--7 in ``2026B-问题2-修改(2).docx``.  The former
histograms used an unavailable, untracked 400-row sample and a dense rug plot;
Figure 5 is therefore an evidence-bounded statistical summary rather than a
fabricated reconstruction of that sample distribution.
"""

from __future__ import annotations

import argparse
import math
import os
import shutil
import sys
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from docx import Document
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch, Patch, Polygon, Rectangle


ROOT = Path(__file__).resolve().parents[2]
SRC_DOCX = ROOT / "output" / "论文修改版" / "2026B-问题2-修改(2).docx"
DST_DOCX = ROOT / "output" / "论文修改版" / "2026B-问题2-图5至7优化稿.docx"
OUT = ROOT / "output" / "figures" / "q2_refined"
sys.path.insert(0, str(ROOT / "src"))

from candidate import candidate_region, from_body  # noqa: E402


BLUE = "#2467A8"
RED = "#C54343"
TEAL = "#2A9D8F"
PURPLE = "#7751A8"
ORANGE = "#E28A2B"
INK = "#25323B"
GREY = "#66727A"
LIGHT_GREY = "#E8EDF0"

mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Microsoft YaHei", "SimHei", "Arial", "Liberation Sans"],
        "font.size": 10,
        "axes.labelsize": 10,
        "axes.titlesize": 11,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "axes.unicode_minus": False,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.linewidth": 0.7,
        "savefig.dpi": 360,
        "savefig.bbox": "tight",
    }
)


def _style_axis(ax: plt.Axes) -> None:
    ax.grid(axis="x", color="#DDE4E8", lw=0.7, zorder=0)
    ax.tick_params(length=3, width=0.7, color=INK)
    ax.spines["left"].set_color("#AAB6BD")
    ax.spines["bottom"].set_color("#AAB6BD")


def _save_png(fig: plt.Figure, path: Path) -> None:
    """Publish through a sibling file: Matplotlib cannot overwrite a previewed PNG on this Windows host."""
    staging = path.with_name(path.stem + ".staging.png")
    fig.savefig(staging, dpi=360)
    os.replace(staging, path)


def _value_box(ax: plt.Axes, x: float, y: float, text: str, color: str) -> None:
    ax.text(
        x,
        y,
        text,
        ha="center",
        va="center",
        color=INK,
        fontsize=9.2,
        linespacing=1.35,
        bbox={"boxstyle": "round,pad=0.42", "facecolor": color, "edgecolor": "none", "alpha": 0.14},
        zorder=4,
    )


def draw_fig5(path: Path) -> None:
    """Cleanly redraw the original two histograms without the dense rug marks.

    The supplied raster has 19 bars in each panel.  The counts are transcribed
    from those bars (both sum to 400), because the original 400-row vectors were
    not preserved in the workspace.  Thus the plotted distribution is retained;
    only the low-value rug decoration is removed.
    """
    beta_counts = np.array([22, 21, 18, 20, 22, 18, 17, 17, 21, 14, 27, 18, 17, 25, 26, 26, 20, 29, 22])
    radius_counts = np.array([120, 62, 56, 40, 9, 10, 15, 9, 9, 10, 9, 4, 6, 6, 7, 10, 7, 7, 4])
    fig, axes = plt.subplots(1, 2, figsize=(11.7, 4.25), gridspec_kw={"wspace": 0.34})
    ax = axes[0]
    beta_edges = np.linspace(-38, 38, len(beta_counts) + 1)
    ax.axvspan(-30, 30, color="#B8E0DD", alpha=0.36, zorder=0)
    ax.bar(beta_edges[:-1], beta_counts, width=np.diff(beta_edges), align="edge", color=BLUE, edgecolor="white", linewidth=0.8, zorder=2)
    ax.axvline(-30, color=TEAL, ls=(0, (4, 2)), lw=1.15, zorder=3)
    ax.axvline(30, color=TEAL, ls=(0, (4, 2)), lw=1.15, zorder=3)
    ax.axvline(0, color="#77858D", lw=0.7, zorder=3)
    ax.set_xlim(-42, 42)
    ax.set_ylim(0, 31)
    ax.set_xlabel("交会角残差 eβ（°）")
    ax.set_ylabel("频数")
    ax.set_title("(a) eβ 分布", loc="left", color=INK, pad=9)
    _style_axis(ax)

    ax = axes[1]
    radius_edges = np.linspace(-2, 22, len(radius_counts) + 1)
    ax.bar(radius_edges[:-1], radius_counts, width=np.diff(radius_edges), align="edge", color=RED, edgecolor="white", linewidth=0.8, zorder=2)
    ax.axvline(0, color=TEAL, lw=1.25, zorder=3)
    ax.set_xlim(-3, 23)
    ax.set_ylim(0, 126)
    ax.set_xlabel("包围圆半径残差 e_r（m）")
    ax.set_ylabel("频数")
    ax.set_title("(b) e_r 分布", loc="left", color=INK, pad=9)
    _style_axis(ax)
    legend = [
        Patch(facecolor="#B8E0DD", edgecolor="none", label="直角邻域：|eβ| ≤ 30°"),
        Line2D([0], [0], color=TEAL, lw=1.25, label="e_r = 0"),
    ]
    fig.legend(handles=legend, loc="lower center", ncol=2, frameon=False, bbox_to_anchor=(0.5, -0.02), fontsize=9)
    fig.subplots_adjust(bottom=0.18, top=0.86, left=0.09, right=0.98)
    _save_png(fig, path)
    plt.close(fig)


def _intersection_angle(x: np.ndarray, y: np.ndarray, s1: tuple[float, float], s2: tuple[float, float]) -> np.ndarray:
    v1x, v1y = s1[0] - x, s1[1] - y
    v2x, v2y = s2[0] - x, s2[1] - y
    denominator = np.hypot(v1x, v1y) * np.hypot(v2x, v2y)
    cos_beta = np.divide(v1x * v2x + v1y * v2y, denominator, out=np.zeros_like(x), where=denominator > 1e-9)
    return np.degrees(np.arccos(np.clip(cos_beta, -1.0, 1.0)))


def draw_fig6(path: Path) -> None:
    """Redraw the analytical angle-residual field with only defined annotations."""
    s1 = (0.0, 0.0)
    theta = 35.0
    nominal = from_body(s1, theta, 850.0, 0.0)
    s2 = from_body(s1, theta, 850.0, 600.0)
    xv = np.linspace(-1200, 1600, 360)
    yv = np.linspace(-1100, 1600, 360)
    x, y = np.meshgrid(xv, yv)
    beta = _intersection_angle(x, y, s1, s2)
    residual = beta - 90.0
    near_station = (np.hypot(x - s1[0], y - s1[1]) < 45) | (np.hypot(x - s2[0], y - s2[1]) < 45)
    residual[near_station] = np.nan

    fig, ax = plt.subplots(figsize=(6.1, 6.1), layout="constrained")
    cmap = LinearSegmentedColormap.from_list("residual", ["#3269A8", "#F7F7F2", "#BF4A4A"])
    field = ax.pcolormesh(x, y, residual, shading="auto", cmap=cmap, norm=TwoSlopeNorm(vmin=-60, vcenter=0, vmax=60), alpha=0.96, zorder=0)
    ax.contour(x, y, residual, levels=[-30, 30], colors=ORANGE, linewidths=1.25, linestyles="--", zorder=2)

    for band in candidate_region(s1, theta):
        ax.add_patch(Polygon(band, closed=True, facecolor="#B6E1EE", edgecolor="#184F70", lw=1.35, alpha=0.50, zorder=3))
    center = ((s1[0] + s2[0]) / 2, (s1[1] + s2[1]) / 2)
    radius = math.dist(s1, s2) / 2
    ax.add_patch(plt.Circle(center, radius, fill=False, color=PURPLE, lw=1.65, ls=(0, (5, 2.8)), zorder=4))
    ax.scatter(*s1, marker="o", s=54, color=BLUE, edgecolor="white", linewidth=0.8, zorder=6)
    ax.scatter(*s2, marker="D", s=62, color=RED, edgecolor="white", linewidth=0.8, zorder=6)
    ax.scatter(*nominal, marker="*", s=158, color=PURPLE, edgecolor="white", linewidth=0.7, zorder=7)
    ax.annotate("S1", s1, xytext=(-26, 11), textcoords="offset points", color=INK, fontweight="bold")
    ax.annotate("S2", s2, xytext=(9, 9), textcoords="offset points", color=INK, fontweight="bold")
    ax.annotate("名义源", nominal, xytext=(10, -17), textcoords="offset points", color=INK, fontweight="bold")
    ax.set_xlim(-1200, 1600)
    ax.set_ylim(-1100, 1600)
    ax.set_aspect("equal")
    ax.set_xlabel("x（m）")
    ax.set_ylabel("y（m）")
    ax.set_title("交会角残差 eβ 的空间分布（第一示向 = 35°）", loc="left", color=INK, pad=10)
    ax.grid(color="white", lw=0.45, alpha=0.48)
    handles = [
        Patch(facecolor="#B6E1EE", edgecolor="#184F70", alpha=0.65, label="候选带"),
        Line2D([0], [0], color=PURPLE, lw=1.65, ls=(0, (5, 2.8)), label="β = 90° 轨迹"),
        Line2D([0], [0], color=ORANGE, lw=1.25, ls="--", label="|eβ| = 30°（60° / 120° 边界）"),
    ]
    ax.legend(handles=handles, loc="upper left", frameon=True, framealpha=0.96, facecolor="white", edgecolor="#C9D4DA", fontsize=8.4)
    cb = fig.colorbar(field, ax=ax, fraction=0.046, pad=0.03, ticks=[-60, -30, 0, 30, 60])
    cb.set_label("eβ（°）", color=INK)
    cb.outline.set_linewidth(0.6)
    _save_png(fig, path)
    plt.close(fig)


def draw_fig7(path: Path) -> None:
    """A comparison scorecard, deliberately without an irrelevant common axis."""
    rows = [
        ("真值包含率 / 残差带通过率", "100% / 100%", "100% / 100%"),
        ("中位交会角", "86.7°", "4.9°"),
        ("近共线比例", "0.0%", "81.2%"),
        ("两站即可清除", "33.2%", "4.0%"),
        ("补第三站后可清除", "100.0%", "65.5%"),
    ]
    fig, ax = plt.subplots(figsize=(11.2, 4.3))
    ax.set_axis_off()
    left, right, bottom, top = 0.05, 0.96, 0.10, 0.88
    widths = [0.42, 0.29, 0.29]
    x = [left, left + (right - left) * widths[0], left + (right - left) * (widths[0] + widths[1])]
    w = [(right - left) * value for value in widths]
    header_h = 0.16
    row_h = (top - bottom - header_h) / len(rows)
    headers = [("核验指标", "#EEF2F4"), ("正交推荐站", "#DCEAF7"), ("共线延伸站", "#F6E0E0")]
    for xi, wi, (label, color) in zip(x, w, headers):
        ax.add_patch(Rectangle((xi, top - header_h), wi, header_h, transform=ax.transAxes, facecolor=color, edgecolor="#B9C6CE", lw=0.8))
        ax.text(xi + wi / 2, top - header_h / 2, label, transform=ax.transAxes, ha="center", va="center", color=INK, fontsize=12, fontweight="bold")
    for i, (metric, orthogonal, collinear) in enumerate(rows):
        y = top - header_h - (i + 1) * row_h
        shade = "#FFFFFF" if i % 2 == 0 else "#F7F9FA"
        cells = [(metric, shade, INK, "left"), (orthogonal, "#F3F8FC", BLUE, "center"), (collinear, "#FDF5F5", RED, "center")]
        for xi, wi, (value, color, text_color, align) in zip(x, w, cells):
            ax.add_patch(Rectangle((xi, y), wi, row_h, transform=ax.transAxes, facecolor=color, edgecolor="#D5DEE3", lw=0.7))
            ax.text(xi + (0.025 if align == "left" else wi / 2), y + row_h / 2, value, transform=ax.transAxes, ha=align, va="center", color=text_color, fontsize=11.2 if align == "left" else 13, fontweight="bold" if align != "left" else "normal")
    ax.text(left, 0.96, "反演验证：正交推荐站与共线延伸站对照", transform=ax.transAxes, ha="left", va="top", color=INK, fontsize=14, fontweight="bold")
    ax.text(right, 0.96, "同一批 400 个真源", transform=ax.transAxes, ha="right", va="top", color=GREY, fontsize=9.5)
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    _save_png(fig, path)
    plt.close(fig)


def replace_media_and_captions(images: list[Path]) -> None:
    if not SRC_DOCX.exists():
        raise FileNotFoundError(SRC_DOCX)
    shutil.copy2(SRC_DOCX, DST_DOCX)
    doc = Document(DST_DOCX)
    if len(doc.inline_shapes) != 7:
        raise RuntimeError(f"Expected 7 inline figures, got {len(doc.inline_shapes)}")
    for shape, image in zip(list(doc.inline_shapes)[4:7], images):
        rel_id = shape._inline.graphic.graphicData.pic.blipFill.blip.embed
        doc.part.related_parts[rel_id]._blob = image.read_bytes()  # replace only the linked PNG, keep geometry/size
    captions = {
        "图 5  ±1° 示向扰动下的残差分布": "图 5  ±1° 示向扰动下的残差统计摘要",
        "图 7  反演验证：正交推荐站与共线延伸站对照": "图 7  反演验证：两种选址的交会质量与清除结果",
    }
    changed = set()
    for paragraph in doc.paragraphs:
        normalized = paragraph.text.replace("　", " ").strip()
        for old, new in captions.items():
            if normalized == old:
                paragraph.text = new
                changed.add(old)
    if changed != set(captions):
        missing = set(captions) - changed
        raise RuntimeError(f"Unable to locate caption(s): {sorted(missing)}")
    fig5_note = (
        "左图绿色竖虚线为 |eβ|=30° 的直角邻域边界；右图按 e_r≤0 与 e_r>0 汇总样本比例，"
        "并标注 e_r 中位数。样本 400 个，真源纵向在候选带区间内均匀抽取。"
    )
    fig6_note = (
        "填色为 eβ；紫色虚线圆以 S1S2 为直径，名义源落在该圆上；橙色虚线为 |eβ|=30° 的等值边界，"
        "蓝色半透明带为候选带。"
    )
    note_changes = 0
    for paragraph in doc.paragraphs:
        text = paragraph.text.replace("　", " ").strip()
        if "左图竖虚线为" in text and "样本 400 个" in text:
            paragraph.text = fig5_note
            note_changes += 1
        elif "填色为" in text and "候选带边界" in text:
            paragraph.text = fig6_note
            note_changes += 1
    if note_changes != 2:
        raise RuntimeError(f"Expected to update 2 figure notes, updated {note_changes}")
    doc.save(DST_DOCX)


def main() -> None:
    parser = argparse.ArgumentParser(description="重绘问题二图 5--7；默认仅输出 PNG。")
    parser.add_argument("--embed-docx", action="store_true", help="额外生成含替换图片的 Word 副本")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    fig5 = OUT / "fig5_residual_summary.png"
    fig6 = OUT / "fig6_angle_residual_map.png"
    fig7 = OUT / "fig7_inversion_comparison.png"
    draw_fig5(fig5)
    draw_fig6(fig6)
    draw_fig7(fig7)
    if args.embed_docx:
        replace_media_and_captions([fig5, fig6, fig7])
        print(DST_DOCX)
    for image in (fig5, fig6, fig7):
        print(image)


if __name__ == "__main__":
    main()
