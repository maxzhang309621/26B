"""Analyze the latest ten downloaded Q3 practice runs without invoking the simulator.

Inputs are immutable local copies of official result metadata and plaintext action
replays. Outputs are diagnostic CSV/JSON/PNG files. The post-hoc shortest path uses
successful clear positions and is an oracle lower bound only, never an online input.
"""

from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "output" / "drill"
RESULT_DIR = ROOT / "Jammers-simulator" / "JammersSimulatorData" / "behavior-logs"
OUT = ROOT / "results" / "Q3" / "reports" / "scan_first_official_20260912"
UTC8 = timezone(timedelta(hours=8))


def parse_utc(value: str) -> datetime:
    """Parse official UTC timestamps whose fractional part has 1--6 digits."""
    text = value[:-1] if value.endswith("Z") else value
    if "." in text:
        whole, fraction = text.split(".", 1)
        text = f"{whole}.{fraction[:6].ljust(6, '0')}"
    return datetime.fromisoformat(text + "+00:00")


def distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def open_path_oracle(start: tuple[float, float], points: list[tuple[float, float]]) -> float:
    """Exact open path through post-hoc successful clear positions (diagnostic only)."""
    n = len(points)
    if not n:
        return 0.0
    pair = [[distance(a, b) for b in points] for a in points]
    dp: dict[tuple[int, int], float] = {
        (1 << i, i): distance(start, point) for i, point in enumerate(points)
    }
    for mask in range(1, 1 << n):
        for j in range(n):
            base = dp.get((mask, j))
            if base is None:
                continue
            for k in range(n):
                if mask & (1 << k):
                    continue
                key = (mask | (1 << k), k)
                candidate = base + pair[j][k]
                if candidate < dp.get(key, math.inf):
                    dp[key] = candidate
    full = (1 << n) - 1
    return min(dp[(full, j)] for j in range(n))


def latest_official_results() -> list[tuple[Path, dict]]:
    rows: list[tuple[datetime, Path, dict]] = []
    for path in RESULT_DIR.glob("practice-p3-*.result.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        ended = parse_utc(payload["ended_at_utc"])
        rows.append((ended, path, payload))
    rows.sort(key=lambda item: item[0])
    return [(path, payload) for _, path, payload in rows[-10:]]


def match_replay(local_end: datetime) -> Path:
    candidates: list[tuple[float, Path]] = []
    for path in LOG_DIR.glob(f"p3-{local_end:%Y%m%d}-*.json"):
        stamp = datetime.strptime(path.stem[3:], "%Y%m%d-%H%M%S").replace(tzinfo=UTC8)
        candidates.append((abs((stamp - local_end).total_seconds()), path))
    if not candidates:
        raise FileNotFoundError(f"No plaintext Q3 replay on {local_end:%Y-%m-%d}")
    delta_s, path = min(candidates, key=lambda item: (item[0], item[1].name))
    if delta_s > 2.0:
        raise FileNotFoundError(f"Nearest Q3 replay is {delta_s:.3f}s away from {local_end.isoformat()}")
    return path


def read_action_events(payload: dict) -> list[dict]:
    events: list[dict] = []
    for event in payload["log"]:
        action = event.get("path")
        pos = event.get("request", {}).get("position")
        if action not in {"/measure", "/clear"} or not isinstance(pos, dict):
            continue
        response = event.get("response", {})
        events.append(
            {
                "action": action[1:],
                "point": (float(pos["x"]), float(pos["y"])),
                "channel": int(event["request"]["channel"]),
                "time_s": float(response["virtual_time_s"]),
                "measure_result": response.get("measure_result"),
                "clear_result": response.get("clear_result"),
            }
        )
    return events


def path_length(events: list[dict], start: tuple[float, float]) -> float:
    total = 0.0
    previous = start
    for event in events:
        total += distance(previous, event["point"])
        previous = event["point"]
    return total


def analyze_case(result_path: Path, official: dict) -> dict:
    local_end = parse_utc(official["ended_at_utc"]).astimezone(UTC8)
    log_path = match_replay(local_end)
    replay = json.loads(log_path.read_text(encoding="utf-8"))
    stats = replay["stats"]
    if int(stats["cleared"]) != int(official["jammer_count"]):
        raise ValueError(f"cleared/jammer_count mismatch for {log_path.name}")
    events = read_action_events(replay)
    first_clear = next(i for i, event in enumerate(events) if event["action"] == "clear")
    scan = events[:first_clear]
    service = events[first_clear:]
    scan_end = scan[-1]["point"]

    service_distance = path_length(service, scan_end)
    successes: list[tuple[float, float]] = []
    seen_channels: set[int] = set()
    for event in service:
        if event["action"] == "clear" and event["clear_result"] == "success":
            if event["channel"] not in seen_channels:
                seen_channels.add(event["channel"])
                successes.append(event["point"])
    success_order_distance = sum(
        distance(scan_end if i == 0 else successes[i - 1], point)
        for i, point in enumerate(successes)
    )
    oracle = open_path_oracle(scan_end, successes)
    move = stats["move_decomposition"]
    movement = float(move["backbone_scan_s"] + move["localization_s"] + move["clear_detour_s"])
    nonmovement = float(stats["virtual_time_s"] - movement)
    unique_scan_points = len({(round(e["point"][0], 6), round(e["point"][1], 6)) for e in scan})
    max_service_leg = 0.0
    previous = scan_end
    for event in service:
        max_service_leg = max(max_service_leg, distance(previous, event["point"]))
        previous = event["point"]

    return {
        "log_path": log_path,
        "result_path": result_path,
        "official": official,
        "events": events,
        "first_clear": first_clear,
        "scan_end": scan_end,
        "N": int(stats["cleared"]),
        "T_s": float(stats["virtual_time_s"]),
        "T_per_N_s": float(stats["avg_clear_s"]),
        "travel_s": float(stats["travel_s"]),
        "detect_s": float(stats["detect_s"]),
        "switch_s": float(stats["switch_s"]),
        "clear_ok_s": float(stats["clear_ok_s"]),
        "clear_miss_s": float(stats["clear_miss_s"]),
        "n_measure": int(stats["n_measure"]),
        "n_clear": int(stats["n_clear"]),
        "clear_miss": int(stats["clear_miss"]),
        "pending_at_exit": int(stats["pending_at_exit"]),
        "exit_accepted": bool(stats["exit_accepted"]),
        "completed": bool(stats["completed"]),
        "q3_path_profile": stats.get("q3_path_profile"),
        "backbone_scan_s": float(move["backbone_scan_s"]),
        "localization_s": float(move["localization_s"]),
        "clear_detour_s": float(move["clear_detour_s"]),
        "nonmovement_s": nonmovement,
        "scan_phase_end_s": float(scan[-1]["time_s"]),
        "service_phase_s": float(stats["virtual_time_s"] - scan[-1]["time_s"]),
        "measures_before_first_clear": first_clear,
        "unique_scan_points": unique_scan_points,
        "service_path_m": service_distance,
        "max_service_leg_m": max_service_leg,
        "success_order_path_m": success_order_distance,
        "posthoc_oracle_path_m": oracle,
        "success_order_gap_m": success_order_distance - oracle,
        "local_probe_extra_m": service_distance - success_order_distance,
        "clear_audit": stats.get("clear_audit", {}),
    }


def pearson(rows: list[dict], x_key: str, y_key: str) -> float:
    xs = [float(row[x_key]) for row in rows]
    ys = [float(row[y_key]) for row in rows]
    mx, my = mean(xs), mean(ys)
    numerator = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    denominator = math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
    return numerator / denominator


def write_tables(rows: list[dict]) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    fields = [
        "log_file", "official_result", "practice_run_no", "case_code", "ended_at_utc",
        "N", "T_s", "T_per_N_s", "travel_s", "detect_s", "switch_s", "clear_ok_s",
        "clear_miss_s", "n_measure", "n_clear", "clear_miss", "pending_at_exit",
        "exit_accepted", "completed", "q3_path_profile", "backbone_scan_s",
        "localization_s", "clear_detour_s", "nonmovement_s", "scan_phase_end_s",
        "service_phase_s", "measures_before_first_clear", "unique_scan_points",
        "service_path_m", "max_service_leg_m", "success_order_path_m",
        "posthoc_oracle_path_m", "success_order_gap_m", "local_probe_extra_m",
    ]
    records = []
    for row in rows:
        official = row["official"]
        record = {
            "log_file": row["log_path"].name,
            "official_result": row["result_path"].name,
            "practice_run_no": official["practice_run_no"],
            "case_code": official["case_code"],
            "ended_at_utc": official["ended_at_utc"],
        }
        record.update({field: row[field] for field in fields if field in row})
        records.append(record)
    with (OUT / "latest_10_metrics.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)

    audit_totals: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for row in rows:
        for source, values in row["clear_audit"].items():
            for key, value in values.items():
                audit_totals[source][key] += float(value)

    low = [row for row in rows if row["N"] <= 13]
    high = [row for row in rows if row["N"] >= 15]
    summary = {
        "cohort_definition": "ten latest Q3 practice result records by ended_at_utc",
        "n_cases": len(rows),
        "all_clear_cases": sum(row["N"] == row["official"]["jammer_count"] for row in rows),
        "completed_cases": sum(row["completed"] and row["exit_accepted"] and row["pending_at_exit"] == 0 for row in rows),
        "total_sources": sum(row["N"] for row in rows),
        "mean_T_s": mean(row["T_s"] for row in rows),
        "weighted_T_per_N_s": sum(row["T_s"] for row in rows) / sum(row["N"] for row in rows),
        "mean_case_T_per_N_s": mean(row["T_per_N_s"] for row in rows),
        "mean_travel_share": sum(row["travel_s"] for row in rows) / sum(row["T_s"] for row in rows),
        "mean_backbone_scan_s": mean(row["backbone_scan_s"] for row in rows),
        "mean_localization_s": mean(row["localization_s"] for row in rows),
        "mean_clear_detour_s": mean(row["clear_detour_s"] for row in rows),
        "mean_nonmovement_s": mean(row["nonmovement_s"] for row in rows),
        "mean_scan_phase_end_s": mean(row["scan_phase_end_s"] for row in rows),
        "mean_service_phase_s": mean(row["service_phase_s"] for row in rows),
        "mean_success_order_gap_m": mean(row["success_order_gap_m"] for row in rows),
        "mean_local_probe_extra_m": mean(row["local_probe_extra_m"] for row in rows),
        "pearson_N_vs_T": pearson(rows, "N", "T_s"),
        "pearson_N_vs_T_per_N": pearson(rows, "N", "T_per_N_s"),
        "pearson_clear_miss_vs_T": pearson(rows, "clear_miss", "T_s"),
        "low_N_11_13": {
            "n_cases": len(low),
            "mean_T_s": mean(row["T_s"] for row in low),
            "mean_T_per_N_s": mean(row["T_per_N_s"] for row in low),
            "mean_scan_phase_end_s": mean(row["scan_phase_end_s"] for row in low),
        },
        "high_N_15_16": {
            "n_cases": len(high),
            "mean_T_s": mean(row["T_s"] for row in high),
            "mean_T_per_N_s": mean(row["T_per_N_s"] for row in high),
            "mean_scan_phase_end_s": mean(row["scan_phase_end_s"] for row in high),
        },
        "clear_audit_totals": {source: dict(values) for source, values in audit_totals.items()},
        "posthoc_oracle_warning": "Uses final successful clear positions; diagnostic lower bound only and forbidden as online policy input.",
    }
    (OUT / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def plot_overview(rows: list[dict]) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.2))
    fig.subplots_adjust(left=0.08, right=0.98, bottom=0.20, top=0.88, wspace=0.28)
    ax = axes[0]
    for row in rows:
        marker = "D" if row["N"] <= 13 else "o"
        color = "#D55E00" if row["N"] <= 13 else "#0072B2"
        ax.scatter(row["N"], row["T_per_N_s"], marker=marker, color=color, s=60, zorder=3)
        ax.annotate(row["log_path"].stem[-6:], (row["N"], row["T_per_N_s"]),
                    xytext=(4, 4), textcoords="offset points", fontsize=7)
    ax.set(xlabel="Cleared source count N", ylabel="Total time per source T/N (s)",
           title="Low-N cases carry larger fixed scan cost per source")
    ax.grid(alpha=0.25)

    ax = axes[1]
    labels = [row["log_path"].stem[-6:] for row in rows]
    components = [
        ("backbone scan", "backbone_scan_s", "#999999"),
        ("localization", "localization_s", "#56B4E9"),
        ("clear detour", "clear_detour_s", "#D55E00"),
        ("detect/switch/clear", "nonmovement_s", "#009E73"),
    ]
    bottom = [0.0] * len(rows)
    for label, key, color in components:
        values = [row[key] for row in rows]
        ax.bar(labels, values, bottom=bottom, label=label, color=color)
        bottom = [a + b for a, b in zip(bottom, values)]
    ax.set(xlabel="Replay ending time (HHMMSS)", ylabel="Virtual time (s)",
           title="Time ledger: clear detour remains the largest variable bucket")
    ax.tick_params(axis="x", rotation=45)
    ax.legend(frameon=False, fontsize=8)
    ax.grid(axis="y", alpha=0.2)
    fig.savefig(OUT / "latest_10_overview.png", dpi=200, facecolor="white")
    plt.close(fig)


def plot_selected_paths(rows: list[dict]) -> None:
    by_name = {row["log_path"].name: row for row in rows}
    selected = [
        by_name["p3-20260912-135150.json"],
        by_name["p3-20260912-135256.json"],
        by_name["p3-20260912-135013.json"],
    ]
    fig, axes = plt.subplots(1, 3, figsize=(15.5, 5.5))
    fig.subplots_adjust(left=0.05, right=0.99, bottom=0.21, top=0.84, wspace=0.28)
    for ax, row in zip(axes, selected):
        events = row["events"]
        scan = events[: row["first_clear"]]
        service = events[row["first_clear"] :]
        scan_points = [(0.0, 0.0)] + [event["point"] for event in scan]
        service_points = [row["scan_end"]] + [event["point"] for event in service]
        ax.plot(*zip(*scan_points), color="#666666", ls="--", lw=1.2, alpha=0.8, zorder=1)
        ax.plot(*zip(*service_points), color="#0072B2", lw=1.2, alpha=0.75, zorder=1)
        success = [event["point"] for event in service if event["action"] == "clear" and event["clear_result"] == "success"]
        misses = [event["point"] for event in service if event["action"] == "clear" and event["clear_result"] != "success"]
        measures = [event["point"] for event in service if event["action"] == "measure"]
        if measures:
            ax.scatter(*zip(*measures), s=12, marker=".", color="#0072B2", alpha=0.75, zorder=2)
        if success:
            ax.scatter(*zip(*success), s=50, marker="*", color="#009E73", edgecolor="black", lw=0.3, zorder=4)
        if misses:
            ax.scatter(*zip(*misses), s=30, marker="x", color="#D55E00", lw=1.2, zorder=3)
        ax.scatter(*row["scan_end"], s=46, marker="D", color="#CC79A7", edgecolor="black", lw=0.4, zorder=5)
        ax.set_title(
            f"N={row['N']}, T={row['T_s']:.0f}s, T/N={row['T_per_N_s']:.0f}s\n"
            f"miss={row['clear_miss']}, service={row['service_path_m']/1000:.2f} km, {row['log_path'].stem[-6:]}",
            fontsize=9,
        )
        ax.set(xlabel="x (m)", ylabel="y (m)")
        ax.set_aspect("equal", adjustable="box")
        ax.grid(alpha=0.2)
    fig.legend(
        handles=[
            Line2D([], [], color="#666666", ls="--", label="coverage scan path"),
            Line2D([], [], color="#0072B2", label="batch service path"),
            Line2D([], [], marker=".", color="#0072B2", ls="none", markersize=8, label="service measure"),
            Line2D([], [], marker="*", color="#009E73", markeredgecolor="black", ls="none", markersize=9, label="clear success"),
            Line2D([], [], marker="x", color="#D55E00", ls="none", markersize=7, label="clear miss"),
            Line2D([], [], marker="D", color="#CC79A7", markeredgecolor="black", ls="none", markersize=7, label="scan endpoint"),
        ],
        loc="lower center", ncol=6, frameon=False, fontsize=8,
    )
    fig.suptitle("Q3 latest official practice replays: scan-first then batch service", fontsize=12)
    fig.savefig(OUT / "selected_scan_first_paths.png", dpi=200, facecolor="white")
    plt.close(fig)


def main() -> None:
    rows = [analyze_case(path, payload) for path, payload in latest_official_results()]
    summary = write_tables(rows)
    plot_overview(rows)
    plot_selected_paths(rows)
    manifest = {
        "scope": "analysis-only replay; no simulator or official endpoint invoked",
        "sources": [
            "Jammers-simulator/JammersSimulatorData/behavior-logs/practice-p3-*.result.json",
            "output/drill/p3-YYYYMMDD-HHMMSS.json",
        ],
        "selection": summary["cohort_definition"],
        "transformations": [
            "sort official Q3 practice metadata by ended_at_utc and select latest 10",
            "match plaintext replay by UTC+8 completion timestamp",
            "split scan/service immediately before the first clear action",
            "reconstruct path lengths from consecutive request positions",
            "compute post-hoc exact open-path lower bound only from final successful clear positions",
        ],
        "figures": ["latest_10_overview.png", "selected_scan_first_paths.png"],
        "data_table": "latest_10_metrics.csv",
        "summary": "summary.json",
        "posthoc_oracle_warning": summary["posthoc_oracle_warning"],
    }
    (OUT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
