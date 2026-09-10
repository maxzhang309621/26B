"""Synchronous robot API client. Transport is HTTP or in-process mock."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class Transport(Protocol):
    def post(self, path: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        ...


class HttpTransport:
    def __init__(self, base_url: str = "http://127.0.0.1:2026", timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def post(self, path: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        req = Request(
            self.base_url + path,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(req, timeout=self.timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                return resp.status, body
        except HTTPError as exc:
            raw = exc.read().decode("utf-8") if exc.fp else "{}"
            try:
                body = json.loads(raw) if raw else {"accepted": False, "real_timestamp_ms": 0, "virtual_time_s": 0}
            except json.JSONDecodeError:
                body = {"accepted": False, "real_timestamp_ms": 0, "virtual_time_s": 0, "error": raw}
            return exc.code, body
        except URLError as exc:
            raise ConnectionError(str(exc.reason)) from exc


class FnTransport:
    def __init__(self, handler: Callable[[str, dict[str, Any]], dict[str, Any]]) -> None:
        self.handler = handler

    def post(self, path: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        body = self.handler(path, payload)
        return 200, body


@dataclass
class RobotClient:
    robot_id: str
    transport: Transport
    arena_id: str = "default"
    position: tuple[float, float] = (0.0, 0.0)
    channel: int = 1
    virtual_time_s: float = 0.0
    remaining_real_duration_s: int | None = None
    log: list[dict[str, Any]] = field(default_factory=list)
    _seq: int = 0

    def new_request_id(self, prefix: str) -> str:
        self._seq += 1
        return f"{prefix}-{self._seq}-{uuid.uuid4().hex[:8]}"

    def _base(self, request_id: str) -> dict[str, Any]:
        return {"arena_id": self.arena_id, "robot_id": self.robot_id, "request_id": request_id}

    def _call(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        last_err: Exception | None = None
        status, body = 0, {}
        for attempt in range(8):
            try:
                status, body = self.transport.post(path, payload)
                last_err = None
                break
            except (ConnectionError, TimeoutError, OSError) as exc:
                last_err = exc
                time.sleep(0.35)
        rec = {"path": path, "http_status": status, "request": payload, "response": body}
        if last_err is not None:
            raise ConnectionError(f"{path} 连接失败（倒计时未结束或接口未开放是正常现象）: {last_err}") from last_err
        self.log.append(rec)
        if status != 200:
            raise RuntimeError(f"HTTP {status} for {path}: {body}")
        if body.get("accepted") is True and path in ("/measure", "/clear"):
            vt = body.get("virtual_time_s")
            if isinstance(vt, (int, float)):
                self.virtual_time_s = float(vt)
            if "position" in payload:
                self.position = (float(payload["position"]["x"]), float(payload["position"]["y"]))
            if path == "/measure":
                self.channel = int(payload["channel"])
        return body

    def wait_enter(self, timeout_s: float = 600.0, poll_s: float = 0.4) -> dict[str, Any]:
        """Poll /enter until the official API is open and the request is accepted."""
        deadline = time.time() + timeout_s
        rid = "enter-wait-1"
        last_body: dict[str, Any] | None = None
        while time.time() < deadline:
            try:
                body = self.enter(request_id=rid)
                last_body = body
                if body.get("accepted") is True:
                    return body
                raise RuntimeError(
                    "模拟器拒绝 /enter（队号须与当前登录参赛队号完全一致，且本局尚未进入）。"
                    f" 响应={body}"
                )
            except (ConnectionError, TimeoutError, OSError):
                rid = "enter-wait-1"
            time.sleep(poll_s)
        raise TimeoutError(f"等待 /enter 超时 {timeout_s:.0f}s，最后响应={last_body}")

    def enter(self, request_id: str | None = None) -> dict[str, Any]:
        rid = request_id or self.new_request_id("enter")
        body = self._call("/enter", self._base(rid))
        if body.get("accepted") is True:
            self.position = (0.0, 0.0)
            self.channel = 1
            self.virtual_time_s = float(body.get("virtual_time_s") or 0.0)
            rem = body.get("remaining_real_duration_s")
            if isinstance(rem, (int, float)):
                self.remaining_real_duration_s = int(rem)
        return body

    def measure(self, x: float, y: float, channel: int, request_id: str | None = None) -> dict[str, Any]:
        rid = request_id or self.new_request_id("measure")
        payload = self._base(rid)
        payload["position"] = {"x": x, "y": y}
        payload["channel"] = channel
        return self._call("/measure", payload)

    def clear(self, x: float, y: float, channel: int, request_id: str | None = None) -> dict[str, Any]:
        rid = request_id or self.new_request_id("clear")
        payload = self._base(rid)
        payload["position"] = {"x": x, "y": y}
        payload["channel"] = channel
        return self._call("/clear", payload)

    def exit(self, request_id: str | None = None) -> dict[str, Any]:
        rid = request_id or self.new_request_id("exit")
        return self._call("/exit", self._base(rid))
