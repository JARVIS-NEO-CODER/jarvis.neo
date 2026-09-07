"""Real WebSocket E2E test for the canonical PC mobile bridge."""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import time
import unittest
from pathlib import Path

import websockets


ROOT = Path(__file__).resolve().parents[1]
PORT = int(os.environ.get("JARVIS_E2E_PORT", "8891"))
BASE = f"ws://127.0.0.1:{PORT}"


async def _wait_server() -> None:
    for _ in range(60):
        try:
            async with websockets.connect(BASE + "/mobile/ws") as ws:
                return
        except Exception:
            await asyncio.sleep(0.1)
    raise RuntimeError("E2E bridge server did not start")


class MobileBridgeE2ETests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.devices = Path(os.environ.get("JARVIS_E2E_DEVICES_FILE", "/tmp/jarvis-e2e-devices.json"))
        cls.server = subprocess.Popen([
            sys.executable, "-m", "uvicorn", "tests.e2e_mobile_server:app",
            "--host", "127.0.0.1", "--port", str(PORT), "--log-level", "warning",
        ], cwd=ROOT, env={**os.environ, "JARVIS_E2E_PORT": str(PORT), "JARVIS_E2E_DEVICES_FILE": str(cls.devices)})
        try:
            asyncio.run(_wait_server())
        except Exception:
            cls.server.kill()
            cls.server.wait()
            raise

    @classmethod
    def tearDownClass(cls):
        cls.server.terminate()
        try:
            cls.server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            cls.server.kill()
            cls.server.wait()

    def test_pair_auth_ping_status_sync_action_and_reconnect(self):
        async def scenario():
            uri = BASE + "/mobile/ws"
            async with websockets.connect(uri) as ws:
                await ws.send(json.dumps({
                    "type": "pair", "protocol": "jarvis-neo/1",
                    "code": "123456", "device_id": "ci-mobile", "name": "CI Mobile",
                }))
                paired = json.loads(await ws.recv())
                self.assertEqual(paired["type"], "paired")
                self.assertEqual(paired["protocol"], "jarvis-neo/1")
                self.assertTrue(paired["token"])
                token = paired["token"]
                device_id = paired["device_id"]

                state = json.loads(await ws.recv())
                self.assertEqual(state["type"], "state")
                self.assertEqual(state["state"]["protocol"], "jarvis-neo/1")

                await ws.send(json.dumps({"type": "ping", "protocol": "jarvis-neo/1", "token": token, "device_id": device_id, "request_id": "r1"}))
                pong = json.loads(await ws.recv())
                self.assertEqual(pong["type"], "response")
                self.assertEqual(pong["request_id"], "r1")
                self.assertTrue(pong["ok"])

                await ws.send(json.dumps({"type": "status", "protocol": "jarvis-neo/1", "token": token, "device_id": device_id, "request_id": "r2"}))
                status = json.loads(await ws.recv())
                self.assertEqual(status["type"], "state")
                self.assertEqual(status["request_id"], "r2")
                self.assertEqual(status["state"]["mode"], "e2e")

                await ws.send(json.dumps({"type": "sync", "protocol": "jarvis-neo/1", "token": token, "device_id": device_id, "request_id": "r3"}))
                sync = json.loads(await ws.recv())
                self.assertEqual(sync["type"], "state")
                self.assertEqual(sync["request_id"], "r3")

                await ws.send(json.dumps({"type": "action", "protocol": "jarvis-neo/1", "token": token, "device_id": device_id, "request_id": "r4", "action": "pc.volume", "args": {"level": 42}}))
                result = json.loads(await ws.recv())
                self.assertEqual(result["type"], "response")
                self.assertEqual(result["request_id"], "r4")
                self.assertTrue(result["ok"])
                self.assertEqual(result["result"]["action"], "pc.volume")

            async with websockets.connect(uri) as ws:
                await ws.send(json.dumps({"type": "authenticate", "protocol": "jarvis-neo/1", "token": token, "device_id": device_id}))
                auth = json.loads(await ws.recv())
                self.assertEqual(auth["type"], "authenticated")
                state = json.loads(await ws.recv())
                self.assertEqual(state["type"], "state")

        asyncio.run(scenario())

    def test_rejects_wrong_protocol_and_token(self):
        async def scenario():
            async with websockets.connect(BASE + "/mobile/ws") as ws:
                await ws.send(json.dumps({"type": "pair", "protocol": "wrong/0", "code": "123456"}))
                error = json.loads(await ws.recv())
                self.assertEqual(error["code"], "PROTOCOL_MISMATCH")

            async with websockets.connect(BASE + "/mobile/ws") as ws:
                await ws.send(json.dumps({"type": "authenticate", "protocol": "jarvis-neo/1", "token": "bad", "device_id": "bad"}))
                error = json.loads(await ws.recv())
                self.assertEqual(error["code"], "UNAUTHORIZED")

        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main(verbosity=2)
