from __future__ import annotations

import asyncio
import json
import secrets
from dataclasses import dataclass
from time import monotonic

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

PROTOCOL = "jarvis-neo/1"
MAX_FRAME_BYTES = 64 * 1024
MAX_NODE_ID = 128
IDLE_TIMEOUT = 120.0

app = FastAPI(title="JARVIS NEO Remote Relay", version=PROTOCOL)


@dataclass
class Tunnel:
    websocket: WebSocket
    secret: str
    connected_at: float
    last_seen: float
    remote: WebSocket | None = None


tunnels: dict[str, Tunnel] = {}
lock = asyncio.Lock()


def _valid_node(node_id: object) -> str | None:
    value = str(node_id or "").strip()
    return value if value and len(value) <= MAX_NODE_ID else None


def _valid_secret(value: object) -> str | None:
    secret = str(value or "").strip()
    return secret if 32 <= len(secret) <= 256 else None


@app.get("/healthz")
async def healthz() -> JSONResponse:
    return JSONResponse({"ok": True, "protocol": PROTOCOL, "tunnels": len(tunnels)})


async def _recv_json(ws: WebSocket) -> dict:
    raw = await asyncio.wait_for(ws.receive_text(), timeout=15)
    if len(raw.encode("utf-8")) > MAX_FRAME_BYTES:
        raise ValueError("FRAME_TOO_LARGE")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("INVALID_FRAME")
    return value


async def _forward(source: WebSocket, target: WebSocket, tunnel: Tunnel) -> None:
    while True:
        raw = await source.receive_text()
        if len(raw.encode("utf-8")) > MAX_FRAME_BYTES:
            raise ValueError("FRAME_TOO_LARGE")
        tunnel.last_seen = monotonic()
        await target.send_text(raw)


async def _relay_pair(tunnel: Tunnel, remote: WebSocket) -> None:
    tasks = [
        asyncio.create_task(_forward(remote, tunnel.websocket, tunnel)),
        asyncio.create_task(_forward(tunnel.websocket, remote, tunnel)),
    ]
    try:
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
        for task in done:
            task.result()
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
    finally:
        tunnel.remote = None


@app.websocket("/ws")
async def websocket_relay(ws: WebSocket) -> None:
    await ws.accept()
    tunnel: Tunnel | None = None
    node_id: str | None = None
    role = ""
    try:
        hello = await _recv_json(ws)
        if hello.get("protocol") != PROTOCOL:
            await ws.close(code=1002, reason="PROTOCOL_MISMATCH")
            return
        role = str(hello.get("type", "")).strip().lower()
        node_id = _valid_node(hello.get("node_id"))

        if role == "tunnel":
            secret = _valid_secret(hello.get("secret"))
            if not node_id or not secret:
                await ws.send_json({"type": "error", "code": "INVALID_TUNNEL_HELLO"})
                await ws.close(code=1008)
                return
            async with lock:
                old = tunnels.pop(node_id, None)
                if old:
                    try:
                        await old.websocket.close(code=1012, reason="REPLACED")
                    except Exception:
                        pass
                tunnel = Tunnel(ws, secret, monotonic(), monotonic())
                tunnels[node_id] = tunnel
            await ws.send_json({"type": "tunnel_ready", "protocol": PROTOCOL, "node_id": node_id})
            while True:
                await asyncio.sleep(10)
                if monotonic() - tunnel.last_seen > IDLE_TIMEOUT:
                    raise TimeoutError("IDLE_TIMEOUT")
                if tunnel.remote is not None:
                    try:
                        await tunnel.remote.send_json({"type": "relay_ping", "protocol": PROTOCOL})
                    except Exception:
                        tunnel.remote = None

        elif role == "remote":
            if not node_id:
                await ws.close(code=1008, reason="INVALID_NODE_ID")
                return
            async with lock:
                tunnel = tunnels.get(node_id)
                if tunnel is None:
                    await ws.send_json({"type": "error", "code": "PC_OFFLINE"})
                    await ws.close(code=1013)
                    return
                optional_secret = str(hello.get("secret", "")).strip()
                if optional_secret and not secrets.compare_digest(tunnel.secret, optional_secret):
                    await ws.send_json({"type": "error", "code": "REMOTE_SECRET_INVALID"})
                    await ws.close(code=1008)
                    return
                if tunnel.remote is not None:
                    await ws.send_json({"type": "error", "code": "REMOTE_BUSY"})
                    await ws.close(code=1013)
                    return
                tunnel.remote = ws
                tunnel.last_seen = monotonic()
            await ws.send_json({"type": "remote_attached", "protocol": PROTOCOL, "node_id": node_id})
            await tunnel.websocket.send_json({"type": "remote_attached", "protocol": PROTOCOL, "node_id": node_id})
            await _relay_pair(tunnel, ws)
        else:
            await ws.close(code=1008, reason="INVALID_ROLE")
    except (WebSocketDisconnect, asyncio.TimeoutError, TimeoutError, ValueError, json.JSONDecodeError):
        pass
    finally:
        if node_id and tunnel is not None:
            async with lock:
                current = tunnels.get(node_id)
                if role == "tunnel" and current is tunnel:
                    tunnels.pop(node_id, None)
                    if tunnel.remote is not None:
                        try:
                            await tunnel.remote.close(code=1012, reason="PC_OFFLINE")
                        except Exception:
                            pass
                elif role == "remote" and current is tunnel and tunnel.remote is ws:
                    tunnel.remote = None
                    try:
                        await tunnel.websocket.send_json({"type": "remote_detached", "protocol": PROTOCOL})
                    except Exception:
                        pass
