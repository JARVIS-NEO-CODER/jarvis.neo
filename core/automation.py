"""Rule-based automation bridge for J.A.R.V.I.S. NEO.

Automation connects observations/context to explicitly registered actions.
Rules are declarative and delegate execution to ActionEngine.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

from .action_engine import ActionEngine, ActionResult
from .context_engine import ContextResult

logger = logging.getLogger("JarvisAutomation")


@dataclass(frozen=True)
class AutomationRule:
    name: str
    context: str
    minimum_confidence: float
    action: str
    enabled: bool = True
    cooldown_seconds: float = 300.0


class AutomationEngine:
    """Evaluate safe, explicit rules and delegate execution to ActionEngine."""

    def __init__(self, actions: ActionEngine | None = None) -> None:
        self.actions = actions or ActionEngine()
        self._rules: dict[str, AutomationRule] = {}
        self._last_triggered: dict[str, float] = {}
        self._bus: Any | None = None
        self._attached = False

    def register_rule(self, rule: AutomationRule) -> None:
        self._rules[rule.name] = rule

    def set_enabled(self, rule_name: str, enabled: bool) -> None:
        rule = self._rules[rule_name]
        self._rules[rule_name] = AutomationRule(
            name=rule.name,
            context=rule.context,
            minimum_confidence=rule.minimum_confidence,
            action=rule.action,
            enabled=enabled,
            cooldown_seconds=rule.cooldown_seconds,
        )

    def attach_to_bus(self, event_bus: Any) -> None:
        """Subscribe to context changes without executing anything at attach time."""
        if self._attached:
            return
        self._bus = event_bus
        event_bus.subscribe("context.changed", self._on_context_changed)
        self._attached = True

    def detach_from_bus(self) -> None:
        """Remove the context subscription created by attach_to_bus()."""
        if self._bus is None or not self._attached:
            return
        self._bus.unsubscribe("context.changed", self._on_context_changed)
        self._attached = False

    def _on_context_changed(self, event: Any) -> None:
        """Translate a bus context event into the existing rule evaluator."""
        payload = event.payload if isinstance(event.payload, dict) else {}
        context = str(payload.get("current_context", "unknown"))
        try:
            confidence = float(payload.get("confidence", 1.0))
        except (TypeError, ValueError):
            confidence = 0.0

        result = ContextResult(
            name=context,
            confidence=max(0.0, min(1.0, confidence)),
            reasons=(f"bus trigger: {payload.get('trigger', 'unknown')}",),
        )
        self.evaluate(result, now=time.time())

    def evaluate(self, result: ContextResult, *, now: float) -> list[ActionResult]:
        """Run rules whose context/confidence match and whose cooldown expired."""
        outputs: list[ActionResult] = []
        for rule in self._rules.values():
            if not rule.enabled:
                continue
            if result.name != rule.context or result.confidence < rule.minimum_confidence:
                continue
            previous = self._last_triggered.get(rule.name)
            if previous is not None and now - previous < rule.cooldown_seconds:
                continue

            try:
                action_result = self.actions.execute(rule.action)
            except Exception as exc:  # noqa: BLE001 - isolate an action from other rules
                logger.error("Action '%s' failed: %s", rule.action, exc, exc_info=True)
                continue

            outputs.append(action_result)
            if action_result.success:
                self._last_triggered[rule.name] = now
        return outputs

    def rules(self) -> tuple[AutomationRule, ...]:
        return tuple(self._rules.values())


__all__ = ["AutomationEngine", "AutomationRule"]
