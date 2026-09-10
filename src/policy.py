"""Search-localize-clear controller for problems 3 and 4."""

from __future__ import annotations

from geometry import Point, add, dist, intersect_cones, scale, smallest_enclosing_circle, sub, unit
from candidate import recommend_second, recommend_second_sides
from belief import ChannelBook
from coverage import directional_waypoints, omni_waypoints
from robot_client import RobotClient

CLEAR_R = 20.0
MAX_FIX_MEASURES = 12
MAX_TOTAL_CLEARED = 16


def _perp(p: Point) -> Point:
    n = dist(p, (0.0, 0.0))
    if n < 1e-9:
        return (0.0, 1.0)
    return (-p[1] / n, p[0] / n)


def _third_point(vertices: list[Point], now: Point) -> Point:
    dmax = -1.0
    a = b = vertices[0]
    for i, u in enumerate(vertices):
        for v in vertices[i + 1 :]:
            d = dist(u, v)
            if d > dmax:
                dmax, a, b = d, u, v
    mid = ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)
    axis = sub(b, a)
    n = _perp(axis)
    step = max(80.0, 0.5 * dmax)
    p1 = add(mid, scale(n, step))
    p2 = add(mid, scale(n, -step))
    return p1 if dist(p1, now) <= dist(p2, now) else p2


def _accepted(body: dict) -> bool:
    return body.get("accepted") is True


class HuntPolicy:
    def __init__(self, bot: RobotClient, directional: bool = False) -> None:
        self.bot = bot
        self.directional = directional
        self.book = ChannelBook()
        self.waypoints = directional_waypoints() if directional else omni_waypoints()
        self.stuck: set[int] = set()
        self.creep_calls = 0
        self.creep_steps = 0
        self.creep_attempted: set[int] = set()

    def run(self, do_enter: bool = True) -> dict:
        if do_enter:
            ent = self.bot.enter()
            if not _accepted(ent):
                raise RuntimeError(f"enter failed: {ent}")
        self._scan_point(self.waypoints[0], list(range(1, 21)))
        self._drain_pending()
        for wp in self.waypoints[1:]:
            if len(self.book.cleared) >= MAX_TOTAL_CLEARED:
                break
            if not self.book.unknown_channels():
                break
            self._scan_point(wp, self.book.unknown_channels())
            self._drain_pending()
        if self.book.pending():
            self.stuck.clear()
            for ch in list(self.book.pending()):
                self._home_and_clear(ch)
        self.bot.exit()
        n_clear = len(self.book.cleared)
        vt = self.bot.virtual_time_s
        avg = vt / n_clear if n_clear else float("inf")
        return {
            "cleared": n_clear,
            "virtual_time_s": vt,
            "avg_clear_s": avg,
            "channels": sorted(self.book.cleared),
            "creep_calls": self.creep_calls,
            "creep_steps": self.creep_steps,
        }

    def _scan_point(self, xy: Point, channels: list[int]) -> None:
        x, y = xy
        for ch in channels:
            if ch in self.book.cleared:
                continue
            body = self.bot.measure(x, y, ch)
            if not _accepted(body):
                continue
            self.book.record_scan(ch, xy)
            kind = body.get("measure_result")
            if kind == "near":
                self._try_clear(xy, ch)
            elif kind == "direction":
                self.book.add_direction(ch, xy, float(body["svd_deg"]))
                self.stuck.discard(ch)

    def _try_clear(self, xy: Point, ch: int) -> bool:
        body = self.bot.clear(xy[0], xy[1], ch)
        if _accepted(body) and body.get("clear_result") == "success":
            self.book.mark_cleared(ch)
            return True
        return False

    def _drain_pending(self) -> None:
        while True:
            pending = [c for c in self.book.pending() if c not in self.stuck]
            if not pending or len(self.book.cleared) >= MAX_TOTAL_CLEARED:
                break
            ch = min(
                pending,
                key=lambda c: dist(self.bot.position, self.book.detections[c][-1].xy),
            )
            self._localize_and_clear(ch)
            if ch not in self.book.cleared:
                self.stuck.add(ch)

    def _localize_and_clear(self, ch: int) -> None:
        for _ in range(MAX_FIX_MEASURES):
            if ch in self.book.cleared:
                return
            obs = self.book.detections.get(ch, [])
            if not obs:
                return
            if len(obs) == 1:
                self._take_second_fix(ch, obs[0].xy, obs[0].svd_deg)
                if ch in self.book.cleared:
                    return
                obs = self.book.detections.get(ch, [])
                if not obs:
                    return
                if len(obs) < 2:
                    last = obs[-1]
                    self._creep_clear(ch, last.xy, last.svd_deg)
                    return
            obs = self.book.detections.get(ch, [])
            stations = [d.xy for d in obs[-4:]]
            bearings = [d.svd_deg for d in obs[-4:]]
            region = intersect_cones(stations, bearings)
            if region.empty or not region.bounded or len(region.vertices) < 2:
                last = obs[-1]
                if self._creep_clear(ch, last.xy, last.svd_deg):
                    return
                continue
            cen, rad = smallest_enclosing_circle(region.vertices)
            if rad <= CLEAR_R:
                if self._try_clear(cen, ch):
                    return
                last = obs[-1]
                along = add(cen, scale(unit(last.svd_deg), 12.0))
                if self._try_clear(along, ch):
                    return
            nxt = _third_point(region.vertices, self.bot.position)
            if not self._measure_obs(ch, nxt, obs):
                last = obs[-1]
                self._creep_clear(ch, last.xy, last.svd_deg)
                return
        obs = self.book.detections.get(ch, [])
        if obs and ch not in self.book.cleared:
            last = obs[-1]
            self._creep_clear(ch, last.xy, last.svd_deg)

    def _take_second_fix(self, ch: int, s1: Point, th: float) -> None:
        sides = list(recommend_second_sides(s1, th))
        sides.sort(key=lambda p: dist(p, self.bot.position))
        pref = recommend_second(s1, th, now=self.bot.position)
        ordered = [pref] + [p for p in sides if dist(p, pref) > 5.0]
        for s2 in ordered:
            if dist(s2, s1) <= 5.0:
                continue
            if self._measure_obs(ch, s2, self.book.detections.get(ch, [])):
                return
            if not self.directional:
                return

    def _measure_obs(self, ch: int, xy: Point, obs: list) -> bool:
        body = self.bot.measure(xy[0], xy[1], ch)
        if not _accepted(body):
            return False
        kind = body.get("measure_result")
        if kind == "near":
            return self._try_clear(xy, ch)
        if kind == "direction":
            self.book.add_direction(ch, xy, float(body["svd_deg"]))
            return True
        return False

    def _creep_clear(self, ch: int, start: Point, th: float) -> bool:
        if not self.directional:
            if ch in self.creep_attempted:
                return False
            self.creep_attempted.add(ch)
        self.creep_calls += 1
        heading = th
        p = start
        last_good = start
        step = 180.0
        seen: set[tuple[int, int]] = set()
        for _ in range(16):
            if ch in self.book.cleared:
                return True
            nxt = add(p, scale(unit(heading), step))
            key = (round(nxt[0]), round(nxt[1]))
            if key in seen:
                break
            seen.add(key)
            self.creep_steps += 1
            body = self.bot.measure(nxt[0], nxt[1], ch)
            if not _accepted(body):
                break
            kind = body.get("measure_result")
            if kind == "near":
                return self._try_clear(nxt, ch)
            if kind == "direction":
                last_good = nxt
                heading = float(body["svd_deg"])
                p = nxt
                self.book.add_direction(ch, nxt, heading)
                step = max(28.0, step * 0.65)
                continue
            if self._try_clear(last_good, ch):
                return True
            closer = add(last_good, scale(unit(heading), 14.0))
            if self._try_clear(closer, ch):
                return True
            if step > 40.0:
                step = 28.0
                p = last_good
                continue
            back = add(nxt, scale(unit(heading), -18.0))
            return self._try_clear(back, ch) or self._try_clear(last_good, ch)
        return self._try_clear(last_good, ch)

    def _home_and_clear(self, ch: int) -> None:
        if ch in self.book.cleared or not self.book.detections.get(ch):
            return
        self._localize_and_clear(ch)
