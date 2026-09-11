"""Worst-case receive-radius coverage waypoints."""

from __future__ import annotations

import math
from typing import Sequence

from geometry import Point, dist

ARENA_R = 1800.0
COVER_R = 1000.0
OMNI_RING_R = 1200.0
OMNI_RING_N = 8
Q3_RING_R = 1150.0
Q3_RING_N = 6
Q3_RING_PHASE_DEG = 10.0
OUTER_RING_R = 2200.0
OUTER_RING_N = 16


def omni_waypoints(
    ring_r: float = OMNI_RING_R,
    n: int = OMNI_RING_N,
    phase_deg: float = 0.0,
) -> list[Point]:
    pts: list[Point] = [(0.0, 0.0)]
    for k in range(n):
        a = 2.0 * math.pi * k / n + math.radians(phase_deg)
        pts.append((ring_r * math.cos(a), ring_r * math.sin(a)))
    return pts


def q3_waypoints(
    ring_r: float = Q3_RING_R,
    phase_deg: float = Q3_RING_PHASE_DEG,
) -> list[Point]:
    """Return the tuned Q3 candidate route: centre plus six ring points."""

    return omni_waypoints(ring_r=ring_r, n=Q3_RING_N, phase_deg=phase_deg)


def q3_worst_case_distance(
    arena_r: float = ARENA_R,
    cover_r: float = COVER_R,
    ring_r: float = Q3_RING_R,
) -> float:
    """Return the analytic worst distance on the Q3 annulus.

    The centre covers ``r <= cover_r``. On the remaining annulus, the
    nearest of six equally spaced ring points is at most ``pi / 6`` away in
    angle, so the squared distance is

    ``r**2 + ring_r**2 - 2*r*ring_r*cos(pi/6)``.

    This convex quadratic reaches its maximum at an endpoint of
    ``[cover_r, arena_r]``. The default value is 988.5114204 m, which is
    below the 1000 m receive radius.
    """

    if arena_r < 0.0 or cover_r < 0.0 or ring_r < 0.0:
        raise ValueError("coverage radii must be non-negative")
    if arena_r <= cover_r:
        return 0.0
    half_gap = math.pi / Q3_RING_N
    cosine = math.cos(half_gap)
    endpoint_distances = [
        math.sqrt(
            max(
                0.0,
                radius * radius
                + ring_r * ring_r
                - 2.0 * radius * ring_r * cosine,
            )
        )
        for radius in (cover_r, arena_r)
    ]
    return max(endpoint_distances)


def q3_coverage_certificate(
    arena_r: float = ARENA_R,
    cover_r: float = COVER_R,
    ring_r: float = Q3_RING_R,
    *,
    waypoints: Sequence[Point] | None = None,
) -> dict[str, object]:
    """Validate the actual Q3 route and build its analytic coverage proof."""

    if arena_r < 0.0 or cover_r < 0.0 or ring_r < 0.0:
        raise ValueError("coverage radii must be non-negative")
    actual = list(waypoints if waypoints is not None else q3_waypoints(ring_r))
    finite = all(math.isfinite(x) and math.isfinite(y) for x, y in actual)
    center_count = sum(dist(point, (0.0, 0.0)) <= 1e-7 for point in actual)
    ring = [point for point in actual if dist(point, (0.0, 0.0)) > 1e-7]
    radii = [dist(point, (0.0, 0.0)) for point in ring]
    radius_matches = bool(radii) and all(abs(value - ring_r) <= 1e-7 for value in radii)
    distinct = all(
        dist(point, other) > 1e-7
        for index, point in enumerate(actual)
        for other in actual[index + 1 :]
    )
    angles = sorted(math.atan2(y, x) % (2.0 * math.pi) for x, y in ring)
    gaps = (
        [angles[index + 1] - angles[index] for index in range(len(angles) - 1)]
        + [angles[0] + 2.0 * math.pi - angles[-1]]
        if angles
        else []
    )
    maximum_gap = max(gaps) if gaps else 2.0 * math.pi
    regular = bool(gaps) and max(gaps) - min(gaps) <= 1e-10
    ring_inside_arena = all(value <= arena_r + 1e-9 for value in radii)
    structure_valid = (
        finite
        and len(actual) == Q3_RING_N + 1
        and center_count == 1
        and len(ring) == Q3_RING_N
        and distinct
        and radius_matches
        and regular
        and ring_inside_arena
    )
    annulus_inner = min(cover_r, arena_r)
    half_gap = maximum_gap / 2.0
    cosine = math.cos(half_gap)
    endpoint_distances = {
        str(radius): math.sqrt(
            max(
                0.0,
                radius * radius
                + ring_r * ring_r
                - 2.0 * radius * ring_r * cosine,
            )
        )
        for radius in (annulus_inner, arena_r)
    }
    annulus_worst = max(endpoint_distances.values()) if arena_r > cover_r else 0.0
    centre_worst = min(arena_r, cover_r)
    overall_worst = max(centre_worst, annulus_worst)
    coverage_valid = annulus_worst * annulus_worst <= cover_r * cover_r + 1e-6
    passes = structure_valid and coverage_valid
    return {
        "certificate_type": "analytic_regular_ring",
        "analytic_proof_valid": structure_valid,
        "ring_count": len(ring),
        "ring_radius_m": ring_r,
        "actual_ring_radii_m": radii,
        "center_count": center_count,
        "distinct_waypoints": distinct,
        "regular_angular_spacing": regular,
        "maximum_angular_gap_deg": math.degrees(maximum_gap),
        "ring_inside_arena": ring_inside_arena,
        "center_covered_radius_m": centre_worst,
        "annulus_inner_radius_m": annulus_inner,
        "annulus_outer_radius_m": arena_r,
        "maximum_nearest_angle_rad": half_gap,
        "maximum_nearest_angle_deg": math.degrees(half_gap),
        "endpoint_distances_m": endpoint_distances,
        "worst_case_distance": annulus_worst,
        "worst_case_distance_m": annulus_worst,
        "overall_worst_case_distance_m": overall_worst,
        "cover_radius_m": cover_r,
        "passes": passes,
    }


def directional_waypoints(
    inner: list[Point] | None = None,
    outer_r: float = OUTER_RING_R,
    outer_n: int = OUTER_RING_N,
) -> list[Point]:
    pts = list(inner if inner is not None else omni_waypoints())
    for i, (radius, n) in enumerate(((2000.0, 12), (outer_r, outer_n), (2450.0, 16))):
        phase = 0.17 * i
        for k in range(n):
            a = 2.0 * math.pi * k / n + phase
            pts.append((radius * math.cos(a), radius * math.sin(a)))
    return pts


def _sample_disk(radius: float, n_radial: int = 8, n_ang: int = 72) -> list[Point]:
    pts = [(0.0, 0.0)]
    for i in range(1, n_radial + 1):
        r = radius * i / n_radial
        n = n_ang if i == n_radial else max(12, n_ang * i // n_radial)
        for k in range(n):
            a = 2.0 * math.pi * k / n
            pts.append((r * math.cos(a), r * math.sin(a)))
    return pts


def coverage_ok(
    waypoints: Sequence[Point] | None = None,
    cover_r: float = COVER_R,
    arena_r: float = ARENA_R,
) -> bool:
    wps = list(waypoints if waypoints is not None else omni_waypoints())
    for p in _sample_disk(arena_r):
        if min(dist(p, w) for w in wps) > cover_r + 1e-6:
            return False
    return True
