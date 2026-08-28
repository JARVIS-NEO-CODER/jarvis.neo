"""Local reminders and event-driven automations for J.A.R.V.I.S. NEO."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable


@dataclass
class Automation:
    name: str
    trigger: str
    actions: list[Callable[[], Any]] = field(default_factory=list)
    conditions: list[Callable[[], bool]] = field(default_factory=list)
    enabled: bool = True


@dataclass
class Reminder:
    text: str
    due_at: datetime
    done: bool = False


class AutomationEngine:
    """Runs local rules and verifies each action through its return value."""

    def __init__(self) -> None:
        self.automations: list[Automation] = []
        self.reminders: list[Reminder] = []
        self.history: list[dict[str, Any]] = []

    def add_automation(self, name: str, trigger: str, actions: list[Callable[[], Any]], conditions: list[Callable[[], bool]] | None = None) -> None:
        self.automations.append(Automation(name, trigger.lower(), actions, conditions or []))

    def add_reminder(self, text: str, due_at: datetime) -> None:
        self.reminders.append(Reminder(text, due_at))

    def fire(self, trigger: str) -> list[dict[str, Any]]:
        results = []
        for rule in self.automations:
            if not rule.enabled or rule.trigger != trigger.lower():
                continue
            if not all(condition() for condition in rule.conditions):
                continue
            action_results = []
            for action in rule.actions:
                try:
                    value = action()
                    action_results.append({"success": value is not False, "result": value})
                except Exception as exc:
                    action_results.append({"success": False, "error": str(exc)})
            result = {"automation": rule.name, "trigger": rule.trigger, "actions": action_results}
            self.history.append(result)
            results.append(result)
        return results

    def due_reminders(self, now: datetime | None = None) -> list[Reminder]:
        current = now or datetime.now()
        return [r for r in self.reminders if not r.done and r.due_at <= current]

    def complete_reminder(self, reminder: Reminder) -> None:
        reminder.done = True


__all__ = ["AutomationEngine", "Automation", "Reminder"]
