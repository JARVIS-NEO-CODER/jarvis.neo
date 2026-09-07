"""Deterministic E2E server built from the MobileBridge used by the PC platform."""
from __future__ import annotations

import os
import time
from pathlib import Path

import neo_platform as platform

platform.DEVICES_FILE = Path(os.environ.get("JARVIS_E2E_DEVICES_FILE", "/tmp/jarvis-e2e-devices.json"))


class _Processor:
    def process(self, text: str):
        return {"accepted": True, "text": text}


class _Assistant:
    VERSION = "e2e"
    processor = _Processor()


bridge = platform.MobileBridge(_Assistant())
bridge.pair_code = "123456"
bridge.pair_expires = time.time() + 3600
app = bridge.app
