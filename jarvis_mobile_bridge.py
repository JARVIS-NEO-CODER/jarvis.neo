"""Authenticated PC <-> J.A.R.V.I.S. NEO Mobile bridge.

LAN-first transport used by the React Native client. The bridge exposes a
small REST API for pairing/commands and a WebSocket for live state/events.
Tokens are persisted locally so an already-authorized phone reconnects after
a PC restart. No arbitrary shell execution is exposed.
"""
from __future__ import annotations

import asyncio
import json
import secrets
import socket
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

DEFAULT_PORT = 8890
DISCOVERY_PORT = 47821
PROTOCOL = "jarvis-neo/1"
PAIRING_TTL = 300
STATE_BROADCAST_INTERVAL = 2.0
DEVICES_FILE = Path.home() / ".jarvis_neo" / "mobile_devices.json"

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
    port: int = DEFAULT_PORT
    discovery_port: int = DISCOVERY_PORT
    device_name: str = "JARVIS NEO PC"
    action_handler: ActionHandler | None = None
    state_provider: StateProvider | None = None
    app: FastAPI = field(init=False)
    _pairing_code: str = field(default_factory=_code, init=False)
    _pairing_expires_at: float = field(default_factory=lambda: time.time() + PAIRING_TTL, init=False)
    _devices: dict[str, dict[str, Any]] = field(default_factory=dict, init=False)
    _sessions: dict[str, MobileSession] = field(default_factory=dict, init=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)
    _state: dict[str, Any] = field(default_factory=dict, init=False)
    _events: list[dict[str, Any]] = field(default_factory=list, init=False)
    _state_task: asyncio.Task | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        self._load_devices()
        self.app = FastAPI(title="JARVIS NEO Mobile Bridge", version=PROTOCOL)
        self._routes()
        self.app.add_event_handler("startup", self._startup)
        self.app.add_event_handler("shutdown", self._shutdown)

    @property
    def pairing_code(self) -> str:
        return self._pairing_code

    @property
    def pairing_expires_at(self) -> float:
        return self._pairing_expires_at

    def rotate_pairing_code(self) -> str:
        self._pairing_code = _code()
        self._pairing_expires_at = time.time() + PAIRING_TTL
        return self._pairing_code

    def _load_devices(self) -> None:
        try:
            data = json.loads(DEVICES_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                self._devices = {
                    str(d["device_id"]): d for d in data
                    if isinstance(d, dict) and d.get("device_id") and d.get("token")
                }
        except Exception:
            self._devices = {}

    def _save_devices(self) -> None:
        try:
            DEVICES_FILE.parent.mkdir(parents=True, exist_ok=True)
            DEVICES_FILE.write_text(json.dumps(list(self._devices.values()), ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    def set_state(self, **values: Any) -> None:
        self._state.update(values)

    def snapshot(self) -> dict[str, Any]:
        result = dict(self._state)
        if self.state_provider:
            try:
                result.update(self.state_provider())
            except Exception:
                pass
        result.update({
            "protocol": PROTOCOL,
            "device": self.device_name,
            "connected_devices": len(self._sessions),
            "authorized_devices": len(self._devices),
            "ts": time.time(),
        })
        return result

    def _authorized(self, token: str) -> dict[str, Any] | None:
        token = str(token or "")
        for device in self._devices.values():
            if secrets.compare_digest(str(device.get("token", "")), token):
                return device
        return None

    async def _startup(self) -> None:
        self._state_task = asyncio.create_task(self._state_broadcast_loop())

    async def _shutdown(self) -> None:
        if self._state_task:
            self._state_task.cancel()
            try:
                await self._state_task
            except asyncio.CancelledError:
                pass
            self._state_task = None

    async def _state_broadcast_loop(self) -> None:
        while True:
            await asyncio.sleep(STATE_BROADCAST_INTERVAL)
            if self._sessions:
                await self.broadcast_state()

    def _routes(self) -> None:
        @self.app.post("/api/pair")
        async def pair(payload: dict[str, Any]) -> dict[str, Any]:
            code = str(payload.get("code", ""))
            if time.time() >= self._pairing_expires_at or not secrets.compare_digest(code, self._pairing_code):
                return JSONResponse(status_code=401, content={"error": "PAIRING_FAILED"})
            device_id = str(payload.get("device_id") or secrets.token_hex(8))
            token = _token()
            self._devices[device_id] = {
                "device_id": device_id,
                "token": token,
                "name": str(payload.get("name") or "Appareil mobile"),
                "created_at": time.time(),
            }
            self._save_devices()
            self.rotate_pairing_code()
            return {"device_id": device_id, "token": token, "protocol": PROTOCOL, "server": self.device_name}

        @self.app.get("/api/system")
        async def system(token: str = "") -> dict[str, Any]:
            if not self._authorized(token):
                return JSONResponse(status_code=401, content={"error": "TOKEN_INVALID"})
            return self.snapshot()

        @self.app.get("/api/devices")
        async def devices(token: str = "") -> dict[str, Any]:
            if not self._authorized(token):
                return JSONResponse(status_code=401, content={"error": "TOKEN_INVALID"})
            return {"devices": [
                {"device_id": d["device_id"], "name": d.get("name", "Appareil"),
                 "connected": any(s.device_id == d["device_id"] for s in self._sessions.values())}
                for d in self._devices.values()
            ]}

        @self.app.post("/api/command")
        async def command(payload: dict[str, Any]) -> dict[str, Any]:
            device = self._authorized(str(payload.get("token", "")))
            if not device:
                return JSONResponse(status_code=401, content={"error": "TOKEN_INVALID"})
            text = str(payload.get("command", "")).strip()
            if not text:
                return {"ok": False, "error": "EMPTY_COMMAND"}
            result = await self._execute("command", {
                "command": text,
                "confirmed": bool(payload.get("confirmed", False)),
                "device_id": device["device_id"],
            })
            return {"ok": True, "result": result}

        @self.app.post("/api/agent")
        async def agent(payload: dict[str, Any]) -> dict[str, Any]:
            if not self._authorized(str(payload.get("token", ""))):
                return JSONResponse(status_code=401, content={"error": "TOKEN_INVALID"})
            instruction = str(payload.get("instruction", "")).strip()
            if not instruction:
                return {"ok": False, "error": "EMPTY_INSTRUCTION"}
            result = await self._execute("agent", {
                "instruction": instruction,
                "confirmed": bool(payload.get("confirmed", False)),
            })
            return {"ok": True, "result": result}

        @self.app.post("/api/agent/stop")
        async def agent_stop(payload: dict[str, Any]) -> dict[str, Any]:
            if not self._authorized(str(payload.get("token", ""))):
                return JSONResponse(status_code=401, content={"error": "TOKEN_INVALID"})
            result = await self._execute("agent.stop", {})
            return {"ok": True, "result": result}

        @self.app.get("/api/events")
        async def events(token: str = "", limit: int = 40) -> dict[str, Any]:
            if not self._authorized(token):
                return JSONResponse(status_code=401, content={"error": "TOKEN_INVALID"})
            return {"events": self._events[-max(1, min(limit, 100)):]} 

        @self.app.websocket("/ws")
        async def websocket(ws: WebSocket) -> None:
            token = str(ws.query_params.get("token", ""))
            device = self._authorized(token)
            await ws.accept()
            if not device:
                await ws.send_json({"type": "error", "code": "TOKEN_INVALID"})
                await ws.close(code=1008)
                return
            session = MobileSession(device_id=device["device_id"], token=token, websocket=ws)
            async with self._lock:
                self._sessions[token] = session
            await ws.send_json({"type": "status", "payload": self.snapshot()})
            try:
                while True:
                    msg = await ws.receive_json()
                    if not secrets.compare_digest(str(msg.get("token", token)), token):
                        await ws.send_json({"type": "error", "code": "TOKEN_INVALID"})
                        continue
                    kind = str(msg.get("type", ""))
                    request_id = msg.get("id") or msg.get("request_id")
                    if kind == "ping":
                        await ws.send_json({"type": "pong", "id": request_id, "ts": time.time()})
                    elif kind in {"status", "sync"}:
                        await ws.send_json({"type": "status", "id": request_id, "payload": self.snapshot()})
                    elif kind in {"command", "action"}:
                        args = msg.get("args") if isinstance(msg.get("args"), dict) else {}
                        text = str(msg.get("command") or args.get("command", "")).strip()
                        result = await self._execute("command", {
                            "command": text,
                            "confirmed": bool(msg.get("confirmed", False)),
                            "device_id": device["device_id"],
                        })
                        await ws.send_json({"type": "response", "id": request_id, "ok": True, "result": result})
                    else:
                        await ws.send_json({"type": "error", "id": request_id, "code": "UNKNOWN_MESSAGE"})
            except (WebSocketDisconnect, asyncio.CancelledError):
                pass
            finally:
                async with self._lock:
                    self._sessions.pop(token, None)

    async def _execute(self, action: str, args: dict[str, Any]) -> Any:
        if self.action_handler is None:
            return {"accepted": False, "reason": "NO_HOST_ACTION_HANDLER"}
        try:
            result = self.action_handler(action, args)
            return await result if asyncio.iscoroutine(result) else result
        except Exception as exc:
            return {"accepted": False, "error": str(exc)}

    async def publish(self, event: str, payload: dict[str, Any] | None = None) -> None:
        item = {"event": event, "payload": payload or {}, "ts": time.time()}
        self._events.append(item)
        self._events = self._events[-100:]
        message = {"type": "event", **item}
        for session in list(self._sessions.values()):
            try:
                await session.websocket.send_json(message)
            except Exception:
                pass

    async def broadcast_state(self) -> None:
        message = {"type": "state", "state": self.snapshot(), "ts": time.time()}
        for session in list(self._sessions.values()):
            try:
                await session.websocket.send_json(message)
            except Exception:
                pass

    def discovery_payload(self) -> bytes:
        return json.dumps({
            "type": "jarvis_discovery", "protocol": PROTOCOL,
            "device": self.device_name, "port": self.port,
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
    print(f"JARVIS NEO Mobile Bridge: port {bridge.port} | pairing code: {bridge.pairing_code}")
    uvicorn.run(bridge.app, host=bridge.host, port=bridge.port)
