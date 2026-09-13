"""Plot official-practice trajectories captured in local drill logs.

The official ``.jlog`` / ``.psum`` files are encrypted; the drill JSON files in
``output/drill/`` are the local HTTP logs of the same practice runs and contain
every action position, channel and result.  This script renders reference route
maps: trajectory coloured by virtual time, measure points, clear successes and
misses, arena boundary and the search rings used by the run's scheme.

With ``--behavior-dir`` the script reads the plaintext header of each official
``.jlog`` (export timestamp + case code) and its sibling ``.result.json``
(jammer count), then matches each drill run by its ``/exit`` timestamp so the
plot title carries the official case code and the true jammer count.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402

ARENA_R = 1800.0
JLOG_MARK = b'{"package_type"'


def load_drill(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def jlog_header(path: Path) -> dict | None:
    raw = path.read_bytes()
    i = raw.find(JLOG_MARK)
    if i < 0:
        return None
    try:
        obj, _ = json.JSONDecoder().raw_decode(raw[i:].decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        return None
    return obj


def official_index(behavior_dir: Path) -> list[dict]:
    out: list[dict] = []
    for jlog in sorted(behavior_dir.glob("*.jlog")):
        h = jlog_header(jlog)
        if not h:
            continue
        result = jlog.with_suffix(".result.json")
        jammers = None
        if result.exists():
            try:
                jammers = json.loads(result.read_text(encoding="utf-8")).get("jammer_count")
            except json.JSONDecodeError:
                jammers = None
        out.append(
            {
                "stem": jlog.stem,
                "problem": str(h.get("problem_no")),
                "case_code": h.get("case_code"),
                "created_at": h.get("created_at_utc"),
                "jammers": jammers,
            }
        )
    return out


def exit_ms(d: dict) -> float | None:
    for rec in reversed(d.get("log", [])):
        if rec.get("path") == "/exit":
            ms = (rec.get("response") or {}).get("real_timestamp_ms")
            return float(ms) if ms else None
    return None


def match_official(d: dict, index: list[dict]) -> dict | None:
    ms = exit_ms(d)
    if ms is None:
        return None
    t = datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)
    best: tuple[float, dict] | None = None
    for entry in index:
        if entry["problem"] != str(d.get("problem")) or not entry["created_at"]:
            continue
        created = datetime.fromisoformat(entry["created_at"].replace("Z", "+00:00"))
        diff = abs((created - t).total_seconds())
        if best is None or diff < best[0]:
            best = (diff, entry)
    if best is None or best[0] > 10.0:
        return None
    return best[1]


def actions(d: dict) -> list[dict]:
    out: list[dict] = []
    for rec in d.get("log", []):
        p = rec.get("path")
        if p not in ("/measure", "/clear"):
            continue
        req = rec.get("request") or {}
        pos = req.get("position")
        resp = rec.get("response") or {}
        if not pos or resp.get("accepted") is not True:
            continue
        out.append(
            {
                "kind": p[1:],
                "x": float(pos["x"]),
                "y": float(pos["y"]),
                "ch": int(req.get("channel") or 0),
                "vt": float(resp.get("virtual_time_s") or 0.0),
                "result": resp.get("clear_result") if p == "/clear" else resp.get("measure_result"),
            }
        )
    return out


def rings_from_stats(stats: dict, problem: str) -> list[tuple[float, int, str]]:
    rings: list[tuple[float, int, str]] = []
    if problem == "3":
        n = stats.get("q3_ring_n")
        r = stats.get("q3_ring_r")
        if isinstance(n, int) and isinstance(r, (int, float)):
            rings.append((float(r), int(n), "search ring"))
        else:
            rings.append((1200.0, 8, "search ring (legacy)"))
    else:
        inn = stats.get("q4_inner_n")
        ir = stats.get("q4_inner_r")
        on = stats.get("q4_outer_n")
        orr = stats.get("q4_outer_r")
        rings.append(
            (float(ir), int(inn), "inner ring")
            if isinstance(inn, int) and isinstance(ir, (int, float))
            else (1200.0, 8, "inner ring (legacy)")
        )
        rings.append(
            (float(orr), int(on), "outer ring")
            if isinstance(on, int) and isinstance(orr, (int, float))
            else (2100.0, 12, "outer ring (legacy)")
        )
    return rings


def plot_case(path: Path, outdir: Path, case: dict | None = None) -> tuple[Path, dict]:
    d = load_drill(path)
    stats = d.get("stats", {})
    problem = str(d.get("problem"))
    acts = actions(d)
    if not acts:
        raise ValueError(f"no accepted actions in {path}")

    pts = [(0.0, 0.0)] + [(a["x"], a["y"]) for a in acts]
    vts = [0.0] + [a["vt"] for a in acts]
    segs = np.array(
        [[pts[i], pts[i + 1]] for i in range(len(pts) - 1)], dtype=float
    )
    seg_vt = np.array([(vts[i] + vts[i + 1]) / 2.0 for i in range(len(vts) - 1)])

    fig, ax = plt.subplots(figsize=(9.5, 9.5), dpi=150)
    ax.add_patch(plt.Circle((0.0, 0.0), ARENA_R, fill=False, color="0.75", lw=1.2, zorder=1))
    for radius, n, label in rings_from_stats(stats, problem):
        ax.add_patch(
            plt.Circle((0.0, 0.0), radius, fill=False, color="0.55", lw=1.0, ls="--", zorder=1)
        )
        for k in range(n):
            a = 2.0 * np.pi * k / n
            ax.plot(
                radius * np.cos(a),
                radius * np.sin(a),
                marker="s",
                ms=3.5,
                color="0.45",
                zorder=2,
            )
        ax.plot([], [], color="0.55", ls="--", lw=1.0, label=f"{label} r={radius:.0f} m, n={n}")

    norm = plt.Normalize(vmin=float(np.min(seg_vt)), vmax=float(np.max(seg_vt)))
    lc = LineCollection(segs, cmap="viridis", norm=norm, linewidths=1.1, zorder=3, alpha=0.9)
    lc.set_array(seg_vt)
    ax.add_collection(lc)
    cbar = fig.colorbar(lc, ax=ax, fraction=0.046, pad=0.03, shrink=0.85)
    cbar.set_label("virtual time (s)")

    mx = [a["x"] for a in acts if a["kind"] == "measure"]
    my = [a["y"] for a in acts if a["kind"] == "measure"]
    ax.scatter(mx, my, s=5, color="tab:blue", alpha=0.45, zorder=4, label="measure stops")

    okx = [a["x"] for a in acts if a["kind"] == "clear" and a["result"] == "success"]
    oky = [a["y"] for a in acts if a["kind"] == "clear" and a["result"] == "success"]
    ax.scatter(
        okx, oky, s=130, marker="*", color="tab:green", edgecolor="k", linewidths=0.4,
        zorder=6, label=f"clear success ({len(okx)})",
    )
    msx = [a["x"] for a in acts if a["kind"] == "clear" and a["result"] != "success"]
    msy = [a["y"] for a in acts if a["kind"] == "clear" and a["result"] != "success"]
    if msx:
        ax.scatter(msx, msy, s=42, marker="x", color="tab:red", linewidths=1.2, zorder=6, label=f"clear miss ({len(msx)})")

    ax.scatter([0.0], [0.0], marker="s", s=70, color="black", zorder=7, label="origin")

    all_x = [p[0] for p in pts]
    all_y = [p[1] for p in pts]
    lim = max(ARENA_R + 250.0, max(abs(v) for v in all_x + all_y) + 150.0)
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.set_aspect("equal")
    ax.grid(True, color="0.92", lw=0.6)
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")

    vt = float(stats.get("virtual_time_s") or acts[-1]["vt"])
    cleared = stats.get("cleared")
    avg = stats.get("avg_clear_s")
    scheme = d.get("scheme") or stats.get("q3_path_profile") or stats.get("q4_path_profile") or "-"
    if case and case.get("jammers"):
        ratio = f" ({100.0 * float(cleared) / float(case['jammers']):.0f}%)"
        line1 = f"official case {case['case_code']} | jammers={case['jammers']} | cleared={cleared}{ratio}"
    elif case:
        line1 = f"official case {case['case_code']} | cleared={cleared}"
    else:
        line1 = f"cleared={cleared}"
    ax.set_title(
        f"{path.stem}\n{line1}\nP{problem} | scheme={scheme} | vt={vt:.1f} s | avg={avg:.1f} s",
        fontsize=10.5,
    )
    ax.legend(loc="lower right", fontsize=8, framealpha=0.9)

    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / f"{path.stem}.png"
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)
    info = {
        "plot": str(out),
        "drill": str(path),
        "problem": problem,
        "scheme": scheme,
        "virtual_time_s": vt,
        "cleared": cleared,
        "avg_clear_s": avg,
        "clear_miss": sum(1 for a in acts if a["kind"] == "clear" and a["result"] != "success"),
        "official_case_code": case.get("case_code") if case else None,
        "official_jammers": case.get("jammers") if case else None,
    }
    return out, info


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("logs", nargs="+", type=Path)
    parser.add_argument(
        "--outdir",
        type=Path,
        default=Path("output/figures/official_routes"),
    )
    parser.add_argument(
        "--behavior-dir",
        type=Path,
        default=None,
        help="JammersSimulatorData/behavior-logs; enables official case matching",
    )
    args = parser.parse_args()

    index = official_index(args.behavior_dir) if args.behavior_dir else []
    records: list[dict] = []
    for log in args.logs:
        d = load_drill(log)
        case = match_official(d, index) if index else None
        out, info = plot_case(log, args.outdir, case)
        records.append(info)
        print(out)
    if records:
        index_path = args.outdir / "index.json"
        index_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        print(index_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
