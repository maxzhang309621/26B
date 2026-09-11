"""Worst-case receive-radius coverage waypoints."""

from __future__ import annotations

import math
from functools import lru_cache
from typing import Sequence

from geometry import Point, convex_hull, dist, point_in_convex_polygon

ARENA_R = 1800.0
COVER_R = 1000.0
# Q3 omnidirectional ring
OMNI_RING_R = 1200.0
OMNI_RING_N = 8
Q3_RING_R = 1150.0
Q3_RING_N = 6
Q3_RING_PHASE_DEG = 10.0
MID_RING_R = 900.0
MID_RING_N = 0
# Q4 directional certificate route: origin + 8×995 + 12×1865 (= 21)
Q4_INNER_R = 995.0
Q4_INNER_N = 8
OUTER_RING_R = 1865.0  # arena 1800 + 65 m for boundary outward sources
OUTER_RING_N = 12
Q4_OUTER_FULL_R = OUTER_RING_R
Q4_OUTER_FULL_N = OUTER_RING_N
Q4_OUTER_LITE_R = 1865.0
Q4_OUTER_LITE_N = 12
Q4_DIR_FULL_OUTER_MIN = 8
ENROUTE_R = 900.0  # legacy Q3-era mid stop; unused on Q4 995+1865 route
INNER_R_MAX = 1400.0  # split inner 995 vs outer 1865
Q4_SPIRAL_PITCH = 800.0
Q4_SPIRAL_STEP = 500.0
Q4_SPIRAL_R0 = 400.0
Q4_SPIRAL_OUTER_LAPS = 1.0
CERT_MIN_CELL = 1800.0 / 64.0  # 28.125 m uniform leaf size


def pick_q4_outer_ring(
    omni_n: int | None,
    dir_n: int | None,
    *,
    jammer_count: int | None = None,
    pure: bool = False,
) -> tuple[float, int]:
    """Pick outer ring after /enter (Q4-only; not Q3 route logic).

    Default certificate route keeps 12×1865. Dynamic profiles may still skip
    the outer ring when there are zero directional sources.
    """
    if dir_n is None or omni_n is None:
        return Q4_OUTER_FULL_R, Q4_OUTER_FULL_N
    if not pure and dir_n <= 0:
        return Q4_OUTER_LITE_R, 0
    return Q4_OUTER_FULL_R, Q4_OUTER_FULL_N


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
    """Q4 cover skeleton: origin + 8×995 + 12×1865 (optional mid unused).

    Geometry matches the directional convex-hull certificate: any source in the
    arena that lies in the convex hull of nearby (≤1000 m) listens is heard
    for every 180° heading. Outer ring sits 65 m outside the arena so
    boundary-outward sources still have a front-halfplane listen.
    """
    pts = list(inner if inner is not None else omni_waypoints(Q4_INNER_R, Q4_INNER_N))
    if mid_n > 0:
        pts.extend(_ring(mid_r, mid_n))
    for k in range(outer_n):
        a = 2.0 * math.pi * k / outer_n
        pts.append((outer_r * math.cos(a), outer_r * math.sin(a)))
    return pts


def _archimedean_q4_points(
    r_max: float = Q4_OUTER_FULL_R,
    pitch: float = Q4_SPIRAL_PITCH,
    step: float = Q4_SPIRAL_STEP,
    r0: float = Q4_SPIRAL_R0,
    outer_laps: float = Q4_SPIRAL_OUTER_LAPS,
) -> list[Point]:
    """Origin to r_max along r = bθ, then continue one lap on the r_max circle."""
    b = pitch / (2.0 * math.pi)
    pts: list[Point] = [(0.0, 0.0)]
    theta = r0 / b
    last = pts[0]
    dth = 0.008
    while True:
        r = min(b * theta, r_max)
        p = (r * math.cos(theta), r * math.sin(theta))
        if dist(p, last) >= step:
            pts.append(p)
            last = p
        if b * theta >= r_max:
            break
        theta += dth
    theta0 = theta
    while theta - theta0 < 2.0 * math.pi * outer_laps:
        p = (r_max * math.cos(theta), r_max * math.sin(theta))
        if dist(p, last) >= step:
            pts.append(p)
            last = p
        theta += dth
    return pts


def _front_cover_holds(
    waypoints: Sequence[Point],
    cover_r: float = COVER_R,
    arena_r: float = ARENA_R,
) -> bool:
    """Sampled directional cover (legacy). Prefer ``directional_hull_cover_ok``."""
    headings = [i * 15.0 for i in range(24)]
    for g in _sample_disk(arena_r, n_radial=6, n_ang=48):
        for h in headings:
            if not any(
                dist(w, g) <= cover_r + 1e-6 and _in_front_halfplane(g, h, w)
                for w in waypoints
            ):
                return False
    return True


def directional_hull_cover_at(
    g: Point,
    waypoints: Sequence[Point],
    cover_r: float = COVER_R,
) -> bool:
    """True iff g lies in conv({w : ||w-g|| ≤ cover_r}).

    Equivalent to: every 180° emission heading has a listen in its front
    half-plane among the nearby waypoints (separating-hyperplane argument).
    """
    near = [w for w in waypoints if dist(w, g) <= cover_r + 1e-9]
    if len(near) < 3:
        return False
    hull = convex_hull(near)
    if len(hull) < 3:
        return False
    return point_in_convex_polygon(g, hull)


def directional_hull_cover_ok(
    waypoints: Sequence[Point] | None = None,
    cover_r: float = COVER_R,
    arena_r: float = ARENA_R,
) -> bool:
    """Sampled check of the convex-hull directional criterion over the arena."""
    wps = list(waypoints if waypoints is not None else directional_waypoints())
    return all(
        directional_hull_cover_at(g, wps, cover_r=cover_r)
        for g in _sample_disk(arena_r, n_radial=8, n_ang=72)
    )


def _cell_corners(xmin: float, ymin: float, xmax: float, ymax: float) -> list[Point]:
    return [
        (xmin, ymin),
        (xmin, ymax),
        (xmax, ymin),
        (xmax, ymax),
    ]


def _cell_outside_arena(xmin: float, ymin: float, xmax: float, ymax: float, arena_r: float) -> bool:
    # Closest point of axis-aligned square to origin.
    cx = 0.0 if xmin <= 0.0 <= xmax else (xmin if xmin > 0.0 else xmax)
    cy = 0.0 if ymin <= 0.0 <= ymax else (ymin if ymin > 0.0 else ymax)
    return dist((cx, cy), (0.0, 0.0)) > arena_r + 1e-9


def _cell_leaf_ok(
    xmin: float,
    ymin: float,
    xmax: float,
    ymax: float,
    waypoints: Sequence[Point],
    cover_r: float,
    arena_r: float,
) -> bool:
    """Finest-cell check: hull criterion at center + in-arena corners."""
    cx = 0.5 * (xmin + xmax)
    cy = 0.5 * (ymin + ymax)
    probes = [(cx, cy)] + [
        c for c in _cell_corners(xmin, ymin, xmax, ymax) if dist(c, (0.0, 0.0)) <= arena_r + 1e-9
    ]
    return all(directional_hull_cover_at(g, waypoints, cover_r=cover_r) for g in probes)


def build_directional_certificate(
    waypoints: Sequence[Point] | None = None,
    *,
    arena_r: float = ARENA_R,
    cover_r: float = COVER_R,
    min_cell: float = CERT_MIN_CELL,
) -> dict:
    """Quadtree certificate for the directional convex-hull cover criterion.

    Uniformly refines the arena-boxed square to ``min_cell`` (~28 m). Each leaf
    whose center lies in the arena is checked by ``g ∈ conv(S_g)``. With the
    default 21-point route this yields a finite proof (≈1.1e4 leaves; lecture
    notes quote ~7228 under a slightly different adaptive stop).
    """
    wps = list(waypoints if waypoints is not None else directional_waypoints())
    leaves = 0
    failed = 0
    stack = [(-arena_r, -arena_r, arena_r, arena_r)]
    while stack:
        xmin, ymin, xmax, ymax = stack.pop()
        if _cell_outside_arena(xmin, ymin, xmax, ymax, arena_r):
            continue
        cx = 0.5 * (xmin + xmax)
        cy = 0.5 * (ymin + ymax)
        if dist((cx, cy), (0.0, 0.0)) > arena_r + 1e-9:
            continue
        side = max(xmax - xmin, ymax - ymin)
        if side > min_cell + 1e-9:
            mx = 0.5 * (xmin + xmax)
            my = 0.5 * (ymin + ymax)
            stack.extend(
                [
                    (xmin, ymin, mx, my),
                    (mx, ymin, xmax, my),
                    (xmin, my, mx, ymax),
                    (mx, my, xmax, ymax),
                ]
            )
            continue
        leaves += 1
        if not _cell_leaf_ok(xmin, ymin, xmax, ymax, wps, cover_r, arena_r):
            failed += 1
    return {
        "ok": failed == 0,
        "leaves": leaves,
        "failed_leaves": failed,
        "n_waypoints": len(wps),
        "min_cell": min_cell,
        "cover_r": cover_r,
        "arena_r": arena_r,
    }


@lru_cache(maxsize=1)
def directional_certificate() -> dict:
    """Cached certificate for the default 21-point Q4 route."""
    return build_directional_certificate(tuple(directional_waypoints()))


@lru_cache(maxsize=1)
def q4_spiral_waypoints() -> tuple[Point, ...]:
    """Q4 covering spiral: Archimedean out to outer full R, then one outer lap.

    Double-ring certificate route stays the submission default. Spiral is kept
    dense as an experimental alternate walk.
    """
    return tuple(_archimedean_q4_points())


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


def q4_bounce_order(
    inner: Sequence[Point],
    outer: Sequence[Point],
    start: Point = (0.0, 0.0),
) -> list[Point]:
    """Alternate nearest remaining inner / outer listen (ping-pong)."""
    inner_left = list(inner)
    outer_left = list(outer)
    cur = start
    want_inner = True
    ordered: list[Point] = [start]
    while inner_left or outer_left:
        if want_inner and inner_left:
            pool = inner_left
        elif (not want_inner) and outer_left:
            pool = outer_left
        elif inner_left:
            pool = inner_left
        else:
            pool = outer_left
        wp = min(pool, key=lambda p: dist(cur, p))
        pool.remove(wp)
        ordered.append(wp)
        cur = wp
        want_inner = dist(wp, (0.0, 0.0)) > INNER_R_MAX
    return ordered


def q4_bounce_waypoints() -> list[Point]:
    origin, inner, outer = covering_phases(directional_waypoints())
    return q4_bounce_order(inner, outer, origin)


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
    """Covering waypoints for Q4 (995+1865 route; no extra 900 m enroute stops)."""
    return list(waypoints if waypoints is not None else directional_waypoints())


def directional_front_cover_ok(
    waypoints: Sequence[Point] | None = None,
    cover_r: float = COVER_R,
    arena_r: float = ARENA_R,
    *,
    include_ring_enroute: bool = True,
) -> bool:
    """Directional no-blind-spot cover via the convex-hull criterion.

    ``include_ring_enroute`` is kept for API compatibility; the certificate
    route does not add 900 m stops.
    """
    del include_ring_enroute
    wps = q4_listen_set(waypoints)
    return directional_hull_cover_ok(wps, cover_r=cover_r, arena_r=arena_r)


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
