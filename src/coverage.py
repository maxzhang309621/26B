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
Q4_OUTER_FULL_R = OUTER_RING_R
Q4_OUTER_FULL_N = OUTER_RING_N
Q4_OUTER_LITE_R = 1900.0
Q4_OUTER_LITE_N = 11
Q4_DIR_FULL_OUTER_MIN = 8
ENROUTE_R = 900.0
INNER_R_MAX = 1550.0  # origin / 1200 m ring / optional mid ring vs outer ring


def pick_q4_outer_ring(
    omni_n: int | None,
    dir_n: int | None,
    *,
    jammer_count: int | None = None,
    pure: bool = False,
) -> tuple[float, int]:
    """Pick outer ring after /enter (Q4-only; not Q3 route logic).

    pure=False (v2):
      - 0 directional → skip outer
      - directional >= 8 → 12×2100
      - else → 11×1900
    pure=True: only dir>=6 full else lite (always keep outer ring).
    """
    if dir_n is None or omni_n is None:
        return Q4_OUTER_FULL_R, Q4_OUTER_FULL_N
    if not pure and dir_n <= 0:
        return Q4_OUTER_LITE_R, 0
    if dir_n >= Q4_DIR_FULL_OUTER_MIN:
        return Q4_OUTER_FULL_R, Q4_OUTER_FULL_N
    return Q4_OUTER_LITE_R, Q4_OUTER_LITE_N


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
    *,
    dense: bool = False,
    n_radial: int | None = None,
    n_ang: int | None = None,
    n_headings: int | None = None,
) -> bool:
    """Every sampled pose has a listen point in its 180° front disk of radius cover_r.

    This is the directional-sensor covering condition (Ma & Liu style sector
    coverage): a source is heard only if a waypoint lies in heading ±90° and
    within r_eff. Enroute 900 m stops are included for near-center outward sources.
    dense=True uses the paper-figure grid (16 radial × 180 angular × 36 headings).
    """
    wps = q4_listen_set(waypoints)
    if dense:
        n_radial = 16 if n_radial is None else n_radial
        n_ang = 180 if n_ang is None else n_ang
        n_headings = 36 if n_headings is None else n_headings
    else:
        n_radial = 6 if n_radial is None else n_radial
        n_ang = 48 if n_ang is None else n_ang
        n_headings = 24 if n_headings is None else n_headings
    headings = [i * (360.0 / n_headings) for i in range(n_headings)]
    for g in _sample_disk(arena_r, n_radial=n_radial, n_ang=n_ang):
        for h in headings:
            if not any(
                dist(w, g) <= cover_r + 1e-6 and _in_front_halfplane(g, h, w) for w in wps
            ):
                return False
    return True


def sector_fused_order(waypoints: Sequence[Point], n_bins: int = OUTER_RING_N) -> list[Point]:
    """Polar Morse / radial-cell zigzag: even bins out, odd bins in.

    Origin is dropped; caller should scan the origin first.  Existing Q4 listen
    points are reused (900 / 1200 / 2100); only the visit topology changes.
    """
    if n_bins < 1:
        raise ValueError("n_bins must be positive")
    rest = [p for p in waypoints if dist(p, (0.0, 0.0)) > 1e-6]
    bins: list[list[Point]] = [[] for _ in range(n_bins)]
    for p in rest:
        ang = math.atan2(p[1], p[0]) % (2.0 * math.pi)
        k = int(ang * n_bins / (2.0 * math.pi)) % n_bins
        bins[k].append(p)
    out: list[Point] = []
    for k, group in enumerate(bins):
        group = sorted(group, key=lambda q: dist(q, (0.0, 0.0)))
        if k % 2 == 1:
            group.reverse()
        out.extend(group)
    return out


def open_path_cost(start: Point, order: Sequence[Point]) -> float:
    """Length of an open path start → order[0] → … → order[-1]."""
    return _path_length(start, order)


def open_path_channel_order(start: Point, points: dict[int, Point]) -> list[int]:
    """Open shortest-path visit order of labeled points from ``start``."""
    if not points:
        return []
    channels = list(points)
    ordered_pts = open_path_order(start, [points[c] for c in channels])
    remaining = set(channels)
    out: list[int] = []
    for p in ordered_pts:
        ch = min(remaining, key=lambda c: (dist(points[c], p), c))
        remaining.remove(ch)
        out.append(ch)
    if remaining:
        out.extend(sorted(remaining, key=lambda c: (dist(start, points[c]), c)))
    return out


def open_path_order(start: Point, pts: Sequence[Point]) -> list[Point]:
    """Open Held–Karp path from start through pts (n≤12); NN+2-opt if larger."""
    pts = list(pts)
    n = len(pts)
    if n <= 1:
        return pts
    if n > 12:
        return _open_nn_two_opt(start, pts)
    nodes = [start, *pts]
    m = n + 1
    inf = float("inf")
    dist_m = [[dist(nodes[i], nodes[j]) for j in range(m)] for i in range(m)]
    nmask = 1 << m
    dp = [[inf] * m for _ in range(nmask)]
    parent = [[-1] * m for _ in range(nmask)]
    dp[1][0] = 0.0
    for mask in range(nmask):
        if mask & 1 == 0:
            continue
        for j in range(m):
            if mask & (1 << j) == 0 or dp[mask][j] >= inf:
                continue
            for k in range(1, m):
                if mask & (1 << k):
                    continue
                nxt = mask | (1 << k)
                cost = dp[mask][j] + dist_m[j][k]
                if cost < dp[nxt][k]:
                    dp[nxt][k] = cost
                    parent[nxt][k] = j
    full = nmask - 1
    end = min(range(1, m), key=lambda j: dp[full][j])
    order_idx: list[int] = []
    mask, j = full, end
    while j > 0:
        order_idx.append(j)
        prev = parent[mask][j]
        mask ^= 1 << j
        j = prev
    order_idx.reverse()
    return [nodes[i] for i in order_idx]


def _path_length(start: Point, order: Sequence[Point]) -> float:
    if not order:
        return 0.0
    total = dist(start, order[0])
    for i in range(1, len(order)):
        total += dist(order[i - 1], order[i])
    return total


def _open_nn_two_opt(start: Point, pts: Sequence[Point]) -> list[Point]:
    remaining = set(range(len(pts)))
    order: list[Point] = []
    cur = start
    while remaining:
        j = min(remaining, key=lambda i: dist(cur, pts[i]))
        remaining.remove(j)
        order.append(pts[j])
        cur = pts[j]
    improved = True
    while improved:
        improved = False
        best = _path_length(start, order)
        for i in range(len(order) - 1):
            for j in range(i + 1, len(order)):
                cand = order[:i] + list(reversed(order[i : j + 1])) + order[j + 1 :]
                length = _path_length(start, cand)
                if length + 1e-9 < best:
                    order = cand
                    best = length
                    improved = True
                    break
            if improved:
                break
    return order


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


# Origin + regular n-gon listen tour (problem 3 coverage ring).
DETECT_S = 5.0
SWITCH_S = 1.0
SPEED_MPS = 5.0
N_CHANNELS = 20


def regular_ring_rho_interval(
    n: int,
    arena_r: float = ARENA_R,
    cover_r: float = COVER_R,
) -> tuple[float, float] | None:
    """Feasible circumradius interval for origin + regular n-gon covering the disk.

    A point in the annulus [cover_r, arena_r] is farthest from both the origin and
    the ring at an angular bisector. Convexity of squared distance in radius reduces
    coverage to the two endpoints. The outer endpoint is coverable iff
    ``arena_r * sin(π/n) ≤ cover_r`` (hence n≥6 for 1800/1000). Inner-gap coverage
    requires ``ρ ≤ 2 cover_r cos(π/n)``.
    """
    if n < 3:
        raise ValueError("n must be at least 3")
    half = math.pi / n
    cosine = math.cos(half)
    sine = math.sin(half)
    disc = cover_r * cover_r - arena_r * arena_r * sine * sine
    if disc < 0.0:
        return None
    delta = math.sqrt(disc)
    lo = arena_r * cosine - delta
    hi = min(arena_r * cosine + delta, 2.0 * cover_r * cosine)
    if lo > hi + 1e-9:
        return None
    return (max(0.0, lo), max(0.0, hi))


def regular_ring_open_path_m(n: int, ring_r: float) -> float:
    """Origin → n vertices in cyclic order, no return (search then clear)."""
    side = 2.0 * ring_r * math.sin(math.pi / n)
    return ring_r + (n - 1) * side


def origin_full_sweep_s(
    n_channels: int = N_CHANNELS,
    detect_s: float = DETECT_S,
    switch_s: float = SWITCH_S,
) -> float:
    """Dwell at origin after /enter (tuned to channel 1): first channel has no switch."""
    if n_channels < 1:
        return 0.0
    return detect_s + (n_channels - 1) * (switch_s + detect_s)


def ring_full_sweep_s(
    n_channels: int = N_CHANNELS,
    detect_s: float = DETECT_S,
    switch_s: float = SWITCH_S,
) -> float:
    """Dwell at a later stop that must sweep every still-unknown channel.

    Arriving from channel 20 to channel 1 pays a switch on the first measure.
    """
    return n_channels * (switch_s + detect_s)


def regular_ring_search_time(
    n: int,
    ring_r: float | None = None,
    *,
    arena_r: float = ARENA_R,
    cover_r: float = COVER_R,
    speed_mps: float = SPEED_MPS,
) -> dict[str, float | int | bool | None]:
    """Coverage-tour virtual time: travel + origin 1–20 sweep + full sweep at each vertex.

    ``ring_r=None`` selects the shortest feasible circumradius (travel is increasing
    in ρ). Unused channels stay unknown, so a coverage guarantee still listens to
    all 20 at every ring stop in the worst case.
    """
    interval = regular_ring_rho_interval(n, arena_r=arena_r, cover_r=cover_r)
    if interval is None:
        return {
            "n": n,
            "feasible": False,
            "ring_r": None,
            "rho_min": None,
            "rho_max": None,
            "path_m": None,
            "travel_s": None,
            "detect_s": None,
            "switch_s": None,
            "dwell_s": None,
            "total_s": None,
        }
    lo, hi = interval
    rho = lo if ring_r is None else float(ring_r)
    feasible = lo - 1e-9 <= rho <= hi + 1e-9
    path_m = regular_ring_open_path_m(n, rho)
    travel_s = path_m / speed_mps
    origin_detect = N_CHANNELS * DETECT_S
    origin_switch = (N_CHANNELS - 1) * SWITCH_S
    ring_detect = n * N_CHANNELS * DETECT_S
    ring_switch = n * N_CHANNELS * SWITCH_S
    detect_s = origin_detect + ring_detect
    switch_s = origin_switch + ring_switch
    dwell_s = origin_full_sweep_s() + n * ring_full_sweep_s()
    return {
        "n": n,
        "feasible": feasible,
        "ring_r": rho,
        "rho_min": lo,
        "rho_max": hi,
        "path_m": path_m,
        "travel_s": travel_s,
        "detect_s": detect_s,
        "switch_s": switch_s,
        "dwell_s": dwell_s,
        "total_s": travel_s + dwell_s,
    }
