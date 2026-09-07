"""Real WebSocket E2E test for the remote relay."""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

import websockets

ROOT = Path(__file__).resolve().parents[1]
PORT = int(os.environ.get("JARVIS_RELAY_E2E_PORT", "8799"))
BASE = f"ws://127.0.0.1:{PORT}/ws"
NODE = "e2e-node-jarvis"
SECRET = "s" * 32


async def wait_ready():
    for _ in range(60):
        try:
            async with websockets.connect(BASE) as ws:
                return
        except Exception:
            await asyncio.sleep(0.1)
    raise RuntimeError("Relay E2E server did not start")


class RemoteRelayE2ETests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = subprocess.Popen([
            sys.executable, "-m", "uvicorn", "remote_relay.server:app",
            "--host", "127.0.0.1", "--port", str(PORT), "--log-level", "warning",
        ], cwd=ROOT)
        asyncio.run(wait_ready())

    @classmethod
    def tearDownClass(cls):
        cls.server.terminate()
        try:
            cls.server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            cls.server.kill()
            cls.server.wait()

    def test_tunnel_attach_and_bidirectional_forwarding(self):
        async def scenario():
            tunnel = await websockets.connect(BASE)
            remote = None
            try:
                await tunnel.send(json.dumps({"type": "tunnel", "protocol": "jarvis-neo/1", "node_id": NODE, "secret": SECRET}))
                ready = json.loads(await tunnel.recv())
                self.assertEqual(ready["type"], "tunnel_ready")

                remote = await websockets.connect(BASE)
                await remote.send(json.dumps({"type": "remote", "protocol": "jarvis-neo/1", "node_id": NODE}))
                attached_remote = json.loads(await remote.recv())
                attached_tunnel = json.loads(await tunnel.recv())
                self.assertEqual(attached_remote["type"], "remote_attached")
                self.assertEqual(attached_tunnel["type"], "remote_attached")

                frame = {"type": "authenticate", "protocol": "jarvis-neo/1", "device_id": "mobile-ci", "token": "token-ci", "request_id": "r1"}
                await remote.send(json.dumps(frame))
                forwarded_to_pc = json.loads(await tunnel.recv())
                self.assertEqual(forwarded_to_pc, frame)

                response = {"type": "response", "protocol": "jarvis-neo/1", "request_id": "r1", "ok": True}
                await tunnel.send(json.dumps(response))
                forwarded_to_mobile = json.loads(await remote.recv())
                self.assertEqual(forwarded_to_mobile, response)
            finally:
                if remote is not None:
                    await remote.close()
                await tunnel.close()

        asyncio.run(scenario())

    def test_wrong_secret_is_rejected(self):
        async def scenario():
            tunnel = await websockets.connect(BASE)
            try:
                await tunnel.send(json.dumps({"type": "tunnel", "protocol": "jarvis-neo/1", "node_id": NODE + "-secret", "secret": SECRET}))
                ready = json.loads(await tunnel.recv())
                self.assertEqual(ready["type"], "tunnel_ready")
                remote = await websockets.connect(BASE)
                try:
                    await remote.send(json.dumps({"type": "remote", "protocol": "jarvis-neo/1", "node_id": NODE + "-secret", "secret": "x" * 32}))
                    error = json.loads(await remote.recv())
                    self.assertEqual(error["code"], "REMOTE_SECRET_INVALID")
                finally:
                    await remote.close()
            finally:
                await tunnel.close()

        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main(verbosity=2)
