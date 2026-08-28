"""Local habit learning for J.A.R.V.I.S. NEO."""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class Habit:
    pattern: str
    occurrences: int
    confidence: float
    examples: list[dict[str, Any]]


class HabitMemory:
    """Learns recurring combinations of events locally, without an AI call."""

    def __init__(self, minimum_occurrences: int = 3) -> None:
        self.minimum_occurrences = max(2, minimum_occurrences)
        self._observations: list[tuple[datetime, tuple[str, ...], dict[str, Any]]] = []

    def observe(self, events: list[str], data: dict[str, Any] | None = None) -> None:
        normalized = tuple(sorted({e.strip().lower() for e in events if e and e.strip()}))
        if normalized:
            self._observations.append((datetime.now(), normalized, data or {}))

    def habits(self) -> list[Habit]:
        counts = Counter(events for _, events, _ in self._observations)
        result: list[Habit] = []
        total = max(1, len(self._observations))
        for pattern, count in counts.items():
            if count < self.minimum_occurrences:
                continue
            confidence = min(1.0, count / total * 2.0)
            examples = [d for _, events, d in self._observations if events == pattern][-5:]
            result.append(Habit(" + ".join(pattern), count, round(confidence, 3), examples))
        return sorted(result, key=lambda h: (h.confidence, h.occurrences), reverse=True)

    def predict(self, active_events: list[str]) -> list[Habit]:
        active = {e.strip().lower() for e in active_events}
        return [h for h in self.habits() if active.intersection(set(h.pattern.split(" + ")))]


__all__ = ["HabitMemory", "Habit"]
