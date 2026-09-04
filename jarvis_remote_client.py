from __future__ import annotations

import asyncio
import json
import os
import secrets
import threading
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from jarvis_mobile_bridge import PROTOCOL, MobileBridge

REMOTE_STATE_FILE = Path.home() / ".jarvis_neo" / "remote.json"
RECONNECT_SECONDS = 5


def _load_or_create_identity() -> tuple[str, str]:
    try:
        data = json.loads(REMOTE_STATE_FILE.read_text(encoding="utf-8"))
        node_id = str(data.get("node_id", "")).strip()
        secret = str(data.get("secret", "")).strip()
        if node_id and len(secret) >= 32:
            return node_id, secret
    except (OSError, ValueError, TypeError):
        pass
    node_id = secrets.token_urlsafe(24)
    secret = secrets.token_urlsafe(48)
    REMOTE_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = REMOTE_STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps({"node_id": node_id, "secret": secret}, indent=2), encoding="utf-8")
    tmp.replace(REMOTE_STATE_FILE)
    try:
        os.chmod(REMOTE_STATE_FILE, 0o600)
    except OSError:
        pass
    return node_id, secret


def _relay_ws_url(relay_url: str) -> str:
    parsed = urlparse(relay_url)
    if parsed.scheme != "wss" or not parsed.netloc:
        raise ValueError("JARVIS_REMOTE_RELAY_URL doit utiliser wss://")
    path = parsed.path.rstrip("/") or "/ws"
    if path != "/ws":
        raise ValueError("Le relais JARVIS NEO doit exposer /ws")
    return parsed._replace(path="/ws", query="", fragment="").geturl()


class RemoteTunnelClient:
    """Keeps an outbound WSS tunnel and terminates the JARVIS protocol on the PC side."""

    def __init__(self, bridge: MobileBridge, relay_url: str, node_id: str | None = None, secret: str | None = None):
        self.bridge = bridge
        self.relay_url = _relay_ws_url(relay_url)
        generated_node, generated_secret = _load_or_create_identity()
        self.node_id = node_id or generated_node
        self.secret = secret or generated_secret
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def remote_url(self) -> str:
        parsed = urlparse(self.relay_url)
        return parsed._replace(path="").geturl().rstrip("/")

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="NEO-remote-tunnel")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        try:
            asyncio.run(self._loop())
        except Exception as exc:
            try:
                self.bridge.publish_from_thread("remote_error", {"error": str(exc)})
            except Exception:
                pass

    async def _loop(self) -> None:
        import websockets

        while not self._stop.is_set():
            try:
                async with websockets.connect(
                    self.relay_url,
                    open_timeout=10,
                    ping_interval=20,
                    ping_timeout=20,
                    max_size=64 * 1024,
                ) as ws:
                    await ws.send(json.dumps({
                        "type": "tunnel",
                        "protocol": PROTOCOL,
                        "node_id": self.node_id,
                        "secret": self.secret,
                    }))
                    ready = json.loads(await asyncio.wait_for(ws.recv(), 10))
                    if ready.get("type") != "tunnel_ready" or ready.get("protocol") != PROTOCOL:
                        raise RuntimeError("Relais distant refusé")
                    self.bridge.publish_from_thread("remote_connected", {"node_id": self.node_id})
                    await self._serve(ws)
            except Exception as exc:
                self.bridge.publish_from_thread("remote_disconnected", {"error": str(exc)})
                await asyncio.sleep(RECONNECT_SECONDS)

    async def _serve(self, ws: Any) -> None:
        import websockets

        async for raw in ws:
            if not isinstance(raw, str) or len(raw.encode("utf-8")) > 64 * 1024:
                raise RuntimeError("REMOTE_FRAME_TOO_LARGE")
            message = json.loads(raw)
            if not isinstance(message, dict):
                raise RuntimeError("REMOTE_INVALID_FRAME")
            await self._handle(ws, message)

    async def _handle(self, ws: Any, message: dict[str, Any]) -> None:
        kind = str(message.get("type", "")).strip().lower()
        if kind == "remote_attached":
            return
        if kind == "relay_ping":
            await ws.send(json.dumps({"type": "relay_pong", "protocol": PROTOCOL}))
            return
        if str(message.get("protocol", PROTOCOL)) != PROTOCOL:
            await ws.send(json.dumps({"type": "error", "code": "PROTOCOL_MISMATCH"}))
            return

        device_id = str(message.get("device_id", "")).strip()
        token = str(message.get("token", "")).strip()
        device = self.bridge._authorized(token, device_id or None)
        if device is None:
            await ws.send(json.dumps({"type": "error", "code": "UNAUTHORIZED"}))
            return

        if kind == "authenticate":
            await ws.send(json.dumps({"type": "authenticated", "protocol": PROTOCOL, "device_id": device.device_id}))
            await ws.send(json.dumps({"type": "state", "state": self.bridge.snapshot()}))
            return
        request_id = message.get("request_id")
        if kind == "ping":
            await ws.send(json.dumps({"type": "response", "request_id": request_id, "ok": True, "result": {"pong": True}}))
        elif kind in {"status", "sync"}:
            await ws.send(json.dumps({"type": "state", "request_id": request_id, "state": self.bridge.snapshot()}))
        elif kind == "action":
            action = str(message.get("action", "")).strip()
            args = message.get("args") if isinstance(message.get("args"), dict) else {}
            result = await self.bridge._handle_action({"token": token, "device_id": device.device_id, **args}, action)
            await ws.send(json.dumps({"type": "response", "request_id": request_id, "ok": True, "result": result}))
        else:
            await ws.send(json.dumps({"type": "error", "request_id": request_id, "code": "UNKNOWN_MESSAGE_TYPE"}))
