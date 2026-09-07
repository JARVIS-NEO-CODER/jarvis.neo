"""Small deterministic JARVIS Mobile bridge server used by cross-repo CI.

It runs the real jarvis_mobile_bridge implementation, but replaces the hardware
callbacks with deterministic fixtures so the Flutter client can exercise the
real WebSocket contract in GitHub Actions.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

import jarvis_mobile_bridge as mobile

mobile.DEVICES_FILE = Path(os.environ.get("JARVIS_E2E_DEVICES_FILE", "/tmp/jarvis-e2e-devices.json"))
bridge = mobile.MobileBridge(host="127.0.0.1", port=int(os.environ.get("JARVIS_E2E_PORT", "8890")))
bridge._pairing_code = "123456"
bridge._pairing_expires_at = time.time() + 3600
bridge.state_provider = lambda: {"status": "online", "mode": "e2e", "cpu": 1, "ram": 2}
bridge.action_handler = lambda action, args: {"accepted": True, "action": action, "args": args}
app = bridge.app
