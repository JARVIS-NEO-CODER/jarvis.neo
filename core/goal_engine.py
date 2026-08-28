"""Goal-oriented execution engine for J.A.R.V.I.S. NEO.

Turns a user objective into a small executable plan, runs each step through
ActionEngine, verifies the result, and attempts a bounded correction when a
step fails.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class GoalStatus(str, Enum):
    PLANNED = "planned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CORRECTING = "correcting"


@dataclass
class GoalStep:
    name: str
    action: str
    kwargs: dict[str, Any] = field(default_factory=dict)
    verifier: Callable[[Any], bool] | None = None
    correction: "GoalStep | None" = None


@dataclass
class Goal:
    objective: str
    steps: list[GoalStep]
    status: GoalStatus = GoalStatus.PLANNED
    results: list[Any] = field(default_factory=list)


class GoalEngine:
    """Plan and execute objective-driven workflows without replacing ActionEngine."""

    def __init__(self, action_engine: Any, planner: Callable[[str], list[GoalStep]] | None = None) -> None:
        self.action_engine = action_engine
        self.planner = planner or self._default_planner

    def create_goal(self, objective: str) -> Goal:
        objective = objective.strip()
        if not objective:
            raise ValueError("L'objectif ne peut pas être vide.")
        return Goal(objective=objective, steps=self.planner(objective))

    def run(self, goal: Goal) -> Goal:
        goal.status = GoalStatus.RUNNING
        goal.results.clear()

        if not goal.steps:
            goal.status = GoalStatus.FAILED
            return goal

        for step in goal.steps:
            result = self.action_engine.execute(step.action, **step.kwargs)
            goal.results.append(result)

            verified = bool(getattr(result, "success", False)) and bool(
                getattr(result, "verified", False)
            )
            if step.verifier is not None:
                try:
                    verified = verified and bool(step.verifier(result))
                except Exception:
                    verified = False

            if verified:
                continue

            if step.correction is None:
                goal.status = GoalStatus.FAILED
                return goal

            goal.status = GoalStatus.CORRECTING
            correction = step.correction
            correction_result = self.action_engine.execute(
                correction.action, **correction.kwargs
            )
            goal.results.append(correction_result)

            correction_verified = bool(getattr(correction_result, "success", False)) and bool(
                getattr(correction_result, "verified", False)
            )
            if correction.verifier is not None:
                try:
                    correction_verified = correction_verified and bool(
                        correction.verifier(correction_result)
                    )
                except Exception:
                    correction_verified = False

            if not correction_verified:
                goal.status = GoalStatus.FAILED
                return goal

            goal.status = GoalStatus.RUNNING

        goal.status = GoalStatus.COMPLETED
        return goal

    @staticmethod
    def _default_planner(objective: str) -> list[GoalStep]:
        """Safe fallback planner.

        Complex natural-language planning is deliberately delegated to an
        injected planner, such as the local Ollama layer. The fallback never
        invents destructive actions.
        """
        return [
            GoalStep(
                name="publish_goal",
                action="action.publish_event",
                kwargs={"event_name": "goal.received", "payload": {"objective": objective}},
            )
        ]


__all__ = ["GoalEngine", "Goal", "GoalStep", "GoalStatus"]
