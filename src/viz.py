"""Paper figures for intersection, candidate bands, and coverage waypoints."""

from __future__ import annotations

from pathlib import Path

from geometry import Point, intersect_cones
from candidate import candidate_region, recommend_second
from coverage import directional_waypoints, omni_waypoints


def _setup_font() -> None:
    import matplotlib.pyplot as plt
    from matplotlib import font_manager

    for name in ("Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Source Han Sans SC"):
        if any(name.lower() in f.name.lower() for f in font_manager.fontManager.ttflist):
            plt.rcParams["font.sans-serif"] = [name, "DejaVu Sans"]
            plt.rcParams["axes.unicode_minus"] = False
            return


def _save(fig, path: Path) -> None:
    _setup_font()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160, bbox_inches="tight")


def plot_intersection(out: Path) -> None:
    import matplotlib.pyplot as plt

    s1, s2 = (0.0, 0.0), (400.0, 0.0)
    g = (200.0, 300.0)
    import math

    th1 = math.degrees(math.atan2(g[1] - s1[1], g[0] - s1[0]))
    th2 = math.degrees(math.atan2(g[1] - s2[1], g[0] - s2[0]))
    res = intersect_cones([s1, s2], [th1, th2])
    fig, ax = plt.subplots(figsize=(6, 5))
    if res.vertices:
        xs = [p[0] for p in res.vertices] + [res.vertices[0][0]]
        ys = [p[1] for p in res.vertices] + [res.vertices[0][1]]
        ax.fill(xs, ys, alpha=0.35, label="定位区")
        ax.plot(xs, ys)
    ax.scatter([s1[0], s2[0], g[0]], [s1[1], s2[1], g[1]], c=["C0", "C0", "C3"])
    ax.set_aspect("equal")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_title("两站交会定位区")
    ax.legend()
    _save(fig, out)
    plt.close(fig)


def plot_candidate(out: Path) -> None:
    import matplotlib.pyplot as plt

    s1 = (0.0, 0.0)
    th = 35.0
    bands = candidate_region(s1, th)
    s2 = recommend_second(s1, th)
    fig, ax = plt.subplots(figsize=(6, 5))
    circ = plt.Circle((0, 0), 1800, fill=False, linestyle="--")
    ax.add_patch(circ)
    for band in bands:
        xs = [p[0] for p in band] + [band[0][0]]
        ys = [p[1] for p in band] + [band[0][1]]
        ax.fill(xs, ys, alpha=0.3)
    ax.scatter([s1[0], s2[0]], [s1[1], s2[1]])
    ax.set_aspect("equal")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_title("第二检测点候选带")
    _save(fig, out)
    plt.close(fig)


def plot_waypoints(out: Path) -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.add_patch(plt.Circle((0, 0), 1800, fill=False, linestyle="--"))
    omni = omni_waypoints()
    dire = directional_waypoints()
    ax.scatter([p[0] for p in dire], [p[1] for p in dire], s=12, label="问题4 航路")
    ax.scatter([p[0] for p in omni], [p[1] for p in omni], s=28, label="问题3 航路")
    ax.set_aspect("equal")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_title("覆盖航路点")
    ax.legend()
    _save(fig, out)
    plt.close(fig)


def write_all(out_dir: Path) -> list[Path]:
    paths = [
        out_dir / "q1_intersection.png",
        out_dir / "q2_candidate.png",
        out_dir / "coverage_waypoints.png",
    ]
    plot_intersection(paths[0])
    plot_candidate(paths[1])
    plot_waypoints(paths[2])
    return paths
