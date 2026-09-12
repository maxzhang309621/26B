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
# Dense-certified shortest Q4 detection tour: heptagon inner + dodecagon outer.
Q4_OPT_INNER_N = 7
Q4_OPT_OUTER_N = 12
Q4_OPT_OUTER_R = 1865.0
Q4_OPT_ALIGN = "radial"
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
    the way to the inner ring (policy), not a separate mid ring.
    A 12-point ring at 2100 m keeps a listen in the 180° front half-plane.
    Default Q4 inner stays origin + 8×1200 m. Hexbatch uses Q3 hexagon inner
    via ``q4_hexagon_waypoints``; six inner points alone fail front-cover.
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


def q4_hexagon_waypoints(
    outer_r: float = OUTER_RING_R,
    outer_n: int = OUTER_RING_N,
) -> list[Point]:
    """Q4 hexbatch cover: Q3 hexagon inner plus the directional outer ring."""
    return directional_waypoints(
        inner=q3_waypoints(),
        outer_r=outer_r,
        outer_n=outer_n,
    )


def q4_listen_set(waypoints: Sequence[Point] | None = None) -> list[Point]:
    """Covering waypoints plus the 900 m enroute stops used by HuntPolicy."""
    pts = list(waypoints if waypoints is not None else directional_waypoints())
    for k in range(OMNI_RING_N):
        a = 2.0 * math.pi * k / OMNI_RING_N
        pts.append((ENROUTE_R * math.cos(a), ENROUTE_R * math.sin(a)))
    return pts


def q4_hex_listen_set(waypoints: Sequence[Point] | None = None) -> list[Point]:
    """Hexbatch covering set: the exact search waypoints, no extra 900 m ring."""
    return list(waypoints if waypoints is not None else q4_opt_search_waypoints())


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
    return _front_cover_ok_on(
        wps,
        cover_r=cover_r,
        arena_r=arena_r,
        n_radial=n_radial,
        n_ang=n_ang,
        n_headings=n_headings,
    )


def _front_cover_ok_on(
    listens: Sequence[Point],
    cover_r: float = COVER_R,
    arena_r: float = ARENA_R,
    *,
    n_radial: int = 6,
    n_ang: int = 48,
    n_headings: int = 24,
) -> bool:
    """Directional front-disk cover on an exact listen set (no extra enroute)."""
    wps = list(listens)
    headings = [i * (360.0 / n_headings) for i in range(n_headings)]
    for g in _sample_disk(arena_r, n_radial=n_radial, n_ang=n_ang):
        for h in headings:
            if not any(
                dist(w, g) <= cover_r + 1e-6 and _in_front_halfplane(g, h, w) for w in wps
            ):
                return False
    return True


def _regular_polygon(radius: float, n: int, phase_rad: float = 0.0) -> list[Point]:
    if n < 1:
        return []
    return [
        (
            radius * math.cos(2.0 * math.pi * k / n + phase_rad),
            radius * math.sin(2.0 * math.pi * k / n + phase_rad),
        )
        for k in range(n)
    ]


def q4_outer_phase_rad(n_inner: int, n_outer: int, align: str) -> float:
    """Outer ring phase relative to inner vertices at phase 0.

    radial: share the 0° ray (inner rays are a subset when n_outer is a multiple).
    stagger: shift by half an outer step so vertices sit in each other's gaps.
    """
    del n_inner
    if align == "stagger":
        return math.pi / n_outer if n_outer else 0.0
    if align != "radial":
        raise ValueError("align must be 'radial' or 'stagger'")
    return 0.0


def q4_double_ring_waypoints(
    n_inner: int,
    inner_r: float,
    n_outer: int,
    outer_r: float,
    *,
    align: str = "radial",
    inner_phase_rad: float = 0.0,
    enroute_r: float | None = ENROUTE_R,
) -> list[Point]:
    """Origin + optional inner-ray enroute + inner n-gon + outer m-gon."""
    if n_inner < 1 or n_outer < 1:
        raise ValueError("ring vertex counts must be positive")
    outer_phase = inner_phase_rad + q4_outer_phase_rad(n_inner, n_outer, align)
    pts: list[Point] = [(0.0, 0.0)]
    inner = _regular_polygon(inner_r, n_inner, inner_phase_rad)
    if enroute_r is not None and enroute_r > 1e-9:
        pts.extend(_regular_polygon(enroute_r, n_inner, inner_phase_rad))
    pts.extend(inner)
    pts.extend(_regular_polygon(outer_r, n_outer, outer_phase))
    return pts


def q4_opt_inner_r(arena_r: float = ARENA_R, cover_r: float = COVER_R) -> float:
    """Shortest heptagon circumradius that already omni-covers with the origin."""
    interval = regular_ring_rho_interval(Q4_OPT_INNER_N, arena_r=arena_r, cover_r=cover_r)
    if interval is None:
        raise RuntimeError("n=7 must admit an omni ring interval for 1800/1000")
    return interval[0]


def q4_opt_search_waypoints(
    *,
    outer_r: float = Q4_OPT_OUTER_R,
    outer_n: int = Q4_OPT_OUTER_N,
) -> list[Point]:
    """Minimum-time dense-feasible Q4 listen set: 7×ρ_min + 12×1865, same radial, no extra 900 m ring."""
    return q4_double_ring_waypoints(
        Q4_OPT_INNER_N,
        q4_opt_inner_r(),
        outer_n,
        outer_r,
        align=Q4_OPT_ALIGN,
        enroute_r=None,
    )


def q4_double_ring_cover_ok(
    n_inner: int,
    inner_r: float,
    n_outer: int,
    outer_r: float,
    *,
    align: str = "radial",
    inner_phase_rad: float = 0.0,
    enroute_r: float | None = ENROUTE_R,
    cover_r: float = COVER_R,
    arena_r: float = ARENA_R,
    n_radial: int = 6,
    n_ang: int = 48,
    n_headings: int = 24,
) -> dict[str, bool]:
    """Omni disk cover and directional front-disk cover on the exact listen set."""
    listens = q4_double_ring_waypoints(
        n_inner,
        inner_r,
        n_outer,
        outer_r,
        align=align,
        inner_phase_rad=inner_phase_rad,
        enroute_r=enroute_r,
    )
    omni = coverage_ok(listens, cover_r=cover_r, arena_r=arena_r)
    directional = _front_cover_ok_on(
        listens,
        cover_r=cover_r,
        arena_r=arena_r,
        n_radial=n_radial,
        n_ang=n_ang,
        n_headings=n_headings,
    )
    return {"omni": omni, "directional": directional, "ok": omni and directional}


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


def nearest_open_path_channel_order(start: Point, points: dict[int, Point]) -> list[int]:
    """Pin the first hop to the nearest city, then open TSP the rest.

    Euclidean open TSP may leave a nearby isolated city for last when a far
    cluster is cheaper overall.  Pinning the nearest hop forbids that skip;
    the Held–Karp tail is still the shortest path through the remainder.
    """
    if not points:
        return []
    nearest = min(points, key=lambda c: (dist(start, points[c]), c))
    rest = {c: p for c, p in points.items() if c != nearest}
    if not rest:
        return [nearest]
    return [nearest] + open_path_channel_order(points[nearest], rest)


def no_skip_open_path_channel_order(
    start: Point,
    points: dict[int, Point],
    local_m: float = 650.0,
) -> list[int]:
    """Visit every nearby city before any far city; TSP inside each group.

    Local = within ``local_m`` of ``start``.  This is a two-level open
    Hamiltonian path: nearest-pinned TSP on the local cluster, then
    nearest-pinned TSP on the far cluster from the last local city.
    """
    if not points:
        return []
    local = {c: p for c, p in points.items() if dist(start, p) <= local_m + 1e-9}
    far = {c: p for c, p in points.items() if c not in local}
    if not local:
        return nearest_open_path_channel_order(start, points)
    order = nearest_open_path_channel_order(start, local)
    if not far:
        return order
    last = local[order[-1]]
    return order + nearest_open_path_channel_order(last, far)


def open_path_order(start: Point, pts: Sequence[Point]) -> list[Point]:
    """Open Held–Karp path from start through pts (n≤16); NN+2-opt if larger."""
    pts = list(pts)
    n = len(pts)
    if n <= 1:
        return pts
    if n > 16:
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


def q4_double_ring_path_m(
    n_inner: int,
    inner_r: float,
    n_outer: int,
    outer_r: float,
    *,
    align: str = "radial",
    inner_phase_rad: float = 0.0,
    enroute_r: float | None = ENROUTE_R,
) -> float:
    """Serial concentric tour: origin → enroute ring → inner ring → outer ring.

    Same-radial layouts jump along a shared ray; stagger pays the chord to the
    nearest outer vertex. No return to the origin (search then clear).
    """
    origin = (0.0, 0.0)
    inner_phase = inner_phase_rad
    outer_phase = inner_phase + q4_outer_phase_rad(n_inner, n_outer, align)
    inner = _regular_polygon(inner_r, n_inner, inner_phase)
    outer = _regular_polygon(outer_r, n_outer, outer_phase)
    tour: list[Point] = [origin]
    if enroute_r is not None and enroute_r > 1e-9:
        enroute = _regular_polygon(enroute_r, n_inner, inner_phase)
        tour.extend(enroute)
    tour.extend(inner)
    tour.extend(outer)
    return _path_length(tour[0], tour[1:])


def q4_double_ring_search_time(
    n_inner: int,
    inner_r: float,
    n_outer: int,
    outer_r: float,
    *,
    align: str = "radial",
    inner_phase_rad: float = 0.0,
    enroute_r: float | None = ENROUTE_R,
    speed_mps: float = SPEED_MPS,
    n_radial: int = 6,
    n_ang: int = 48,
    n_headings: int = 24,
    check_cover: bool = True,
) -> dict[str, float | int | bool | str | None]:
    """Worst-case detection-tour virtual time for a Q4 double ring.

    Every listen stop except the origin pays a full 20-channel sweep (unknown
    channels remain). Coverage is the exact listen set, not the extra 8×900
    points injected by ``q4_listen_set``.
    """
    n_enroute = n_inner if enroute_r is not None and enroute_r > 1e-9 else 0
    n_stops = 1 + n_enroute + n_inner + n_outer
    path_m = q4_double_ring_path_m(
        n_inner,
        inner_r,
        n_outer,
        outer_r,
        align=align,
        inner_phase_rad=inner_phase_rad,
        enroute_r=enroute_r,
    )
    travel_s = path_m / speed_mps
    dwell_s = origin_full_sweep_s() + (n_stops - 1) * ring_full_sweep_s()
    detect_s = n_stops * N_CHANNELS * DETECT_S
    switch_s = (N_CHANNELS - 1) * SWITCH_S + (n_stops - 1) * N_CHANNELS * SWITCH_S
    cover = {"omni": None, "directional": None, "ok": True}
    if check_cover:
        cover = q4_double_ring_cover_ok(
            n_inner,
            inner_r,
            n_outer,
            outer_r,
            align=align,
            inner_phase_rad=inner_phase_rad,
            enroute_r=enroute_r,
            n_radial=n_radial,
            n_ang=n_ang,
            n_headings=n_headings,
        )
    return {
        "n_inner": n_inner,
        "n_outer": n_outer,
        "inner_r": inner_r,
        "outer_r": outer_r,
        "align": align,
        "enroute_r": enroute_r,
        "n_enroute": n_enroute,
        "n_stops": n_stops,
        "feasible": bool(cover["ok"]),
        "omni_ok": cover["omni"],
        "dir_ok": cover["directional"],
        "path_m": path_m,
        "travel_s": travel_s,
        "dwell_s": dwell_s,
        "detect_s": detect_s,
        "switch_s": switch_s,
        "total_s": travel_s + dwell_s,
    }


def q4_min_outer_radius(
    n_inner: int,
    inner_r: float,
    n_outer: int,
    *,
    align: str = "radial",
    enroute_r: float | None = ENROUTE_R,
    inner_phase_rad: float = 0.0,
    candidates: Sequence[float] | None = None,
    n_radial: int = 4,
    n_ang: int = 24,
    n_headings: int = 12,
) -> float | None:
    """Smallest sampled outer circumradius that omni- and front-covers.

    Feasible outer radii form an interval: too close sits behind outward
    boundary sources, too far exceeds r_eff=1000 m.  ``r_hi = arena+cover``
    is therefore not a safe upper oracle.
    """
    if candidates is None:
        candidates = (
            1865.0,
            1900.0,
            1950.0,
            2000.0,
            2050.0,
            2100.0,
            2150.0,
            2200.0,
            2300.0,
            2400.0,
            2500.0,
        )
    kwargs = dict(
        n_inner=n_inner,
        inner_r=inner_r,
        n_outer=n_outer,
        align=align,
        inner_phase_rad=inner_phase_rad,
        enroute_r=enroute_r,
        n_radial=n_radial,
        n_ang=n_ang,
        n_headings=n_headings,
    )
    for outer_r in candidates:
        if q4_double_ring_cover_ok(outer_r=outer_r, **kwargs)["ok"]:
            return float(outer_r)
    return None


def q4_enumerate_double_rings(
    *,
    inner_ns: Sequence[int] = (6, 7, 8, 9, 10, 12),
    outer_ns: Sequence[int] = (8, 10, 11, 12, 14, 16),
    aligns: Sequence[str] = ("radial", "stagger"),
    enroute_radii: Sequence[float | None] = (None, ENROUTE_R),
    inner_radii: Sequence[float] | None = None,
    certify: bool = True,
) -> list[dict[str, float | int | bool | str | None]]:
    """Enumerate regular inner/outer n-gons; keep covering layouts, min outer radius."""
    if inner_radii is None:
        inner_radii = (1000.0, 1123.0, 1150.0, 1200.0)
    rows: list[dict[str, float | int | bool | str | None]] = []
    seen: set[tuple] = set()
    for n_in in inner_ns:
        radii = list(inner_radii)
        interval = regular_ring_rho_interval(n_in)
        if interval is not None:
            radii.append(interval[0])
        for inner_r in sorted(set(round(r, 3) for r in radii)):
            for n_out in outer_ns:
                for align in aligns:
                    for enroute_r in enroute_radii:
                        key = (n_in, inner_r, n_out, align, enroute_r)
                        if key in seen:
                            continue
                        seen.add(key)
                        outer_r = q4_min_outer_radius(
                            n_in,
                            inner_r,
                            n_out,
                            align=align,
                            enroute_r=enroute_r,
                        )
                        if outer_r is None:
                            continue
                        row = q4_double_ring_search_time(
                            n_in,
                            inner_r,
                            n_out,
                            outer_r,
                            align=align,
                            enroute_r=enroute_r,
                            check_cover=certify,
                            n_radial=6,
                            n_ang=48,
                            n_headings=24,
                        )
                        if row["feasible"]:
                            rows.append(row)
    rows.sort(key=lambda r: (float(r["total_s"]), int(r["n_stops"]), float(r["path_m"])))
    return rows
