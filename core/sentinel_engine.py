"""Privacy-first Sentinel event engine for J.A.R.V.I.S. NEO."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class SentinelEvent:
    kind: str
    confidence: float
    timestamp: datetime
    zone: str | None = None
    details: dict[str, Any] | None = None


class SentinelEngine:
    """Stores detections only while explicitly enabled by the user."""

    def __init__(self) -> None:
        self.enabled = False
        self.zones: dict[str, tuple[int, int, int, int]] = {}
        self.history: list[SentinelEvent] = []

    def enable(self) -> None:
        self.enabled = True

    def disable(self) -> None:
        self.enabled = False

    def set_zone(self, name: str, rect: tuple[int, int, int, int]) -> None:
        self.zones[name] = rect

    def record_detection(self, kind: str, confidence: float, zone: str | None = None, **details: Any) -> SentinelEvent | None:
        if not self.enabled:
            return None
        event = SentinelEvent(kind, max(0.0, min(1.0, confidence)), datetime.now(), zone, details or None)
        self.history.append(event)
        return event

    def recent_alerts(self, minimum_confidence: float = 0.7) -> list[SentinelEvent]:
        return [e for e in self.history[-100:] if e.confidence >= minimum_confidence]

    def status(self) -> dict[str, Any]:
        return {"enabled": self.enabled, "zones": list(self.zones), "events": len(self.history)}


__all__ = ["SentinelEngine", "SentinelEvent"]
