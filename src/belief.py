"""Per-channel observation bookkeeping."""

from __future__ import annotations

from dataclasses import dataclass, field

from geometry import Point


@dataclass
class Detection:
    xy: Point
    svd_deg: float


@dataclass
class ChannelBook:
    detections: dict[int, list[Detection]] = field(default_factory=dict)
    cleared: set[int] = field(default_factory=set)
    scanned_at: dict[int, list[Point]] = field(default_factory=dict)
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

    def record_no_signal(self, ch: int, xy: Point) -> None:
        self.no_signal_at.setdefault(ch, []).append(xy)
