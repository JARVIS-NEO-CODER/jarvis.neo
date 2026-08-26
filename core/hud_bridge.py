"""EventBus bridge for HUD requests."""
from __future__ import annotations

from typing import Any, Callable


class HudBridge:
    """Turns hud.show bus events into a UI callback without coupling core to Qt."""

    def __init__(self, callback: Callable[[dict[str, Any]], None] | None = None) -> None:
        self.callback = callback
        self._bus: Any | None = None
        self._attached = False

    def attach_to_bus(self, bus: Any) -> None:
        if self._attached:
            return
        self._bus = bus
        bus.subscribe("hud.show", self._on_hud_show)
        self._attached = True

    def detach_from_bus(self) -> None:
        if not self._attached or self._bus is None:
            return
        self._bus.unsubscribe("hud.show", self._on_hud_show)
        self._bus = None
        self._attached = False

    def _on_hud_show(self, event: Any) -> None:
        payload = getattr(event, "payload", event)
        if self.callback is not None:
            self.callback(dict(payload or {}))


__all__ = ["HudBridge"]
