"""Context detection for J.A.R.V.I.S. NEO.

This module deliberately stays lightweight: it consumes local events and
history from NeoMemory and produces context + confidence. It does not execute
system actions and does not call an AI model for every event.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .memory import NeoMemory


@dataclass(frozen=True)
class ContextResult:
    name: str
    confidence: float
    reasons: tuple[str, ...] = ()


class ContextEngine:
    """Small rule/statistics-based context engine for local NEO events."""

    def __init__(self, memory: NeoMemory | None = None) -> None:
        self.memory = memory or NeoMemory()

    def detect(self, *, now: datetime | None = None) -> ContextResult:
        """Infer the most likely context from recent local observations."""
        now = now or datetime.now()
        events = self.memory.recent_events(limit=200)
        scores: Counter[str] = Counter()
        reasons: dict[str, list[str]] = {}

        def add(name: str, points: float, reason: str) -> None:
            scores[name] += points
            reasons.setdefault(name, []).append(reason)

        hour = now.hour + now.minute / 60
        recent_text = " ".join(
            f"{event.get('kind', '')} {event.get('message', '')}".lower()
            for event in events[:50]
        )

        gaming_terms = ("ets2", "euro truck", "steam", "game", "gaming")
        if any(term in recent_text for term in gaming_terms):
            add("gaming", 0.55, "un événement récent correspond au gaming")
        if 19 <= hour < 24:
            add("gaming", 0.10, "horaire fréquent pour le gaming")

        work_terms = ("vscode", "visual studio code", "python", "coding", "development")
        if any(term in recent_text for term in work_terms):
            add("work", 0.50, "activité de développement détectée")

        study_terms = ("school", "étude", "study", "devoir", "cours")
        if any(term in recent_text for term in study_terms):
            add("study", 0.50, "activité d'étude détectée")

        if not scores:
            return ContextResult("unknown", 0.0, ("aucun signal suffisant",))

        name, raw_score = scores.most_common(1)[0]
        confidence = min(0.99, raw_score)
        return ContextResult(name, confidence, tuple(reasons[name]))

    def learn_current_context(self, result: ContextResult) -> None:
        """Persist a lightweight observation for future habit learning."""
        if result.name == "unknown" or result.confidence < 0.5:
            return
        self.memory.remember_fact(
            "context",
            f"last_{result.name}",
            result.name,
            confidence=result.confidence,
            source="context_engine",
        )


__all__ = ["ContextEngine", "ContextResult"]
