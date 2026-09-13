"""Directional AOA set corrector for Q4: heading-interval + worst-case 1000 m exclusion.

Does not replace Problem 1 ``locate_quality``. Empty / over-shrink / larger SEC
falls back to the uncorrected cone intersection.
"""

from __future__ import annotations

import math
from typing import Sequence

from candidate import (
    front_compatible,
    next_stations,
    recommend_second_sides_compact,
    to_body,
)
from geometry import (
    CLEAR_R,
    IntersectionResult,
    LocateQuality,
    Point,
    Q3_NO_SIGNAL_EXCLUSION_R,
    Q3_POSITIVE_RANGE_MAX,
    convex_hull,
    dist,
    intersect_feasible_region,
    locate_quality,
    point_in_convex_polygon,
    smallest_enclosing_circle,
)

HEAR_R_MAX = Q3_POSITIVE_RANGE_MAX  # 1500 m: still-might-hear upper bound
SILENCE_R = Q3_NO_SIGNAL_EXCLUSION_R  # 1000 m: if visible, must have been heard
HEADING_BINS = 720
_BIN = 360.0 / HEADING_BINS


def _bearing_deg(origin: Point, target: Point) -> float:
    return math.degrees(math.atan2(target[1] - origin[1], target[0] - origin[0]))


def _in_front(heading_deg: float, probe_bearing_deg: float) -> bool:
    rel = (probe_bearing_deg - heading_deg + 180.0) % 360.0 - 180.0
    return abs(rel) <= 90.0 + 1e-9


def heading_feasible(
    g: Point,
    hears: Sequence[Point],
    silences: Sequence[Point] | None = None,
    *,
    hear_r_max: float = HEAR_R_MAX,
    silence_r: float = SILENCE_R,
) -> bool:
    """True iff some heading at ``g`` explains every hear and every nearby silence."""
    if not hears:
        return True
    for s in hears:
        if dist(g, s) > hear_r_max + 1e-6:
            return False
    hear_brg = [_bearing_deg(g, s) for s in hears]
    silences = silences or []
    active_sil = [(q, _bearing_deg(g, q)) for q in silences if dist(g, q) <= silence_r + 1e-9]
    for i in range(HEADING_BINS):
        h = i * _BIN
        if any(not _in_front(h, a) for a in hear_brg):
            continue
        if any(_in_front(h, b) for _q, b in active_sil):
            continue
        return True
    return False


def heard_region(
    stations: Sequence[Point],
    bearings_deg: Sequence[float],
    delta_deg: float = 1.0,
) -> IntersectionResult:
    """Conservative outer envelope: AOA cones ∩ 1500 m disks ∩ arena."""
    return intersect_feasible_region(
        stations,
        bearings_deg,
        angle_half_width_deg=delta_deg,
    )


def _sample_convex(vertices: Sequence[Point], max_pts: int = 360) -> list[Point]:
    if not vertices:
        return []
    pts = list(vertices)
    n = len(vertices)
    for i in range(n):
        a, b = vertices[i], vertices[(i + 1) % n]
        for t in (0.25, 0.5, 0.75):
            pts.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
    xs = [v[0] for v in vertices]
    ys = [v[1] for v in vertices]
    minx, maxx = min(xs), max(xs)
    miny, maxy = min(ys), max(ys)
    span = max(maxx - minx, maxy - miny, 1.0)
    step = max(10.0, span / 10.0)
    for _ in range(8):
        grid: list[Point] = []
        x = minx
        while x <= maxx + 1e-9:
            y = miny
            while y <= maxy + 1e-9:
                p = (x, y)
                if point_in_convex_polygon(p, vertices):
                    grid.append(p)
                y += step
            x += step
        if len(pts) + len(grid) <= max_pts:
            pts.extend(grid)
            break
        step *= 1.4
    uniq: list[Point] = []
    for p in pts:
        if all(dist(p, q) > 0.5 for q in uniq):
            uniq.append(p)
    return uniq


def _dilate_in_poly(samples: Sequence[Point], vertices: Sequence[Point], step: float) -> list[Point]:
    out: list[Point] = []
    seen: set[tuple[int, int]] = set()
    scale = max(step, 8.0)
    offsets = (
        (0.0, 0.0),
        (scale, 0.0),
        (-scale, 0.0),
        (0.0, scale),
        (0.0, -scale),
        (scale, scale),
        (scale, -scale),
        (-scale, scale),
        (-scale, -scale),
    )
    for p in samples:
        for dx, dy in offsets:
            q = (p[0] + dx, p[1] + dy)
            key = (int(round(q[0] * 10)), int(round(q[1] * 10)))
            if key in seen:
                continue
            if point_in_convex_polygon(q, vertices):
                seen.add(key)
                out.append(q)
    return out


def locate_quality_dir(
    stations: Sequence[Point],
    bearings_deg: Sequence[float],
    silence: Sequence[Point] | None = None,
    delta_deg: float = 1.0,
    baseline: LocateQuality | None = None,
) -> tuple[LocateQuality, bool]:
    """Corrected locate quality. ``fallback=True`` means caller must keep ``baseline``."""
    base = baseline or locate_quality(
        stations, bearings_deg, delta_deg=delta_deg, silence=silence
    )
    if len(stations) < 2:
        return base, True
    env = heard_region(stations, bearings_deg, delta_deg=delta_deg)
    if env.empty or not env.bounded or len(env.vertices) < 3:
        return base, True
    hears = list(stations)
    silences = list(silence or [])
    samples = _sample_convex(env.vertices)
    feasible = [p for p in samples if heading_feasible(p, hears, silences)]
    if len(feasible) < 3:
        return base, True
    xs = [v[0] for v in env.vertices]
    ys = [v[1] for v in env.vertices]
    step = max(8.0, 0.08 * max(max(xs) - min(xs), max(ys) - min(ys), 1.0))
    dilated = _dilate_in_poly(feasible, env.vertices, step)
    hull = convex_hull(dilated)
    if len(hull) < 3:
        return base, True
    cen, rad = smallest_enclosing_circle(hull)
    if base.sec_radius < math.inf and rad > base.sec_radius + 1e-6:
        return base, True
    region = IntersectionResult(hull, bounded=True, empty=False)
    collinear = base.near_collinear
    if collinear:
        return (
            LocateQuality(region, cen, rad, False, True, True),
            False,
        )
    can = rad <= CLEAR_R + 1e-9 and heading_feasible(cen, hears, silences)
    return LocateQuality(region, cen, rad, can, need_another_fix=not can, near_collinear=False), False


def next_station_dir(
    s1: Point,
    theta_deg: float,
    now: Point | None = None,
    region_vertices: Sequence[Point] | None = None,
    silence: Sequence[Point] | None = None,
) -> Point | None:
    """Nearest compact front-lobe second station using ``R*`` for the heading guess."""
    now = now if now is not None else s1
    rho_g: float | None = None
    if region_vertices and len(region_vertices) >= 2:
        cen, _ = smallest_enclosing_circle(list(region_vertices))
        rho_g = max(to_body(s1, theta_deg, cen)[0], 80.0)
    compact = list(recommend_second_sides_compact(s1, theta_deg))
    compact.sort(key=lambda p: dist(p, now))
    for p in compact:
        if dist(p, s1) <= 5.0:
            continue
        if not front_compatible(s1, theta_deg, p, rho_g=rho_g):
            continue
        if silence and any(dist(p, q) < 35.0 for q in silence):
            continue
        return p
    extra = next_stations(
        s1,
        theta_deg,
        now=now,
        directional=True,
        silence=silence,
    )
    for p in extra:
        if dist(p, s1) > 5.0:
            return p
    return None
