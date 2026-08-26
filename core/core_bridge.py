"""Compatibility bridge between the legacy JARVIS runtime and the new core.

This module intentionally has no side effects on import. It provides one small
object that the legacy ``assistant.py`` can instantiate when we are ready to
integrate the new architecture.
"""
from __future__ import annotations

from dataclasses import dataclass
from time import monotonic

from .action_engine import ActionEngine
from .automation import AutomationEngine
from .context_engine import ContextEngine
from .memory import NeoMemory
from .performance_manager import PerformanceManager


@dataclass
class CoreBridge:
    """Own the new core components without replacing the legacy runtime yet."""

    memory: NeoMemory
    context: ContextEngine
    actions: ActionEngine
    automation: AutomationEngine
    performance: PerformanceManager

    @classmethod
    def create(cls) -> "CoreBridge":
        memory = NeoMemory()
        context = ContextEngine(memory=memory)
        actions = ActionEngine(memory=memory)
        automation = AutomationEngine(actions=actions)
        performance = PerformanceManager()
        return cls(memory, context, actions, automation, performance)

    def tick(self) -> None:
        """Run one lightweight core cycle.

        The bridge deliberately does not start its own background thread or
        invoke Ollama. The legacy application controls when this is called,
        allowing Gaming/Performance mode to remain inexpensive.
        """
        self.performance.update()
        self.context.update()

    def shutdown(self) -> None:
        """Release core resources when the legacy application exits."""
        close = getattr(self.memory, "close", None)
        if callable(close):
            close()


__all__ = ["CoreBridge"]
