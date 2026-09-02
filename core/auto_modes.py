"""Automatic mode selection from runtime-configurable context rules."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .data_registry import get_data


@dataclass(frozen=True)
class ModeRule:
    name: str
    required_events: frozenset[str]
    action: Callable[[], Any] | None = None


class AutoModeEngine:
    def __init__(self) -> None:
        self.rules: list[ModeRule] = []
        self.active_mode = "general"

    def register(self, name: str, required_events: set[str], action: Callable[[], Any] | None = None) -> None:
        self.rules.append(ModeRule(name.lower(), frozenset(e.lower() for e in required_events), action))

    def evaluate(self, events: list[str]) -> dict[str, Any]:
        active = {e.lower() for e in events}
        matches = [r for r in self.rules if r.required_events and r.required_events.issubset(active)]
        if not matches:
            self.active_mode = "general"
            return {"mode": self.active_mode, "changed": False}
        selected = max(matches, key=lambda r: len(r.required_events))
        changed = selected.name != self.active_mode
        self.active_mode = selected.name
        if changed and selected.action:
            selected.action()
        return {"mode": self.active_mode, "changed": changed}

    def configure_defaults(self) -> None:
        """Load mode rules from the runtime data source instead of source-code lists."""
        for rule in get_data("auto_modes", []):
            if not isinstance(rule, dict):
                continue
            name = str(rule.get("name", "")).strip()
            events = rule.get("events", [])
            if name and isinstance(events, list) and events:
                self.register(name, {str(event) for event in events})


__all__ = ["AutoModeEngine", "ModeRule"]
