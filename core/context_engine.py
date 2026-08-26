"""Context detection for J.A.R.V.I.S. NEO.

This module deliberately stays lightweight: it consumes local events and
history from NeoMemory and produces context changes. It does not execute
system actions and does not call an AI model for every event.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .bus import Event
from .memory import NeoMemory


@dataclass(frozen=True)
class ContextResult:
    name: str
    confidence: float
    reasons: tuple[str, ...] = ()


class ContextEngine:
    """Small rule/statistics-based context engine for local NEO events."""

    def __init__(self, memory: NeoMemory | None = None, event_bus: Any | None = None) -> None:
        self.memory = memory or NeoMemory()
        self.bus = event_bus
        self.current_context = "IDLE"
        self._attached = False

    def attach_to_bus(self, event_bus: Any | None = None) -> None:
        """Subscribe to live events without requiring a bus at construction."""
        if event_bus is not None:
            self.bus = event_bus
        if self.bus is None or self._attached:
            return
        self.bus.subscribe("app.started", self._on_app_started)
        self.bus.subscribe("system.metric", self._on_system_metric)
        self._attached = True

    def detach_from_bus(self) -> None:
        """Remove the subscriptions created by attach_to_bus()."""
        if self.bus is None or not self._attached:
            return
        self.bus.unsubscribe("app.started", self._on_app_started)
        self.bus.unsubscribe("system.metric", self._on_system_metric)
        self._attached = False

    def _on_app_started(self, event: Event) -> None:
        """React immediately to known application launches."""
        app = str(event.payload.get("app", "")).lower()
        if app in {"ets2.exe", "eurotrucks2.exe"}:
            self._set_context("gaming", trigger=app)

    def _on_system_metric(self, event: Event) -> None:
        """Reserved for lightweight system-context rules."""
        return None

    def _set_context(self, context: str, *, trigger: str) -> None:
        if context == self.current_context:
            return
        previous = self.current_context
        self.current_context = context
        if self.bus is not None:
            self.bus.publish(
                Event(
                    name="context.changed",
                    payload={
                        "previous_context": previous,
                        "current_context": context,
                        "trigger": trigger,
                    },
                    priority=5,
                )
            )

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
