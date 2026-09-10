"""Local simulator matching attachment timing and physics (no official GUI)."""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from typing import Any

from geometry import dist

SPEED = 5.0
DETECT_S = 5.0
SWITCH_S = 1.0
CLEAR_OK_S = 5.0
CLEAR_MISS_S = 3.0
NEAR_M = 5.0
CLEAR_M = 20.0
R_MAX = 1500.0


def _bearing_deg(from_pt: tuple[float, float], to_pt: tuple[float, float]) -> float:
    return math.degrees(math.atan2(to_pt[1] - from_pt[1], to_pt[0] - from_pt[0])) % 360.0


def _site_error_deg(x: float, y: float, channel: int) -> float:
    """Fixed error in [-1, 1] for a location (repeatable)."""
    key = f"{x:.6f},{y:.6f},{channel}".encode("utf-8")
    h = hashlib.sha256(key).digest()
    u = int.from_bytes(h[:4], "little") / 2**32
    return u * 2.0 - 1.0


def _in_sector(src_xy: tuple[float, float], heading_deg: float | None, probe: tuple[float, float]) -> bool:
    if heading_deg is None:
        return True
    brg = _bearing_deg(src_xy, probe)
    # coverage: heading ± 90° inclusive
    rel = (brg - heading_deg + 180.0) % 360.0 - 180.0
    return abs(rel) <= 90.0 + 1e-9


@dataclass
class Source:
    channel: int
    xy: tuple[float, float]
    r_eff: float
    heading_deg: float | None = None  # None = omni
    cleared: bool = False


@dataclass
class MockSim:
    robot_id: str
    sources: list[Source] = field(default_factory=list)
    arena_id: str = "default"
    entered: bool = False
    exited: bool = False
    position: tuple[float, float] = (0.0, 0.0)
    channel: int = 1
    virtual_time_s: float = 0.0
    real_timestamp_ms: int = 1_760_000_000_000
    _idem: dict[str, dict[str, Any]] = field(default_factory=dict)
    _idem_path: dict[str, str] = field(default_factory=dict)

    def handle(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        extra = set(payload) - {"arena_id", "robot_id", "request_id", "position", "channel"}
        if extra:
            return self._reject()
        if payload.get("arena_id") != self.arena_id or payload.get("robot_id") != self.robot_id:
            return self._reject()
        rid = payload.get("request_id")
        if not isinstance(rid, str) or not rid:
            return self._reject()
        if rid in self._idem:
            if self._idem_path[rid] != path:
                return self._reject()
            return self._idem[rid]
        if path == "/enter":
            body = self._enter(payload)
        elif path == "/exit":
            body = self._exit(payload)
        elif path == "/measure":
            body = self._measure(payload)
        elif path == "/clear":
            body = self._clear(payload)
        else:
            return self._reject()
        if body.get("accepted"):
            self._idem[rid] = body
            self._idem_path[rid] = path
        return body

    def _reject(self) -> dict[str, Any]:
        return {"accepted": False, "real_timestamp_ms": self.real_timestamp_ms, "virtual_time_s": 0}

    def _ok_base(self) -> dict[str, Any]:
        return {
            "accepted": True,
            "real_timestamp_ms": self.real_timestamp_ms,
            "virtual_time_s": self.virtual_time_s,
        }

    def _enter(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self.entered:
            return self._reject()
        if "position" in payload or "channel" in payload:
            return self._reject()
        self.entered = True
        self.position = (0.0, 0.0)
        self.channel = 1
        self.virtual_time_s = 0.0
        body = self._ok_base()
        body.update(
            {
                "max_virtual_duration_s": 360000,
                "max_real_duration_s": 1200,
                "remaining_real_duration_s": 1200,
            }
        )
        return body

    def _exit(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.entered or self.exited:
            return self._reject()
        if "position" in payload or "channel" in payload:
            return self._reject()
        self.exited = True
        body = self._ok_base()
        body["exit_reason"] = "user_exit"
        return body

    def _move_cost(self, x: float, y: float) -> float:
        d = dist(self.position, (x, y))
        return d / SPEED

    def _measure(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.entered or self.exited:
            return self._reject()
        pos = payload.get("position")
        ch = payload.get("channel")
        if not isinstance(pos, dict) or "x" not in pos or "y" not in pos:
            return self._reject()
        if extra := set(pos) - {"x", "y"}:
            return self._reject()
        try:
            x, y = float(pos["x"]), float(pos["y"])
            channel = int(ch)
        except (TypeError, ValueError):
            return self._reject()
        if channel < 1 or channel > 20:
            return self._reject()
        move = self._move_cost(x, y)
        sw = SWITCH_S if channel != self.channel else 0.0
        self.virtual_time_s += move + sw + DETECT_S
        self.position = (x, y)
        self.channel = channel
        body = self._ok_base()
        src = self._alive(channel)
        if src is None:
            body["measure_result"] = "no_signal"
            return body
        d = dist((x, y), src.xy)
        visible = d <= src.r_eff + 1e-9 and _in_sector(src.xy, src.heading_deg, (x, y))
        if not visible:
            body["measure_result"] = "no_signal"
            return body
        if d <= NEAR_M:
            body["measure_result"] = "near"
            return body
        true_brg = _bearing_deg((x, y), src.xy)
        err = _site_error_deg(x, y, channel)
        svd = (true_brg + err) % 360.0
        body["measure_result"] = "direction"
        body["svd_deg"] = round(svd, 2)
        return body

    def _clear(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.entered or self.exited:
            return self._reject()
        pos = payload.get("position")
        ch = payload.get("channel")
        if not isinstance(pos, dict) or "x" not in pos or "y" not in pos:
            return self._reject()
        if set(pos) - {"x", "y"}:
            return self._reject()
        x, y = float(pos["x"]), float(pos["y"])
        channel = int(ch)
        move = self._move_cost(x, y)
        self.position = (x, y)
        src = self._alive(channel)
        hit = src is not None and dist((x, y), src.xy) <= CLEAR_M + 1e-9
        if hit:
            assert src is not None
            src.cleared = True
            self.virtual_time_s += move + CLEAR_OK_S
            body = self._ok_base()
            body["clear_result"] = "success"
            return body
        self.virtual_time_s += move + CLEAR_MISS_S
        body = self._ok_base()
        body["clear_result"] = "no_target_in_range"
        return body

    def _alive(self, channel: int) -> Source | None:
        for s in self.sources:
            if s.channel == channel and not s.cleared:
                return s
        return None
