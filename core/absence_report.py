"""Compact local summaries of important events during user absence."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class AbsenceEvent:
    name: str
    timestamp: datetime
    importance: int = 1
    details: dict[str, Any] | None = None


class AbsenceReport:
    """Collects important events and produces a concise return-home report."""

    def __init__(self) -> None:
        self._events: list[AbsenceEvent] = []
        self._away = False
        self._started_at: datetime | None = None

    def start(self) -> None:
        self._away = True
        self._started_at = datetime.now()
        self._events.clear()

    def stop(self) -> dict[str, Any]:
        report = self.summary()
        self._away = False
        return report

    def record(self, name: str, importance: int = 1, **details: Any) -> None:
        if self._away:
            self._events.append(AbsenceEvent(name, datetime.now(), max(1, importance), details or None))

    def summary(self, limit: int = 5) -> dict[str, Any]:
        important = sorted(self._events, key=lambda e: (e.importance, e.timestamp), reverse=True)[:max(0, limit)]
        counts = Counter(e.name for e in self._events)
        return {
            "away": self._away,
            "started_at": self._started_at.isoformat() if self._started_at else None,
            "event_count": len(self._events),
            "important_events": [
                {"name": e.name, "timestamp": e.timestamp.isoformat(), "importance": e.importance, "details": e.details}
                for e in important
            ],
            "event_counts": dict(counts),
        }


__all__ = ["AbsenceReport", "AbsenceEvent"]
