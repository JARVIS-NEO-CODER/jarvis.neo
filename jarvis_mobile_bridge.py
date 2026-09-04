"""Authenticated PC <-> J.A.R.V.I.S. NEO Mobile bridge.

Protocol contract:
- discovery UDP: 47821
- WebSocket: /ws on 47822 by default
- protocol: jarvis-neo/1
- first WebSocket frame is pair or authenticate
- pairing uses a 6-digit code with a 5-minute TTL
- subsequent sessions authenticate with a per-device bearer token
- no arbitrary shell execution is exposed
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

DEFAULT_PORT = 47822
DISCOVERY_PORT = 47821
PROTOCOL = "jarvis-neo/1"
PAIRING_TTL = 300
STATE_BROADCAST_INTERVAL = 2.0
DEVICES_FILE = Path.home() / ".jarvis_neo" / "mobile_devices.json"

ActionHandler = Callable[[str, dict[str, Any]], Awaitable[Any] | Any]
StateProvider = Callable[[], dict[str, Any]]


def _code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


@dataclass
class Device:
    device_id: str
    name: str
    token: str
    created_at: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)


class MobileBridge:
    def __init__(self, host: str = "0.0.0.0", port: int = DEFAULT_PORT):
        self.host = host
        self.port = port
        self.discovery_port = DISCOVERY_PORT
        self.app = FastAPI(title="JARVIS NEO Mobile Bridge", version=PROTOCOL)
        self.action_handler: ActionHandler | None = None
        self.state_provider: StateProvider | None = None
        self._devices: dict[str, Device] = {}
        self._pairing_code = _code()
        self._pairing_expires_at = time.time() + PAIRING_TTL
        self._clients: set[WebSocket] = set()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._broadcast_task: asyncio.Task | None = None
        self._discovery_thread: threading.Thread | None = None
        self._load_devices()
        self._register_routes()

    @property
    def pairing_code(self) -> str:
        if time.time() >= self._pairing_expires_at:
            self._rotate_pairing_code()
        return self._pairing_code

    @property
    def pairing_expires_at(self) -> float:
        return self._pairing_expires_at

    def _rotate_pairing_code(self) -> None:
        self._pairing_code = _code()
        self._pairing_expires_at = time.time() + PAIRING_TTL

    def _load_devices(self) -> None:
        try:
            raw = json.loads(DEVICES_FILE.read_text(encoding="utf-8"))
            for item in raw if isinstance(raw, list) else []:
                if item.get("device_id") and item.get("token"):
                    self._devices[item["device_id"]] = Device(
                        device_id=item["device_id"],
                        name=item.get("name", "JARVIS Mobile"),
                        token=item["token"],
                        created_at=float(item.get("created_at", time.time())),
                        last_seen=float(item.get("last_seen", time.time())),
                    )
        except (OSError, ValueError, TypeError):
            self._devices = {}

    def _save_devices(self) -> None:
        DEVICES_FILE.parent.mkdir(parents=True, exist_ok=True)
        payload = [
            {
                "device_id": d.device_id,
                "name": d.name,
                "token": d.token,
                "created_at": d.created_at,
                "last_seen": d.last_seen,
            }
            for d in self._devices.values()
        ]
        tmp = DEVICES_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(DEVICES_FILE)

    def _authorized(self, token: str | None, device_id: str | None = None) -> Device | None:
        if not token:
            return None
        for device in self._devices.values():
            if secrets.compare_digest(device.token, str(token)):
                if device_id is not None and device.device_id != device_id:
                    return None
                device.last_seen = time.time()
                return device
        return None

    def snapshot(self) -> dict[str, Any]:
        state = dict(self.state_provider() if self.state_provider else {})
        state.setdefault("status", "online")
        state["protocol"] = PROTOCOL
        state["port"] = self.port
        state["timestamp"] = time.time()
        return state

    def discovery_payload(self) -> bytes:
        payload = {
            "type": "jarvis_discovery",
            "protocol": PROTOCOL,
            "port": self.port,
            "hostname": socket.gethostname(),
            "device": "JARVIS NEO PC",
        }
        return json.dumps(payload, ensure_ascii=False).encode("utf-8")

    def _register_routes(self) -> None:
        @self.app.post("/api/pair")
        async def pair(payload: dict[str, Any]):
            if str(payload.get("protocol", PROTOCOL)) != PROTOCOL:
                return JSONResponse({"error": "PROTOCOL_MISMATCH"}, status_code=400)
            result = await self._pair_device(payload)
            if result is None:
                return JSONResponse({"error": "PAIRING_CODE_INVALID_OR_EXPIRED"}, status_code=403)
            return result

        @self.app.get("/api/system")
        async def system(token: str = "", device_id: str = ""):
            if not self._authorized(token, device_id or None):
                return JSONResponse({"error": "UNAUTHORIZED"}, status_code=401)
            return self.snapshot()

        @self.app.get("/api/devices")
        async def devices(token: str = "", device_id: str = ""):
            if not self._authorized(token, device_id or None):
                return JSONResponse({"error": "UNAUTHORIZED"}, status_code=401)
            return {"devices": [
                {"device_id": d.device_id, "name": d.name, "last_seen": d.last_seen}
                for d in self._devices.values()
            ]}

        @self.app.post("/api/revoke")
        async def revoke(payload: dict[str, Any]):
            if not self._authorized(payload.get("token"), payload.get("device_id")):
                return JSONResponse({"error": "UNAUTHORIZED"}, status_code=401)
            device_id = str(payload.get("device_id", "")).strip()
            if device_id and device_id in self._devices:
                del self._devices[device_id]
                self._save_devices()
            return {"ok": True}

        @self.app.post("/api/command")
        async def command(payload: dict[str, Any]):
            return await self._handle_action(payload, "command")

        @self.app.post("/api/agent")
        async def agent(payload: dict[str, Any]):
            return await self._handle_action(payload, "agent")

        @self.app.post("/api/agent/stop")
        async def agent_stop(payload: dict[str, Any]):
            return await self._handle_action(payload, "agent.stop")

        @self.app.get("/api/events")
        async def events(token: str = "", device_id: str = ""):
            if not self._authorized(token, device_id or None):
                return JSONResponse({"error": "UNAUTHORIZED"}, status_code=401)
            return {"events": []}

        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            self._loop = asyncio.get_running_loop()
            try:
                first = await asyncio.wait_for(websocket.receive_json(), timeout=10)
                if str(first.get("protocol", "")) != PROTOCOL:
                    await websocket.send_json({"type": "error", "code": "PROTOCOL_MISMATCH"})
                    await websocket.close(code=1002)
                    return

                kind = str(first.get("type", "")).strip().lower()
                if kind == "pair":
                    result = await self._pair_device(first)
                    if result is None:
                        await websocket.send_json({"type": "error", "code": "PAIRING_CODE_INVALID_OR_EXPIRED"})
                        await websocket.close(code=1008)
                        return
                    device = self._devices[result["device_id"]]
                    await websocket.send_json({"type": "paired", **result})
                elif kind == "authenticate":
                    device = self._authorized(first.get("token"), first.get("device_id"))
                    if device is None:
                        await websocket.send_json({"type": "error", "code": "UNAUTHORIZED"})
                        await websocket.close(code=1008)
                        return
                    await websocket.send_json({"type": "authenticated", "protocol": PROTOCOL, "device_id": device.device_id})
                else:
                    await websocket.send_json({"type": "error", "code": "AUTHENTICATION_REQUIRED"})
                    await websocket.close(code=1008)
                    return

                self._clients.add(websocket)
                if self._broadcast_task is None or self._broadcast_task.done():
                    self._broadcast_task = asyncio.create_task(self._broadcast_loop())
                await websocket.send_json({"type": "state", "state": self.snapshot()})

                while True:
                    message = await websocket.receive_json()
                    msg_token = message.get("token") or (device.token if device else None)
                    msg_device_id = message.get("device_id") or device.device_id
                    if self._authorized(msg_token, msg_device_id) is None:
                        await websocket.send_json({"type": "error", "code": "UNAUTHORIZED"})
                        await websocket.close(code=1008)
                        break
                    kind = str(message.get("type", "")).strip().lower()
                    request_id = message.get("request_id")
                    if kind == "ping":
                        await websocket.send_json({"type": "response", "request_id": request_id, "ok": True, "result": {"pong": True}})
                    elif kind in {"status", "sync"}:
                        await websocket.send_json({"type": "state", "request_id": request_id, "state": self.snapshot()})
                    elif kind == "action":
                        action = str(message.get("action", "")).strip()
                        args = message.get("args") if isinstance(message.get("args"), dict) else {}
                        result = await self._handle_action({"token": msg_token, "device_id": msg_device_id, **args}, action)
                        await websocket.send_json({"type": "response", "request_id": request_id, "ok": not isinstance(result, JSONResponse), "result": result})
                    else:
                        await websocket.send_json({"type": "error", "request_id": request_id, "code": "UNKNOWN_MESSAGE_TYPE"})
            except (WebSocketDisconnect, asyncio.TimeoutError):
                pass
            finally:
                self._clients.discard(websocket)

    async def _pair_device(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        if str(payload.get("protocol", PROTOCOL)) != PROTOCOL:
            return None
        if time.time() >= self._pairing_expires_at:
            return None
        if not secrets.compare_digest(str(payload.get("code", "")), self._pairing_code):
            return None
        device_id = str(payload.get("device_id") or secrets.token_hex(8)).strip()
        name = str(payload.get("name") or "JARVIS Mobile").strip()[:80]
        token = secrets.token_urlsafe(32)
        self._devices[device_id] = Device(device_id=device_id, name=name, token=token)
        self._save_devices()
        self._rotate_pairing_code()
        return {"protocol": PROTOCOL, "device_id": device_id, "token": token, "port": self.port}

    async def _handle_action(self, payload: dict[str, Any], action: str):
        if not self._authorized(payload.get("token"), payload.get("device_id")):
            return {"accepted": False, "reason": "UNAUTHORIZED"}
        args = dict(payload)
        args.pop("token", None)
        args.pop("device_id", None)
        if self.action_handler is None:
            return {"accepted": False, "reason": "ACTION_HANDLER_UNAVAILABLE"}
        try:
            result = self.action_handler(action, args)
            if asyncio.iscoroutine(result):
                result = await result
            return result
        except Exception as exc:
            return {"accepted": False, "error": str(exc)}

    async def _broadcast_loop(self):
        while self._clients:
            await asyncio.sleep(STATE_BROADCAST_INTERVAL)
            message = {"type": "state", "state": self.snapshot()}
            for client in list(self._clients):
                try:
                    await client.send_json(message)
                except Exception:
                    self._clients.discard(client)

    def publish_from_thread(self, event: str, payload: dict[str, Any]) -> None:
        if self._loop is None or not self._clients:
            return
        message = {"type": "event", "event": event, "payload": payload, "ts": time.time()}
        asyncio.run_coroutine_threadsafe(self._broadcast_event(message), self._loop)

    async def _broadcast_event(self, message: dict[str, Any]) -> None:
        for client in list(self._clients):
            try:
                await client.send_json(message)
            except Exception:
                self._clients.discard(client)

    def start_discovery(self) -> None:
        if self._discovery_thread and self._discovery_thread.is_alive():
            return

        def worker():
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                while True:
                    try:
                        sock.sendto(self.discovery_payload(), ("255.255.255.255", self.discovery_port))
                    except OSError:
                        pass
                    time.sleep(3)
            finally:
                sock.close()

        self._discovery_thread = threading.Thread(target=worker, daemon=True, name="NEO-mobile-discovery")
        self._discovery_thread.start()


bridge = MobileBridge()
