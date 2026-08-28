"""Runtime context aggregation built on ContextMemory and ContextMonitor."""
from __future__ import annotations

from typing import Any


class ContextRuntime:
    """Turns locally recorded events into a compact current-context snapshot."""

    def __init__(self, memory: Any) -> None:
        self.memory = memory

    def snapshot(self) -> dict[str, Any]:
        events = self.memory.recent(50)
        return {
            "context": self.memory.detect_context(),
            "recent_events": [
                {"name": e.name, "timestamp": e.timestamp.isoformat(), "data": e.data}
                for e in events
            ],
            "recurring_events": self.memory.recurring(),
        }

    def should_invoke_ai(self) -> bool:
        """AI is reserved for context that local rules cannot classify."""
        return self.memory.detect_context() == "general" and bool(self.memory.recent(1))


__all__ = ["ContextRuntime"]
