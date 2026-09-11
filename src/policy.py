"""Search-localize-clear controller for problems 3 and 4."""

from __future__ import annotations

from geometry import Point, add, cross, dist, intersect_cones, scale, smallest_enclosing_circle, sub, unit
from candidate import recommend_second, recommend_second_sides_compact
from belief import ChannelBook, Detection, R_RULE_OUT
from coverage import ENROUTE_R, covering_phases, directional_waypoints, omni_waypoints
from robot_client import RobotClient

CLEAR_R = 20.0
MAX_FIX_MEASURES = 12
MAX_TOTAL_CLEARED = 16
ARENA_LIM = 2500.0
SPEED_MPS = 5.0
MAX_CLEAR_MISS_PER_CH = 12
MAX_UNCHARGED_CLEAR_PER_CH = 3
FAN_CLEAR_OFFSETS = (12.0, 18.0)
MAX_CREEP_STEPS_DIR = 8


def _perp(p: Point) -> Point:
    n = dist(p, (0.0, 0.0))
    if n < 1e-9:
        return (0.0, 1.0)
    return (-p[1] / n, p[0] / n)


def _lerp(a: Point, b: Point, t: float) -> Point:
    return (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))


def _rays_meet(p1: Point, th1: float, p2: Point, th2: float) -> Point | None:
    """Intersection of two bearing lines; None if nearly parallel or far behind."""
    u1, u2 = unit(th1), unit(th2)
    den = cross(u1, u2)
    if abs(den) < 0.08:
        return None
    w = sub(p2, p1)
    t = cross(w, u2) / den
    s = cross(w, u1) / den
    if t < -30.0 or s < -30.0:
        return None
    q = add(p1, scale(u1, t))
    if dist(q, (0.0, 0.0)) > ARENA_LIM:
        return None
    return q


def _best_fixes(obs: list[Detection]) -> list[Point]:
    scored: list[tuple[float, Point]] = []
    for i, a in enumerate(obs):
        for b in obs[i + 1 :]:
            q = _rays_meet(a.xy, a.svd_deg, b.xy, b.svd_deg)
            if q is None:
                continue
            u1, u2 = unit(a.svd_deg), unit(b.svd_deg)
            sep = dist(a.xy, b.xy)
            scored.append((abs(cross(u1, u2)) * min(sep, 1200.0), q))
    scored.sort(reverse=True)
    out: list[Point] = []
    for _, q in scored:
        if all(dist(q, p) > 8.0 for p in out):
            out.append(q)
        if len(out) >= 3:
            break
    return out


def _diverse_obs(obs: list[Detection], k: int = 4) -> list[Detection]:
    if len(obs) <= k:
        return list(obs)
    picked = [obs[0]]
    rest = list(obs[1:])
    while len(picked) < k and rest:
        j = max(range(len(rest)), key=lambda i: min(dist(rest[i].xy, p.xy) for p in picked))
        picked.append(rest.pop(j))
    return picked


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


def action_stats(log: list[dict], speed_mps: float = SPEED_MPS) -> dict:
    """Reconstruct travel / detect / clear-miss from a RobotClient action log."""
    pos = (0.0, 0.0)
    travel_m = 0.0
    detect_s = 0.0
    n_measure = n_clear = clear_ok = clear_miss = 0
    last_vt = 0.0
    for rec in log:
        path = rec.get("path")
        if path not in ("/measure", "/clear"):
            continue
        body = rec.get("response") or {}
        if body.get("accepted") is not True:
            continue
        req = rec.get("request") or {}
        p = req.get("position") or {}
        xy = (float(p["x"]), float(p["y"]))
        d = dist(pos, xy)
        travel_m += d
        pos = xy
        vt = float(body.get("virtual_time_s") or last_vt)
        dwell = max(0.0, vt - last_vt - d / speed_mps)
        last_vt = vt
        if path == "/measure":
            n_measure += 1
            detect_s += dwell
        else:
            n_clear += 1
            if body.get("clear_result") == "success":
                clear_ok += 1
            else:
                clear_miss += 1
    return {
        "travel_m": travel_m,
        "travel_s": travel_m / speed_mps,
        "detect_s": detect_s,
        "n_measure": n_measure,
        "n_clear": n_clear,
        "clear_ok": clear_ok,
        "clear_miss": clear_miss,
    }


class HuntPolicy:
    def __init__(
        self,
        bot: RobotClient,
        directional: bool = False,
        target_n: int | None = None,
    ) -> None:
        self.bot = bot
        self.directional = directional
        self.book = ChannelBook()
        self.waypoints = directional_waypoints() if directional else omni_waypoints()
        self.stuck: set[int] = set()
        self.creep_calls = 0
        self.creep_steps = 0
        self.creep_attempted: set[int] = set()
        self._tried_clear: set[tuple[int, int, int]] = set()
        self._clear_miss_n: dict[int, int] = {}
        self._uncharged_n: dict[int, int] = {}
        self._behind_lobe_free: set[int] = set()
        self._inner_done = False
        self._cover_listens: list[Point] = []
        self._target_n = MAX_TOTAL_CLEARED
        self._set_target_n(target_n)

    def _set_target_n(self, n: int | None) -> None:
        if isinstance(n, int) and 1 <= n <= MAX_TOTAL_CLEARED:
            self._target_n = n

    def _apply_target_n(self, body: dict | None) -> None:
        if not body:
            return
        self._set_target_n(body.get("jammer_count"))

    def _target_from_log(self) -> None:
        for rec in reversed(self.bot.log):
            if rec.get("path") != "/enter":
                continue
            self._apply_target_n(rec.get("response") or {})
            return

    def run(self, do_enter: bool = True) -> dict:
        if do_enter:
            ent = self.bot.enter()
            if not _accepted(ent):
                raise RuntimeError(f"enter failed: {ent}")
            self._apply_target_n(ent)
        else:
            self._target_from_log()
        origin, inner, outer = covering_phases(self.waypoints)
        self._scan_point(origin, list(range(1, 21)))
        self._cover_listens.append(origin)
        self._drain_pending()
        self._cover_tour(inner)
        self._inner_done = True
        self._cover_tour(outer)
        if self.book.pending():
            self.stuck.clear()
            for ch in list(self.book.pending()):
                self._home_and_clear(ch)
        self.bot.exit()
        n_clear = len(self.book.cleared)
        vt = self.bot.virtual_time_s
        avg = vt / n_clear if n_clear else float("inf")
        extra = action_stats(self.bot.log)
        return {
            "cleared": n_clear,
            "virtual_time_s": vt,
            "avg_clear_s": avg,
            "channels": sorted(self.book.cleared),
            "creep_calls": self.creep_calls,
            "creep_steps": self.creep_steps,
            **extra,
        }

    def _done(self) -> bool:
        return len(self.book.cleared) >= self._target_n

    def _search_complete(self) -> bool:
        """Stop covering once every live source is heard (n from /enter, else 16)."""
        heard = len(self.book.cleared) + len(self.book.pending())
        return heard >= self._target_n or not self.book.unknown_channels()

    def _cover_tour(self, remaining: list[Point]) -> None:
        """Visit remaining covering points by nearest neighbor; skip same-ring redundant disks."""
        ring = list(remaining)
        if not ring:
            return
        self._cover_nn(ring)

    def _visit_cover_wp(self, wp: Point) -> None:
        self._listen_enroute(wp)
        if self._done() or self._search_complete():
            return
        unknown = self.book.unknown_channels()
        if self._waypoint_useful(wp, unknown) and not self._redundant_cover(wp):
            self._scan_point(wp, self._channels_for(wp, unknown))
            self._cover_listens.append(wp)
            self._drain_pending()

    def _cover_nn(self, remaining: list[Point]) -> None:
        pending = set(remaining)
        ring = list(remaining)
        while pending and not self._done() and not self._search_complete():
            unknown = self.book.unknown_channels()
            useful = [
                wp
                for wp in ring
                if wp in pending and self._waypoint_useful(wp, unknown) and not self._redundant_cover(wp)
            ]
            if not useful:
                break
            wp = min(useful, key=lambda p: dist(self.bot.position, p))
            pending.remove(wp)
            self._visit_cover_wp(wp)

    def _channels_for(self, xy: Point, channels: list[int]) -> list[int]:
        assume = bool(self.directional and self._inner_done)
        return [
            ch
            for ch in channels
            if self.book.might_hear(ch, xy, directional=self.directional, assume_directional=assume)
        ]

    def _waypoint_useful(self, xy: Point, unknown: list[int]) -> bool:
        assume = bool(self.directional and self._inner_done)
        return any(
            self.book.might_hear(ch, xy, directional=self.directional, assume_directional=assume)
            for ch in unknown
        )

    def _redundant_cover(self, xy: Point) -> bool:
        """Skip a listen that sits in another same-ring covering disk of radius min r_eff.

        Inner (1200 m) must not suppress outer (~2100 m): radial gap is ~900 m < 1000 m,
        but that disk overlap is isotropic and misses outward directional sources.
        """
        if not self._inner_done:
            return False
        r = dist(xy, (0.0, 0.0))
        for p in self._cover_listens:
            if abs(r - dist(p, (0.0, 0.0))) > 200.0:
                continue
            if dist(xy, p) <= R_RULE_OUT:
                return True
        return False

    def _listen_enroute(self, dest: Point) -> None:
        """Stop at 900 m on the origin→inner-ring ray so near-center outward sources are heard."""
        origin = (0.0, 0.0)
        rd = dist(dest, origin)
        if rd < 1100.0 or rd > 1300.0:
            return
        if dist(self.bot.position, origin) > 850.0:
            return
        u = (dest[0] / rd, dest[1] / rd)
        mid = (ENROUTE_R * u[0], ENROUTE_R * u[1])
        if dist(self.bot.position, mid) + dist(mid, dest) > dist(self.bot.position, dest) + 35.0:
            return
        unknown = self.book.unknown_channels()
        chs = self._channels_for(mid, unknown)
        if not chs:
            return
        self._scan_point(mid, chs)
        self._cover_listens.append(mid)
        self._drain_pending()

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
            else:
                self.book.record_silence(ch, xy)

    def _clear_budget_left(self, ch: int) -> int:
        return MAX_CLEAR_MISS_PER_CH - self._clear_miss_n.get(ch, 0)

    def _try_clear(
        self,
        xy: Point,
        ch: int,
        charge: bool = True,
        behind_lobe: bool = False,
    ) -> bool:
        if charge and self._clear_budget_left(ch) <= 0:
            return False
        if not charge and behind_lobe:
            used = self._uncharged_n.get(ch, 0)
            first_free = ch not in self._behind_lobe_free
            if used >= MAX_UNCHARGED_CLEAR_PER_CH and not first_free:
                return False
        key = (ch, int(round(xy[0])), int(round(xy[1])))
        if key in self._tried_clear:
            return False
        self._tried_clear.add(key)
        body = self.bot.clear(xy[0], xy[1], ch)
        if _accepted(body) and body.get("clear_result") == "success":
            self.book.mark_cleared(ch)
            return True
        if charge:
            self._clear_miss_n[ch] = self._clear_miss_n.get(ch, 0) + 1
        elif behind_lobe:
            if ch not in self._behind_lobe_free:
                self._behind_lobe_free.add(ch)
            else:
                self._uncharged_n[ch] = self._uncharged_n.get(ch, 0) + 1
        return False

    def _drain_pending(self) -> None:
        while True:
            pending = [c for c in self.book.pending() if c not in self.stuck]
            if not pending or len(self.book.cleared) >= self._target_n:
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
            if self._try_bearing_clears(ch, obs):
                return
            used = _diverse_obs(obs, 4)
            stations = [d.xy for d in used]
            bearings = [d.svd_deg for d in used]
            region = intersect_cones(stations, bearings)
            if region.empty or not region.bounded or len(region.vertices) < 2:
                last = obs[-1]
                if self._creep_clear(ch, last.xy, last.svd_deg):
                    return
                continue
            cen, rad = smallest_enclosing_circle(region.vertices)
            if rad <= CLEAR_R:
                if self._try_clear(cen, ch, charge=False):
                    return
                last = obs[-1]
                along = add(cen, scale(unit(last.svd_deg), 12.0))
                if self._try_clear(along, ch, charge=False):
                    return
            nxt = cen if dist(cen, self.bot.position) >= 8.0 else _third_point(region.vertices, self.bot.position)
            if self._measure_obs(ch, nxt, obs):
                continue
            if self._try_clear(nxt, ch):
                return
            last = obs[-1]
            self._creep_clear(ch, last.xy, last.svd_deg)
            return
        obs = self.book.detections.get(ch, [])
        if obs and ch not in self.book.cleared:
            last = obs[-1]
            if self._creep_clear(ch, last.xy, last.svd_deg):
                return
            self._fan_clear(ch, last.xy, last.svd_deg)

    def _try_bearing_clears(self, ch: int, obs: list[Detection]) -> bool:
        for q in _best_fixes(obs):
            if self._try_clear(q, ch, charge=False):
                return True
        return False

    def _take_second_fix(self, ch: int, s1: Point, th: float) -> None:
        compact = list(recommend_second_sides_compact(s1, th))
        compact.sort(key=lambda p: dist(p, self.bot.position))
        ordered = compact
        if not self.directional:
            pref = recommend_second(s1, th, now=self.bot.position)
            ordered = [pref] + [p for p in compact if dist(p, pref) > 5.0]
        for s2 in ordered:
            if dist(s2, s1) <= 5.0:
                continue
            if self._measure_obs(ch, s2, self.book.detections.get(ch, [])):
                return
            if self._try_clear(s2, ch):
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
        self.book.record_silence(ch, xy)
        if obs and self._try_clear(xy, ch, charge=False, behind_lobe=True):
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
        n_steps = MAX_CREEP_STEPS_DIR if self.directional else 16
        for _ in range(n_steps):
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
                if self._try_bearing_clears(ch, self.book.detections.get(ch, [])):
                    return True
                step = max(28.0, step * 0.65)
                continue
            # no_signal: may be just behind a directional lobe but still <20 m
            if self._try_clear(nxt, ch, charge=False, behind_lobe=True):
                return True
            if step <= 80.0 and self._clear_budget_left(ch) >= 3 and self._probe_segment(ch, last_good, nxt, heading):
                return True
            if self._try_clear(last_good, ch):
                return True
            closer = add(last_good, scale(unit(heading), 14.0))
            if self._try_clear(closer, ch):
                return True
            if step > 40.0:
                step = 28.0
                p = last_good
                continue
            return self._fan_clear(ch, last_good, heading)
        return self._try_clear(last_good, ch) or self._fan_clear(ch, last_good, heading)

    def _probe_segment(self, ch: int, a: Point, b: Point, _heading: float) -> bool:
        for t in (0.5, 0.25, 0.75):
            p = _lerp(a, b, t)
            if self._try_clear(p, ch):
                return True
            body = self.bot.measure(p[0], p[1], ch)
            if not _accepted(body):
                continue
            kind = body.get("measure_result")
            if kind == "near":
                return self._try_clear(p, ch)
            if kind == "direction":
                self.book.add_direction(ch, p, float(body["svd_deg"]))
                if self._try_clear(p, ch):
                    return True
                along = add(p, scale(unit(float(body["svd_deg"])), 12.0))
                if self._try_clear(along, ch):
                    return True
        return False

    def _fan_clear(self, ch: int, xy: Point, heading: float) -> bool:
        u = unit(heading)
        n = (-u[1], u[0])
        # Four nearby probes: along, back, left, right. Diagonals were mostly wasted misses.
        dirs = (u, scale(u, -1.0), n, scale(n, -1.0))
        for r in FAN_CLEAR_OFFSETS:
            for v in dirs:
                if self._try_clear(add(xy, scale(v, r)), ch):
                    return True
        return False

    def _home_and_clear(self, ch: int) -> None:
        if ch in self.book.cleared or not self.book.detections.get(ch):
            return
        self._localize_and_clear(ch)
        if ch in self.book.cleared:
            return
        obs = self.book.detections.get(ch, [])
        if not obs:
            return
        if self._try_bearing_clears(ch, obs):
            return
        last = obs[-1]
        self._fan_clear(ch, last.xy, last.svd_deg)
