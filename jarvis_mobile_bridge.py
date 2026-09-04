"""JARVIS NEO PC <-> Mobile bridge.

LAN-first, authenticated WebSocket bridge with UDP discovery. The protocol is
transport-agnostic so a future TLS/relay transport can reuse the same frames.
No arbitrary shell execution is exposed: host actions must go through the
allow-listed handler supplied by the PC application.
"""
from __future__ import annotations

import asyncio
import json
import secrets
import socket
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

DISCOVERY_PORT = 47821
WS_PORT = 47822
PROTOCOL = "jarvis-neo/1"

ActionHandler = Callable[[str, dict[str, Any]], Awaitable[Any] | Any]
StateProvider = Callable[[], dict[str, Any]]


def _code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _token() -> str:
    return secrets.token_urlsafe(32)


@dataclass
class MobileSession:
    device_id: str
    token: str
    websocket: WebSocket
    connected_at: float = field(default_factory=time.time)


@dataclass
class MobileBridge:
    host: str = "0.0.0.0"
    ws_port: int = WS_PORT
    discovery_port: int = DISCOVERY_PORT
    device_name: str = "JARVIS NEO PC"
    action_handler: ActionHandler | None = None
    state_provider: StateProvider | None = None
    app: FastAPI = field(init=False)
    _pairing_code: str = field(default_factory=_code, init=False)
    _sessions: dict[str, MobileSession] = field(default_factory=dict, init=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)
    _state: dict[str, Any] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self.app = FastAPI(title="JARVIS NEO Mobile Bridge", version=PROTOCOL)
        self._routes()

    @property
    def pairing_code(self) -> str:
        return self._pairing_code

    def rotate_pairing_code(self) -> str:
        self._pairing_code = _code()
        return self._pairing_code

    def set_state(self, **values: Any) -> None:
        self._state.update(values)

    def snapshot(self) -> dict[str, Any]:
        result = dict(self._state)
        if self.state_provider:
            try:
                result.update(self.state_provider())
            except Exception:
                pass
        result["protocol"] = PROTOCOL
        result["device"] = self.device_name
        result["connected_devices"] = len(self._sessions)
        return result

    def _routes(self) -> None:
        @self.app.get("/mobile/status")
        async def status() -> dict[str, Any]:
            return self.snapshot()

        @self.app.websocket("/mobile/ws")
        async def mobile_ws(ws: WebSocket) -> None:
            await ws.accept()
            session: MobileSession | None = None
            try:
                hello = await asyncio.wait_for(ws.receive_json(), timeout=15)
                if hello.get("type") != "pair" or str(hello.get("protocol")) != PROTOCOL:
                    await ws.send_json({"type": "error", "code": "PROTOCOL_INVALID"})
                    await ws.close(code=1008)
                    return
                if not secrets.compare_digest(str(hello.get("code", "")), self._pairing_code):
                    await ws.send_json({"type": "error", "code": "PAIRING_FAILED"})
                    await ws.close(code=1008)
                    return

                device_id = str(hello.get("device_id") or secrets.token_hex(8))
                session = MobileSession(device_id=device_id, token=_token(), websocket=ws)
                async with self._lock:
                    self._sessions[session.token] = session
                await ws.send_json({
                    "type": "paired", "protocol": PROTOCOL,
                    "device_id": device_id, "token": session.token,
                    "server": self.device_name, "state": self.snapshot(),
                })
                self.rotate_pairing_code()  # one-time pairing secret
                await self._broadcast_state()

                while True:
                    msg = await ws.receive_json()
                    if msg.get("token") != session.token:
                        await ws.send_json({"type": "error", "code": "TOKEN_INVALID"})
                        continue
                    await self._handle(ws, msg)
            except (WebSocketDisconnect, asyncio.TimeoutError):
                pass
            finally:
                if session:
                    async with self._lock:
                        self._sessions.pop(session.token, None)
                    await self._broadcast_state()

    async def _handle(self, ws: WebSocket, msg: dict[str, Any]) -> None:
        request_id = msg.get("request_id")
        kind = msg.get("type")
        if kind == "ping":
            await ws.send_json({"type": "pong", "request_id": request_id, "ts": time.time()})
            return
        if kind == "status":
            await ws.send_json({"type": "status", "request_id": request_id, "state": self.snapshot()})
            return
        if kind == "sync":
            await ws.send_json({"type": "sync", "request_id": request_id, "state": self.snapshot()})
            return
        if kind == "action":
            action = str(msg.get("action", ""))
            args = msg.get("args") or {}
            if not action or not isinstance(args, dict):
                await ws.send_json({"type": "error", "request_id": request_id, "code": "ACTION_INVALID"})
                return
            try:
                if self.action_handler is None:
                    result = {"accepted": False, "reason": "NO_HOST_ACTION_HANDLER"}
                else:
                    result = self.action_handler(action, args)
                    if asyncio.iscoroutine(result):
                        result = await result
            except Exception as exc:
                result = {"accepted": False, "error": str(exc)}
            await ws.send_json({"type": "action_result", "request_id": request_id,
                                "action": action, "result": result})
            return
        await ws.send_json({"type": "error", "request_id": request_id, "code": "UNKNOWN_MESSAGE"})

    async def _broadcast_state(self) -> None:
        if not self._sessions:
            return
        message = {"type": "state", "state": self.snapshot(), "ts": time.time()}
        dead: list[str] = []
        for token, session in list(self._sessions.items()):
            try:
                await session.websocket.send_json(message)
            except Exception:
                dead.append(token)
        for token in dead:
            self._sessions.pop(token, None)

    async def publish(self, event: str, payload: dict[str, Any] | None = None) -> None:
        message = {"type": "event", "event": event, "payload": payload or {}, "ts": time.time()}
        for session in list(self._sessions.values()):
            try:
                await session.websocket.send_json(message)
            except Exception:
                pass

    def discovery_payload(self) -> bytes:
        # Never broadcast the pairing code or an access token.
        return json.dumps({
            "type": "jarvis_discovery", "protocol": PROTOCOL,
            "device": self.device_name, "port": self.ws_port,
            "hostname": socket.gethostname(),
        }).encode()

    def start_discovery(self) -> threading.Thread:
        def worker() -> None:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            payload = self.discovery_payload()
            while True:
                try:
                    sock.sendto(payload, ("255.255.255.255", self.discovery_port))
                except OSError:
                    pass
                threading.Event().wait(3)
        t = threading.Thread(target=worker, name="jarvis-mobile-discovery", daemon=True)
        t.start()
        return t


bridge = MobileBridge()

if __name__ == "__main__":
    import uvicorn
    bridge.start_discovery()
    print(f"JARVIS NEO Mobile Bridge: port {WS_PORT} | pairing code: {bridge.pairing_code}")
    uvicorn.run(bridge.app, host=bridge.host, port=bridge.ws_port)
