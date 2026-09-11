"""Problem 2: second-station candidate band and recommended point."""

from __future__ import annotations

import math
from typing import Sequence

from geometry import Point, add, dist, dot, scale, sub, unit

ARENA_R = 1800.0
X_MIN, X_MAX = 400.0, 1300.0
Y_MIN, Y_MAX = 400.0, 800.0
H_DEFAULT = 600.0
H_COMPACT = 400.0
RHO_COMPACT = 450.0


def body_axes(theta_deg: float) -> tuple[Point, Point]:
    u = unit(theta_deg)
    n = (-u[1], u[0])
    return u, n


def to_body(s1: Point, theta_deg: float, p: Point) -> Point:
    u, n = body_axes(theta_deg)
    d = sub(p, s1)
    return (dot(d, u), dot(d, n))


def from_body(s1: Point, theta_deg: float, x: float, y: float) -> Point:
    u, n = body_axes(theta_deg)
    return add(s1, add(scale(u, x), scale(n, y)))


def ray_exit_t(s1: Point, theta_deg: float, radius: float = ARENA_R) -> float:
    """Smallest t>0 with |s1 + t u| = radius; inf if none."""
    u = unit(theta_deg)
    # |s1 + t u|^2 = R^2
    a = 1.0
    b = 2.0 * dot(s1, u)
    c = dist(s1, (0.0, 0.0)) ** 2 - radius * radius
    disc = b * b - 4 * a * c
    if disc < 0:
        return 0.0
    sdisc = math.sqrt(disc)
    t1 = (-b - sdisc) / 2.0
    t2 = (-b + sdisc) / 2.0
    cands = [t for t in (t1, t2) if t > 1e-6]
    return min(cands) if cands else 0.0


def in_candidate_region(s1: Point, theta_deg: float, p: Point) -> bool:
    if dist(p, (0.0, 0.0)) > ARENA_R + 1e-6:
        return False
    x, y = to_body(s1, theta_deg, p)
    if not (X_MIN - 1e-6 <= x <= X_MAX + 1e-6):
        return False
    ay = abs(y)
    return Y_MIN - 1e-6 <= ay <= Y_MAX + 1e-6


def _rect_corners(s1: Point, theta_deg: float, y_sign: float) -> list[Point]:
    y0, y1 = y_sign * Y_MIN, y_sign * Y_MAX
    raw = [
        from_body(s1, theta_deg, X_MIN, y0),
        from_body(s1, theta_deg, X_MAX, y0),
        from_body(s1, theta_deg, X_MAX, y1),
        from_body(s1, theta_deg, X_MIN, y1),
    ]
    out = []
    for p in raw:
        r = dist(p, (0.0, 0.0))
        if r <= ARENA_R:
            out.append(p)
        else:
            out.append(scale(p, ARENA_R / r))
    return out


def candidate_region(s1: Point, theta_deg: float) -> list[list[Point]]:
    """Two side bands as quadrilaterals (may be clipped to the arena)."""
    return [_rect_corners(s1, theta_deg, 1.0), _rect_corners(s1, theta_deg, -1.0)]


def recommend_second_sides(
    s1: Point,
    theta_deg: float,
    h: float = H_DEFAULT,
) -> tuple[Point, Point]:
    """Two orthogonal side points; clip to the arena disk."""
    t_exit = ray_exit_t(s1, theta_deg, ARENA_R)
    t_cap = min(1500.0, t_exit if t_exit > 0 else 1500.0)
    rho = max(X_MIN, min(0.7 * t_cap, 0.5 * (X_MIN + min(X_MAX, t_cap))))
    rho = min(max(rho, X_MIN), X_MAX)

    def clip(p: Point) -> Point:
        r = dist(p, (0.0, 0.0))
        if r > ARENA_R:
            return scale(p, ARENA_R / r)
        return p

    return clip(from_body(s1, theta_deg, rho, h)), clip(from_body(s1, theta_deg, rho, -h))


def _clip_arena(p: Point) -> Point:
    r = dist(p, (0.0, 0.0))
    if r > ARENA_R:
        return scale(p, ARENA_R / r)
    return p


def recommend_second_sides_compact(
    s1: Point,
    theta_deg: float,
    h: float = H_COMPACT,
    rho: float = RHO_COMPACT,
) -> tuple[Point, Point]:
    """Shorter orthogonal pair: enough for ±1° → 20 m clear, less travel."""
    return (
        _clip_arena(from_body(s1, theta_deg, rho, h)),
        _clip_arena(from_body(s1, theta_deg, rho, -h)),
    )


def recommend_second(
    s1: Point,
    theta_deg: float,
    now: Point | None = None,
    h: float = H_DEFAULT,
) -> Point:
    t_exit = ray_exit_t(s1, theta_deg, ARENA_R)
    t_cap = min(1500.0, t_exit if t_exit > 0 else 1500.0)
    rho = max(X_MIN, min(0.7 * t_cap, 0.5 * (X_MIN + min(X_MAX, t_cap))))
    rho = min(max(rho, X_MIN), X_MAX)

    def try_point(hh: float, sign: float) -> Point:
        return from_body(s1, theta_deg, rho, sign * hh)

    now = now if now is not None else s1
    best: Point | None = None
    best_key = None
    for hh in (h, 500.0, 400.0, Y_MIN):
        for sign in (1.0, -1.0):
            p = try_point(hh, sign)
            if dist(p, (0.0, 0.0)) > ARENA_R:
                continue
            if not in_candidate_region(s1, theta_deg, p) and hh > Y_MAX:
                continue
            key = (dist(p, now), dist(p, (0.0, 0.0)))
            if best is None or key < best_key:  # type: ignore[operator]
                best, best_key = p, key
        if best is not None and in_candidate_region(s1, theta_deg, best):
            break
    if best is None:
        best = try_point(Y_MIN, 1.0)
        r = dist(best, (0.0, 0.0))
        if r > ARENA_R:
            best = scale(best, ARENA_R / r)
    return best


def front_compatible(s1: Point, theta_deg: float, p: Point, rho_g: float | None = None) -> bool:
    """True if P can still lie in the 180° front half-plane of a source on the ray.

    Heard-at-S1 forces the unknown heading to include S1. P is compatible when it
    sits on the S1 side of the perpendicular through a guess G on the bearing.
    """
    x, _y = to_body(s1, theta_deg, p)
    if rho_g is None:
        rho_g = max(x + 80.0, 250.0)
    g = from_body(s1, theta_deg, rho_g, 0.0)
    return dot(sub(p, g), sub(s1, g)) >= -1.0


def next_stations(
    s1: Point,
    theta_deg: float,
    now: Point | None = None,
    directional: bool = False,
    silence: Sequence[Point] | None = None,
) -> list[Point]:
    """Legal second stations: off the bearing, 60–120° if possible; empty if none.

    Directional mode rejects far orthogonal points that sit behind the first lobe.
    """
    now = now if now is not None else s1
    raw: list[Point] = []
    if directional:
        compact = list(recommend_second_sides_compact(s1, theta_deg))
        raw.extend(compact)
        extras: list[Point] = []
        for rho, h in ((320.0, 400.0), (400.0, 450.0)):
            extras.extend(
                (
                    _clip_arena(from_body(s1, theta_deg, rho, h)),
                    _clip_arena(from_body(s1, theta_deg, rho, -h)),
                )
            )
        g_hat = from_body(s1, theta_deg, 800.0, 0.0)
        for p in extras:
            ang = intersection_angle_deg(s1, p, g_hat)
            if 55.0 <= ang <= 125.0:
                raw.append(p)
    else:
        pref = recommend_second(s1, theta_deg, now=now)
        rest = [p for p in recommend_second_sides_compact(s1, theta_deg) if dist(p, pref) > 5.0]
        ordered_omni = [pref] + rest
        out_omni: list[Point] = []
        for p in ordered_omni:
            if dist(p, s1) <= 5.0:
                continue
            _x, y = to_body(s1, theta_deg, p)
            if abs(y) < Y_MIN - 1e-6:
                continue
            if silence and any(dist(p, q) < 35.0 for q in silence):
                continue
            if all(dist(p, q) > 5.0 for q in out_omni):
                out_omni.append(p)
        return out_omni

    scored: list[tuple[int, float, Point]] = []
    for p in raw:
        if dist(p, s1) <= 5.0:
            continue
        _x, y = to_body(s1, theta_deg, p)
        if abs(y) < Y_MIN - 1e-6:
            continue
        if silence and any(dist(p, q) < 35.0 for q in silence):
            continue
        if any(dist(p, q) <= 5.0 for _, _, q in scored):
            continue
        front = 0 if (not directional or front_compatible(s1, theta_deg, p)) else 1
        scored.append((front, dist(p, now), p))
    scored.sort()
    return [p for _, _, p in scored]


def intersection_angle_deg(s1: Point, s2: Point, g: Point) -> float:
    v1 = sub(s1, g)
    v2 = sub(s2, g)
    n1 = math.hypot(*v1)
    n2 = math.hypot(*v2)
    if n1 < 1e-9 or n2 < 1e-9:
        return 0.0
    c = max(-1.0, min(1.0, dot(v1, v2) / (n1 * n2)))
    return math.degrees(math.acos(c))

def recommend_second_options(
    s1: Point,
    theta_deg: float,
    now: Point | None = None,
    h: float = H_DEFAULT,
) -> list[Point]:
    """Return only arena- and band-legal second stations, nearest first."""
    t_exit = ray_exit_t(s1, theta_deg, ARENA_R)
    t_cap = min(1500.0, t_exit if t_exit > 0 else 1500.0)
    rho = max(X_MIN, min(0.7 * t_cap, 0.5 * (X_MIN + min(X_MAX, t_cap))))
    rho = min(max(rho, X_MIN), X_MAX)
    now = now if now is not None else s1
    heights: list[float] = []
    for value in (h, 500.0, 400.0, Y_MIN):
        hh = abs(float(value))
        if Y_MIN <= hh <= Y_MAX and all(abs(hh - old) > 1e-9 for old in heights):
            heights.append(hh)
    for hh in heights:
        options = [
            from_body(s1, theta_deg, rho, sign * hh)
            for sign in (1.0, -1.0)
        ]
        legal = [
            p
            for p in options
            if math.isfinite(p[0])
            and math.isfinite(p[1])
            and in_candidate_region(s1, theta_deg, p)
        ]
        if legal:
            legal.sort(key=lambda p: (dist(p, now), dist(p, (0.0, 0.0))))
            return legal
    return []
