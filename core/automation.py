"""Rule-based automation bridge for J.A.R.V.I.S. NEO.

Automation connects observations/context to explicitly registered actions.
Rules are declarative and do not execute arbitrary commands themselves.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .action_engine import ActionEngine, ActionResult
from .context_engine import ContextResult


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

            action_result = self.actions.execute(rule.action)
            outputs.append(action_result)
            if action_result.success:
                self._last_triggered[rule.name] = now
        return outputs

    def rules(self) -> tuple[AutomationRule, ...]:
        return tuple(self._rules.values())


__all__ = ["AutomationEngine", "AutomationRule"]
