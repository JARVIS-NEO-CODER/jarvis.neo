import asyncio
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import core  # noqa: F401  # installs the mobile control adapter
import jarvis_mobile_bridge as mobile


class MobileControlAdapterTests(unittest.TestCase):
    def make_bridge(self):
        patcher = patch("jarvis_mobile_bridge.DEVICES_FILE", Path(tempfile.mkdtemp()) / "mobile_devices.json")
        patcher.start()
        self.addCleanup(patcher.stop)
        return mobile.MobileBridge()

    def pair(self, bridge):
        result = asyncio.run(bridge._pair_device({
            "protocol": mobile.PROTOCOL,
            "code": bridge.pairing_code,
            "device_id": "phone-test",
        }))
        return result

    def test_capabilities_are_exposed_in_snapshot(self):
        bridge = self.make_bridge()
        with patch.dict(sys.modules, {"assistant": types.SimpleNamespace(state=types.SimpleNamespace(
            security_mode=False, camera_enabled=False, alarm_triggered=False
        ))}):
            snapshot = bridge.snapshot()
        self.assertEqual(snapshot["mobile_protocol"], mobile.PROTOCOL)
        self.assertTrue(snapshot["capabilities"]["pc.screen.capture"]["available"])
        self.assertFalse(snapshot["remote_desktop"]["streaming"])
        self.assertFalse(snapshot["sentinel"]["enabled"])

    def test_sensitive_mobile_actions_require_confirmation(self):
        bridge = self.make_bridge()
        pair = self.pair(bridge)
        payload = {"token": pair["token"], "device_id": pair["device_id"]}
        fake_processor = types.SimpleNamespace(
            lock_pc=lambda: "Session verrouillée.",
            toggle_security=lambda mode: "ok",
        )
        fake_state = types.SimpleNamespace(
            security_mode=False, camera_enabled=False, alarm_triggered=False
        )
        fake_assistant = types.SimpleNamespace(state=fake_state, processor=fake_processor)
        with patch.dict(sys.modules, {"assistant": fake_assistant}):
            lock = asyncio.run(bridge._handle_action(payload, "pc.lock"))
            sentinel = asyncio.run(bridge._handle_action(payload, "sentinel.enable"))
        self.assertTrue(lock["requires_confirmation"])
        self.assertEqual(lock["reason"], "USER_CONFIRMATION_REQUIRED")
        self.assertTrue(sentinel["requires_confirmation"])

    def test_sentinel_status_is_authenticated(self):
        bridge = self.make_bridge()
        pair = self.pair(bridge)
        fake_assistant = types.SimpleNamespace(
            state=types.SimpleNamespace(
                security_mode=True, camera_enabled=True, alarm_triggered=True
            )
        )
        with patch.dict(sys.modules, {"assistant": fake_assistant}):
            result = asyncio.run(bridge._handle_action({
                "token": pair["token"], "device_id": pair["device_id"]
            }, "sentinel.status"))
        self.assertTrue(result["accepted"])
        self.assertTrue(result["enabled"])
        self.assertTrue(result["camera_enabled"])
        self.assertTrue(result["alarm"])

    def test_invalid_mobile_token_is_rejected(self):
        bridge = self.make_bridge()
        fake_assistant = types.SimpleNamespace(
            state=types.SimpleNamespace(
                security_mode=False, camera_enabled=False, alarm_triggered=False
            )
        )
        with patch.dict(sys.modules, {"assistant": fake_assistant}):
            result = asyncio.run(bridge._handle_action({
                "token": "wrong", "device_id": "phone-test"
            }, "sentinel.status"))
        self.assertFalse(result["accepted"])
        self.assertEqual(result["reason"], "UNAUTHORIZED")


if __name__ == "__main__":
    unittest.main()
