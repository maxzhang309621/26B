"""Worst-case receive-radius coverage waypoints."""

from __future__ import annotations

import math
from typing import Sequence

from geometry import Point, dist

ARENA_R = 1800.0
COVER_R = 1000.0
OMNI_RING_R = 1200.0
OMNI_RING_N = 8
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
