"""Figure 21: high-resolution Q3 drill-route triptych from recorded drill logs."""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "figures"))
import fig_q4_drill_routes as route_figure  # noqa: E402
from fig_q4_drill_routes import _draw_panel, _legend_handles  # noqa: E402
from drill_viz import _setup_font, load_drill  # noqa: E402

OUT = Path(__file__).resolve().parent / "revised_assets" / "figure21_revised"
DRILL = ROOT / "output" / "drill"
CASES = [
    ("p3-20260912-130724.json", "(a) 十六源（最多）"),
    ("p3-20260912-135118.json", "(b) 十三源（多数）"),
    ("p3-20260912-135150.json", "(c) 十一源（少数）"),
]


def _draw_panel_with_q3_labels(ax, scene, fig) -> None:
    """Use the original geometry while keeping source labels out of the map."""
    original_place = route_figure._place_labels

    def place_without_prefix(axis, items, canvas, obstacles, fontsize=7.0):
        # Source categories are already in the per-panel legend.  At this
        # final display size, individual channel labels collide in dense
        # clusters; omit them rather than leaving a pseudo-readable overlap.
        return []

    route_figure._place_labels = place_without_prefix
    try:
        _draw_panel(ax, scene, fig)
    finally:
        route_figure._place_labels = original_place


def main() -> None:
    _setup_font()
    plt.rcParams["savefig.bbox"] = None
    plt.rcParams["savefig.pad_inches"] = 0.0
    # Match the original Word container exactly: 6.98 in x 2.45 in.
    fig, axes = plt.subplots(1, 3, figsize=(6.98, 2.45), dpi=600)
    fig.subplots_adjust(left=0.045, right=0.995, bottom=0.12, top=0.84, wspace=0.22)
    for ax, (filename, title) in zip(axes, CASES):
        _draw_panel_with_q3_labels(ax, load_drill(DRILL / filename), fig)
        ax.set_title(title, fontsize=5.5, pad=2)
        ax.tick_params(labelsize=4.0, length=1.5)
        ax.set_xlabel("x (m)", fontsize=4.4, labelpad=1)
        ax.set_ylabel("y (m)", fontsize=4.4, labelpad=1)
        # Keep the original per-panel key; a shared eight-item key overprints
        # a short, three-panel canvas.
        ax.legend(handles=_legend_handles(), loc="lower right", frameon=True,
                  fontsize=3.0, borderpad=0.25, labelspacing=0.18,
                  handlelength=1.0, handletextpad=0.3, markerscale=0.55)
        for text in ax.texts:
            if text.get_text().startswith("已清除："):
                text.set_fontsize(4.2)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(OUT) + ".png", dpi=600, facecolor="white", bbox_inches=None)
    fig.savefig(str(OUT) + ".pdf", facecolor="white", bbox_inches=None)
    fig.savefig(str(OUT) + ".svg", facecolor="white", bbox_inches=None)
    plt.close(fig)
    print("wrote", OUT.with_suffix(".png"))


if __name__ == "__main__":
    main()
