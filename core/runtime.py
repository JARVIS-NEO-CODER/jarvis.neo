"""Runtime orchestration for the NEO core pipeline."""
from __future__ import annotations

import logging
from typing import Any

from .automation import AutomationEngine
from .context_engine import ContextEngine

logger = logging.getLogger("JarvisRuntime")


class NeoRuntime:
    """Connects context detection and automation without hidden side effects."""

    def __init__(self, bus: Any, context_engine: ContextEngine, automation: AutomationEngine) -> None:
        self.bus = bus
        self.context_engine = context_engine
        self.automation = automation
        self._attached = False

    def attach(self) -> None:
        if self._attached:
            return
        self.context_engine.attach_to_bus(self.bus)
        self.automation.attach_to_bus(self.bus)
        self._attached = True
        logger.info("NEO core pipeline attached")

    def detach(self) -> None:
        if not self._attached:
            return
        self.automation.detach_from_bus(self.bus)
        self.context_engine.detach_from_bus(self.bus)
        self._attached = False
        logger.info("NEO core pipeline detached")


__all__ = ["NeoRuntime"]
