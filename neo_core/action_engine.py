"""Small, safe action orchestration layer for NEO.

Actions are explicit callables. The engine tracks steps and verification rather
than letting an LLM execute arbitrary shell commands.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Any

@dataclass
class ActionStep:
    name: str
    run: Callable[[], Any]
    verify: Callable[[Any], bool] | None = None

@dataclass
class ActionResult:
    success: bool
    completed: list[str] = field(default_factory=list)
    failed: str | None = None
    error: str | None = None

class ActionEngine:
    def execute(self, steps: list[ActionStep]) -> ActionResult:
        result = ActionResult(True)
        for step in steps:
            try:
                value = step.run()
                if step.verify and not step.verify(value):
                    result.success = False
                    result.failed = step.name
                    result.error = "verification_failed"
                    return result
                result.completed.append(step.name)
            except Exception as exc:
                result.success = False
                result.failed = step.name
                result.error = str(exc)
                return result
        return result
