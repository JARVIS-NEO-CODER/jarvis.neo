"""Context inference for J.A.R.V.I.S. NEO.

The engine deliberately contains no hard-coded application/game list. It
consumes neutral observations and derives broad runtime contexts. More
specialised classifiers can later provide semantic contexts such as GAMING.
"""
from __future__ import annotations

import json
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
    """Lightweight observation-based context engine with no app allow-list."""

    def __init__(self, memory: NeoMemory | None = None, event_bus: Any | None = None) -> None:
        self.memory = memory or NeoMemory()
        self.bus = event_bus
        self.current_context = "IDLE"
        self._attached = False
        self._last_metric: dict[str, Any] = {}

    def attach_to_bus(self, event_bus: Any | None = None) -> None:
        if event_bus is not None:
            self.bus = event_bus
        if self.bus is None or self._attached:
            return
        self.bus.subscribe("app.started", self._on_app_started)
        self.bus.subscribe("system.metric", self._on_system_metric)
        self._attached = True

    def detach_from_bus(self) -> None:
        if self.bus is None or not self._attached:
            return
        self.bus.unsubscribe("app.started", self._on_app_started)
        self.bus.unsubscribe("system.metric", self._on_system_metric)
        self._attached = False

    def _on_app_started(self, event: Event) -> None:
        """Accept an explicitly classified activity without knowing app names."""
        payload = event.payload
        context = self._normalise_context(payload.get("context"))
        activity = self._normalise_context(payload.get("activity_type", payload.get("app_type")))
        if context:
            self._set_context(context, trigger=str(payload.get("app", event.name)))
        elif activity:
            self._set_context(activity, trigger=str(payload.get("app", event.name)))

    def _on_system_metric(self, event: Event) -> None:
        payload = dict(event.payload or {})
        self._last_metric = payload

        # These are deliberately broad, application-independent states.
        # A high resource load alone is not enough evidence to call something
        # "gaming", so NEO does not make that claim here.
        active_process = str(payload.get("active_process") or "").strip()
        active_window = str(payload.get("active_window") or "").strip()
        cpu = self._number(payload.get("cpu_percent"))

        if active_process or active_window:
            self._set_context("ACTIVE", trigger=active_process or active_window)
        elif cpu is not None and cpu >= 90:
            self._set_context("RESOURCE_HEAVY", trigger="system.metric")

    def _set_context(self, context: str, *, trigger: str) -> None:
        context = context.upper()
        if not context or context == self.current_context:
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
        """Infer the strongest broad context from recent neutral observations."""
        _ = now or datetime.now()
        events = self.memory.recent_events(limit=200)
        scores: Counter[str] = Counter()
        reasons: dict[str, list[str]] = {}

        def add(name: str, points: float, reason: str) -> None:
            name = self._normalise_context(name)
            if not name:
                return
            scores[name] += points
            reasons.setdefault(name, []).append(reason)

        for row in events[:50]:
            payload = self._metadata(row.get("metadata"))
            context = payload.get("context")
            activity = payload.get("activity_type", payload.get("app_type"))
            if context:
                add(str(context), 0.8, "observation explicite")
            if activity:
                add(str(activity), 0.8, "activité fournie par le producteur")

            process = payload.get("active_process")
            window = payload.get("active_window")
            if process or window:
                add("ACTIVE", 0.25, "activité au premier plan")

            cpu = self._number(payload.get("cpu_percent"))
            if cpu is not None and cpu >= 90:
                add("RESOURCE_HEAVY", 0.2, "charge CPU élevée")

        if not scores:
            return ContextResult("UNKNOWN", 0.0, ("aucun signal suffisant",))

        name, raw_score = scores.most_common(1)[0]
        return ContextResult(name, min(0.99, raw_score), tuple(reasons[name]))

    def learn_current_context(self, result: ContextResult) -> None:
        if result.name == "UNKNOWN" or result.confidence < 0.5:
            return
        self.memory.remember_fact(
            "context",
            f"last_{result.name}",
            result.name,
            confidence=result.confidence,
            source="context_engine",
        )

    @staticmethod
    def _metadata(value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        if not value:
            return {}
        try:
            parsed = json.loads(str(value))
            return parsed if isinstance(parsed, dict) else {}
        except (TypeError, ValueError, json.JSONDecodeError):
            return {}

    @staticmethod
    def _normalise_context(value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip().replace(" ", "_").upper()

    @staticmethod
    def _number(value: Any) -> float | None:
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None


__all__ = ["ContextEngine", "ContextResult"]
