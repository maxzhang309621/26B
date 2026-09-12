"""Side-by-side Q3 path GIF: baseline ring vs edge second-looks. Local mock only."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import animation
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import policy as policy_mod
from coverage import q3_waypoints
from figures.fig_q3_enroute_compare import (
    GREEN,
    GREY,
    INK,
    LIGHT,
    RED,
    UNK,
    _clone_sources,
    _draw_static,
    _pts,
)
from figures.fig_q3_path_gif import _events, _heading, _interpolate, _setup_font, _stops
from mock_sim import MockSim
from q3_benchmark import _random_sources
from robot_client import FnTransport, RobotClient
from runner_q3 import run_q3

OUT_GIF = ROOT.parent / "output" / "figures" / "q3_edge_second_compare.gif"
OUT_PNG = ROOT.parent / "output" / "figures" / "q3_edge_second_compare.png"


def _run(sources, label: str, edge_second: bool):
    saved = policy_mod.Q3_COVER_EDGE_SECOND
    try:
        policy_mod.Q3_COVER_EDGE_SECOND = edge_second
        rid = f"q3-edge-gif-{label}"
        sim = MockSim(robot_id=rid, sources=_clone_sources(sources))
        bot = RobotClient(robot_id=rid, transport=FnTransport(sim.handle))
        stats = run_q3(bot)
        frames = _interpolate(_stops(_events(bot.log)), step_m=80.0)
        return stats, frames
    finally:
        policy_mod.Q3_COVER_EDGE_SECOND = saved


def _pick_seed() -> int:
    """Prefer a seed where edge second-looks clearly cuts per-source time."""
    best = None
    for seed in range(24):
        sources = _random_sources(seed)
        st_off, _ = _run(sources, f"probe-off-{seed}", False)
        st_on, _ = _run(sources, f"probe-on-{seed}", True)
        if st_off["cleared"] != len(sources) or st_on["cleared"] != len(sources):
            continue
        delta = st_off["virtual_time_s"] / st_off["cleared"] - st_on["virtual_time_s"] / st_on[
            "cleared"
        ]
        recheck = int(st_on.get("route_rechecks") or 0) - int(st_off.get("route_rechecks") or 0)
        score = (delta, recheck, -st_on["virtual_time_s"] / st_on["cleared"])
        if best is None or score > best[0]:
            best = (score, seed)
        if delta >= 20.0 and recheck >= 2:
            return seed
    return best[1] if best is not None else 6


def main() -> None:
    _setup_font()
    mpl.rcParams["axes.unicode_minus"] = False
    picked = _pick_seed()
    sources = _random_sources(picked)
    st_old, fr_old = _run(sources, "old", False)
    st_new, fr_new = _run(sources, "new", True)
    src_by_ch = {s.channel: s for s in sources}
    wps = q3_waypoints()
    n = max(len(fr_old), len(fr_new))
    OUT_GIF.parent.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, 2, figsize=(12.8, 6.6), dpi=100)
    fig.suptitle(
        f"问题3 环上补二测对照  同一组源 seed={picked}（{len(sources)} 个）",
        fontsize=13,
        color=INK,
        y=0.98,
    )
    titles = [
        f"上一版：只在六边形顶点听\nVT {st_old['virtual_time_s']:.0f} s　"
        f"{st_old['virtual_time_s']/st_old['cleared']:.0f} s/源　"
        f"顶点复测 {st_old.get('route_rechecks', 0)}",
        f"当前：边上可二测就补听\nVT {st_new['virtual_time_s']:.0f} s　"
        f"{st_new['virtual_time_s']/st_new['cleared']:.0f} s/源　"
        f"边/点复测 {st_new.get('route_rechecks', 0)}",
    ]
    arts = []
    for ax, title in zip(axes, titles):
        _draw_static(ax, wps)
        ax.set_title(title, fontsize=10)
        trail, = ax.plot([], [], color="#4C72B0", lw=1.7, alpha=0.9, zorder=2)
        unk = ax.scatter([], [], s=42, c=UNK, edgecolors=GREY, zorder=5)
        heard = ax.scatter([], [], s=56, c=GREEN, edgecolors=INK, zorder=6)
        cleared = ax.scatter([], [], s=64, c=RED, edgecolors=INK, zorder=7)
        robot = ax.scatter([], [], s=58, c="#222222", marker="o", zorder=8)
        arrow = FancyArrowPatch(
            (0, 0), (1, 1), mutation_scale=10, color="#222222", lw=0, zorder=9
        )
        ax.add_patch(arrow)
        status = ax.text(
            0.02,
            0.98,
            "",
            transform=ax.transAxes,
            va="top",
            ha="left",
            fontsize=8,
            color=INK,
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.85, "pad": 2.5},
        )
        arts.append((trail, unk, heard, cleared, robot, arrow, status))

    handles = [
        Line2D([0], [0], color=LIGHT, ls="--", lw=1.4, label="六边形听点 6×1150 m"),
        Line2D([0], [0], color="#4C72B0", lw=1.6, label="行驶轨迹"),
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor=UNK,
            markeredgecolor=GREY,
            label="未发现",
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor=GREEN,
            markeredgecolor=INK,
            label="已检测",
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor=RED,
            markeredgecolor=INK,
            label="已清除",
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor="#222222",
            markeredgecolor="#222222",
            label="机器狗",
        ),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=6, frameon=False, fontsize=8)

    def apply(idx, fr, stats):
        trail, unk, heard, cleared, robot, arrow, status = arts[idx]
        trail.set_data([p[0] for p in fr["trail"]], [p[1] for p in fr["trail"]])
        u = set(src_by_ch) - fr["heard"] - fr["cleared"]
        h = fr["heard"] - fr["cleared"]
        unk.set_offsets(_pts(src_by_ch, u))
        heard.set_offsets(_pts(src_by_ch, h))
        cleared.set_offsets(_pts(src_by_ch, fr["cleared"]))
        robot.set_offsets([fr["xy"]])
        ang = _heading(fr["trail"])
        dx, dy = 80.0 * math.cos(ang), 80.0 * math.sin(ang)
        arrow.set_positions(fr["xy"], (fr["xy"][0] + dx, fr["xy"][1] + dy))
        status.set_text(
            f"{fr['action']}  |  {fr['vt']:.0f} s  |  已清 {len(fr['cleared'])}/{stats['cleared']}"
        )

    def update(i: int):
        apply(0, fr_old[min(i, len(fr_old) - 1)], st_old)
        apply(1, fr_new[min(i, len(fr_new) - 1)], st_new)
        return ()

    update(n - 1)
    fig.tight_layout(rect=(0.0, 0.07, 1.0, 0.93))
    fig.savefig(OUT_PNG, dpi=150, bbox_inches="tight", facecolor="white")
    anim = animation.FuncAnimation(fig, update, frames=n, interval=60, blit=False)
    anim.save(str(OUT_GIF), writer=animation.PillowWriter(fps=14))
    plt.close(fig)
    print(
        f"seed={picked} n={len(sources)} "
        f"old {st_old['virtual_time_s']:.1f}s / {st_old['virtual_time_s']/st_old['cleared']:.1f} "
        f"new {st_new['virtual_time_s']:.1f}s / {st_new['virtual_time_s']/st_new['cleared']:.1f} "
        f"recheck {st_old.get('route_rechecks')}→{st_new.get('route_rechecks')} "
        f"frames {len(fr_old)}/{len(fr_new)}"
    )
    print("wrote", OUT_GIF)
    print("wrote", OUT_PNG)


if __name__ == "__main__":
    main()
