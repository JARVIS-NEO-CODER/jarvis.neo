"""Lightweight local context memory for J.A.R.V.I.S. NEO."""
from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
from datetime import datetime
from typing import Any

@dataclass(frozen=True)
class ContextEvent:
    name: str
    timestamp: datetime
    data: dict[str, Any]

class ContextMemory:
    def __init__(self, max_events: int = 5000) -> None:
        self.events: deque[ContextEvent] = deque(maxlen=max_events)

    def record(self, name: str, data: dict[str, Any] | None = None) -> ContextEvent:
        event = ContextEvent(name, datetime.now(), data or {})
        self.events.append(event)
        return event

    def recent(self, limit: int = 50) -> list[ContextEvent]:
        return list(self.events)[-max(0, limit):]

    def recurring(self, minimum: int = 3) -> list[tuple[str, int]]:
        counts = Counter(event.name for event in self.events)
        return sorted(((n, c) for n, c in counts.items() if c >= minimum), key=lambda x: x[1], reverse=True)

    def detect_context(self) -> str:
        names = {e.name.lower() for e in self.recent(25)}
        if any("ets2" in n or "gaming" in n for n in names): return "gaming"
        if any("study" in n or "school" in n for n in names): return "study"
        if any("music" in n for n in names): return "music"
        return "general"
