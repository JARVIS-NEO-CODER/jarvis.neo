import asyncio
import json
import time

import jarvis_mobile_bridge as mobile


def test_mobile_bridge_protocol_and_routes(tmp_path, monkeypatch):
    devices_file = tmp_path / "mobile_devices.json"
    monkeypatch.setattr(mobile, "DEVICES_FILE", devices_file)
    bridge = mobile.MobileBridge()

    paths = {route.path for route in bridge.app.routes}
    assert "/api/pair" in paths
    assert "/api/system" in paths
    assert "/api/devices" in paths
    assert "/api/command" in paths
    assert "/api/agent" in paths
    assert "/api/agent/stop" in paths
    assert "/api/events" in paths
    assert "/ws" in paths
    assert bridge.snapshot()["protocol"] == mobile.PROTOCOL
    assert bridge.pairing_expires_at > time.time()


def test_pairing_token_persistence(tmp_path, monkeypatch):
    devices_file = tmp_path / "mobile_devices.json"
    monkeypatch.setattr(mobile, "DEVICES_FILE", devices_file)
    bridge = mobile.MobileBridge()

    async def run():
        bridge._devices["phone-1"] = {
            "device_id": "phone-1",
            "token": "test-token",
            "name": "Téléphone",
            "created_at": 1,
        }
        bridge._save_devices()

    asyncio.run(run())
    assert devices_file.exists()
    assert json.loads(devices_file.read_text(encoding="utf-8"))[0]["device_id"] == "phone-1"
    bridge2 = mobile.MobileBridge()
    assert bridge2._authorized("test-token")["device_id"] == "phone-1"


def test_expired_pairing_code_is_not_valid(monkeypatch, tmp_path):
    monkeypatch.setattr(mobile, "DEVICES_FILE", tmp_path / "mobile_devices.json")
    bridge = mobile.MobileBridge()
    bridge._pairing_expires_at = time.time() - 1
    assert bridge.pairing_expires_at < time.time()
