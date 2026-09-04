import asyncio
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import jarvis_mobile_bridge as mobile
from jarvis_remote_transport import RemoteTransportConfig, build_remote_hello


class MobileBridgeContractTests(unittest.TestCase):
    def make_bridge(self):
        patcher = patch("jarvis_mobile_bridge.DEVICES_FILE", Path(tempfile.mkdtemp()) / "mobile_devices.json")
        patcher.start()
        self.addCleanup(patcher.stop)
        return mobile.MobileBridge()

    def test_protocol_ports_and_routes(self):
        bridge = self.make_bridge()
        paths = {route.path for route in bridge.app.routes}
        self.assertIn("/api/system", paths)
        self.assertIn("/api/devices", paths)
        self.assertIn("/api/revoke", paths)
        self.assertIn("/api/events", paths)
        self.assertIn("/ws", paths)
        self.assertEqual(bridge.port, 47822)
        self.assertEqual(bridge.discovery_port, 47821)
        self.assertEqual(bridge.snapshot()["protocol"], mobile.PROTOCOL)
        self.assertGreater(bridge.pairing_expires_at, time.time())

    def test_pairing_token_and_rotation(self):
        bridge = self.make_bridge()
        old_code = bridge.pairing_code
        result = asyncio.run(bridge._pair_device({
            "protocol": mobile.PROTOCOL, "code": old_code,
            "device_id": "phone-1", "name": "JARVIS Mobile",
        }))
        self.assertEqual(result["protocol"], mobile.PROTOCOL)
        self.assertTrue(result["token"])
        self.assertNotEqual(old_code, bridge.pairing_code)
        self.assertIsNotNone(bridge._authorized(result["token"], "phone-1"))

    def test_wrong_and_expired_codes(self):
        bridge = self.make_bridge()
        self.assertIsNone(asyncio.run(bridge._pair_device({"code": "000000", "device_id": "phone-1"})))
        bridge._pairing_expires_at = time.time() - 1
        self.assertIsNone(asyncio.run(bridge._pair_device({"code": bridge.pairing_code, "device_id": "phone-1"})))

    def test_token_is_bound_to_device(self):
        bridge = self.make_bridge()
        result = asyncio.run(bridge._pair_device({"code": bridge.pairing_code, "device_id": "phone-1"}))
        self.assertIsNotNone(bridge._authorized(result["token"], "phone-1"))
        self.assertIsNone(bridge._authorized(result["token"], "other-device"))
        self.assertIsNone(bridge._authorized("wrong-token", "phone-1"))

    def test_pairing_code_is_not_broadcast(self):
        bridge = self.make_bridge()
        payload = json.loads(bridge.discovery_payload().decode())
        self.assertEqual(payload["protocol"], mobile.PROTOCOL)
        self.assertNotIn(bridge.pairing_code, payload.values())

    def test_device_token_survives_restart(self):
        devices_file = Path(tempfile.mkdtemp()) / "mobile_devices.json"
        with patch("jarvis_mobile_bridge.DEVICES_FILE", devices_file):
            bridge = mobile.MobileBridge()
            result = asyncio.run(bridge._pair_device({"code": bridge.pairing_code, "device_id": "phone-1"}))
            bridge2 = mobile.MobileBridge()
            self.assertTrue(devices_file.exists())
            self.assertIsNotNone(bridge2._authorized(result["token"], "phone-1"))

    def test_remote_requires_wss_and_keeps_protocol(self):
        cfg = RemoteTransportConfig("wss://relay.example.test/ws")
        cfg.validate()
        hello = build_remote_hello("phone-1", "secret")
        self.assertEqual(hello["protocol"], mobile.PROTOCOL)
        with self.assertRaises(ValueError):
            RemoteTransportConfig("ws://relay.example.test/ws").validate()


if __name__ == "__main__":
    unittest.main()
