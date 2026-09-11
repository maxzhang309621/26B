"""Search-localize-clear controller for problems 3 and 4."""

from __future__ import annotations

from geometry import Point, Q3_ARENA_R, add, dist, entirely_excluded_by_no_signal, intersect_cones, intersect_feasible_region, plausible_vertices_after_no_signal, scale, smallest_enclosing_circle, sub, unit
from candidate import in_candidate_region, recommend_second, recommend_second_options
from belief import ChannelBook
from coverage import directional_waypoints, omni_waypoints, q3_waypoints
from robot_client import RobotClient

CLEAR_R = 20.0
MAX_FIX_MEASURES = 12
MAX_TOTAL_CLEARED = 16


def _perp(p: Point) -> Point:
    n = dist(p, (0.0, 0.0))
    if n < 1e-9:
        return (0.0, 1.0)
    return (-p[1] / n, p[0] / n)


def _third_point(vertices: list[Point], now: Point, arena_radius: float | None = None) -> Point:
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
    chosen = p1 if dist(p1, now) <= dist(p2, now) else p2
    radius = dist(chosen, (0.0, 0.0))
    if arena_radius is not None and radius > arena_radius:
        return scale(chosen, (arena_radius - 1e-6) / radius)
    return chosen


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
        self.inconsistent_regions = 0
        self.route_rechecks = 0
        self.route_recheck_hits = 0
        self.deferred_channels: set[int] = set()
        self.dedicated_localizations = 0
        self.localization_services = 0
        self.first_seen_order: dict[int, int] = {}

    def run(self, do_enter: bool = True) -> dict:
        if do_enter:
            ent = self.bot.enter()
            if not _accepted(ent):
                raise RuntimeError(f"enter failed: {ent}")
        self._scan_point(self.waypoints[0], list(range(1, 21)))
        first_future = self.waypoints[1:] if not self.directional else None
        self._drain_pending(first_future)
        for index, wp in enumerate(self.waypoints[1:], start=1):
            if len(self.book.cleared) >= MAX_TOTAL_CLEARED:
                break
            unknown = self.book.unknown_channels()
            if not unknown and not self.book.pending():
                break
            opportunistic = (
                []
                if self.directional
                else self._opportunistic_channels(wp)
            )
            before_counts = {
                ch: len(self.book.detections.get(ch, []))
                for ch in opportunistic
            }
            channels = unknown + [ch for ch in opportunistic if ch not in unknown]
            if channels:
                self.route_rechecks += len(opportunistic)
                self._scan_point(wp, channels)
                self.route_recheck_hits += sum(
                    ch in self.book.cleared
                    or len(self.book.detections.get(ch, [])) > before_counts[ch]
                    for ch in opportunistic
                )
            future = self.waypoints[index + 1 :] if not self.directional else None
            self._drain_pending(future)
        if self.book.pending():
            self.stuck.clear()
            self._drain_pending([])
        if self.book.pending():
            self.stuck.clear()
            for ch in list(self.book.pending()):
                self._home_and_clear(ch)
        pending_at_exit = len(self.book.pending())
        exit_body = self.bot.exit()
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
            "inconsistent_regions": self.inconsistent_regions,
            "route_rechecks": self.route_rechecks,
            "route_recheck_hits": self.route_recheck_hits,
            "deferred_channels": len(self.deferred_channels),
            "dedicated_localizations": self.dedicated_localizations,
            "localization_services": self.localization_services,
            "pending_at_exit": pending_at_exit,
            "exit_accepted": _accepted(exit_body),
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
                self._record_direction(ch, xy, float(body["svd_deg"]))
                self.stuck.discard(ch)
            elif kind == "no_signal" and not self.directional:
                self.book.record_no_signal(ch, xy)

    def _try_clear(self, xy: Point, ch: int) -> bool:
        body = self.bot.clear(xy[0], xy[1], ch)
        if _accepted(body) and body.get("clear_result") == "success":
            self.book.mark_cleared(ch)
            return True
        return False

    def _record_direction(self, ch: int, xy: Point, svd: float) -> None:
        if ch not in self.book.detections:
            self.first_seen_order.setdefault(ch, len(self.first_seen_order))
        self.book.add_direction(ch, xy, svd)

    def _eligible_route_probe(self, ch: int, waypoint: Point) -> bool:
        obs = self.book.detections.get(ch, [])
        return (
            not self.directional
            and len(obs) == 1
            and in_candidate_region(obs[0].xy, obs[0].svd_deg, waypoint)
        )

    def _has_future_route_probe(self, ch: int, future_waypoints: list[Point]) -> bool:
        return any(self._eligible_route_probe(ch, wp) for wp in future_waypoints)

    def _opportunistic_channels(self, waypoint: Point) -> list[int]:
        return [
            ch
            for ch in self.book.pending()
            if ch not in self.stuck and self._eligible_route_probe(ch, waypoint)
        ]

    def _estimated_service_point(self, ch: int) -> Point:
        obs = self.book.detections.get(ch, [])
        if not obs:
            return self.bot.position
        if not self.directional and len(obs) >= 2:
            region = intersect_feasible_region(
                [item.xy for item in obs],
                [item.svd_deg for item in obs],
            )
            if not region.empty and region.vertices:
                center, _ = smallest_enclosing_circle(region.vertices)
                radius = dist(center, (0.0, 0.0))
                if radius > Q3_ARENA_R:
                    return scale(center, (Q3_ARENA_R - 1e-6) / radius)
                return center
        if not self.directional and len(obs) == 1:
            options = recommend_second_options(
                obs[0].xy,
                obs[0].svd_deg,
                now=self.bot.position,
            )
            if options:
                return options[0]
        return obs[-1].xy

    def _incremental_service_cost(self, ch: int, rejoin: Point | None) -> float:
        service = self._estimated_service_point(ch)
        cost = dist(self.bot.position, service)
        if rejoin is not None:
            cost += dist(service, rejoin) - dist(self.bot.position, rejoin)
        return cost

    def _drain_pending(self, future_waypoints: list[Point] | None = None) -> None:
        future = future_waypoints or []
        while True:
            pending = [c for c in self.book.pending() if c not in self.stuck]
            if not pending or len(self.book.cleared) >= MAX_TOTAL_CLEARED:
                break
            ready: list[int] = []
            for ch in pending:
                obs = self.book.detections.get(ch, [])
                if (
                    not self.directional
                    and len(obs) == 1
                    and self._has_future_route_probe(ch, future)
                ):
                    self.deferred_channels.add(ch)
                    continue
                ready.append(ch)
            if not ready:
                break
            rejoin = future[0] if future else None
            ch = min(
                ready,
                key=lambda c: (
                    self._incremental_service_cost(c, rejoin),
                    self.first_seen_order.get(c, c),
                    c,
                ),
            )
            self.localization_services += 1
            if len(self.book.detections.get(ch, [])) == 1:
                self.dedicated_localizations += 1
            self._localize_and_clear(ch)
            if ch not in self.book.cleared:
                self.stuck.add(ch)

    def _localize_and_clear(self, ch: int) -> None:
        obs = self.book.detections.get(ch, [])
        if not obs:
            return
        if self.directional:
            last = obs[-1]
            if self._creep_clear(ch, last.xy, last.svd_deg):
                return
        for _ in range(MAX_FIX_MEASURES):
            if ch in self.book.cleared:
                return
            obs = self.book.detections.get(ch, [])
            if not obs:
                return
            if len(obs) == 1:
                s1, th = obs[0].xy, obs[0].svd_deg
                if self.directional:
                    second = recommend_second(s1, th, now=self.bot.position)
                    options = [second]
                else:
                    options = recommend_second_options(s1, th, now=self.bot.position)
                for s2 in options:
                    if dist(s2, s1) > 5.0 and self._measure_obs(ch, s2, obs):
                        break
                    if ch in self.book.cleared:
                        return
                if ch in self.book.cleared:
                    return
                # Fuse a successful second bearing before considering fallback.
                if len(self.book.detections.get(ch, [])) >= 2:
                    continue
                last = self.book.detections.get(ch, obs)[-1]
                self._creep_clear(ch, last.xy, last.svd_deg)
                return
            stations = [d.xy for d in obs]
            bearings = [d.svd_deg for d in obs]
            region = (
                intersect_cones(stations, bearings)
                if self.directional
                else intersect_feasible_region(stations, bearings)
            )
            if region.empty or not region.bounded or len(region.vertices) < 2:
                last = obs[-1]
                if self._creep_clear(ch, last.xy, last.svd_deg):
                    return
                continue
            no_signal_sites = self.book.no_signal_at.get(ch, []) if not self.directional else []
            if entirely_excluded_by_no_signal(region.vertices, no_signal_sites):
                self.inconsistent_regions += 1
                last = obs[-1]
                self._creep_clear(ch, last.xy, last.svd_deg)
                return
            cen, rad = smallest_enclosing_circle(region.vertices)
            cen_radius = dist(cen, (0.0, 0.0))
            if not self.directional and cen_radius > Q3_ARENA_R:
                cen = scale(cen, (Q3_ARENA_R - 1e-6) / cen_radius)
                rad = max(dist(cen, v) for v in region.vertices)
            if rad <= CLEAR_R and self._try_clear(cen, ch):
                return
            if rad <= CLEAR_R:
                for v in region.vertices:
                    if dist(v, (0.0, 0.0)) <= Q3_ARENA_R + 1e-6 and self._try_clear(v, ch):
                        return
            plausible = plausible_vertices_after_no_signal(region.vertices, no_signal_sites)
            target_vertices = plausible if len(plausible) >= 2 else region.vertices
            nxt = _third_point(
                target_vertices,
                self.bot.position,
                None if self.directional else Q3_ARENA_R,
            )
            if not self._measure_obs(ch, nxt, obs):
                last = obs[-1]
                self._creep_clear(ch, last.xy, last.svd_deg)
                return
        obs = self.book.detections.get(ch, [])
        if obs:
            last = obs[-1]
            self._creep_clear(ch, last.xy, last.svd_deg)

    def _measure_obs(self, ch: int, xy: Point, obs: list) -> bool:
        body = self.bot.measure(xy[0], xy[1], ch)
        if not _accepted(body):
            return False
        self.book.record_scan(ch, xy)
        kind = body.get("measure_result")
        if kind == "near":
            return self._try_clear(xy, ch)
        if kind == "direction":
            self._record_direction(ch, xy, float(body["svd_deg"]))
            return True
        if kind == "no_signal" and not self.directional:
            self.book.record_no_signal(ch, xy)
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
        seen: set[tuple[int, int]] = set()
        for _ in range(40):
            if ch in self.book.cleared:
                return True
            nxt = add(p, scale(unit(heading), 12.0))
            key = (round(nxt[0], 1), round(nxt[1], 1))
            if key in seen:
                break
            seen.add(key)
            self.creep_steps += 1
            body = self.bot.measure(nxt[0], nxt[1], ch)
            if not _accepted(body):
                break
            self.book.record_scan(ch, nxt)
            kind = body.get("measure_result")
            if kind == "near":
                return self._try_clear(nxt, ch)
            if kind == "direction":
                last_good = nxt
                heading = float(body["svd_deg"])
                p = nxt
                self._record_direction(ch, nxt, heading)
                continue
            if not self.directional:
                self.book.record_no_signal(ch, nxt)
            back = add(nxt, scale(unit(heading), -16.0))
            if self._try_clear(back, ch):
                return True
            if self._try_clear(last_good, ch):
                return True
            closer = add(last_good, scale(unit(heading), 8.0))
            return self._try_clear(closer, ch)
        return self._try_clear(last_good, ch)

    def _home_and_clear(self, ch: int) -> None:
        if not self.book.detections.get(ch):
            return
        self._localize_and_clear(ch)
