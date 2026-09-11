"""Offline AOA inversion: replay the same cone intersection used by the hunt."""

from __future__ import annotations

from dataclasses import dataclass

from geometry import (
    Q3_ANGLE_HALF_WIDTH_DEG,
    IntersectionResult,
    LocateQuality,
    Point,
    cone_halfplanes,
    intersect_cones,
    locate_quality,
)
from log_parse import ChannelObs


@dataclass
class InvertResult:
    channel: int
    n_direction: int
    region: IntersectionResult
    quality: LocateQuality
    point_est: Point | None
    sec_radius: float
    can_clear_20: bool


def truth_in_cones(
    stations: list[Point],
    bearings_deg: list[float],
    truth: Point,
    delta_deg: float = Q3_ANGLE_HALF_WIDTH_DEG,
) -> bool:
    """True iff truth lies in every closed ±delta bearing cone (no clip-box)."""
    if not stations:
        return False
    for s, th in zip(stations, bearings_deg):
        for hp in cone_halfplanes(s, th, delta_deg):
            if not hp.contains(truth):
                return False
    return True


def invert_channel(
    obs: ChannelObs,
    delta_deg: float = Q3_ANGLE_HALF_WIDTH_DEG,
) -> InvertResult:
    n = len(obs.stations)
    region = (
        intersect_cones(obs.stations, obs.bearings_deg, delta_deg=delta_deg)
        if n
        else IntersectionResult([], bounded=True, empty=True)
    )
    quality = locate_quality(
        obs.stations,
        obs.bearings_deg,
        delta_deg=delta_deg,
        silence=obs.silence or None,
    )
    point_est = quality.sec_center if n >= 2 else None
    sec_r = quality.sec_radius if point_est is not None else float("inf")
    return InvertResult(
        channel=obs.channel,
        n_direction=n,
        region=region,
        quality=quality,
        point_est=point_est,
        sec_radius=sec_r,
        can_clear_20=bool(quality.can_clear_20),
    )
