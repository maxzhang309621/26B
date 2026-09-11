"""Problem 1 geometry: bearing cones, intersection polygon, diameter, SEC."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Iterable, Sequence

Point = tuple[float, float]
DEG = math.pi / 180.0
CLIP = 1_000_000.0
EPS = 1e-9
Q3_ANGLE_HALF_WIDTH_DEG = 1.01
Q3_ARENA_R = 1800.0
Q3_POSITIVE_RANGE_MAX = 1500.0
Q3_NO_SIGNAL_EXCLUSION_R = 1000.0
Q3_CIRCLE_SIDES = 96


def _ang_norm_deg(deg: float) -> float:
    x = deg % 360.0
    return x if x >= 0.0 else x + 360.0


def unit(deg: float) -> Point:
    a = _ang_norm_deg(deg) * DEG
    return (math.cos(a), math.sin(a))


def sub(a: Point, b: Point) -> Point:
    return (a[0] - b[0], a[1] - b[1])


def add(a: Point, b: Point) -> Point:
    return (a[0] + b[0], a[1] + b[1])


def scale(a: Point, s: float) -> Point:
    return (a[0] * s, a[1] * s)


def dot(a: Point, b: Point) -> float:
    return a[0] * b[0] + a[1] * b[1]


def cross(a: Point, b: Point) -> float:
    return a[0] * b[1] - a[1] * b[0]


def dist(a: Point, b: Point) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def dist2(a: Point, b: Point) -> float:
    dx, dy = a[0] - b[0], a[1] - b[1]
    return dx * dx + dy * dy


@dataclass(frozen=True)
class HalfPlane:
    """Closed half-plane: cross(direction, p - origin) has the required sign."""

    origin: Point
    direction: Point  # boundary ray direction
    keep_left: bool  # True: cross(direction, p-origin) >= -EPS

    def contains(self, p: Point) -> bool:
        cr = cross(self.direction, sub(p, self.origin))
        if self.keep_left:
            return cr >= -EPS
        return cr <= EPS

    def line_point(self) -> Point:
        return self.origin

    def line_dir(self) -> Point:
        return self.direction


def cone_halfplanes(station: Point, bearing_deg: float, delta_deg: float = 1.0) -> tuple[HalfPlane, HalfPlane]:
    right = unit(bearing_deg - delta_deg)
    left = unit(bearing_deg + delta_deg)
    # v is CCW from right edge; v is CW from left edge
    return (
        HalfPlane(station, right, keep_left=True),
        HalfPlane(station, left, keep_left=False),
    )


def _line_intersect(p: Point, d: Point, q: Point, e: Point) -> Point | None:
    """Intersection of p + s d and q + t e."""
    den = cross(d, e)
    if abs(den) < 1e-14:
        return None
    w = sub(q, p)
    s = cross(w, e) / den
    return add(p, scale(d, s))


def _clip_box_planes() -> list[HalfPlane]:
    # inward: from bottom side going +x, keep left (above)
    return [
        HalfPlane((-CLIP, -CLIP), (1.0, 0.0), True),   # bottom, keep north
        HalfPlane((CLIP, -CLIP), (0.0, 1.0), True),    # right, keep west
        HalfPlane((CLIP, CLIP), (-1.0, 0.0), True),    # top, keep south
        HalfPlane((-CLIP, CLIP), (0.0, -1.0), True),   # left, keep east
    ]


def _circumscribed_polygon(center: Point, radius: float, sides: int) -> list[Point]:
    """Regular polygon that conservatively contains a disk."""
    if sides < 8:
        raise ValueError("sides must be at least 8")
    vertex_r = radius / math.cos(math.pi / sides)
    return [
        add(center, scale(unit((k + 0.5) * 360.0 / sides), vertex_r))
        for k in range(sides)
    ]


def clip_polygon_halfplane(vertices: Sequence[Point], hp: HalfPlane) -> list[Point]:
    """Sutherland-Hodgman clipping against one closed half-plane."""
    if not vertices:
        return []
    out: list[Point] = []
    prev = vertices[-1]
    prev_inside = hp.contains(prev)
    for cur in vertices:
        cur_inside = hp.contains(cur)
        if cur_inside != prev_inside:
            hit = _line_intersect(prev, sub(cur, prev), hp.origin, hp.direction)
            if hit is not None:
                out.append(hit)
        if cur_inside:
            out.append(cur)
        prev, prev_inside = cur, cur_inside
    return _unique_points(out)


def _disk_outer_halfplanes(center: Point, radius: float, sides: int) -> list[HalfPlane]:
    """Tangent half-planes whose intersection contains the exact disk."""
    planes: list[HalfPlane] = []
    for k in range(sides):
        normal = unit(k * 360.0 / sides)
        boundary = add(center, scale(normal, radius))
        tangent = (-normal[1], normal[0])
        # cross(tangent, p-boundary) = -dot(normal, p-boundary);
        # keep_left therefore keeps dot(normal, p-center) <= radius.
        planes.append(HalfPlane(boundary, tangent, keep_left=True))
    return planes


def point_in_convex_polygon(p: Point, vertices: Sequence[Point]) -> bool:
    """Boundary-inclusive containment for a consistently oriented convex polygon."""
    if not vertices:
        return False
    if len(vertices) == 1:
        return dist(p, vertices[0]) <= EPS
    signs: list[float] = []
    for a, b in zip(vertices, list(vertices[1:]) + [vertices[0]]):
        cr = cross(sub(b, a), sub(p, a))
        if abs(cr) > EPS:
            signs.append(cr)
    return not signs or min(signs) >= -EPS or max(signs) <= EPS


def optical_grid_centers(
    vertices: Sequence[Point],
    cell: float = 25.0,
    *,
    max_cells: int = 96,
) -> list[Point]:
    """Centers of ``cell``×``cell`` squares that intersect a convex feasible polygon.

    Half-diagonal of a 25 m cell is ``25√2/2 ≈ 17.68 < 20``, so a successful
    clear at a center covers that whole cell.  Intended as a finite optical
    fallback over an already-shrunk AOA region — not a full-arena raster.
    """
    if cell <= 0.0 or len(vertices) < 2:
        return []
    xs = [v[0] for v in vertices]
    ys = [v[1] for v in vertices]
    pad = 0.5 * cell
    x0 = math.floor((min(xs) - pad) / cell) * cell
    x1 = math.ceil((max(xs) + pad) / cell) * cell
    y0 = math.floor((min(ys) - pad) / cell) * cell
    y1 = math.ceil((max(ys) + pad) / cell) * cell
    half = 0.5 * cell
    centers: list[Point] = []
    y = y0 + half
    while y <= y1 + 1e-9:
        x = x0 + half
        while x <= x1 + 1e-9:
            c = (x, y)
            corners = (
                (x - half, y - half),
                (x - half, y + half),
                (x + half, y - half),
                (x + half, y + half),
            )
            hit = point_in_convex_polygon(c, vertices) or any(
                point_in_convex_polygon(q, vertices) for q in corners
            )
            if not hit:
                hit = any(
                    abs(v[0] - x) <= half + EPS and abs(v[1] - y) <= half + EPS
                    for v in vertices
                )
            if hit:
                centers.append(c)
            x += cell
        y += cell
    if len(centers) <= max_cells:
        return centers
    # Prefer cells near the polygon centroid when the region is still large.
    cx = sum(v[0] for v in vertices) / len(vertices)
    cy = sum(v[1] for v in vertices) / len(vertices)
    centers.sort(key=lambda p: dist(p, (cx, cy)))
    return centers[:max_cells]


def intersect_feasible_region(
    stations: Sequence[Point],
    bearings_deg: Sequence[float],
    angle_half_width_deg: float = Q3_ANGLE_HALF_WIDTH_DEG,
    arena_radius: float = Q3_ARENA_R,
    positive_range_max: float = Q3_POSITIVE_RANGE_MAX,
    circle_sides: int = Q3_CIRCLE_SIDES,
) -> "IntersectionResult":
    """Conservative convex outer envelope for Q3 positive observations.

    Exact disks are replaced by circumscribed regular polygons. The result thus
    contains every physically feasible source, so its enclosing circle is safe
    for a clear certificate.
    """
    if len(stations) != len(bearings_deg):
        raise ValueError("stations and bearings must have the same length")
    polygon = _circumscribed_polygon((0.0, 0.0), arena_radius, circle_sides)
    for station, bearing in zip(stations, bearings_deg):
        for hp in cone_halfplanes(station, bearing, angle_half_width_deg):
            polygon = clip_polygon_halfplane(polygon, hp)
            if not polygon:
                return IntersectionResult([], bounded=True, empty=True)
        for hp in _disk_outer_halfplanes(station, positive_range_max, circle_sides):
            polygon = clip_polygon_halfplane(polygon, hp)
            if not polygon:
                return IntersectionResult([], bounded=True, empty=True)
    hull = convex_hull(polygon)
    return IntersectionResult(hull, bounded=True, empty=not hull)


def entirely_excluded_by_no_signal(
    vertices: Sequence[Point],
    no_signal_sites: Sequence[Point],
    exclusion_radius: float = Q3_NO_SIGNAL_EXCLUSION_R,
) -> bool:
    """Detect a contradiction; never use this non-convex fact to certify a clear."""
    return bool(vertices) and any(
        all(dist(v, site) <= exclusion_radius + EPS for v in vertices)
        for site in no_signal_sites
    )


def plausible_vertices_after_no_signal(
    vertices: Sequence[Point],
    no_signal_sites: Sequence[Point],
    exclusion_radius: float = Q3_NO_SIGNAL_EXCLUSION_R,
) -> list[Point]:
    """Heuristic vertices outside every proven no-signal exclusion disk."""
    return [
        v
        for v in vertices
        if all(dist(v, site) > exclusion_radius + EPS for site in no_signal_sites)
    ]

@dataclass
class IntersectionResult:
    vertices: list[Point]
    bounded: bool
    empty: bool

    @property
    def diameter(self) -> float:
        if self.empty:
            return float("nan")
        if not self.bounded:
            return float("inf")
        return polygon_diameter(self.vertices)


def intersect_cones(
    stations: Sequence[Point],
    bearings_deg: Sequence[float],
    delta_deg: float = 1.0,
    clip: bool = True,
) -> IntersectionResult:
    if len(stations) != len(bearings_deg):
        raise ValueError("stations and bearings must have the same length")
    planes: list[HalfPlane] = []
    for s, th in zip(stations, bearings_deg):
        planes.extend(cone_halfplanes(s, th, delta_deg))
    if clip:
        planes.extend(_clip_box_planes())
    verts: list[Point] = []
    n = len(planes)
    for i in range(n):
        for j in range(i + 1, n):
            p = _line_intersect(planes[i].origin, planes[i].direction, planes[j].origin, planes[j].direction)
            if p is None:
                continue
            if abs(p[0]) > CLIP + 1 or abs(p[1]) > CLIP + 1:
                continue
            if all(hp.contains(p) for hp in planes):
                verts.append(p)
    verts = _unique_points(verts)
    if not verts:
        return IntersectionResult([], bounded=True, empty=True)
    hull = convex_hull(verts)
    bounded = True
    if clip:
        for x, y in hull:
            if abs(abs(x) - CLIP) < 1e-3 or abs(abs(y) - CLIP) < 1e-3:
                bounded = False
                break
    return IntersectionResult(hull, bounded=bounded, empty=False)


def _unique_points(pts: Iterable[Point], tol: float = 1e-7) -> list[Point]:
    out: list[Point] = []
    for p in pts:
        if all(dist(p, q) > tol for q in out):
            out.append(p)
    return out


def convex_hull(points: Sequence[Point]) -> list[Point]:
    pts = _unique_points(points)
    if len(pts) <= 1:
        return list(pts)
    pts = sorted(pts)
    def build(seq: Sequence[Point]) -> list[Point]:
        h: list[Point] = []
        for p in seq:
            while len(h) >= 2 and cross(sub(h[-1], h[-2]), sub(p, h[-1])) <= EPS:
                h.pop()
            h.append(p)
        return h
    lower = build(pts)
    upper = build(list(reversed(pts)))
    return lower[:-1] + upper[:-1]


def polygon_diameter(vertices: Sequence[Point]) -> float:
    if len(vertices) < 2:
        return 0.0
    m = 0.0
    for i, a in enumerate(vertices):
        for b in vertices[i + 1 :]:
            m = max(m, dist(a, b))
    return m


def _circumscribe_two(a: Point, b: Point) -> tuple[Point, float]:
    c = ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)
    return c, dist(a, b) / 2.0


def _circumscribe_three(a: Point, b: Point, c: Point) -> tuple[Point, float] | None:
    d = 2.0 * (a[0] * (b[1] - c[1]) + b[0] * (c[1] - a[1]) + c[0] * (a[1] - b[1]))
    if abs(d) < 1e-18:
        return None
    a2, b2, c2 = dist2(a, (0.0, 0.0)), dist2(b, (0.0, 0.0)), dist2(c, (0.0, 0.0))
    ux = (a2 * (b[1] - c[1]) + b2 * (c[1] - a[1]) + c2 * (a[1] - b[1])) / d
    uy = (a2 * (c[0] - b[0]) + b2 * (a[0] - c[0]) + c2 * (b[0] - a[0])) / d
    cen = (ux, uy)
    return cen, dist(cen, a)


def _circle_contains(cen: Point, r: float, p: Point) -> bool:
    return dist(cen, p) <= r + 1e-9


def smallest_enclosing_circle(points: Sequence[Point], rng: random.Random | None = None) -> tuple[Point, float]:
    """Welzl expected-linear SEC. Points shuffled; n is tiny for contest polygons."""
    pts = [(float(x), float(y)) for x, y in points]
    if not pts:
        raise ValueError("empty point set")
    if len(pts) == 1:
        return pts[0], 0.0
    rr = rng or random.Random(0)
    shuffled = pts[:]
    rr.shuffle(shuffled)

    def welzl(pset: list[Point], rset: list[Point]) -> tuple[Point, float]:
        if not pset or len(rset) == 3:
            return _trivial(rset)
        p = pset[-1]
        rest = pset[:-1]
        cen, rad = welzl(rest, rset)
        if _circle_contains(cen, rad, p):
            return cen, rad
        return welzl(rest, rset + [p])

    return welzl(shuffled, [])


def _trivial(rset: Sequence[Point]) -> tuple[Point, float]:
    if not rset:
        return (0.0, 0.0), 0.0
    if len(rset) == 1:
        return rset[0], 0.0
    if len(rset) == 2:
        return _circumscribe_two(rset[0], rset[1])
    a, b, c = rset
    sa, sb, sc = dist2(b, c), dist2(a, c), dist2(a, b)
    # obtuse or right: SEC is the diameter of the longest side (Thales)
    if sa + sb <= sc + 1e-12 or sa + sc <= sb + 1e-12 or sb + sc <= sa + 1e-12:
        u, v = max([(a, b), (a, c), (b, c)], key=lambda pr: dist(pr[0], pr[1]))
        return _circumscribe_two(u, v)
    tri = _circumscribe_three(a, b, c)
    if tri is None:
        u, v = max([(a, b), (a, c), (b, c)], key=lambda pr: dist(pr[0], pr[1]))
        return _circumscribe_two(u, v)
    return tri


def diameter_circle_covers(vertices: Sequence[Point]) -> bool:
    if len(vertices) < 2:
        return True
    d = polygon_diameter(vertices)
    _, r = smallest_enclosing_circle(vertices)
    return r <= d / 2.0 + 1e-8


def jung_bound(diameter: float) -> float:
    return diameter / math.sqrt(3.0)


CLEAR_R = 20.0
# Two unit bearings with |sin β| below this are treated as near-collinear.
COLLINEAR_SIN = 0.08
# svd_deg is two decimals; keep the feasible set slightly fat.
DELTA_ROUNDING_DEG = 1.01


@dataclass
class LocateQuality:
    """Problem-1 quality used by problems 3/4. Never use diameter<=40 to clear."""

    region: IntersectionResult
    sec_center: Point | None
    sec_radius: float
    can_clear_20: bool
    need_another_fix: bool
    near_collinear: bool


def _near_collinear(bearings_deg: Sequence[float]) -> bool:
    if len(bearings_deg) < 2:
        return True
    us = [unit(th) for th in bearings_deg]
    best = 0.0
    for i, a in enumerate(us):
        for b in us[i + 1 :]:
            best = max(best, abs(cross(a, b)))
    return best < COLLINEAR_SIN


def locate_quality(
    stations: Sequence[Point],
    bearings_deg: Sequence[float],
    delta_deg: float = 1.0,
    silence: Sequence[Point] | None = None,
    rule_out_r: float = 1000.0,
) -> LocateQuality:
    """Classify a multi-station AOA fix: clearable at 20 m, or need another station."""
    empty_reg = IntersectionResult([], bounded=True, empty=True)
    if len(stations) < 2:
        return LocateQuality(empty_reg, None, float("inf"), False, True, True)
    collinear = _near_collinear(bearings_deg)
    region = intersect_cones(stations, bearings_deg, delta_deg=delta_deg)
    if region.empty or not region.bounded or len(region.vertices) < 2:
        return LocateQuality(region, None, float("inf"), False, True, collinear)
    if collinear:
        return LocateQuality(region, None, float("inf"), False, True, True)
    cen, rad = smallest_enclosing_circle(region.vertices)
    if silence:
        for q in silence:
            if dist(cen, q) <= rule_out_r + 1e-9:
                return LocateQuality(region, cen, rad, False, True, False)
    can = rad <= CLEAR_R + 1e-9
    return LocateQuality(region, cen, rad, can, need_another_fix=not can, near_collinear=False)
