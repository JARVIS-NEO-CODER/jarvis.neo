"""Single entry point for the observation-driven NEO core."""
from __future__ import annotations

from typing import Any

from .action_engine import ActionEngine
from .automation import AutomationEngine
from .bus import EventBus
from .context_engine import ContextEngine
from .hud_bridge import HudBridge
from .system_observer import SystemObserver
from .runtime import NeoRuntime


class NeoPipeline:
    """Own and lifecycle-manage the observation-driven NEO core."""

    def __init__(self, *, hud_callback: Any = None, interval: float = 2.0) -> None:
        self.bus = EventBus()
        self.actions = ActionEngine(event_bus=self.bus)
        self.context = ContextEngine(event_bus=self.bus)
        self.automation = AutomationEngine(self.actions)
        self.hud = HudBridge(hud_callback)
        self.runtime = NeoRuntime(self.bus, self.context, self.automation, self.hud)
        self.observer = SystemObserver(self.bus, interval=interval)
        self._running = False

    def start(self) -> None:
        if self._running:
            return
        self.runtime.attach()
        self.bus.start()
        self._running = True
        self.observer.start()

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
