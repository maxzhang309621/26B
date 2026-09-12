"""Search-localize-clear controller for problems 3 and 4.

Engineering guard: a monotonic real-time budget read from the /enter response
and explicit terminal evidence.  When no deadline is armed and no action
fails, the guard is inert and the normal Q3/Q4 path is unchanged.
"""

from __future__ import annotations

import math
import time
from typing import Callable

from geometry import (
    Point,
    Q3_ARENA_R,
    add,
    cross,
    dist,
    intersect_cones,
    intersect_feasible_region,
    locate_quality,
    scale,
    smallest_enclosing_circle,
    sub,
    unit,
)
from candidate import (
    front_compatible,
    from_body,
    in_candidate_region,
    next_stations,
    ray_exit_t,
    recommend_second,
    recommend_second_options,
    recommend_second_sides_compact,
)
from belief import ChannelBook, Detection, R_RULE_OUT
from coverage import (
    ENROUTE_R,
    Q4_OPT_OUTER_N,
    Q4_OPT_OUTER_R,
    Q4_OUTER_FULL_N,
    Q4_OUTER_FULL_R,
    covering_phases,
    directional_waypoints,
    omni_waypoints,
    q3_waypoints,
    q4_opt_search_waypoints,
    open_path_channel_order,
    open_path_cost,
    no_skip_open_path_channel_order,
    pick_q4_outer_ring,
    sector_fused_order,
)
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
DEFAULT_EXIT_RESERVE_S = 15.0
MAX_ACTION_ATTEMPTS = 2
# Receding-horizon open TSP (Q3 batch clear): execute a short prefix, replan.
Q3_RH_STEP_M = 280.0
Q3_RH_SWITCH_MARGIN_M = 50.0
Q3_RH_MAX_ITERS = 480
Q4_CLEAR_LOCAL_M = 650.0
Q4_CLEAR_PROXY_RHO = 380.0


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
    """Reconstruct travel / detect / switch / clear-ok / clear-miss from a RobotClient action log.

    Attribution convention: each action's travel and dwell are attributed to
    the action's target channel.  A measure dwell is detect time (5 s) plus
    channel-switch time (1 s) when the tuned channel changed; a clear dwell is
    success (5 s) or miss (3 s) time.  The tuned channel mirrors the
    simulator: only /measure changes it.
    """
    pos = (0.0, 0.0)
    travel_m = 0.0
    detect_s = 0.0
    switch_s = 0.0
    clear_ok_s = 0.0
    clear_miss_s = 0.0
    n_measure = n_clear = clear_ok = clear_miss = 0
    last_vt = 0.0
    tuned_channel = 1
    per_channel: dict[int, dict[str, float | int]] = {}

    def entry(ch: int) -> dict[str, float | int]:
        return per_channel.setdefault(
            ch,
            {
                "n_measure": 0,
                "n_clear": 0,
                "clear_ok": 0,
                "clear_miss": 0,
                "travel_s": 0.0,
                "detect_s": 0.0,
                "switch_s": 0.0,
                "clear_s": 0.0,
            },
        )

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
        ch = int(req.get("channel") or 0)
        if ch < 1 or ch > 20:
            continue
        d = dist(pos, xy)
        travel = d / speed_mps
        travel_m += d
        pos = xy
        vt = float(body.get("virtual_time_s") or last_vt)
        dwell = max(0.0, vt - last_vt - travel)
        last_vt = vt
        e = entry(ch)
        e["travel_s"] += travel
        if path == "/measure":
            sw = 1.0 if ch != tuned_channel else 0.0
            tuned_channel = ch
            detect = max(0.0, dwell - sw)
            n_measure += 1
            detect_s += detect
            switch_s += sw
            e["n_measure"] += 1
            e["detect_s"] += detect
            e["switch_s"] += sw
        else:
            n_clear += 1
            e["n_clear"] += 1
            if body.get("clear_result") == "success":
                clear_ok += 1
                clear_ok_s += dwell
                e["clear_ok"] += 1
            else:
                clear_miss += 1
                clear_miss_s += dwell
                e["clear_miss"] += 1
            e["clear_s"] += dwell
    for e in per_channel.values():
        e["total_s"] = e["travel_s"] + e["detect_s"] + e["switch_s"] + e["clear_s"]
    return {
        "travel_m": travel_m,
        "travel_s": travel_m / speed_mps,
        "detect_s": detect_s,
        "switch_s": switch_s,
        "clear_ok_s": clear_ok_s,
        "clear_miss_s": clear_miss_s,
        "n_measure": n_measure,
        "n_clear": n_clear,
        "clear_ok": clear_ok,
        "clear_miss": clear_miss,
        "per_channel": per_channel,
    }


class HuntPolicy:
    def __init__(
        self,
        bot: RobotClient,
        directional: bool = False,
        target_n: int | None = None,
        *,
        exit_reserve_s: float = DEFAULT_EXIT_RESERVE_S,
        monotonic_clock: Callable[[], float] | None = None,
        enable_step8_clear_ready_insertion: bool = False,
        q4_dynamic_outer: bool = False,
        q4_profile: str = "dynamic_pure",
        q4_enter_omni: int | None = None,
        q4_enter_dir: int | None = None,
        q4_outer_mode: str | None = None,
        q4_path_profile: str = "v_nofar",
        q4_insert_delta_max_m: float = 400.0,
        q3_path_profile: str = "defer",
    ) -> None:
        if not math.isfinite(exit_reserve_s) or exit_reserve_s < 0.0:
            raise ValueError("exit_reserve_s must be a finite non-negative number")
        self.bot = bot
        self.directional = directional
        self.exit_reserve_s = float(exit_reserve_s)
        self._clock = monotonic_clock or time.monotonic
        # Step 8 is an opt-in Q3 candidate.  The runner keeps this disabled
        # until a paired development/locked evaluation accepts the change.
        self._step8_insertion_enabled = bool(
            enable_step8_clear_ready_insertion and not directional
        )
        self._real_deadline_s: float | None = None
        self._deadline_guard = False
        self._action_failure = False
        self._action_failure_detail: str | None = None
        self._entered = False
        self._route_completed = False
        self._stopped_at_clear_limit = False
        self._coverage_short_circuit = False
        self.book = ChannelBook()
        self.q4_dynamic_outer = q4_dynamic_outer
        self.q4_profile = q4_profile if q4_profile in ("v2", "dynamic_pure") else "v2"
        self.q4_enter_omni = q4_enter_omni
        self.q4_enter_dir = q4_enter_dir
        self.q4_outer_mode = q4_outer_mode
        self.q4_path_profile = (
            q4_path_profile if q4_path_profile in ("v_nofar", "pathopt", "hexbatch") else "v_nofar"
        )
        self.q4_insert_delta_max_m = float(q4_insert_delta_max_m)
        self.q3_path_profile = q3_path_profile if q3_path_profile in ("defer", "batch") else "defer"
        self._pathopt = bool(directional and self.q4_path_profile == "pathopt")
        self._q3_batch = bool(not directional and self.q3_path_profile == "batch")
        self._q4_hexbatch = bool(directional and self.q4_path_profile == "hexbatch")
        self._cover_phase = False
        self._pathopt_rejoin: Point | None = None
        self.q4_outer_r = Q4_OPT_OUTER_R if self._q4_hexbatch else Q4_OUTER_FULL_R
        self.q4_outer_n = Q4_OPT_OUTER_N if self._q4_hexbatch else Q4_OUTER_FULL_N
        self.waypoints = (
            q4_opt_search_waypoints()
            if self._q4_hexbatch
            else (
                directional_waypoints(outer_r=Q4_OUTER_FULL_R, outer_n=Q4_OUTER_FULL_N)
                if directional
                else (q3_waypoints() if self._q3_batch else omni_waypoints())
            )
        )
        self.stuck: set[int] = set()
        self.creep_calls = 0
        self.creep_steps = 0
        self.creep_attempted: set[int] = set()
        self.route_rechecks = 0
        self.route_recheck_hits = 0
        self.deferred_channels: set[int] = set()
        self.dedicated_localizations = 0
        self.localization_services = 0
        self.first_seen_order: dict[int, int] = {}
        self._tried_clear: set[tuple[int, int, int]] = set()
        self._clear_miss_n: dict[int, int] = {}
        self._uncharged_n: dict[int, int] = {}
        self._behind_lobe_free: set[int] = set()
        self._inner_done = False
        self._cover_listens: list[Point] = []
        self._target_n = MAX_TOTAL_CLEARED
        self._move_context = "service"
        self._move_segments: list[dict] = []
        self._clear_audit: dict[str, dict[str, float]] = {}
        self._step8_ready: dict[int, dict[str, object]] = {}
        self._step8_rejected: set[int] = set()
        self._step8_edges: list[tuple[int, Point, Point]] = []
        self._step8_executed_edges: set[int] = set()
        self._step8_edge_start = 0
        self._step8_insertions: list[dict[str, object]] = []
        self.q3_rh_steps = 0
        self.q3_rh_replans = 0
        self.q3_rh_switches = 0
        self._q4_clear_queue: list[int] | None = None
        self._set_target_n(target_n)

    def _set_target_n(self, n: int | None) -> None:
        if isinstance(n, int) and 1 <= n <= MAX_TOTAL_CLEARED:
            self._target_n = n

    def _apply_target_n(self, body: dict | None) -> None:
        if not body:
            return
        self._set_target_n(body.get("jammer_count"))
        self._apply_q4_outer(body)

    def _apply_q4_outer(self, body: dict) -> None:
        """v_nofar keeps 12x2100. Dynamic outer is opt-in (run_q4_v2 only)."""
        if not self.directional or not self.q4_dynamic_outer:
            return
        omni = body.get("omnidirectional_jammer_count")
        dir_n = body.get("directional_jammer_count")
        if not isinstance(omni, int) and isinstance(self.q4_enter_omni, int):
            omni = self.q4_enter_omni
        if not isinstance(dir_n, int) and isinstance(self.q4_enter_dir, int):
            dir_n = self.q4_enter_dir
        self.q4_outer_r, self.q4_outer_n = pick_q4_outer_ring(
            omni if isinstance(omni, int) else None,
            dir_n if isinstance(dir_n, int) else None,
            jammer_count=body.get("jammer_count"),
            pure=self.q4_profile == "dynamic_pure",
        )
        if self._q4_hexbatch:
            self.waypoints = q4_opt_search_waypoints(
                outer_r=self.q4_outer_r,
                outer_n=self.q4_outer_n,
            )
            return
        self.waypoints = directional_waypoints(
            outer_r=self.q4_outer_r,
            outer_n=self.q4_outer_n,
        )

    def _target_from_log(self) -> None:
        for rec in reversed(self.bot.log):
            if rec.get("path") != "/enter":
                continue
            self._apply_target_n(rec.get("response") or {})
            return

    def _arm_real_deadline(self, enter_body: dict) -> None:
        remaining = enter_body.get("remaining_real_duration_s")
        if isinstance(remaining, (int, float)) and math.isfinite(float(remaining)):
            self._real_deadline_s = self._clock() + max(
                0.0, float(remaining) - self.exit_reserve_s
            )
            return
        self._real_deadline_s = None

    def _allow_action(self) -> bool:
        if self._deadline_guard or self._action_failure:
            return False
        if self._real_deadline_s is not None and self._clock() >= self._real_deadline_s:
            self._deadline_guard = True
            return False
        return True

    def _guard_tripped(self) -> bool:
        return self._deadline_guard or self._action_failure

    def _measure_action(self, xy: Point, ch: int) -> dict:
        start = self.bot.position
        for attempt in range(MAX_ACTION_ATTEMPTS):
            if not self._allow_action():
                return {"accepted": False, "q3_guarded": True}
            try:
                body = self.bot.measure(xy[0], xy[1], ch)
            except Exception as exc:  # preserve a terminal reason for the caller
                if attempt + 1 >= MAX_ACTION_ATTEMPTS:
                    self._action_failure = True
                    self._action_failure_detail = f"measure: {exc}"
                    return {"accepted": False, "q3_action_error": str(exc)}
                continue
            if _accepted(body):
                self._record_move("measure", start, xy, ch)
                return body
        self._action_failure = True
        self._action_failure_detail = "measure returned accepted=false after retries"
        return {"accepted": False, "q3_action_error": "measure rejected"}

    def _clear_action(self, xy: Point, ch: int) -> dict:
        start = self.bot.position
        for attempt in range(MAX_ACTION_ATTEMPTS):
            if not self._allow_action():
                return {"accepted": False, "q3_guarded": True}
            try:
                body = self.bot.clear(xy[0], xy[1], ch)
            except Exception as exc:  # preserve a terminal reason for the caller
                if attempt + 1 >= MAX_ACTION_ATTEMPTS:
                    self._action_failure = True
                    self._action_failure_detail = f"clear: {exc}"
                    return {"accepted": False, "q3_action_error": str(exc)}
                continue
            if _accepted(body):
                self._record_move("clear", start, xy, ch)
                return body
        self._action_failure = True
        self._action_failure_detail = "clear returned accepted=false after retries"
        return {"accepted": False, "q3_action_error": "clear rejected"}

    def _record_move(self, kind: str, start: Point, xy: Point, ch: int) -> None:
        travel_s = dist(start, xy) / SPEED_MPS
        self._move_segments.append(
            {
                "kind": kind,
                "context": self._move_context,
                "travel_s": travel_s,
                "xy": xy,
                "ch": ch,
            }
        )

    def _move_decomposition(self) -> dict:
        """Split travel into backbone-scan / planned-leg / rejoin / localization / clear.

        Q3 operational definition: a move issued by a cover-tour scan action
        at a backbone waypoint is backbone-scan travel; every other measure
        move is localization travel; every clear move is clear detour.  For
        the fixed-order omni tour the planned polyline legs are subtracted
        from backbone-scan travel and the remainder (signed) is the rejoin
        cost.  The directional branch keeps the raw buckets.
        """
        backbone_scan_s = sum(
            s["travel_s"] for s in self._move_segments
            if s["kind"] == "measure" and s["context"] == "backbone"
        )
        localization_s = sum(
            s["travel_s"] for s in self._move_segments
            if s["kind"] == "measure" and s["context"] == "service"
        )
        clear_detour_s = sum(s["travel_s"] for s in self._move_segments if s["kind"] == "clear")
        planned_s = 0.0
        visited: list[Point] = []
        for s in self._move_segments:
            if s["kind"] != "measure" or s["context"] != "backbone":
                continue
            xy = s["xy"]
            if all(dist(xy, v) > 1e-6 for v in visited):
                visited.append(xy)
        planned_s = sum(
            dist(visited[i - 1], visited[i]) for i in range(1, len(visited))
        ) / SPEED_MPS
        rejoin_s = backbone_scan_s - planned_s
        total = backbone_scan_s + localization_s + clear_detour_s
        return {
            "backbone_scan_s": backbone_scan_s,
            "backbone_planned_s": planned_s,
            "backbone_rejoin_s": rejoin_s,
            "localization_s": localization_s,
            "clear_detour_s": clear_detour_s,
            "total_s": total,
        }

    def _exit_with_retry(self) -> dict:
        last: dict = {"accepted": False}
        for _ in range(MAX_ACTION_ATTEMPTS):
            try:
                body = self.bot.exit()
            except Exception as exc:
                last = {"accepted": False, "q3_action_error": str(exc)}
                continue
            if _accepted(body):
                return body
            last = body
        return last

    def run(self, do_enter: bool = True) -> dict:
        if do_enter:
            ent = self.bot.enter()
            if not _accepted(ent):
                raise RuntimeError(f"enter failed: {ent}")
            self._entered = True
            self._arm_real_deadline(ent)
            self._apply_target_n(ent)
        else:
            self._entered = True
            remaining = getattr(self.bot, "remaining_real_duration_s", None)
            if isinstance(remaining, (int, float)) and math.isfinite(float(remaining)):
                self._arm_real_deadline({"remaining_real_duration_s": remaining})
            self._target_from_log()
        if not self._guard_tripped():
            if self.directional:
                if self._pathopt:
                    self._run_stagger_search_cover()
                elif self._q4_hexbatch:
                    self._run_q4_hexagon_search_cover()
                else:
                    self._run_directional_cover()
            else:
                if self._q3_batch:
                    self._run_omni_q3_search_cover()
                else:
                    self._run_omni_q3_cover()
        if not self._guard_tripped() and self.book.pending():
            self.stuck.clear()
            if self._q3_batch or self._q4_hexbatch:
                self._batch_clear_by_path()
                if self._q4_hexbatch:
                    leftover = set(self.book.pending())
                    self.stuck.clear()
                    for ch in leftover:
                        self._clear_miss_n[ch] = 0
                    self._tried_clear = {key for key in self._tried_clear if key[0] not in leftover}
                    for ch in list(self.book.pending()):
                        if self._guard_tripped():
                            break
                        self._home_and_clear(ch)
            else:
                for ch in list(self.book.pending()):
                    if self._guard_tripped():
                        break
                    self._home_and_clear(ch)
        pending_at_exit = len(self.book.pending())
        try:
            exit_body = self._exit_with_retry() if self._entered else {"accepted": False}
        except Exception as exc:
            exit_body = {"accepted": False, "q3_action_error": str(exc)}
        n_clear = len(self.book.cleared)
        vt = self.bot.virtual_time_s
        avg = vt / n_clear if n_clear else float("inf")
        extra = action_stats(self.bot.log)
        move_decomposition = self._move_decomposition()
        q4_inner_n = q4_inner_r = None
        if self.directional:
            _origin, inner_wps, _outer = covering_phases(self.waypoints)
            q4_inner_n = len(inner_wps)
            if inner_wps:
                q4_inner_r = dist(inner_wps[0], (0.0, 0.0))
        if self._deadline_guard:
            termination_reason = "deadline_guard"
        elif self._action_failure:
            termination_reason = "action_failure"
        elif self._stopped_at_clear_limit:
            termination_reason = "cleared_max_16"
        elif self._route_completed and pending_at_exit == 0:
            termination_reason = "coverage_complete"
        elif self._coverage_short_circuit:
            termination_reason = "coverage_short_circuit"
        elif self._route_completed:
            termination_reason = "route_completed_with_pending"
        elif self._done() or not self.book.unknown_channels():
            termination_reason = "coverage_complete"
        else:
            termination_reason = "incomplete"
        exit_accepted = _accepted(exit_body)
        completed = (
            pending_at_exit == 0
            and exit_accepted
            and not self._guard_tripped()
        )
        return {
            "cleared": n_clear,
            "virtual_time_s": vt,
            "avg_clear_s": avg,
            "channels": sorted(self.book.cleared),
            "creep_calls": self.creep_calls,
            "creep_steps": self.creep_steps,
            "route_rechecks": self.route_rechecks,
            "route_recheck_hits": self.route_recheck_hits,
            "deferred_channels": len(self.deferred_channels),
            "dedicated_localizations": self.dedicated_localizations,
            "localization_services": self.localization_services,
            "q4_outer_r": self.q4_outer_r if self.directional else None,
            "q4_outer_n": self.q4_outer_n if self.directional else None,
            "q4_path_profile": self.q4_path_profile if self.directional else None,
            "q3_path_profile": None if self.directional else self.q3_path_profile,
            "q3_ring_n": None if self.directional else max(0, len(self.waypoints) - 1),
            "q3_ring_r": (
                None
                if self.directional or len(self.waypoints) < 2
                else dist(self.waypoints[1], (0.0, 0.0))
            ),
            "q4_inner_n": q4_inner_n,
            "q4_inner_r": q4_inner_r,
            "q3_rh_steps": self.q3_rh_steps if self._q3_batch else 0,
            "q3_rh_replans": self.q3_rh_replans if self._q3_batch else 0,
            "q3_rh_switches": self.q3_rh_switches if self._q3_batch else 0,
            "q4_rh_steps": self.q3_rh_steps if self._q4_hexbatch else 0,
            "q4_rh_replans": self.q3_rh_replans if self._q4_hexbatch else 0,
            "q4_rh_switches": self.q3_rh_switches if self._q4_hexbatch else 0,
            "pending_at_exit": pending_at_exit,
            "exit_accepted": exit_accepted,
            "termination_reason": termination_reason,
            "completed": completed,
            "route_completed": self._route_completed,
            "stopped_at_clear_limit": self._stopped_at_clear_limit,
            "deadline_guard": self._deadline_guard,
            "action_failure": self._action_failure,
            "action_failure_detail": self._action_failure_detail,
            "unknown_channels_at_exit": self.book.unknown_channels(),
            "move_decomposition": move_decomposition,
            "clear_audit": self._clear_audit,
            "step8_insertion_enabled": self._step8_insertion_enabled,
            "step8_insertions": list(self._step8_insertions),
            "step8_pending_ready": sorted(self._step8_ready),
            **extra,
        }

    def _run_directional_cover(self) -> None:
        """Q4: origin → inner NN → outer NN (with enroute / redundancy skips)."""
        origin, inner, outer = covering_phases(self.waypoints)
        self._cover_phase = True
        self._pathopt_rejoin = inner[0] if inner else (outer[0] if outer else None)
        self._scan_point(origin, list(range(1, 21)))
        self._cover_listens.append(origin)
        self._drain_pending()
        self._cover_tour(inner)
        self._inner_done = True
        self._cover_tour(outer)
        self._cover_phase = False
        self._pathopt_rejoin = None
        if not self._guard_tripped() and not self._done():
            self._route_completed = True

    def _run_stagger_search_cover(self) -> None:
        """Q4 pathopt: interleaved inner/outer listens; clear as soon as heard."""
        origin, inner, outer = covering_phases(self.waypoints)
        rest = sector_fused_order([*inner, *outer])
        self._cover_phase = True
        self._inner_done = False
        self._scan_point(origin, list(range(1, 21)))
        self._cover_listens.append(origin)
        self._drain_pending()
        for wp in rest:
            if self._done() or self._search_complete() or self._guard_tripped():
                break
            leftover = [p for p in rest if dist(p, wp) > 1e-6]
            self._pathopt_rejoin = (
                min(leftover, key=lambda p: dist(wp, p)) if leftover else None
            )
            self._visit_cover_wp(wp)
            self._refresh_stagger_inner_done(inner)
        self._cover_phase = False
        self._inner_done = True
        self._pathopt_rejoin = None
        if not self._guard_tripped() and not self._done():
            self._route_completed = True

    def _run_q4_hexagon_search_cover(self) -> None:
        """Q4 hexbatch: opt inner/outer rings first; clear only near-field hits."""
        origin, inner, outer = covering_phases(self.waypoints)
        self._cover_phase = True
        self._inner_done = False
        self._scan_point(origin, list(range(1, 21)))
        self._cover_listens.append(origin)
        for wp in inner:
            if self._done() or self._search_complete() or self._guard_tripped():
                break
            self._listen_enroute(wp)
            if self._done() or self._search_complete() or self._guard_tripped():
                break
            unknown = self.book.unknown_channels()
            channels = self._channels_for(wp, unknown)
            if not channels:
                continue
            self._scan_point(wp, channels)
            self._cover_listens.append(wp)
        self._inner_done = True
        pending_outer = list(outer)
        while (
            pending_outer
            and not self._done()
            and not self._search_complete()
            and not self._guard_tripped()
        ):
            unknown = self.book.unknown_channels()
            if not unknown:
                break
            wp = min(pending_outer, key=lambda p: dist(self.bot.position, p))
            pending_outer = [p for p in pending_outer if dist(p, wp) > 1e-6]
            # Visit every certified outer vertex. Same-ring disks at 1865 m overlap
            # inside r_eff, but front-lobe cover does not, so do not skip as redundant.
            channels = self._channels_for(wp, unknown) or list(unknown)
            self._scan_point(wp, channels)
            self._cover_listens.append(wp)
        self._cover_phase = False
        self._inner_done = True
        if not self._guard_tripped() and not self._done():
            self._route_completed = True

    def _refresh_stagger_inner_done(self, inner: list[Point]) -> None:
        if not inner:
            self._inner_done = True
            return
        unknown = self.book.unknown_channels()
        self._inner_done = all(
            any(dist(p, q) <= 8.0 for q in self._cover_listens) or not self._waypoint_useful(p, unknown)
            for p in inner
        )

    def _run_omni_q3_search_cover(self) -> None:
        """Q3 batch: visit every listen point first; clear only near-field hits."""
        self._cover_phase = True
        self._scan_point(self.waypoints[0], list(range(1, 21)))
        self._cover_listens.append(self.waypoints[0])
        for wp in self.waypoints[1:]:
            if self._done() or self._guard_tripped():
                break
            unknown = self.book.unknown_channels()
            opportunistic = self._opportunistic_channels(wp)
            channels = []
            for ch in self._channels_for(wp, unknown) + opportunistic:
                if ch not in channels:
                    channels.append(ch)
            if not channels:
                continue
            self.route_rechecks += len(opportunistic)
            before_counts = {
                ch: len(self.book.detections.get(ch, [])) for ch in opportunistic
            }
            self._scan_point(wp, channels)
            self._cover_listens.append(wp)
            self.route_recheck_hits += sum(
                ch in self.book.cleared
                or len(self.book.detections.get(ch, [])) > before_counts[ch]
                for ch in opportunistic
            )
        self._cover_phase = False
        if not self._guard_tripped() and not self._done():
            self._route_completed = True

    def _batch_clear_by_path(self) -> None:
        """Receding-horizon open TSP: one move, then replan from the new pose."""
        if self._q4_hexbatch:
            self._batch_clear_locked_tsp()
            return
        sticky: int | None = None
        idle = 0
        for _ in range(Q3_RH_MAX_ITERS):
            if (
                not self.book.pending()
                or self._done()
                or self._guard_tripped()
            ):
                break
            ready = [c for c in self.book.pending() if c not in self.stuck]
            if not ready:
                break
            self.q3_rh_replans += 1
            opp = self._rh_standstill_opportunity()
            if opp is not None:
                ch = opp
                if sticky is not None and sticky != ch:
                    self.q3_rh_switches += 1
                sticky = None
            else:
                ch = self._rh_pick_channel(sticky)
                if ch is None:
                    break
                if sticky is not None and sticky != ch:
                    self.q3_rh_switches += 1
                sticky = ch
            before_pos = self.bot.position
            before_n = len(self.book.detections.get(ch, []))
            before_cleared = ch in self.book.cleared
            self.localization_services += 1
            if before_n == 1:
                self.dedicated_localizations += 1
            self._rh_service_step(ch)
            self.q3_rh_steps += 1
            if ch in self.book.cleared:
                sticky = None
                idle = 0
                continue
            moved = dist(self.bot.position, before_pos) > 1.0
            new_obs = len(self.book.detections.get(ch, [])) > before_n
            if moved or new_obs or (ch in self.book.cleared) != before_cleared:
                idle = 0
            else:
                idle += 1
                self.stuck.add(ch)
                sticky = None
            if idle > max(3, len(ready)):
                break

    def _batch_clear_locked_tsp(self) -> None:
        """Clear along a locked no-skip open TSP of estimated source positions."""
        self._q4_clear_queue = None
        idle = 0
        for _ in range(Q3_RH_MAX_ITERS):
            if not self.book.pending() or self._done() or self._guard_tripped():
                break
            pts = self._rh_ready_points()
            if not pts:
                break
            self.q3_rh_replans += 1
            pos = self.bot.position
            queue = [c for c in (self._q4_clear_queue or []) if c in pts]
            local_left = any(dist(pos, pts[c]) <= Q4_CLEAR_LOCAL_M for c in pts)
            planned_far = bool(queue) and dist(pos, pts[queue[0]]) > Q4_CLEAR_LOCAL_M + 1e-9
            if not queue or (local_left and planned_far):
                queue = no_skip_open_path_channel_order(pos, pts, local_m=Q4_CLEAR_LOCAL_M)
            nearest = min(pts, key=lambda c: (dist(pos, pts[c]), c))
            if dist(pos, pts[nearest]) + 80.0 < dist(pos, pts[queue[0]]):
                queue = no_skip_open_path_channel_order(pos, pts, local_m=Q4_CLEAR_LOCAL_M)
            ch = queue[0]
            self._q4_clear_queue = queue
            before_pos = self.bot.position
            before_n = len(self.book.detections.get(ch, []))
            before_cleared = ch in self.book.cleared
            self.localization_services += 1
            if before_n == 1:
                self.dedicated_localizations += 1
            self._rh_service_step(ch)
            self.q3_rh_steps += 1
            self._q4_clear_queue = [c for c in queue if c != ch]
            if ch in self.book.cleared:
                idle = 0
                continue
            moved = dist(self.bot.position, before_pos) > 1.0
            new_obs = len(self.book.detections.get(ch, [])) > before_n
            if moved or new_obs or (ch in self.book.cleared) != before_cleared:
                idle = 0
            else:
                idle += 1
            self.stuck.add(ch)
            if idle > max(3, len(pts)):
                break

    def _rh_ready_points(self) -> dict[int, Point]:
        return {
            ch: self._estimated_service_point(ch)
            for ch in self.book.pending()
            if ch not in self.stuck
        }

    def _rh_pick_channel(self, sticky: int | None) -> int | None:
        """First city of the current-position open TSP, with switch hysteresis."""
        pts = self._rh_ready_points()
        if not pts:
            return None
        start = self.bot.position
        if self._q4_hexbatch:
            order = no_skip_open_path_channel_order(start, pts, local_m=Q4_CLEAR_LOCAL_M)
        else:
            order = open_path_channel_order(start, pts)
        if not order:
            return None
        ch = order[0]
        if sticky is None or sticky not in pts or sticky == ch:
            return ch
        rest = {c: pts[c] for c in pts if c != sticky}
        tail = open_path_channel_order(pts[sticky], rest) if rest else []
        keep_cost = dist(start, pts[sticky]) + open_path_cost(
            pts[sticky], [pts[c] for c in tail]
        )
        tsp_cost = open_path_cost(start, [pts[c] for c in order])
        if keep_cost <= tsp_cost + Q3_RH_SWITCH_MARGIN_M:
            return sticky
        return ch

    def _rh_standstill_opportunity(self) -> int | None:
        """Service a source that is already at the current pose before traveling."""
        pos = self.bot.position
        ready = [c for c in self.book.pending() if c not in self.stuck]
        in_range: list[tuple[float, int]] = []
        for ch in ready:
            obs = self.book.detections.get(ch, [])
            if len(obs) < 2:
                continue
            est = self._estimated_service_point(ch)
            gap = dist(pos, est)
            if gap <= CLEAR_R:
                in_range.append((gap, ch))
        if in_range:
            return min(in_range)[1]
        # Q3 uses the farthest in-region 1-obs source for a wide baseline.
        # On Q4 directional that yanks the dog across the arena before TSP.
        if self._q4_hexbatch:
            return None
        seconds: list[tuple[float, int]] = []
        for ch in ready:
            obs = self.book.detections.get(ch, [])
            if len(obs) != 1:
                continue
            det = obs[0]
            if in_candidate_region(det.xy, det.svd_deg, pos) and dist(pos, det.xy) > 8.0:
                seconds.append((dist(pos, det.xy), ch))
        if seconds:
            return max(seconds)[1]
        return None

    @staticmethod
    def _rh_step_len(gap: float) -> float:
        if gap <= Q3_RH_STEP_M:
            return gap
        return min(Q3_RH_STEP_M, max(120.0, 0.5 * gap))

    def _rh_service_step(self, ch: int) -> None:
        """One protocol action toward the current estimated service point of ``ch``."""
        if self._guard_tripped() or ch in self.book.cleared:
            return
        obs = self.book.detections.get(ch, [])
        if not obs:
            return
        if self._q4_hexbatch:
            self._localize_and_clear(ch)
            return
        pos = self.bot.position
        dest = self._estimated_service_point(ch)
        gap = dist(pos, dest)
        step = self._rh_step_len(gap)
        if len(obs) == 1:
            target = dest if gap <= step + 1e-6 else _lerp(pos, dest, step / max(gap, 1e-9))
            self._measure_obs(ch, target, obs)
            if ch in self.book.cleared:
                return
            if dist(self.bot.position, dest) <= 8.0:
                self._try_clear(self.bot.position, ch, source="second_station")
            return
        used = _diverse_obs(obs, 4)
        quality = locate_quality(
            [d.xy for d in used],
            [d.svd_deg for d in used],
            silence=self.book.silent_at.get(ch),
        )
        if quality.can_clear_20 and quality.sec_center is not None:
            if self._try_clear(quality.sec_center, ch, charge=False, source="sec_center"):
                return
            last = obs[-1]
            along = add(quality.sec_center, scale(unit(last.svd_deg), 12.0))
            self._try_clear(along, ch, charge=False, source="sec_along")
            return
        if not quality.near_collinear and self._try_bearing_clears(ch, obs):
            return
        if gap > step + 1e-6:
            target = _lerp(pos, dest, step / gap)
            self._measure_obs(ch, target, obs)
            return
        if self._measure_obs(ch, dest, obs):
            return
        if self._try_clear(dest, ch, source="measure_fallback"):
            return
        last = obs[-1]
        self._creep_clear(ch, last.xy, last.svd_deg)

    def _run_omni_q3_cover(self) -> None:
        """Q3 round3 tour: fixed 8×1200 ring + opportunistic second looks + deferred drain."""
        self._step8_prepare_route(self.waypoints)
        self._step8_set_edge_start(0)
        self._scan_point(self.waypoints[0], list(range(1, 21)))
        self._drain_pending(self.waypoints[1:])
        for index, wp in enumerate(self.waypoints[1:], start=1):
            if self._done():
                self._stopped_at_clear_limit = True
                break
            edge_index = index - 1
            inserted = False
            if self._step8_insertion_enabled:
                self._step8_set_edge_start(edge_index)
                inserted = self._step8_service_before_edge(edge_index)
            unknown = self.book.unknown_channels()
            if not unknown and not self.book.pending() and not inserted:
                self._coverage_short_circuit = True
                break
            opportunistic = self._opportunistic_channels(wp)
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
            if self._step8_insertion_enabled:
                # The waypoint remains part of the route even when an
                # insertion was serviced immediately before this edge.
                self._step8_mark_edge_executed(edge_index)
                self._step8_set_edge_start(index)
            if self._guard_tripped():
                break
            self._drain_pending(self.waypoints[index + 1 :])
            if self._guard_tripped():
                break
        else:
            self._route_completed = True
        if self.book.pending():
            self.stuck.clear()
            self._drain_pending([])

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
        while pending and not self._done() and not self._search_complete() and not self._guard_tripped():
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
            leftover = [p for p in useful if dist(p, wp) > 1e-6]
            self._pathopt_rejoin = (
                min(leftover, key=lambda p: dist(wp, p)) if leftover else None
            )
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

        Inner (1200 m) must not suppress outer (~1900 m): radial gap is ~700 m < 1000 m,
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
        if not (self._q4_hexbatch and self._cover_phase):
            self._drain_pending()

    def _record_direction(self, ch: int, xy: Point, svd: float) -> None:
        if ch not in self.book.detections:
            self.first_seen_order.setdefault(ch, len(self.first_seen_order))
        self.book.add_direction(ch, xy, svd)

    def _scan_point(self, xy: Point, channels: list[int]) -> None:
        x, y = xy
        prev_context = self._move_context
        self._move_context = "backbone"
        try:
            for ch in channels:
                if self._done() or (self.directional and self._search_complete()):
                    break
                if ch in self.book.cleared:
                    continue
                body = self._measure_action((x, y), ch)
                if not _accepted(body):
                    if self._guard_tripped():
                        break
                    continue
                self.book.record_scan(ch, xy)
                kind = body.get("measure_result")
                if kind == "near":
                    self._try_clear(xy, ch, source="scan_near")
                elif kind == "direction":
                    self._record_direction(ch, xy, float(body["svd_deg"]))
                    self.stuck.discard(ch)
                else:
                    self.book.record_silence(ch, xy)
        finally:
            self._move_context = prev_context

    def _clear_budget_left(self, ch: int) -> int:
        return MAX_CLEAR_MISS_PER_CH - self._clear_miss_n.get(ch, 0)

    def _try_clear(
        self,
        xy: Point,
        ch: int,
        charge: bool = True,
        behind_lobe: bool = False,
        source: str = "unknown",
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
        start = self.bot.position
        body = self._clear_action(xy, ch)
        accepted = _accepted(body)
        if accepted:
            ok = body.get("clear_result") == "success"
            travel_s = dist(start, xy) / SPEED_MPS
            audit = self._clear_audit.setdefault(
                source,
                {
                    "attempts": 0,
                    "success": 0,
                    "miss": 0,
                    "travel_s": 0.0,
                    "miss_travel_s": 0.0,
                },
            )
            audit["attempts"] += 1
            audit["travel_s"] += travel_s
            if ok:
                audit["success"] += 1
            else:
                audit["miss"] += 1
                audit["miss_travel_s"] += travel_s
            if ok:
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

    def _drain_pending(self, future_waypoints: list[Point] | None = None) -> None:
        future = [] if self.directional else list(future_waypoints or [])
        while True:
            if self._guard_tripped():
                break
            pending = [
                c
                for c in self.book.pending()
                if c not in self.stuck and c not in self._step8_ready
            ]
            if not pending or len(self.book.cleared) >= self._target_n:
                break
            if (self._q3_batch or self._q4_hexbatch) and self._cover_phase:
                break
            if not self.directional:
                ready: list[int] = []
                for ch in pending:
                    obs = self.book.detections.get(ch, [])
                    if len(obs) == 1 and self._has_future_route_probe(ch, future):
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
            else:
                ch = min(
                    pending,
                    key=lambda c: dist(self.bot.position, self.book.detections[c][-1].xy),
                )
            self._localize_and_clear(ch)
            if ch not in self.book.cleared:
                self.stuck.add(ch)

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

    @staticmethod
    def _clip_arena_pt(p: Point) -> Point:
        radius = dist(p, (0.0, 0.0))
        if radius > Q3_ARENA_R:
            return scale(p, (Q3_ARENA_R - 1e-6) / radius)
        return p

    def _along_bearing_proxy(self, s1: Point, theta_deg: float, rho: float | None = None) -> Point:
        """Guess the source location on the first bearing (not a lateral second station)."""
        if rho is None:
            rho = Q4_CLEAR_PROXY_RHO if self._q4_hexbatch else 700.0
        t_exit = ray_exit_t(s1, theta_deg, Q3_ARENA_R)
        if t_exit > 1.0:
            rho = min(rho, 0.55 * t_exit)
        rho = max(120.0, rho)
        return self._clip_arena_pt(from_body(s1, theta_deg, rho, 0.0))

    def _estimated_service_point(self, ch: int) -> Point:
        obs = self.book.detections.get(ch, [])
        if not obs:
            return self.bot.position
        if len(obs) >= 2:
            quality = locate_quality(
                [d.xy for d in obs],
                [d.svd_deg for d in obs],
                silence=self.book.silent_at.get(ch),
            )
            if quality.sec_center is not None:
                cen = quality.sec_center
                radius = dist(cen, (0.0, 0.0))
                if radius > Q3_ARENA_R:
                    return scale(cen, (Q3_ARENA_R - 1e-6) / radius)
                return cen
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
        if self._q4_hexbatch:
            return self._along_bearing_proxy(obs[0].xy, obs[0].svd_deg)
        stations = next_stations(
            obs[0].xy,
            obs[0].svd_deg,
            now=self.bot.position,
            directional=self.directional,
            silence=self.book.silent_at.get(ch),
        )
        if stations:
            return stations[0]
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

    def _step8_prepare_route(self, route: list[Point]) -> None:
        if not self._step8_insertion_enabled:
            return
        self._step8_edges = [
            (index, route[index], route[index + 1])
            for index in range(max(0, len(route) - 1))
        ]
        self._step8_executed_edges.clear()
        self._step8_edge_start = 0

    def _step8_set_edge_start(self, index: int) -> None:
        if not self._step8_insertion_enabled:
            return
        self._step8_edge_start = max(0, min(index, len(self._step8_edges)))

    def _step8_mark_edge_executed(self, index: int) -> None:
        if self._step8_insertion_enabled and index == self._step8_edge_start:
            self._step8_executed_edges.add(index)

    @staticmethod
    def _step8_insert_delta(a: Point, c: Point, b: Point) -> float:
        """Extra path length for inserting C between an unexecuted A→B edge."""
        return dist(a, c) + dist(c, b) - dist(a, b)

    def _step8_future_edges(self) -> list[tuple[int, Point, Point]]:
        if not self._step8_insertion_enabled:
            return []
        return [
            edge
            for edge in self._step8_edges
            if edge[0] >= self._step8_edge_start
            and edge[0] not in self._step8_executed_edges
        ]

    def _step8_choose_insertion_edge(
        self,
        clear_point: Point,
        future_edges: list[tuple[int, Point, Point]] | None = None,
    ) -> tuple[int, float] | None:
        """Choose the cheapest still-future backbone edge for clear point C."""
        if not self._step8_insertion_enabled:
            return None
        edges = future_edges if future_edges is not None else self._step8_future_edges()
        candidates = [
            (self._step8_insert_delta(a, clear_point, b), index)
            for index, a, b in edges
            if index >= self._step8_edge_start
            and index not in self._step8_executed_edges
        ]
        if not candidates:
            return None
        delta, index = min(candidates, key=lambda item: (item[0], item[1]))
        return index, delta

    def _step8_clear_ready_point(self, quality: object) -> Point | None:
        if not self._step8_insertion_enabled:
            return None
        if not getattr(quality, "can_clear_20", False):
            return None
        point = getattr(quality, "sec_center", None)
        if point is None:
            return None
        if not all(math.isfinite(float(value)) for value in point):
            return None
        if dist(point, (0.0, 0.0)) > Q3_ARENA_R + 1e-6:
            return None
        return point

    def _step8_queue_clear_ready(self, ch: int, clear_point: Point) -> bool:
        if (
            not self._step8_insertion_enabled
            or ch in self.book.cleared
            or ch in self._step8_rejected
            or ch in self._step8_ready
        ):
            return False
        choice = self._step8_choose_insertion_edge(clear_point)
        if choice is None:
            return False
        edge_index, delta = choice
        self._step8_ready[ch] = {
            "point": clear_point,
            "edge_index": edge_index,
            "delta_m": delta,
        }
        self.stuck.discard(ch)
        return True

    def _step8_service_before_edge(self, edge_index: int) -> bool:
        if not self._step8_insertion_enabled:
            return False
        ready = sorted(
            (
                ch,
                item,
            )
            for ch, item in self._step8_ready.items()
            if item.get("edge_index") == edge_index
        )
        inserted = False
        for ch, item in ready:
            point = item["point"]
            if ch in self.book.cleared:
                self._step8_ready.pop(ch, None)
                continue
            ok = self._try_clear(point, ch, charge=False, source="step8_insert")
            if ok:
                status = "success"
                inserted = True
            else:
                # Do not lose a pending channel if a candidate point misses;
                # release it to the existing baseline service path.
                status = "fallback"
                self._step8_rejected.add(ch)
                self.stuck.discard(ch)
                self._localize_and_clear(ch)
            self._step8_ready.pop(ch, None)
            self._step8_insertions.append(
                {
                    "channel": ch,
                    "edge_index": edge_index,
                    "point": point,
                    "delta_m": item["delta_m"],
                    "status": status,
                }
            )
        return inserted

    def _localize_and_clear(self, ch: int) -> None:
        for _ in range(MAX_FIX_MEASURES):
            if self._guard_tripped():
                return
            if ch in self.book.cleared:
                return
            if ch in self._step8_ready:
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
            used = _diverse_obs(obs, 4)
            stations = [d.xy for d in used]
            bearings = [d.svd_deg for d in used]
            if not self.directional:
                # Q3: Q1 locate_quality first; skip near-collinear ray clears.
                quality = locate_quality(
                    stations,
                    bearings,
                    silence=self.book.silent_at.get(ch),
                )
                clear_ready = self._step8_clear_ready_point(quality)
                if clear_ready is not None and self._step8_queue_clear_ready(ch, clear_ready):
                    return
                if quality.can_clear_20 and quality.sec_center is not None:
                    if self._try_clear(quality.sec_center, ch, charge=False, source="sec_center"):
                        return
                    last = obs[-1]
                    along = add(quality.sec_center, scale(unit(last.svd_deg), 12.0))
                    if self._try_clear(along, ch, charge=False, source="sec_along"):
                        return
                if not quality.near_collinear and self._try_bearing_clears(ch, obs):
                    return
                region = (
                    quality.region if not quality.region.empty else intersect_cones(stations, bearings)
                )
            else:
                quality = locate_quality(
                    stations,
                    bearings,
                    silence=self.book.silent_at.get(ch),
                )
                # Hexbatch: collinear along-ray looks must not fire far false intersections.
                if not (self._q4_hexbatch and quality.near_collinear) and self._try_bearing_clears(ch, obs):
                    return
                if quality.can_clear_20 and quality.sec_center is not None:
                    if self._try_clear(quality.sec_center, ch, charge=False, source="sec_center"):
                        return
                    last = obs[-1]
                    along = add(quality.sec_center, scale(unit(last.svd_deg), 12.0))
                    if self._try_clear(along, ch, charge=False, source="sec_along"):
                        return
                region = intersect_cones(stations, bearings)
            if region.empty or not region.bounded or len(region.vertices) < 2:
                last = obs[-1]
                if self._creep_clear(ch, last.xy, last.svd_deg):
                    return
                continue
            cen, rad = smallest_enclosing_circle(region.vertices)
            if rad <= CLEAR_R:
                if self._try_clear(cen, ch, charge=False, source="sec_center"):
                    return
                last = obs[-1]
                along = add(cen, scale(unit(last.svd_deg), 12.0))
                if self._try_clear(along, ch, charge=False, source="sec_along"):
                    return
            nxt = cen if dist(cen, self.bot.position) >= 8.0 else _third_point(region.vertices, self.bot.position)
            if self._measure_obs(ch, nxt, obs):
                continue
            if self._try_clear(nxt, ch, source="measure_fallback"):
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
            if self._try_clear(q, ch, charge=False, source="bearing"):
                return True
        return False

    def _take_second_fix(self, ch: int, s1: Point, th: float) -> None:
        if self._q4_hexbatch and self.directional:
            self._take_second_fix_hexbatch(ch, s1, th)
            return
        if not self.directional:
            # Q3: Q2 next_stations primary, then legal recommend_second_options.
            ordered = next_stations(
                s1,
                th,
                now=self.bot.position,
                directional=False,
                silence=self.book.silent_at.get(ch),
            )
            for p in recommend_second_options(s1, th, now=self.bot.position):
                if all(dist(p, q) > 5.0 for q in ordered):
                    ordered.append(p)
            if not ordered:
                pref = recommend_second(s1, th, now=self.bot.position)
                compact = list(recommend_second_sides_compact(s1, th))
                ordered = [pref] + [p for p in compact if dist(p, pref) > 5.0]
        else:
            compact = list(recommend_second_sides_compact(s1, th))
            compact.sort(key=lambda p: dist(p, self.bot.position))
            extra = next_stations(
                s1,
                th,
                now=self.bot.position,
                directional=True,
                silence=self.book.silent_at.get(ch),
            )
            ordered = compact
            for p in extra:
                if all(dist(p, q) > 5.0 for q in ordered):
                    ordered.append(p)
        for s2 in ordered:
            if dist(s2, s1) <= 5.0:
                continue
            if self._measure_obs(ch, s2, self.book.detections.get(ch, [])):
                return
            if self._try_clear(s2, ch, source="second_station"):
                return
            if not self.directional:
                return

    def _take_second_fix_hexbatch(self, ch: int, s1: Point, th: float) -> None:
        """One nearest front-lobe second station, then along-ray; never both sides."""
        now = self.bot.position
        silence = self.book.silent_at.get(ch)
        ordered: list[Point] = []
        compact = list(recommend_second_sides_compact(s1, th))
        compact.sort(key=lambda p: dist(p, now))
        for p in compact:
            if dist(p, s1) <= 5.0:
                continue
            if not front_compatible(s1, th, p):
                continue
            if silence and any(dist(p, q) < 35.0 for q in silence):
                continue
            ordered.append(p)
            break
        if not ordered:
            extra = next_stations(
                s1,
                th,
                now=now,
                directional=True,
                silence=silence,
            )
            for p in extra:
                if dist(p, s1) > 5.0:
                    ordered.append(p)
                    break
        along = self._along_bearing_proxy(s1, th, rho=450.0)
        if dist(along, s1) > 80.0 and all(dist(along, q) > 40.0 for q in ordered):
            ordered.append(along)
        for s2 in ordered:
            if ch in self.book.cleared:
                return
            before = len(self.book.detections.get(ch, []))
            heard = self._measure_obs(ch, s2, self.book.detections.get(ch, []))
            if ch in self.book.cleared or heard or len(self.book.detections.get(ch, [])) > before:
                return
            if dist(s2, s1) <= 40.0 and self._try_clear(s2, ch, source="second_station"):
                return

    def _measure_obs(self, ch: int, xy: Point, obs: list) -> bool:
        body = self._measure_action(xy, ch)
        if not _accepted(body):
            return False
        kind = body.get("measure_result")
        if kind == "near":
            return self._try_clear(xy, ch, source="near_pos")
        if kind == "direction":
            self._record_direction(ch, xy, float(body["svd_deg"]))
            return True
        self.book.record_silence(ch, xy)
        near_last = bool(obs) and dist(xy, obs[-1].xy) <= 40.0
        if obs and (near_last or not self._q4_hexbatch):
            if self._try_clear(xy, ch, charge=False, behind_lobe=True, source="behind_lobe"):
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
            body = self._measure_action(nxt, ch)
            if not _accepted(body):
                break
            kind = body.get("measure_result")
            if kind == "near":
                return self._try_clear(nxt, ch, source="creep_near")
            if kind == "direction":
                last_good = nxt
                heading = float(body["svd_deg"])
                p = nxt
                self._record_direction(ch, nxt, heading)
                if not self._q4_hexbatch and self._try_bearing_clears(ch, self.book.detections.get(ch, [])):
                    return True
                step = max(28.0, step * 0.65)
                continue
            # no_signal: may be just behind a directional lobe but still <20 m
            if self._try_clear(nxt, ch, charge=False, behind_lobe=True, source="creep_behind_lobe"):
                return True
            if step <= 80.0 and self._clear_budget_left(ch) >= 3 and self._probe_segment(ch, last_good, nxt, heading):
                return True
            if self._try_clear(last_good, ch, source="creep_last"):
                return True
            closer = add(last_good, scale(unit(heading), 14.0))
            if self._try_clear(closer, ch, source="creep_closer"):
                return True
            if step > 40.0:
                step = 28.0
                p = last_good
                continue
            return self._fan_clear(ch, last_good, heading)
        return self._try_clear(last_good, ch, source="creep_last") or self._fan_clear(ch, last_good, heading)

    def _probe_segment(self, ch: int, a: Point, b: Point, _heading: float) -> bool:
        for t in (0.5, 0.25, 0.75):
            p = _lerp(a, b, t)
            if self._try_clear(p, ch, source="probe"):
                return True
            body = self._measure_action(p, ch)
            if not _accepted(body):
                continue
            kind = body.get("measure_result")
            if kind == "near":
                return self._try_clear(p, ch, source="probe_near")
            if kind == "direction":
                self._record_direction(ch, p, float(body["svd_deg"]))
                if self._try_clear(p, ch, source="probe_dir"):
                    return True
                along = add(p, scale(unit(float(body["svd_deg"])), 12.0))
                if self._try_clear(along, ch, source="probe_along"):
                    return True
        return False

    def _fan_clear(self, ch: int, xy: Point, heading: float) -> bool:
        u = unit(heading)
        n = (-u[1], u[0])
        # Four nearby probes: along, back, left, right. Diagonals were mostly wasted misses.
        dirs = (u, scale(u, -1.0), n, scale(n, -1.0))
        for r in FAN_CLEAR_OFFSETS:
            for v in dirs:
                if self._try_clear(add(xy, scale(v, r)), ch, source="fan"):
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
