"""Same sources, old large optical grid vs gated grid. Local mock only."""

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

OUT_GIF = ROOT.parent / "output" / "figures" / "q3_optical_compare.gif"
OUT_PNG = ROOT.parent / "output" / "figures" / "q3_optical_compare.png"

_KEYS = (
    "OPTICAL_GRID_MAX_CELLS",
    "OPTICAL_GRID_MAX_TRIES",
    "OPTICAL_GRID_MAX_SEC_R",
    "OPTICAL_GRID_ABORT_MISSES",
)
# Left panel = the gated grid the user just watched (still some local dither).
_GATED = {
    "OPTICAL_GRID_MAX_CELLS": 16,
    "OPTICAL_GRID_MAX_TRIES": 4,
    "OPTICAL_GRID_MAX_SEC_R": 45.0,
    "OPTICAL_GRID_ABORT_MISSES": 2,
}


def _opt_stats(st: dict) -> tuple[int, int]:
    audit = (st.get("clear_audit") or {}).get("optical_grid") or {}
    return int(audit.get("attempts") or 0), int(audit.get("miss") or 0)


def _bearing_multi(self, ch, obs):
    fixes = sorted(policy_mod._best_fixes(obs), key=lambda q: policy_mod.dist(self.bot.position, q))
    for q in fixes:
        if self._try_clear(q, ch, charge=False, source="bearing"):
            return True
    return False


def _run(sources, label: str, gated_old: bool):
    saved = {k: getattr(policy_mod, k) for k in _KEYS}
    orig_bearing = policy_mod.HuntPolicy._try_bearing_clears
    try:
        if gated_old:
            for k, v in _GATED.items():
                setattr(policy_mod, k, v)
            policy_mod.HuntPolicy._try_bearing_clears = _bearing_multi
        rid = f"q3-opt-gif-{label}"
        sim = MockSim(robot_id=rid, sources=_clone_sources(sources))
        bot = RobotClient(robot_id=rid, transport=FnTransport(sim.handle))
        stats = run_q3(bot)
        frames = _interpolate(_stops(_events(bot.log)), step_m=80.0)
        return stats, frames
    finally:
        for k, v in saved.items():
            setattr(policy_mod, k, v)
        policy_mod.HuntPolicy._try_bearing_clears = orig_bearing


def main() -> None:
    _setup_font()
    mpl.rcParams["axes.unicode_minus"] = False
    seed = 6
    sources = _random_sources(seed)
    st_old, fr_old = _run(sources, "gated", True)
    st_new, fr_new = _run(sources, "tight", False)
    att_o, miss_o = _opt_stats(st_old)
    att_n, miss_n = _opt_stats(st_new)
    src_by_ch = {s.channel: s for s in sources}
    wps = q3_waypoints()
    n = max(len(fr_old), len(fr_new))
    OUT_GIF.parent.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, 2, figsize=(12.8, 6.6), dpi=100)
    fig.suptitle(
        f"问题3 折返对照  同一组源 seed={seed}（{len(sources)} 个）",
        fontsize=13,
        color=INK,
        y=0.98,
    )
    titles = [
        f"上一版：门控网格（仍可连试多交点）\n"
        f"VT {st_old['virtual_time_s']:.0f} s　{st_old['virtual_time_s']/st_old['cleared']:.0f} s/源\n"
        f"网格 {att_o} 次 / miss {miss_o}",
        f"当前：只试最近交点，网格最多 1 格\n"
        f"VT {st_new['virtual_time_s']:.0f} s　{st_new['virtual_time_s']/st_new['cleared']:.0f} s/源\n"
        f"网格 {att_n} 次 / miss {miss_n}",
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
        arrow = FancyArrowPatch((0, 0), (1, 1), mutation_scale=10, color="#222222", lw=0, zorder=9)
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
        Line2D([0], [0], marker="o", color="w", markerfacecolor=UNK, markeredgecolor=GREY, label="未发现"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=GREEN, markeredgecolor=INK, label="已检测"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=RED, markeredgecolor=INK, label="已清除"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#222222", markeredgecolor="#222222", label="机器狗"),
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
    fig.tight_layout(rect=(0.0, 0.07, 1.0, 0.90))
    fig.savefig(OUT_PNG, dpi=150, bbox_inches="tight", facecolor="white")
    anim = animation.FuncAnimation(fig, update, frames=n, interval=55, blit=False)
    anim.save(str(OUT_GIF), writer=animation.PillowWriter(fps=14))
    plt.close(fig)
    print(
        f"seed={seed} old {st_old['virtual_time_s']:.1f}s {st_old['virtual_time_s']/st_old['cleared']:.1f}/src "
        f"opt {att_o}/{miss_o}  new {st_new['virtual_time_s']:.1f}s "
        f"{st_new['virtual_time_s']/st_new['cleared']:.1f}/src opt {att_n}/{miss_n}"
    )
    print("wrote", OUT_GIF)
    print("wrote", OUT_PNG)


if __name__ == "__main__":
    main()
