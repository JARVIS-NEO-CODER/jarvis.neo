"""Natural voice/text session state for J.A.R.V.I.S. NEO."""
from __future__ import annotations
import time
from dataclasses import dataclass

@dataclass
class ConversationSession:
    """Keep short-lived conversational context without requiring the wake word."""
    active: bool = False
    last_interaction: float = 0.0
    timeout_seconds: float = 12.0
    def start(self):
        self.active = True
        self.touch()
    def touch(self):
        self.last_interaction = time.monotonic()
        self.active = True
    def expire_if_idle(self):
        if self.active and time.monotonic() - self.last_interaction >= self.timeout_seconds:
            self.active = False
            return True
        return False
    def accepts_followup(self):
        self.expire_if_idle()
        return self.active
    def should_wake(self, text, wake_word="jarvis"):
        normalized = text.strip().lower()
        if wake_word.lower() in normalized:
            self.start()
            return True
        if self.accepts_followup():
            self.touch()
            return True
        return False

__all__ = ["ConversationSession"]
