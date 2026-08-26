"""Single entry point for the observation-driven NEO core."""
from __future__ import annotations

from typing import Any

from .automation import AutomationEngine
from .bus import EventBus
from .context_engine import ContextEngine
from .hud_bridge import HudBridge
from .system_observer import SystemObserver
from .runtime import NeoRuntime


class NeoPipeline:
    """Own and lifecycle-manage the core observation pipeline."""

    def __init__(self, *, hud_callback: Any = None, interval: float = 2.0) -> None:
        self.bus = EventBus()
        self.context = ContextEngine(event_bus=self.bus)
        self.automation = AutomationEngine()
        self.hud = HudBridge(hud_callback)
        self.runtime = NeoRuntime(self.bus, self.context, self.automation, self.hud)
        self.observer = SystemObserver(self.bus, interval=interval)
        self._running = False

    def start(self) -> None:
        if self._running:
            return
        self.runtime.attach()
        self.bus.start()
        self.observer.start()
        self._running = True

    def stop(self) -> None:
        if not self._running:
            return
        self.observer.stop()
        self.runtime.detach()
        self.bus.stop()
        self._running = False

    @property
    def running(self) -> bool:
        return self._running


__all__ = ["NeoPipeline"]
