"""Natural voice/text session state for J.A.R.V.I.S. NEO."""
from __future__ import annotations
import time
from dataclasses import dataclass

@dataclass
class ConversationSession:
    """Keep short-lived conversational context without requiring the wake word.

    The idle countdown starts only after JARVIS has finished answering. Calling
    touch() marks the end of a completed interaction, not the start of an AI call.
    """
    active: bool = False
    last_interaction: float = 0.0
    timeout_seconds: float = 12.0
    awaiting_response: bool = False

    def start(self):
        self.active = True
        self.awaiting_response = False
        self.touch()

    def begin_response(self):
        self.active = True
        self.awaiting_response = True

    def touch(self):
        self.last_interaction = time.monotonic()
        self.active = True
        self.awaiting_response = False

    def expire_if_idle(self):
        if self.awaiting_response:
            return False
        if self.active and time.monotonic() - self.last_interaction >= self.timeout_seconds:
            self.active = False
            return True
        return False

    def accepts_followup(self):
        self.expire_if_idle()
        return self.active and not self.awaiting_response

    def should_wake(self, text, wake_word="jarvis"):
        normalized = text.strip().lower()
        if wake_word.lower() in normalized:
            self.start()
            return True
        return self.accepts_followup()

__all__ = ["ConversationSession"]
