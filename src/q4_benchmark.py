"""Deterministic local Q4 benchmark; never connects to the official simulator."""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import sys
from pathlib import Path
from typing import Any

from mock_sim import MockSim, Source
from robot_client import FnTransport, RobotClient
def _mix_sources(seed: int, n: int | None = None, n_dir: int | None = None) -> list[Source]:
    rng = random.Random(seed)
    if n is None:
        n = rng.randint(10, 16)
    if n_dir is None:
        n_dir = rng.randint(0, n)
    chs = rng.sample(range(1, 21), n)
    out: list[Source] = []
    for i, ch in enumerate(chs):
        r = 400.0 + math.sqrt(rng.random()) * 1300.0
        a = rng.random() * 2.0 * math.pi
        xy = (r * math.cos(a), r * math.sin(a))
        reff = rng.uniform(1000.0, 1500.0)
        heading = math.degrees(a) if i < n_dir else None
        out.append(Source(channel=ch, xy=xy, r_eff=reff, heading_deg=heading))
    return out


def _run_case(
    case_id: str,
    sources: list[Source],
    *,
    q4_outer_mode: str = "nn",
    dynamic_outer: bool = True,
    q4_profile: str = "v2",
) -> dict[str, Any]:
    robot_id = f"q4-benchmark-{case_id}-{q4_outer_mode}"
    sim = MockSim(robot_id=robot_id, sources=sources)
    bot = RobotClient(robot_id=robot_id, transport=FnTransport(sim.handle))
    from policy import HuntPolicy

    policy = HuntPolicy(
        bot,
        directional=True,
        q4_outer_mode=q4_outer_mode,
        q4_dynamic_outer=dynamic_outer,
        q4_profile=q4_profile,
    )
    stats = policy.run()
    n_dir = sum(1 for s in sources if s.heading_deg is not None)
    return {
        "case_id": case_id,
        "source_count": len(sources),
        "n_dir": n_dir,
        "n_omni": len(sources) - n_dir,
        "cleared": stats["cleared"],
        "all_cleared": stats["cleared"] == len(sources),
        "virtual_time_s": stats["virtual_time_s"],
        "travel_s": stats.get("travel_s"),
        "detect_s": stats.get("detect_s"),
        "clear_miss": stats.get("clear_miss"),
        "creep_calls": stats.get("creep_calls"),
        "q4_outer_r": stats.get("q4_outer_r"),
        "q4_outer_n": stats.get("q4_outer_n"),
        "q4_outer_fill_visits": stats.get("q4_outer_fill_visits"),
        "channels": stats["channels"],
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Local Q4 mock benchmark (no official simulator).")
    p.add_argument("--seeds", type=int, default=80, help="Number of random mixed cases")
    p.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "output" / "drill" / "q4-mock-summary.json",
    )
    p.add_argument(
        "--outer-mode",
        choices=("nn", "gain", "arc"),
        default="nn",
        help="Q4 outer ring visit order (default: nn)",
    )
    p.add_argument(
        "--compare",
        action="store_true",
        help="Run fixed 12x2100 vs dynamic outer on same seeds; write compare JSON",
    )
    p.add_argument(
        "--compare-profiles",
        action="store_true",
        help="Run dynamic_pure vs v2 on same seeds",
    )
    p.add_argument(
        "--profile",
        choices=("v2", "dynamic_pure"),
        default="v2",
        help="Q4 profile (default: v2)",
    )
    p.add_argument(
        "--fixed-outer",
        action="store_true",
        help="Always use 12x2100 (ignore /enter omni/dir profile)",
    )
    args = p.parse_args()

    def _summarize(tag: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
        misses = [r for r in rows if not r["all_cleared"]]
        vts = [r["virtual_time_s"] for r in rows]
        travels = [float(r["travel_s"]) for r in rows if r.get("travel_s") is not None]
        return {
            "tag": tag,
            "n": len(rows),
            "miss": len(misses),
            "mean_vt": statistics.mean(vts),
            "median_vt": statistics.median(vts),
            "p90_vt": sorted(vts)[max(0, int(0.9 * (len(vts) - 1)))],
            "mean_travel_s": statistics.mean(travels) if travels else None,
            "miss_cases": [{"case_id": m["case_id"], "cleared": m["cleared"], "n": m["source_count"]} for m in misses],
            "rows": rows,
        }

    def _print_summary(summary: dict[str, Any]) -> None:
        print(
            f"{summary['tag']}: miss={summary['miss']}  "
            f"mean_vt={summary['mean_vt']:.1f}  median={summary['median_vt']:.1f}  "
            f"p90={summary['p90_vt']:.1f}  travel={summary['mean_travel_s']:.1f}"
            if summary["mean_travel_s"] is not None
            else f"{summary['tag']}: miss={summary['miss']} mean_vt={summary['mean_vt']:.1f}"
        )

    dynamic = not args.fixed_outer

    if args.compare_profiles:
        seeds = list(range(args.seeds))
        pure_rows = [
            _run_case(f"seed-{i}", _mix_sources(i), q4_profile="dynamic_pure") for i in seeds
        ]
        v2_rows = [
            _run_case(f"seed-{i}", _mix_sources(i), q4_profile="v2") for i in seeds
        ]
        pure = _summarize("q4_dynamic_pure", pure_rows)
        v2 = _summarize("q4_dynamic_v2", v2_rows)
        compare = {
            "seeds": args.seeds,
            "dynamic_pure": {k: pure[k] for k in ("tag", "miss", "mean_vt", "median_vt", "p90_vt", "mean_travel_s")},
            "v2": {k: v2[k] for k in ("tag", "miss", "mean_vt", "median_vt", "p90_vt", "mean_travel_s")},
            "delta_mean_vt_v2_vs_pure": v2["mean_vt"] - pure["mean_vt"],
        }
        out = args.out.with_name("q4-dynamic-pure-vs-v2.json")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(compare, ensure_ascii=False, indent=2), encoding="utf-8")
        _print_summary(pure)
        _print_summary(v2)
        print(f"delta mean_vt (v2 - pure) = {compare['delta_mean_vt_v2_vs_pure']:+.1f}s")
        print("wrote", out)
        if pure["miss"] or v2["miss"]:
            sys.exit(1)
        return

    if args.compare:
        seeds = list(range(args.seeds))
        fixed_rows = [
            _run_case(f"seed-{i}", _mix_sources(i), dynamic_outer=False) for i in seeds
        ]
        dyn_rows = [
            _run_case(f"seed-{i}", _mix_sources(i), dynamic_outer=True) for i in seeds
        ]
        fixed = _summarize("q4_fixed_12x2100", fixed_rows)
        dyn = _summarize("q4_dynamic_outer", dyn_rows)
        lite = sum(1 for r in dyn_rows if r.get("q4_outer_n") == 11)
        compare = {
            "seeds": args.seeds,
            "fixed": {k: fixed[k] for k in ("tag", "miss", "mean_vt", "median_vt", "p90_vt", "mean_travel_s")},
            "dynamic": {k: dyn[k] for k in ("tag", "miss", "mean_vt", "median_vt", "p90_vt", "mean_travel_s")},
            "dynamic_lite_cases": lite,
            "delta_mean_vt": dyn["mean_vt"] - fixed["mean_vt"],
            "miss_delta": dyn["miss"] - fixed["miss"],
        }
        out = args.out if args.out.name != "q4-mock-summary.json" else args.out.with_name("q4-dynamic-outer-compare.json")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(compare, ensure_ascii=False, indent=2), encoding="utf-8")
        _print_summary(fixed)
        _print_summary(dyn)
        print(f"dynamic lite 11x1900 cases: {lite}/{args.seeds}")
        print(f"delta mean_vt (dynamic - fixed) = {compare['delta_mean_vt']:+.1f}s")
        print("wrote", out)
        if fixed["miss"] or dyn["miss"]:
            sys.exit(1)
        return

    tag = (
        f"q4_{args.profile}"
        if dynamic
        else f"q4_fixed_12x2100_{args.outer_mode}"
    )
    rows = [
        _run_case(
            f"seed-{i}",
            _mix_sources(i),
            q4_outer_mode=args.outer_mode,
            dynamic_outer=dynamic,
            q4_profile=args.profile,
        )
        for i in range(args.seeds)
    ]
    summary = _summarize(tag, rows)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    _print_summary(summary)
    print("wrote", args.out)
    if summary["miss"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
