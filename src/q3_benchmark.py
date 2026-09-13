"""Deterministic local Q3 benchmark; never connects to the official simulator."""

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
from runner_q3 import run_q3


def _random_sources(seed: int) -> list[Source]:
    rng = random.Random(seed)
    n = rng.randint(10, 16)
    channels = rng.sample(range(1, 21), n)
    sources: list[Source] = []
    for channel in channels:
        radius = math.sqrt(rng.random()) * 1800.0
        angle = rng.random() * 2.0 * math.pi
        sources.append(
            Source(
                channel=channel,
                xy=(radius * math.cos(angle), radius * math.sin(angle)),
                r_eff=rng.uniform(1000.0, 1500.0),
            )
        )
    return sources


def _boundary_sources() -> list[Source]:
    return [
        Source(
            channel=channel,
            xy=(
                1799.0 * math.cos(2.0 * math.pi * (channel - 1) / 16.0),
                1799.0 * math.sin(2.0 * math.pi * (channel - 1) / 16.0),
            ),
            r_eff=1000.0,
        )
        for channel in range(1, 17)
    ]


def _run_case(
    case_id: str,
    sources: list[Source],
    *,
    enable_step8_clear_ready_insertion: bool = False,
) -> dict[str, Any]:
    robot_id = f"q3-benchmark-{case_id}"
    sim = MockSim(robot_id=robot_id, sources=sources)
    bot = RobotClient(robot_id=robot_id, transport=FnTransport(sim.handle))
    stats = run_q3(
        bot,
        enable_step8_clear_ready_insertion=enable_step8_clear_ready_insertion,
    )
    direction_count = sum(
        rec["path"] == "/measure"
        and rec["response"].get("measure_result") == "direction"
        for rec in bot.log
    )
    measure_count = sum(rec["path"] == "/measure" for rec in bot.log)
    clear_count = sum(rec["path"] == "/clear" for rec in bot.log)
    move = stats.get("move_decomposition") or {}
    step8_insertions = list(stats.get("step8_insertions") or [])
    cleared = stats["cleared"]
    per_source = {}
    if cleared:
        per_source = {
            "travel_per_source": stats.get("travel_s", 0.0) / cleared,
            "localization_move_per_source": move.get("localization_s", 0.0) / cleared,
            "clear_detour_per_source": move.get("clear_detour_s", 0.0) / cleared,
            "service_move_per_source": (
                move.get("localization_s", 0.0) + move.get("clear_detour_s", 0.0)
            ) / cleared,
            "clear_miss_per_source": stats.get("clear_miss", 0) / cleared,
            "dedicated_localizations_per_source": stats.get("dedicated_localizations", 0) / cleared,
        }
    return {
        "case_id": case_id,
        "source_count": len(sources),
        "cleared": cleared,
        "all_cleared": stats["cleared"] == len(sources),
        "virtual_time_s": stats["virtual_time_s"],
        "action_count": len(bot.log),
        "measure_count": measure_count,
        "direction_count": direction_count,
        "clear_count": clear_count,
        "creep_calls": stats.get("creep_calls"),
        "creep_steps": stats.get("creep_steps"),
        "inconsistent_regions": stats.get("inconsistent_regions", 0),
        "route_rechecks": stats.get("route_rechecks", 0),
        "route_recheck_hits": stats.get("route_recheck_hits", 0),
        "deferred_channels": stats.get("deferred_channels", 0),
        "dedicated_localizations": stats.get("dedicated_localizations", 0),
        "localization_services": stats.get("localization_services", 0),
        "pending_at_exit": stats.get("pending_at_exit", 0),
        "travel_s": stats.get("travel_s"),
        "detect_s": stats.get("detect_s"),
        "switch_s": stats.get("switch_s"),
        "clear_ok_s": stats.get("clear_ok_s"),
        "clear_miss_s": stats.get("clear_miss_s"),
        "clear_ok": stats.get("clear_ok"),
        "clear_miss": stats.get("clear_miss"),
        "per_channel": stats.get("per_channel", {}),
        "clear_audit": stats.get("clear_audit", {}),
        "step8_insertion_enabled": stats.get("step8_insertion_enabled", False),
        "step8_insertions": step8_insertions,
        "step8_insertion_count": len(step8_insertions),
        "step8_insertion_successes": sum(
            item.get("status") == "success" for item in step8_insertions
        ),
        "step8_insertion_fallbacks": sum(
            item.get("status") == "fallback" for item in step8_insertions
        ),
        "step8_planned_delta_m": sum(
            float(item.get("delta_m") or 0.0) for item in step8_insertions
        ),
        "step8_pending_ready": stats.get("step8_pending_ready", []),
        "backbone_scan_s": move.get("backbone_scan_s"),
        "backbone_planned_s": move.get("backbone_planned_s"),
        "backbone_rejoin_s": move.get("backbone_rejoin_s"),
        "localization_s": move.get("localization_s"),
        "clear_detour_s": move.get("clear_detour_s"),
        **per_source,
        "invalid_action_count": sum(rec["response"].get("accepted") is not True for rec in bot.log),
        "exit_accepted": bot.log[-1]["path"] == "/exit" and bot.log[-1]["response"].get("accepted") is True,
        "channels": stats["channels"],
    }


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    pos = fraction * (len(ordered) - 1)
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return ordered[lo]
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo)


def _aggregate(cases: list[dict[str, Any]]) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "case_count": len(cases),
        "all_clear_cases": sum(case["all_cleared"] for case in cases),
        "failed_case_ids": [case["case_id"] for case in cases if not case["all_cleared"]],
    }
    for key in ("virtual_time_s", "action_count", "measure_count", "direction_count", "clear_count", "creep_calls", "creep_steps", "inconsistent_regions", "route_rechecks", "route_recheck_hits", "deferred_channels", "dedicated_localizations", "localization_services", "pending_at_exit", "invalid_action_count", "travel_s", "detect_s", "switch_s", "clear_ok_s", "clear_miss_s", "clear_ok", "clear_miss", "backbone_scan_s", "backbone_planned_s", "backbone_rejoin_s", "localization_s", "clear_detour_s", "travel_per_source", "localization_move_per_source", "clear_detour_per_source", "service_move_per_source", "clear_miss_per_source", "dedicated_localizations_per_source", "step8_insertion_count", "step8_insertion_successes", "step8_insertion_fallbacks", "step8_planned_delta_m"):
        values = [float(case[key]) for case in cases if case[key] is not None]
        metrics[key] = {
            "mean": statistics.fmean(values),
            "median": statistics.median(values),
            "p90": _percentile(values, 0.9),
            "max": max(values),
        }
    channel_totals: dict[str, dict[str, float]] = {}
    for case in cases:
        for ch, e in (case.get("per_channel") or {}).items():
            acc = channel_totals.setdefault(
                str(ch),
                {
                    "n_measure": 0.0,
                    "n_clear": 0.0,
                    "clear_ok": 0.0,
                    "clear_miss": 0.0,
                    "travel_s": 0.0,
                    "detect_s": 0.0,
                    "switch_s": 0.0,
                    "clear_s": 0.0,
                    "total_s": 0.0,
                },
            )
            for field in acc:
                acc[field] += float(e.get(field, 0.0))
    metrics["channel_totals"] = channel_totals
    audit_totals: dict[str, dict[str, float]] = {}
    for case in cases:
        for source, e in (case.get("clear_audit") or {}).items():
            acc = audit_totals.setdefault(
                source,
                {
                    "attempts": 0.0,
                    "success": 0.0,
                    "miss": 0.0,
                    "travel_s": 0.0,
                    "miss_travel_s": 0.0,
                },
            )
            for field in acc:
                acc[field] += float(e.get(field, 0.0))
    for source, acc in audit_totals.items():
        acc["attempts_per_case"] = acc["attempts"] / len(cases) if cases else 0.0
        acc["success_rate_pct"] = (
            100.0 * acc["success"] / acc["attempts"] if acc["attempts"] else 0.0
        )
    metrics["clear_audit_totals"] = audit_totals
    return metrics


def _paired_deltas(cases: list[dict[str, Any]], baseline_path: Path | None) -> dict[str, Any]:
    if baseline_path is None:
        return {}
    base_data = json.loads(baseline_path.read_text(encoding="utf-8"))
    base_cases = {case["case_id"]: case for case in base_data.get("cases", [])}
    keys = ("virtual_time_s", "travel_s", "action_count", "clear_miss", "dedicated_localizations")
    paired: dict[str, dict[str, float]] = {key: {} for key in keys}
    n_paired = 0
    for case in cases:
        base = base_cases.get(case["case_id"])
        if base is None:
            continue
        n_paired += 1
        for key in keys:
            if case.get(key) is None or base.get(key) is None:
                continue
            delta = float(case[key]) - float(base[key])
            paired[key][case["case_id"]] = delta
    summary: dict[str, dict[str, float]] = {}
    for key, deltas in paired.items():
        if not deltas:
            continue
        values = list(deltas.values())
        ordered = sorted(values)
        summary[key] = {
            "mean_delta": statistics.fmean(values),
            "median_delta": statistics.median(values),
            "p90_delta": _percentile(values, 0.9),
            "worst_delta": max(values),
            "candidate_better_share": sum(v < 0.0 for v in values) / len(values),
        }
    return {"baseline": str(baseline_path), "n_paired": n_paired, "deltas": paired, "summary": summary}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=int, default=100)
    parser.add_argument(
        "--seed-start",
        type=int,
        default=0,
        help="first deterministic local-mock seed; use a new range for development/locked evaluation",
    )
    parser.add_argument("--label", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, default=None, help="previous benchmark JSON for paired deltas")
    parser.add_argument(
        "--step8-clear-ready-insertion",
        action="store_true",
        help="explicitly enable the unaccepted Step 8 Q3 candidate",
    )
    args = parser.parse_args()
    if args.cases <= 0:
        parser.error("--cases must be positive")

    random_cases = [
        _run_case(
            f"seed-{seed}",
            _random_sources(seed),
            enable_step8_clear_ready_insertion=args.step8_clear_ready_insertion,
        )
        for seed in range(args.seed_start, args.seed_start + args.cases)
    ]
    boundary = _run_case(
        "boundary-16-r1799-reff1000",
        _boundary_sources(),
        enable_step8_clear_ready_insertion=args.step8_clear_ready_insertion,
    )
    result = {
        "question": "Q3",
        "suite": "local_mock_full_disk_v1",
        "label": args.label,
        "step8_clear_ready_insertion": args.step8_clear_ready_insertion,
        "seed_range": [args.seed_start, args.seed_start + args.cases - 1],
        "python": sys.version,
        "formal_test": False,
        "random_summary": _aggregate(random_cases),
        "boundary_case": boundary,
        "paired_vs_baseline": _paired_deltas(random_cases, args.baseline),
        "cases": random_cases,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "label": args.label,
        "random_summary": result["random_summary"],
        "boundary_case": boundary,
        "output": str(args.output),
    }, ensure_ascii=False, indent=2))
    random_ok = (
        result["random_summary"]["all_clear_cases"] == args.cases
        and result["random_summary"]["pending_at_exit"]["max"] == 0
        and result["random_summary"]["invalid_action_count"]["max"] == 0
        and all(case["exit_accepted"] for case in random_cases)
    )
    boundary_ok = (
        boundary["all_cleared"]
        and boundary["pending_at_exit"] == 0
        and boundary["invalid_action_count"] == 0
        and boundary["exit_accepted"]
    )
    return 0 if random_ok and boundary_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
