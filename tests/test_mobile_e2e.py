"""Real WebSocket E2E tests for the canonical PC mobile bridge."""
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
PORT = int(os.environ.get("JARVIS_E2E_PORT", "8891"))
BASE = f"ws://127.0.0.1:{PORT}"
PROTOCOL = "jarvis-neo/1"


async def _wait_server() -> None:
    for _ in range(60):
        try:
            async with websockets.connect(BASE + "/mobile/ws"):
                return
        except Exception:
            await asyncio.sleep(0.1)
    raise RuntimeError("E2E bridge server did not start")


class MobileBridgeE2ETests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.devices = Path(os.environ.get("JARVIS_E2E_DEVICES_FILE", "/tmp/jarvis-e2e-devices.json"))
        cls.server = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "tests.e2e_mobile_server:app", "--host", "127.0.0.1", "--port", str(PORT), "--log-level", "warning"],
            cwd=ROOT,
            env={**os.environ, "JARVIS_E2E_PORT": str(PORT), "JARVIS_E2E_DEVICES_FILE": str(cls.devices)},
        )
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
                    "type": "pair", "protocol": PROTOCOL,
                    "code": "123456", "device_id": "ci-mobile", "name": "CI Mobile",
                }))
                paired = json.loads(await ws.recv())
                self.assertEqual(paired["type"], "paired")
                self.assertEqual(paired["protocol"], PROTOCOL)
                token = paired["token"]
                device_id = paired["device_id"]
                self.assertTrue(token)

                state = json.loads(await ws.recv())
                self.assertEqual(state["type"], "status")
                self.assertTrue(state["data"]["online"])

                await ws.send(json.dumps({"type": "ping", "protocol": PROTOCOL, "token": token, "device_id": device_id, "request_id": "r1"}))
                pong = json.loads(await ws.recv())
                self.assertEqual(pong["type"], "pong")
                self.assertEqual(pong["protocol"], PROTOCOL)

                await ws.send(json.dumps({"type": "status", "protocol": PROTOCOL, "token": token, "device_id": device_id, "request_id": "r2"}))
                status = json.loads(await ws.recv())
                self.assertEqual(status["type"], "status")
                self.assertEqual(status["protocol"], PROTOCOL)
                self.assertTrue(status["data"]["online"])

                await ws.send(json.dumps({"type": "sync", "protocol": PROTOCOL, "token": token, "device_id": device_id, "request_id": "r3"}))
                sync = json.loads(await ws.recv())
                self.assertEqual(sync["type"], "sync")
                self.assertEqual(sync["protocol"], PROTOCOL)

                await ws.send(json.dumps({"type": "action", "protocol": PROTOCOL, "token": token, "device_id": device_id, "request_id": "r4", "action": "ouvre test", "args": {}}))
                result = json.loads(await ws.recv())
                self.assertEqual(result["type"], "action_result")
                self.assertEqual(result["protocol"], PROTOCOL)
                self.assertEqual(result["action"], "ouvre test")
                self.assertTrue(result["data"]["ok"])

            async with websockets.connect(uri) as ws:
                await ws.send(json.dumps({"type": "authenticate", "protocol": PROTOCOL, "token": token, "device_id": device_id}))
                auth = json.loads(await ws.recv())
                self.assertEqual(auth["type"], "authenticated")
                self.assertEqual(auth["protocol"], PROTOCOL)
                state = json.loads(await ws.recv())
                self.assertEqual(state["type"], "status")

        asyncio.run(scenario())

    def test_rejects_wrong_protocol_and_token(self):
        async def scenario():
            async with websockets.connect(BASE + "/mobile/ws") as ws:
                await ws.send(json.dumps({"type": "pair", "protocol": "wrong/0", "code": "123456"}))
                error = json.loads(await ws.recv())
                self.assertEqual(error["code"], "PROTOCOL_MISMATCH")

            async with websockets.connect(BASE + "/mobile/ws") as ws:
                await ws.send(json.dumps({"type": "authenticate", "protocol": PROTOCOL, "token": "bad", "device_id": "bad"}))
                error = json.loads(await ws.recv())
                self.assertEqual(error["code"], "AUTH_REJECTED")

        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main(verbosity=2)
