"""Local privacy controls for NEO.

The panic switch is deliberately independent from the generative AI layer.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime

@dataclass
class PrivacyState:
    panic: bool = False
    context_paused: bool = False
    camera_enabled: bool = False
    microphone_enabled: bool = False
    screen_capture_enabled: bool = False

class PrivacyController:
    def __init__(self):
        self.state = PrivacyState()
        self.events: list[dict] = []

    def panic(self):
        self.state.panic = True
        self.state.context_paused = True
        self.state.camera_enabled = False
        self.state.microphone_enabled = False
        self.state.screen_capture_enabled = False
        self.events.append({"time": datetime.now().isoformat(), "event": "PANIC_ENABLED"})

    def resume(self):
        self.state.panic = False
        self.state.context_paused = False
        self.events.append({"time": datetime.now().isoformat(), "event": "PRIVACY_RESUMED"})

    def can_capture(self, source: str) -> bool:
        if self.state.panic or self.state.context_paused:
            return False
        return {
            "camera": self.state.camera_enabled,
            "microphone": self.state.microphone_enabled,
            "screen": self.state.screen_capture_enabled,
        }.get(source, False)
