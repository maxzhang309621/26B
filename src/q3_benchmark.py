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


def _run_case(case_id: str, sources: list[Source]) -> dict[str, Any]:
    robot_id = f"q3-benchmark-{case_id}"
    sim = MockSim(robot_id=robot_id, sources=sources)
    bot = RobotClient(robot_id=robot_id, transport=FnTransport(sim.handle))
    stats = run_q3(bot)
    direction_count = sum(
        rec["path"] == "/measure"
        and rec["response"].get("measure_result") == "direction"
        for rec in bot.log
    )
    measure_count = sum(rec["path"] == "/measure" for rec in bot.log)
    clear_count = sum(rec["path"] == "/clear" for rec in bot.log)
    return {
        "case_id": case_id,
        "source_count": len(sources),
        "cleared": stats["cleared"],
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
    for key in ("virtual_time_s", "action_count", "measure_count", "direction_count", "clear_count", "creep_calls", "creep_steps", "inconsistent_regions", "route_rechecks", "route_recheck_hits", "deferred_channels", "dedicated_localizations", "localization_services", "pending_at_exit", "invalid_action_count"):
        values = [float(case[key]) for case in cases if case[key] is not None]
        metrics[key] = {
            "mean": statistics.fmean(values),
            "median": statistics.median(values),
            "p90": _percentile(values, 0.9),
            "max": max(values),
        }
    return metrics


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=int, default=100)
    parser.add_argument("--label", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    random_cases = [_run_case(f"seed-{seed}", _random_sources(seed)) for seed in range(args.cases)]
    boundary = _run_case("boundary-16-r1799-reff1000", _boundary_sources())
    result = {
        "question": "Q3",
        "suite": "local_mock_full_disk_v1",
        "label": args.label,
        "seed_range": [0, args.cases - 1],
        "python": sys.version,
        "formal_test": False,
        "random_summary": _aggregate(random_cases),
        "boundary_case": boundary,
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
