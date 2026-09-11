"""Model-rationality metrics: set containment (with truth) and self-consistency."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any, Sequence

RESIDUAL_BAND_DEG = 1.01  # ±1° 赛题带 + svd 两位小数舍入

from geometry import Point, dist
from inversion import InvertResult, truth_in_cones
from log_parse import ChannelObs


def wrap_deg(delta: float) -> float:
    x = (delta + 180.0) % 360.0 - 180.0
    return x if x != -180.0 else 180.0


def true_bearing_deg(station: Point, source: Point) -> float:
    return math.degrees(math.atan2(source[1] - station[1], source[0] - station[0])) % 360.0


def bearing_residuals_deg(
    stations: Sequence[Point],
    bearings_deg: Sequence[float],
    source: Point,
) -> list[float]:
    return [
        wrap_deg(true_bearing_deg(s, source) - th)
        for s, th in zip(stations, bearings_deg)
    ]


@dataclass
class TruthMetrics:
    channel: int
    n_direction: int
    inside_region: bool | None
    err_m: float | None
    residuals_deg: list[float]
    residual_max_abs_deg: float | None
    residuals_within_1deg: bool | None
    clear_ok_any: bool
    clear_dist_m: float | None
    can_clear_20: bool
    sec_radius: float

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["sec_radius"] = None if math.isinf(self.sec_radius) else self.sec_radius
        return d


@dataclass
class ConsistMetrics:
    channel: int
    n_direction: int
    empty: bool
    bounded: bool
    can_clear_20: bool
    last_clear_ok: bool | None
    clear_agree: bool | None
    self_residuals_deg: list[float]
    self_residual_max_abs_deg: float | None
    mode: str = "consistency_only_not_accuracy"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BatchSummary:
    n_channels: int
    n_eligible: int
    containment_rate: float | None
    residual_1deg_rate: float | None
    mean_err_m: float | None
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_with_truth(result: InvertResult, obs: ChannelObs, source_xy: Point) -> TruthMetrics:
    eligible = obs.stations and result.n_direction >= 2
    inside = (
        truth_in_cones(obs.stations, obs.bearings_deg, source_xy)
        if eligible
        else None
    )
    residuals = bearing_residuals_deg(obs.stations, obs.bearings_deg, source_xy)
    rmax = max(abs(r) for r in residuals) if residuals else None
    within = all(abs(r) <= RESIDUAL_BAND_DEG + 1e-9 for r in residuals) if residuals else None
    err = dist(result.point_est, source_xy) if result.point_est is not None else None
    ok_dists = [
        dist(xy, source_xy) for xy, ok in zip(obs.clear_xy, obs.clear_ok) if ok
    ]
    return TruthMetrics(
        channel=obs.channel,
        n_direction=result.n_direction,
        inside_region=inside,
        err_m=err,
        residuals_deg=residuals,
        residual_max_abs_deg=rmax,
        residuals_within_1deg=within,
        clear_ok_any=any(obs.clear_ok),
        clear_dist_m=min(ok_dists) if ok_dists else None,
        can_clear_20=result.can_clear_20,
        sec_radius=result.sec_radius,
    )


def validate_consistency(result: InvertResult, obs: ChannelObs) -> ConsistMetrics:
    last_ok = obs.clear_ok[-1] if obs.clear_ok else None
    agree = None
    if last_ok is not None:
        agree = (result.can_clear_20 and last_ok) or (not result.can_clear_20 and not last_ok)
        # A later successful clear after extra measures still counts as agree if last is success
        if last_ok:
            agree = True
    self_res: list[float] = []
    if result.point_est is not None:
        self_res = bearing_residuals_deg(obs.stations, obs.bearings_deg, result.point_est)
    rmax = max(abs(r) for r in self_res) if self_res else None
    return ConsistMetrics(
        channel=obs.channel,
        n_direction=result.n_direction,
        empty=result.region.empty,
        bounded=result.region.bounded,
        can_clear_20=result.can_clear_20,
        last_clear_ok=last_ok,
        clear_agree=agree,
        self_residuals_deg=self_res,
        self_residual_max_abs_deg=rmax,
    )


def containment_rate(rows: Sequence[TruthMetrics]) -> float:
    eligible = [r for r in rows if r.inside_region is not None]
    if not eligible:
        return float("nan")
    return sum(1 for r in eligible if r.inside_region) / len(eligible)


def summarize_truth(rows: Sequence[TruthMetrics]) -> BatchSummary:
    eligible = [r for r in rows if r.inside_region is not None]
    with_res = [r for r in rows if r.residuals_within_1deg is not None]
    errs = [r.err_m for r in rows if r.err_m is not None]
    crate = containment_rate(rows)
    rrate = (
        sum(1 for r in with_res if r.residuals_within_1deg) / len(with_res)
        if with_res
        else None
    )
    notes = ["有真值：集合包含与 ±1°（含 0.01° 示向舍入）残差为模型合理性门禁"]
    if eligible and crate < 1.0 - 1e-12:
        notes.append("包含率 < 1：几何核或日志解析与测量不一致")
    return BatchSummary(
        n_channels=len(rows),
        n_eligible=len(eligible),
        containment_rate=None if math.isnan(crate) else crate,
        residual_1deg_rate=rrate,
        mean_err_m=(sum(errs) / len(errs)) if errs else None,
        notes=notes,
    )
