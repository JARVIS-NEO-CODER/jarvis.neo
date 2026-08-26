"""Runtime orchestration for the NEO core pipeline."""
from __future__ import annotations

import logging
from typing import Any

from .automation import AutomationEngine
from .context_engine import ContextEngine
from .hud_bridge import HudBridge

logger = logging.getLogger("JarvisRuntime")


class NeoRuntime:
    """Connect the core pipeline with explicit lifecycle management."""

    def __init__(
        self,
        bus: Any,
        context_engine: ContextEngine,
        automation: AutomationEngine,
        hud_bridge: HudBridge | None = None,
    ) -> None:
        self.bus = bus
        self.context_engine = context_engine
        self.automation = automation
        self.hud_bridge = hud_bridge
        self._attached = False

    def attach(self) -> None:
        if self._attached:
            return
        self.context_engine.attach_to_bus(self.bus)
        self.automation.attach_to_bus(self.bus)
        if self.hud_bridge is not None:
            self.hud_bridge.attach_to_bus(self.bus)
        self._attached = True
        logger.info("NEO core pipeline attached")

    def detach(self) -> None:
        if not self._attached:
            return
        if self.hud_bridge is not None:
            self.hud_bridge.detach_from_bus()
        self.automation.detach_from_bus(self.bus)
        self.context_engine.detach_from_bus(self.bus)
        self._attached = False
        logger.info("NEO core pipeline detached")

    @property
    def attached(self) -> bool:
        return self._attached


__all__ = ["NeoRuntime"]
