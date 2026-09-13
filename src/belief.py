"""Per-channel observation bookkeeping and no_signal feasible-set prune."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from geometry import Point, dist

ARENA_R = 1800.0
R_RULE_OUT = 1000.0  # min r_eff: inside this, a visible source would have been heard
R_MIGHT_HEAR = 1500.0  # max r_eff: still worth listening

_SAMPLES: list[Point] | None = None
_HEADINGS = [i * 15.0 for i in range(24)]


def _sample_arena() -> list[Point]:
    global _SAMPLES
    if _SAMPLES is not None:
        return _SAMPLES
    pts: list[Point] = [(0.0, 0.0)]
    for i in range(1, 8):
        r = ARENA_R * i / 7.0
        n = max(10, 10 * i)
        for k in range(n):
            a = 2.0 * math.pi * k / n
            pts.append((r * math.cos(a), r * math.sin(a)))
    _SAMPLES = pts
    return pts


def _in_sector(src: Point, heading_deg: float, probe: Point) -> bool:
    brg = math.degrees(math.atan2(probe[1] - src[1], probe[0] - src[0]))
    rel = (brg - heading_deg + 180.0) % 360.0 - 180.0
    return abs(rel) <= 90.0 + 1e-9


@dataclass
class Detection:
    xy: Point
    svd_deg: float


@dataclass
class ChannelBook:
    detections: dict[int, list[Detection]] = field(default_factory=dict)
    cleared: set[int] = field(default_factory=set)
    scanned_at: dict[int, list[Point]] = field(default_factory=dict)
    silent_at: dict[int, list[Point]] = field(default_factory=dict)
    no_signal_at: dict[int, list[Point]] = field(default_factory=dict)

    def remaining_to_scan(self) -> list[int]:
        return [ch for ch in range(1, 21) if ch not in self.cleared]

    def unknown_channels(self) -> list[int]:
        return [ch for ch in range(1, 21) if ch not in self.cleared and ch not in self.detections]

    def pending(self) -> list[int]:
        return [ch for ch in self.detections if ch not in self.cleared]

    def add_direction(self, ch: int, xy: Point, svd: float) -> None:
        self.detections.setdefault(ch, []).append(Detection(xy, svd))

    def mark_cleared(self, ch: int) -> None:
        self.cleared.add(ch)
        self.detections.pop(ch, None)

    def record_scan(self, ch: int, xy: Point) -> None:
        self.scanned_at.setdefault(ch, []).append(xy)

    def record_silence(self, ch: int, xy: Point) -> None:
        self.silent_at.setdefault(ch, []).append(xy)

    def record_no_signal(self, ch: int, xy: Point) -> None:
        self.no_signal_at.setdefault(ch, []).append(xy)

    def might_hear(
        self, ch: int, probe: Point, directional: bool = True, assume_directional: bool = False
    ) -> bool:
        """True if an unheard source on this channel could still be audible at probe.

        After the omni inner cover is finished, assume_directional=True: locations
        still compatible with an omni source are ignored (they should already have
        been heard). Only 180° front-lobe survivors can justify an outer waypoint.
        """
        if ch in self.cleared or ch in self.detections:
            return False
        scans = self.silent_at.get(ch, [])
        if not scans:
            return True
        for p in scans:
            if dist(p, probe) < 35.0:
                return False
        return self.hypothesis_hits(ch, probe, directional=directional, assume_directional=assume_directional) > 0

    def hypothesis_hits(
        self,
        ch: int,
        probe: Point,
        directional: bool = True,
        assume_directional: bool = False,
    ) -> int:
        """Count remaining (pose, heading) samples still audible at probe."""
        if ch in self.cleared or ch in self.detections:
            return 0
        scans = self.silent_at.get(ch, [])
        if not scans:
            return 1
        for p in scans:
            if dist(p, probe) < 35.0:
                return 0
        hits = 0
        samples = _sample_arena()
        for g in samples:
            if dist(probe, g) > R_MIGHT_HEAR + 1e-9:
                continue
            omni_dead = any(dist(p, g) <= R_RULE_OUT + 1e-9 for p in scans)
            if not omni_dead:
                if assume_directional:
                    continue
                hits += 1
                continue
            if not directional:
                continue
            for h in _HEADINGS:
                ruled = False
                for p in scans:
                    if dist(p, g) <= R_RULE_OUT + 1e-9 and _in_sector(g, h, p):
                        ruled = True
                        break
                if ruled:
                    continue
                if _in_sector(g, h, probe):
                    hits += 1
        return hits
