"""Automatic mode selection from local context and learned habits."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


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
        self.register("gaming", {"gaming"})
        self.register("ets2", {"ets2"})
        self.register("work", {"work"})
        self.register("study", {"study"})
        self.register("creation", {"creation"})
        self.register("music", {"music"})
        self.register("evening", {"evening"})


__all__ = ["AutoModeEngine", "ModeRule"]
