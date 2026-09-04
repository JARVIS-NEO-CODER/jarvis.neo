"""Transport-neutral remote mode foundation for JARVIS NEO.

This module deliberately does not expose the PC WebSocket to the Internet.
A future relay must terminate TLS and forward the exact jarvis-neo/1 frames.
"""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from jarvis_mobile_bridge import PROTOCOL


@dataclass(frozen=True)
class RemoteTransportConfig:
    relay_url: str
    protocol: str = PROTOCOL
    enabled: bool = False

    def validate(self) -> None:
        parsed = urlparse(self.relay_url)
        if parsed.scheme != "wss":
            raise ValueError("Remote relay must use WSS/TLS")
        if not parsed.netloc:
            raise ValueError("Remote relay URL is invalid")
        if self.protocol != PROTOCOL:
            raise ValueError("Protocol mismatch")


def build_remote_hello(device_id: str, token: str) -> dict[str, str]:
    if not device_id or not token:
        raise ValueError("device_id and token are required")
    return {
        "type": "authenticate",
        "protocol": PROTOCOL,
        "device_id": device_id,
        "token": token,
    }
