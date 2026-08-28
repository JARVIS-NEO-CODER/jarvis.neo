"""Adaptive HUD state model for 3, 2, 1-screen and minimized layouts."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


VALID_STATES = {"idle", "listening", "thinking", "executing", "vision", "sentinel", "report"}
VALID_LAYOUTS = {"three", "two", "one", "minimized"}


@dataclass
class HUDState:
    state: str = "idle"
    layout: str = "three"
    progress: float | None = None
    status_text: str = "Prêt"
    context: str | None = None
    metrics: dict[str, Any] = field(default_factory=dict)
    thought_summary: list[str] = field(default_factory=list)

    def set_state(self, state: str, status_text: str | None = None) -> None:
        state = state.lower()
        if state not in VALID_STATES:
            raise ValueError(f"Unknown HUD state: {state}")
        self.state = state
        if status_text is not None:
            self.status_text = status_text

    def set_layout(self, layout: str) -> None:
        layout = layout.lower()
        if layout not in VALID_LAYOUTS:
            raise ValueError(f"Unknown HUD layout: {layout}")
        self.layout = layout

    def set_progress(self, value: float | None) -> None:
        self.progress = None if value is None else max(0.0, min(1.0, value))

    def add_thought_summary(self, text: str) -> None:
        """Store concise progress summaries, never private chain-of-thought."""
        text = text.strip()
        if text:
            self.thought_summary.append(text)
            self.thought_summary = self.thought_summary[-8:]

    def clear_thought_summary(self) -> None:
        self.thought_summary.clear()

    def snapshot(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "layout": self.layout,
            "progress": self.progress,
            "status_text": self.status_text,
            "context": self.context,
            "metrics": dict(self.metrics),
            "thought_summary": list(self.thought_summary),
        }


__all__ = ["HUDState", "VALID_STATES", "VALID_LAYOUTS"]
