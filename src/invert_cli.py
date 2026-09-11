"""Batch inversion validation: mock (with truth) or drill logs (consistency only)."""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from inversion import invert_channel
from log_parse import ChannelObs, parse_action_log, parse_drill_file
from mock_sim import MockSim, Source
from robot_client import FnTransport, RobotClient
from runner_q3 import run_q3
from runner_q4 import run_q4
from validation import summarize_truth, validate_consistency, validate_with_truth
from viz_inversion import write_truth_figures

OUT_DIR = ROOT.parent / "output" / "inversion"


def _random_omni(n: int, rng: random.Random) -> list[Source]:
    chs = rng.sample(range(1, 21), n)
    out = []
    for ch in chs:
        r = math.sqrt(rng.random()) * 1700.0
        a = rng.random() * 2.0 * math.pi
        xy = (r * math.cos(a), r * math.sin(a))
        reff = rng.uniform(1000.0, 1500.0)
        out.append(Source(channel=ch, xy=xy, r_eff=reff))
    return out


def _mix_sources(n: int, n_dir: int, rng: random.Random) -> list[Source]:
    chs = rng.sample(range(1, 21), n)
    out = []
    for i, ch in enumerate(chs):
        r = 400.0 + math.sqrt(rng.random()) * 1300.0
        a = rng.random() * 2.0 * math.pi
        xy = (r * math.cos(a), r * math.sin(a))
        reff = rng.uniform(1000.0, 1500.0)
        heading = math.degrees(a) if i < n_dir else None
        out.append(Source(channel=ch, xy=xy, r_eff=reff, heading_deg=heading))
    return out


def _run_mock_case(name: str, sources: list[Source], directional: bool) -> dict[str, Any]:
    sim = MockSim(robot_id="team-invert", sources=sources)
    bot = RobotClient(robot_id="team-invert", transport=FnTransport(sim.handle))
    stats = run_q4(bot) if directional else run_q3(bot)
    truth = {s.channel: s.xy for s in sources}
    grouped = parse_action_log(bot.log)
    rows = []
    pairs = []
    sample = None
    sample_score = -1.0
    for ch, obs in sorted(grouped.items()):
        inv = invert_channel(obs)
        if ch not in truth:
            continue
        met = validate_with_truth(inv, obs, truth[ch])
        rows.append(met)
        if inv.point_est is not None:
            pairs.append((truth[ch], inv.point_est))
        if (
            inv.n_direction >= 2
            and inv.region.vertices
            and inv.region.bounded
            and math.isfinite(inv.sec_radius)
            and 5.0 <= inv.sec_radius <= 50.0
        ):
            score = inv.sec_radius + 0.4 * inv.n_direction
            if score > sample_score:
                sample_score = score
                sample = (obs, inv, truth[ch])
    if sample is None:
        for ch, obs in sorted(grouped.items()):
            if ch not in truth:
                continue
            inv = invert_channel(obs)
            if inv.n_direction >= 2 and inv.region.vertices:
                sample = (obs, inv, truth[ch])
                break
    summary = summarize_truth(rows)
    return {
        "name": name,
        "stats": {k: stats[k] for k in ("cleared", "virtual_time_s", "channels") if k in stats},
        "summary": summary.to_dict(),
        "channels": [r.to_dict() for r in rows],
        "_plot": {"sample": sample, "metrics": rows, "pairs": pairs},
    }


def run_mock(out_dir: Path) -> dict[str, Any]:
    cases = [
        ("q3-seed0-n10", _random_omni(10, random.Random(0)), False),
        ("q3-seed1-n12", _random_omni(12, random.Random(1)), False),
        ("q4-seed3-n12-nd4", _mix_sources(12, 4, random.Random(3)), True),
    ]
    reports = [_run_mock_case(name, src, d) for name, src, d in cases]
    # figures from first case with pairs
    plot_src = next((r for r in reports if r["_plot"]["pairs"]), reports[0])
    figs = write_truth_figures(
        out_dir,
        plot_src["_plot"]["sample"],
        plot_src["_plot"]["metrics"],
        plot_src["_plot"]["pairs"],
    )
    payload = {
        "mode": "mock_with_truth",
        "cases": [{k: v for k, v in r.items() if k != "_plot"} for r in reports],
        "figures": [str(p) for p in figs],
    }
    (out_dir / "mock_summary.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return payload


def run_drill(path: Path, out_dir: Path) -> dict[str, Any]:
    grouped = parse_drill_file(path)
    channels: list[dict[str, Any]] = []
    sample_obs: ChannelObs | None = None
    sample_inv = None
    for ch, obs in sorted(grouped.items()):
        inv = invert_channel(obs)
        met = validate_consistency(inv, obs)
        channels.append(met.to_dict())
        if sample_obs is None and inv.n_direction >= 2 and inv.region.vertices:
            sample_obs, sample_inv = obs, inv
    figs = []
    if sample_obs is not None and sample_inv is not None:
        from viz_inversion import plot_channel_intersection

        p = out_dir / "drill_intersection.png"
        plot_channel_intersection(sample_obs, sample_inv, p, truth=None)
        figs.append(str(p))
    payload = {
        "mode": "consistency_only_not_accuracy",
        "drill": str(path),
        "n_channels": len(channels),
        "channels": channels,
        "figures": figs,
        "notes": ["演练日志无源坐标，本报告仅为内部一致性，不是定位精度"],
    }
    (out_dir / "drill_summary.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return payload


def main() -> None:
    p = argparse.ArgumentParser(description="干扰源模型反演验证（离线，不写回策略）")
    p.add_argument("--mock", action="store_true", help="本地 mock 有真值批次")
    p.add_argument("--drill", type=str, help="演练 JSON 路径（仅一致性）")
    p.add_argument("--out", type=str, default=str(OUT_DIR))
    args = p.parse_args()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    if args.mock:
        payload = run_mock(out_dir)
        print(json.dumps({k: v for k, v in payload.items() if k != "cases"}, ensure_ascii=False, indent=2))
        for case in payload["cases"]:
            s = case["summary"]
            print(
                f"{case['name']}: containment={s['containment_rate']} "
                f"residual_1deg={s['residual_1deg_rate']} mean_err_m={s['mean_err_m']}"
            )
        return
    if args.drill:
        payload = run_drill(Path(args.drill), out_dir)
        print(json.dumps({k: v for k, v in payload.items() if k != "channels"}, ensure_ascii=False, indent=2))
        return
    p.error("请指定 --mock 或 --drill FILE")


if __name__ == "__main__":
    main()
