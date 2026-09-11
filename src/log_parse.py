"""Parse robot action logs into per-channel AOA observations."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from geometry import Point


@dataclass
class ChannelObs:
    channel: int
    stations: list[Point] = field(default_factory=list)
    bearings_deg: list[float] = field(default_factory=list)
    silence: list[Point] = field(default_factory=list)
    near: list[Point] = field(default_factory=list)
    clear_xy: list[Point] = field(default_factory=list)
    clear_ok: list[bool] = field(default_factory=list)


def _xy(payload: dict[str, Any]) -> Point | None:
    pos = payload.get("position")
    if not isinstance(pos, dict):
        return None
    try:
        return (float(pos["x"]), float(pos["y"]))
    except (KeyError, TypeError, ValueError):
        return None


def _channel(payload: dict[str, Any]) -> int | None:
    ch = payload.get("channel")
    if ch is None:
        return None
    try:
        return int(ch)
    except (TypeError, ValueError):
        return None


def parse_action_log(log: Iterable[dict[str, Any]]) -> dict[int, ChannelObs]:
    """Group accepted /measure and /clear events by channel. Ignore accepted=false."""
    out: dict[int, ChannelObs] = {}
    for rec in log:
        if not isinstance(rec, dict):
            continue
        body = rec.get("response") or {}
        if body.get("accepted") is not True:
            continue
        req = rec.get("request") or {}
        path = rec.get("path")
        xy = _xy(req)
        if path == "/measure":
            ch = _channel(req)
            if ch is None or xy is None:
                continue
            obs = out.setdefault(ch, ChannelObs(channel=ch))
            result = body.get("measure_result")
            if result == "direction":
                svd = body.get("svd_deg")
                if isinstance(svd, (int, float)):
                    obs.stations.append(xy)
                    obs.bearings_deg.append(float(svd))
            elif result == "no_signal":
                obs.silence.append(xy)
            elif result == "near":
                obs.near.append(xy)
        elif path == "/clear":
            ch = _channel(req)
            if ch is None or xy is None:
                continue
            obs = out.setdefault(ch, ChannelObs(channel=ch))
            obs.clear_xy.append(xy)
            obs.clear_ok.append(body.get("clear_result") == "success")
    return out


def extract_log(obj: Any) -> list[dict[str, Any]]:
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict) and isinstance(obj.get("log"), list):
        return obj["log"]
    raise ValueError("日志须为动作列表，或含 log 字段的 drill JSON")


def parse_drill_file(path: Path | str) -> dict[int, ChannelObs]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return parse_action_log(extract_log(data))
