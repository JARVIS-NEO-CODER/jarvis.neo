"""Opt-in vision controller abstraction for J.A.R.V.I.S. NEO."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class VisionState:
    enabled: bool = False
    source: str = "none"
    last_result: dict[str, Any] | None = None


class VisionController:
    """Controls optional screen/camera observation and keeps the policy explicit."""

    def __init__(self) -> None:
        self.state = VisionState()
        self._analyzer: Callable[[Any], dict[str, Any]] | None = None

    def set_analyzer(self, analyzer: Callable[[Any], dict[str, Any]]) -> None:
        self._analyzer = analyzer

    def enable(self, source: str) -> None:
        if source not in {"camera", "screen"}:
            raise ValueError("Vision source must be 'camera' or 'screen'")
        self.state.enabled = True
        self.state.source = source

    def disable(self) -> None:
        self.state = VisionState()

    def analyze(self, frame: Any) -> dict[str, Any]:
        if not self.state.enabled:
            return {"enabled": False, "analyzed": False, "reason": "vision_disabled"}
        if self._analyzer is None:
            return {"enabled": True, "analyzed": False, "reason": "no_analyzer_configured"}
        result = self._analyzer(frame)
        self.state.last_result = result
        return {"enabled": True, "analyzed": True, "source": self.state.source, "result": result}

    def status(self) -> dict[str, Any]:
        return {"enabled": self.state.enabled, "source": self.state.source, "has_result": self.state.last_result is not None}


__all__ = ["VisionController", "VisionState"]
