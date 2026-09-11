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
MID_RING_R = 900.0
MID_RING_N = 0
OUTER_RING_R = 2100.0
OUTER_RING_N = 12
ENROUTE_R = 900.0
INNER_R_MAX = 1550.0  # origin / 1200 m ring / optional mid ring vs outer ring


def omni_waypoints(ring_r: float = OMNI_RING_R, n: int = OMNI_RING_N) -> list[Point]:
    pts: list[Point] = [(0.0, 0.0)]
    for k in range(n):
        a = 2.0 * math.pi * k / n
        pts.append((ring_r * math.cos(a), ring_r * math.sin(a)))
    return pts


def _ring(radius: float, n: int) -> list[Point]:
    pts: list[Point] = []
    for k in range(n):
        a = 2.0 * math.pi * k / n
        pts.append((radius * math.cos(a), radius * math.sin(a)))
    return pts


def directional_waypoints(
    inner: list[Point] | None = None,
    outer_r: float = OUTER_RING_R,
    outer_n: int = OUTER_RING_N,
    mid_r: float = MID_RING_R,
    mid_n: int = MID_RING_N,
) -> list[Point]:
    """Omni inner cover plus one outer ring.

    Near-center outward sources (r_eff=1000 m) are heard by a 900 m stop on
    the way to the 1200 m inner ring (policy), not a separate mid ring.
    A 12-point ring at 2100 m keeps a listen in the 180° front half-plane.
    Q4 inner stays origin + 8×1200 m (6 inner fails directional_front_cover_ok).
    """
    pts = list(inner if inner is not None else omni_waypoints())
    if mid_n > 0:
        pts.extend(_ring(mid_r, mid_n))
    for k in range(outer_n):
        a = 2.0 * math.pi * k / outer_n
        pts.append((outer_r * math.cos(a), outer_r * math.sin(a)))
    return pts


def covering_phases(waypoints: Sequence[Point]) -> tuple[Point, list[Point], list[Point]]:
    """Split a covering tour into origin, inner ring, then outer ring."""
    origin = waypoints[0]
    inner: list[Point] = []
    outer: list[Point] = []
    for wp in waypoints[1:]:
        if dist(wp, (0.0, 0.0)) <= INNER_R_MAX:
            inner.append(wp)
        else:
            outer.append(wp)
    return origin, inner, outer


def _sample_disk(radius: float, n_radial: int = 8, n_ang: int = 72) -> list[Point]:
    pts = [(0.0, 0.0)]
    for i in range(1, n_radial + 1):
        r = radius * i / n_radial
        n = n_ang if i == n_radial else max(12, n_ang * i // n_radial)
        for k in range(n):
            a = 2.0 * math.pi * k / n
            pts.append((r * math.cos(a), r * math.sin(a)))
    return pts


def _in_front_halfplane(src: Point, heading_deg: float, probe: Point) -> bool:
    brg = math.degrees(math.atan2(probe[1] - src[1], probe[0] - src[0]))
    rel = (brg - heading_deg + 180.0) % 360.0 - 180.0
    return abs(rel) <= 90.0 + 1e-9


def q4_listen_set(waypoints: Sequence[Point] | None = None) -> list[Point]:
    """Covering waypoints plus the 900 m enroute stops used by HuntPolicy."""
    pts = list(waypoints if waypoints is not None else directional_waypoints())
    for k in range(OMNI_RING_N):
        a = 2.0 * math.pi * k / OMNI_RING_N
        pts.append((ENROUTE_R * math.cos(a), ENROUTE_R * math.sin(a)))
    return pts


def directional_front_cover_ok(
    waypoints: Sequence[Point] | None = None,
    cover_r: float = COVER_R,
    arena_r: float = ARENA_R,
) -> bool:
    """Every sampled pose has a listen point in its 180° front disk of radius cover_r.

    This is the directional-sensor covering condition (Ma & Liu style sector
    coverage): a source is heard only if a waypoint lies in heading ±90° and
    within r_eff. Enroute 900 m stops are included for near-center outward sources.
    """
    wps = q4_listen_set(waypoints)
    headings = [i * 15.0 for i in range(24)]
    for g in _sample_disk(arena_r, n_radial=6, n_ang=48):
        for h in headings:
            if not any(
                dist(w, g) <= cover_r + 1e-6 and _in_front_halfplane(g, h, w) for w in wps
            ):
                return False
    return True


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

def q3_waypoints(
    ring_r: float = Q3_RING_R,
    phase_deg: float = Q3_RING_PHASE_DEG,
) -> list[Point]:
    """Return the evaluated Q3 six-ring candidate, not the active route."""

    pts: list[Point] = [(0.0, 0.0)]
    phase = math.radians(phase_deg)
    for k in range(Q3_RING_N):
        angle = 2.0 * math.pi * k / Q3_RING_N + phase
        pts.append((ring_r * math.cos(angle), ring_r * math.sin(angle)))
    return pts


def q3_worst_case_distance(
    arena_r: float = ARENA_R,
    cover_r: float = COVER_R,
    ring_r: float = Q3_RING_R,
) -> float:
    """Analytic worst distance for the evaluated six-ring candidate."""

    if arena_r < 0.0 or cover_r < 0.0 or ring_r < 0.0:
        raise ValueError("coverage radii must be non-negative")
    if arena_r <= cover_r:
        return 0.0
    half_gap = math.pi / Q3_RING_N
    cosine = math.cos(half_gap)
    return max(
        math.sqrt(
            max(
                0.0,
                radius * radius + ring_r * ring_r - 2.0 * radius * ring_r * cosine,
            )
        )
        for radius in (cover_r, arena_r)
    )


def q3_coverage_certificate(
    arena_r: float = ARENA_R,
    cover_r: float = COVER_R,
    ring_r: float = Q3_RING_R,
    *,
    waypoints: Sequence[Point] | None = None,
) -> dict[str, object]:
    """Validate actual six-ring geometry and return its analytic certificate."""

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
                radius * radius + ring_r * ring_r - 2.0 * radius * ring_r * cosine,
            )
        )
        for radius in (annulus_inner, arena_r)
    }
    annulus_worst = max(endpoint_distances.values()) if arena_r > cover_r else 0.0
    centre_worst = min(arena_r, cover_r)
    overall_worst = max(centre_worst, annulus_worst)
    coverage_valid = annulus_worst * annulus_worst <= cover_r * cover_r + 1e-6
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
        "passes": structure_valid and coverage_valid,
    }
