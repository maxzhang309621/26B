"""Single-owner practice session: no concurrent /enter race on :2026.

Causes of past「接口冲突」:
- orphaned run_*_practice_batch after parent shell killed
- starting next round while previous API still half-open
- ad-hoc enter while a batch is mid-hunt
"""

from __future__ import annotations

import atexit
import json
import os
import signal
import subprocess
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
LOCK_DIR = PROJECT / "output" / "drill"
LOCK_PATH = LOCK_DIR / ".practice_api.lock"

# Only these scripts may own the practice HTTP session.
_PRACTICE_MARKERS = (
    "run_q4_practice_batch.py",
    "run_q3_practice_batch.py",
    "run_practice_batch.py",
    "run_drill.py",
)


class PracticeBusy(RuntimeError):
    """Another practice runner already holds the API lock."""


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    except SystemError:
        return False
    return True


def _list_python_cmdlines() -> list[tuple[int, str]]:
    """Windows: (pid, commandline) for python.exe."""
    ps = (
        "Get-CimInstance Win32_Process -Filter \"Name='python.exe' OR Name='pythonw.exe'\" "
        "| ForEach-Object { '{0}\t{1}' -f $_.ProcessId, $_.CommandLine }"
    )
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    out: list[tuple[int, str]] = []
    for line in (proc.stdout or "").splitlines():
        line = line.strip()
        if not line or "\t" not in line:
            continue
        pid_s, cmd = line.split("\t", 1)
        try:
            out.append((int(pid_s), cmd or ""))
        except ValueError:
            continue
    return out


def find_other_practice_runners(self_pid: int | None = None) -> list[tuple[int, str]]:
    me = self_pid if self_pid is not None else os.getpid()
    found: list[tuple[int, str]] = []
    for pid, cmd in _list_python_cmdlines():
        if pid == me:
            continue
        low = cmd.lower().replace("/", "\\")
        if any(m.lower() in low for m in _PRACTICE_MARKERS):
            found.append((pid, cmd.strip()))
    return found


def stop_other_practice_runners(self_pid: int | None = None) -> list[int]:
    """Kill leftover practice batch/drill processes (not the simulator)."""
    killed: list[int] = []
    for pid, _cmd in find_other_practice_runners(self_pid):
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            try:
                subprocess.run(
                    ["taskkill", "/PID", str(pid), "/F"],
                    capture_output=True,
                    timeout=8,
                )
            except (OSError, subprocess.TimeoutExpired):
                continue
        killed.append(pid)
    if killed:
        time.sleep(1.2)
    return killed


def _read_lock() -> dict[str, Any] | None:
    if not LOCK_PATH.is_file():
        return None
    try:
        return json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def acquire_practice_lock(owner: str, *, steal_dead: bool = True) -> Path:
    """Exclusive lock for practice HTTP use. Raises PracticeBusy if another live owner."""
    LOCK_DIR.mkdir(parents=True, exist_ok=True)
    me = os.getpid()
    existing = _read_lock()
    if existing:
        old_pid = int(existing.get("pid") or 0)
        if old_pid == me:
            return LOCK_PATH
        if _pid_alive(old_pid):
            raise PracticeBusy(
                f"演练接口已被占用：pid={old_pid} owner={existing.get('owner')!r}。"
                "请先结束那个进程，或等它跑完；禁止并行 /enter。"
            )
        if not steal_dead:
            raise PracticeBusy(f"残留锁文件 {LOCK_PATH}（pid={old_pid} 已死）")
    payload = {
        "pid": me,
        "owner": owner,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    LOCK_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    atexit.register(release_practice_lock)
    return LOCK_PATH


def release_practice_lock() -> None:
    me = os.getpid()
    existing = _read_lock()
    if not existing:
        return
    if int(existing.get("pid") or 0) != me:
        return
    try:
        LOCK_PATH.unlink(missing_ok=True)
    except OSError:
        pass


def probe_api(
    url: str = "http://127.0.0.1:2026",
    *,
    robot_id: str = "__api_probe__",
    timeout: float = 1.5,
) -> str:
    """Return closed | reject | accept | http_error.

    Uses a non-team robot_id by default so a readiness probe never steals /enter.
    """
    base = url.rstrip("/")
    body = json.dumps(
        {
            "arena_id": "default",
            "robot_id": robot_id,
            "request_id": f"probe-{time.time_ns()}",
        },
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    req = Request(
        base + "/enter",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
            if raw.get("accepted") is True:
                return "accept"
            return "reject"
    except HTTPError as exc:
        try:
            raw = json.loads(exc.read().decode("utf-8"))
            if raw.get("accepted") is True:
                return "accept"
            return "reject"
        except Exception:
            return "http_error"
    except (URLError, TimeoutError, OSError, ConnectionError):
        return "closed"
    except Exception:
        return "http_error"


def wait_api_closed(
    url: str,
    *,
    timeout_s: float = 45.0,
    need_streak: int = 3,
) -> None:
    """Block until practice HTTP is down for need_streak consecutive probes."""
    deadline = time.time() + timeout_s
    streak = 0
    while time.time() < deadline:
        state = probe_api(url)
        if state == "closed":
            streak += 1
            if streak >= need_streak:
                return
        else:
            streak = 0
        time.sleep(0.35)
    raise TimeoutError(f"等待演练接口关闭超时 {timeout_s:.0f}s（上一局未完全结束）")


def soft_exit(url: str, robot_id: str) -> None:
    """Best-effort /exit so the simulator can tear down before next start click."""
    body = json.dumps(
        {
            "arena_id": "default",
            "robot_id": robot_id,
            "request_id": f"soft-exit-{time.time_ns()}",
        },
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    req = Request(
        url.rstrip("/") + "/exit",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=2.0) as resp:
            resp.read()
    except Exception:
        pass


def claim_practice_api(owner: str, url: str, robot_id: str) -> None:
    """Call once at batch start: stop orphans, take lock, refuse if API already open."""
    killed = stop_other_practice_runners()
    if killed:
        print(f"已结束残留演练进程 pid={killed}，避免接口冲突")
    try:
        acquire_practice_lock(owner)
    except PracticeBusy:
        stop_other_practice_runners()
        time.sleep(0.5)
        acquire_practice_lock(owner)
    state = probe_api(url)
    if state != "closed":
        print(f"检测到接口仍开着（{state}），先 /exit 并等待关闭…")
        soft_exit(url, robot_id)
        wait_api_closed(url, timeout_s=60.0)
    print(f"演练单实例锁已获取 pid={os.getpid()} → {LOCK_PATH}")


def finish_round_api(url: str, robot_id: str, *, timeout_s: float = 60.0) -> None:
    """After a hunt (ok or fail): exit and wait until :2026 is fully down before next start."""
    soft_exit(url, robot_id)
    try:
        wait_api_closed(url, timeout_s=timeout_s)
    except TimeoutError as exc:
        print(f"警告: {exc}；仍继续，但下一局可能不稳")
        soft_exit(url, robot_id)
        time.sleep(2.0)