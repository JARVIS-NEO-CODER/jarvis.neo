"""Data-driven context classification for NEO."""
from __future__ import annotations

from collections import defaultdict
from typing import Any


class ContextClassifier:
    """Learns context signals from observations instead of a fixed app list."""

    def __init__(self) -> None:
        self._signals: dict[str, dict[str, float]] = defaultdict(dict)

    def learn(self, context: str, **signals: Any) -> None:
        context = str(context).strip().upper()
        if not context:
            return
        for key, value in signals.items():
            if value is None:
                continue
            self._signals[context][str(value).strip().lower()] = 1.0

    def classify(self, **signals: Any) -> tuple[str, float]:
        candidates: dict[str, float] = defaultdict(float)
        observed = {str(v).strip().lower() for v in signals.values() if v is not None}
        if not observed:
            return "UNKNOWN", 0.0
        for context, known in self._signals.items():
            matches = sum(1 for value in observed if value in known)
            if matches:
                candidates[context] = min(0.99, matches / max(1, len(observed)))
        if not candidates:
            return "UNKNOWN", 0.0
        return max(candidates.items(), key=lambda item: item[1])


__all__ = ["ContextClassifier"]
