import unittest
from unittest.mock import patch

from jarvis_remote_client import RemoteTunnelClient, _relay_ws_url
from remote_relay.server import PROTOCOL, _valid_node, _valid_secret


class RemoteRelayContractTests(unittest.TestCase):
    def test_protocol_and_validation(self):
        self.assertEqual(PROTOCOL, "jarvis-neo/1")
        self.assertEqual(_valid_node("node-123"), "node-123")
        self.assertIsNone(_valid_node(""))
        self.assertIsNone(_valid_node("x" * 129))
        self.assertEqual(_valid_secret("x" * 32), "x" * 32)
        self.assertIsNone(_valid_secret("short"))

    def test_relay_url_requires_wss(self):
        self.assertEqual(_relay_ws_url("wss://relay.example"), "wss://relay.example/ws")
        with self.assertRaises(ValueError):
            _relay_ws_url("ws://relay.example")
        with self.assertRaises(ValueError):
            _relay_ws_url("https://relay.example")

    def test_remote_identity_is_persistent(self):
        with patch("jarvis_remote_client.REMOTE_STATE_FILE") as path:
            path.read_text.side_effect = OSError
            path.parent.mkdir.return_value = None
            path.with_suffix.return_value.write_text.return_value = None
            # The identity generator must still produce sufficiently strong values.
            from jarvis_remote_client import _load_or_create_identity
            node_id, secret = _load_or_create_identity()
            self.assertGreaterEqual(len(node_id), 20)
            self.assertGreaterEqual(len(secret), 32)


if __name__ == "__main__":
    unittest.main()
