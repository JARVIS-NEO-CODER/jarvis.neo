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
from .context_engine import ContextEngine, ContextResult
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
    _last_tick: float = 0.0
    last_context: ContextResult | None = None

    @classmethod
    def create(cls) -> "CoreBridge":
        memory = NeoMemory()
        context = ContextEngine(memory=memory)
        actions = ActionEngine(memory=memory)
        automation = AutomationEngine(actions=actions)
        performance = PerformanceManager()
        return cls(memory, context, actions, automation, performance)

    def tick(self, *, force: bool = False) -> ContextResult | None:
        """Run one lightweight core cycle.

        ``force=True`` bypasses the normal polling throttle, which is useful
        for explicit/manual refreshes and deterministic tests.
        """
        now = monotonic()
        if not force and self._last_tick and not self.performance.should_poll(now - self._last_tick):
            return self.last_context

        self._last_tick = now
        result = self.context.detect()
        self.last_context = result
        self.performance.apply_context(result.name)
        self.context.learn_current_context(result)
        self.automation.evaluate(result, now=now)
        return result

    def shutdown(self) -> None:
        """Release core resources when the legacy application exits."""
        self.memory.close()


__all__ = ["CoreBridge"]
