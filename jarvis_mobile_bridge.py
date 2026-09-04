"""JARVIS NEO PC <-> Mobile bridge.

LAN-first WebSocket transport with UDP discovery and one-time 6-digit pairing.
The protocol is transport-agnostic so a future relay can carry the same frames.
No arbitrary shell execution is performed here: the host supplies an allow-listed
action handler.
"""
from __future__ import annotations
import asyncio, json, secrets, socket, threading
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

DISCOVERY_PORT = 47821
WS_PORT = 47822
PROTOCOL = "jarvis-neo/1"
ActionHandler = Callable[[str, dict[str, Any]], Awaitable[Any] | Any]

def _code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"

@dataclass
class MobileBridge:
    host: str = "0.0.0.0"
    ws_port: int = WS_PORT
    discovery_port: int = DISCOVERY_PORT
    device_name: str = "JARVIS NEO PC"
    action_handler: ActionHandler | None = None
    app: FastAPI = field(init=False)
    _pairing_code: str = field(default_factory=_code, init=False)
    _sessions: dict[str, WebSocket] = field(default_factory=dict, init=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)

    def __post_init__(self) -> None:
        self.app = FastAPI(title="JARVIS NEO Mobile Bridge", version=PROTOCOL)
        self._routes()

    @property
    def pairing_code(self) -> str:
        return self._pairing_code

    def rotate_pairing_code(self) -> str:
        self._pairing_code = _code()
        return self._pairing_code

    def _routes(self) -> None:
        @self.app.get("/mobile/status")
        async def status() -> dict[str, Any]:
            return {"protocol": PROTOCOL, "device": self.device_name,
                    "port": self.ws_port, "paired_devices": len(self._sessions)}

        @self.app.websocket("/mobile/ws")
        async def mobile_ws(ws: WebSocket) -> None:
            await ws.accept()
            device_id = None
            token = None
            try:
                hello = await ws.receive_json()
                if hello.get("type") != "pair" or str(hello.get("code", "")) != self._pairing_code:
                    await ws.send_json({"type": "error", "code": "PAIRING_FAILED"})
                    await ws.close(code=1008)
                    return
                device_id = str(hello.get("device_id") or secrets.token_hex(8))
                token = secrets.token_urlsafe(32)
                async with self._lock:
                    self._sessions[token] = ws
                await ws.send_json({"type": "paired", "protocol": PROTOCOL,
                                    "device_id": device_id, "token": token,
                                    "server": self.device_name})
                self.rotate_pairing_code()  # one-time pairing code
                while True:
                    msg = await ws.receive_json()
                    if msg.get("token") != token:
                        await ws.send_json({"type": "error", "code": "TOKEN_INVALID"})
                        continue
                    await self._handle(ws, msg)
            except WebSocketDisconnect:
                pass
            finally:
                if token:
                    async with self._lock:
                        self._sessions.pop(token, None)

    async def _handle(self, ws: WebSocket, msg: dict[str, Any]) -> None:
        request_id = msg.get("request_id")
        kind = msg.get("type")
        if kind == "ping":
            await ws.send_json({"type": "pong", "request_id": request_id})
            return
        if kind == "status":
            await ws.send_json({"type": "status", "request_id": request_id,
                                "protocol": PROTOCOL, "device": self.device_name})
            return
        if kind == "action":
            action = str(msg.get("action", ""))
            args = msg.get("args") or {}
            if not action:
                await ws.send_json({"type": "error", "request_id": request_id, "code": "ACTION_MISSING"})
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

    def discovery_payload(self) -> bytes:
        # Never broadcast the pairing code.
        return json.dumps({"type": "jarvis_discovery", "protocol": PROTOCOL,
                           "device": self.device_name, "port": self.ws_port,
                           "hostname": socket.gethostname()}).encode()

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
