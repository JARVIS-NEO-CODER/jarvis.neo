import asyncio
import json
import time

import jarvis_mobile_bridge as mobile


def make_bridge(tmp_path, monkeypatch):
    monkeypatch.setattr(mobile, "DEVICES_FILE", tmp_path / "mobile_devices.json")
    return mobile.MobileBridge()


def test_mobile_bridge_protocol_ports_and_routes(tmp_path, monkeypatch):
    bridge = make_bridge(tmp_path, monkeypatch)
    paths = {route.path for route in bridge.app.routes}
    assert "/api/system" in paths
    assert "/api/devices" in paths
    assert "/api/revoke" in paths
    assert "/api/events" in paths
    assert "/ws" in paths
    assert bridge.port == 47822
    assert bridge.discovery_port == 47821
    assert bridge.snapshot()["protocol"] == mobile.PROTOCOL
    assert bridge.pairing_expires_at > time.time()


def test_pairing_returns_token_and_rotates_code(tmp_path, monkeypatch):
    bridge = make_bridge(tmp_path, monkeypatch)
    old_code = bridge.pairing_code
    result = asyncio.run(bridge._pair_device({
        "protocol": mobile.PROTOCOL,
        "code": old_code,
        "device_id": "phone-1",
        "name": "JARVIS Mobile",
    }))
    assert result["protocol"] == mobile.PROTOCOL
    assert result["device_id"] == "phone-1"
    assert result["token"]
    assert old_code != bridge.pairing_code
    assert bridge._authorized(result["token"], "phone-1") is not None


def test_wrong_and_expired_pairing_codes_are_rejected(tmp_path, monkeypatch):
    bridge = make_bridge(tmp_path, monkeypatch)
    assert asyncio.run(bridge._pair_device({"code": "000000", "device_id": "phone-1"})) is None
    bridge._pairing_expires_at = time.time() - 1
    assert asyncio.run(bridge._pair_device({"code": bridge.pairing_code, "device_id": "phone-1"})) is None


def test_token_is_bound_to_device(tmp_path, monkeypatch):
    bridge = make_bridge(tmp_path, monkeypatch)
    result = asyncio.run(bridge._pair_device({"code": bridge.pairing_code, "device_id": "phone-1"}))
    assert bridge._authorized(result["token"], "phone-1") is not None
    assert bridge._authorized(result["token"], "other-device") is None
    assert bridge._authorized("wrong-token", "phone-1") is None


def test_pairing_code_is_not_broadcast(tmp_path, monkeypatch):
    bridge = make_bridge(tmp_path, monkeypatch)
    payload = json.loads(bridge.discovery_payload().decode())
    assert payload["protocol"] == mobile.PROTOCOL
    assert bridge.pairing_code not in payload.values()


def test_device_token_survives_restart(tmp_path, monkeypatch):
    devices_file = tmp_path / "mobile_devices.json"
    monkeypatch.setattr(mobile, "DEVICES_FILE", devices_file)
    bridge = mobile.MobileBridge()
    result = asyncio.run(bridge._pair_device({"code": bridge.pairing_code, "device_id": "phone-1"}))
    assert devices_file.exists()
    saved = json.loads(devices_file.read_text(encoding="utf-8"))
    assert saved[0]["device_id"] == "phone-1"
    bridge2 = mobile.MobileBridge()
    assert bridge2._authorized(result["token"], "phone-1") is not None
