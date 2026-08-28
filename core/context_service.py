"""Persistent context service facade."""
from __future__ import annotations

from typing import Any

from .context_memory import ContextMemory
from .context_runtime import ContextRuntime


class ContextService:
    """Single entry point for recording events and querying current context."""

    def __init__(self, max_events: int = 5000) -> None:
        self.memory = ContextMemory(max_events=max_events)
        self.runtime = ContextRuntime(self.memory)

    def record(self, name: str, **data: Any) -> None:
        self.memory.record(name, data)

    def get_context(self) -> dict[str, Any]:
        return self.runtime.snapshot()

    def current(self) -> str:
        return self.memory.detect_context()


__all__ = ["ContextService"]
