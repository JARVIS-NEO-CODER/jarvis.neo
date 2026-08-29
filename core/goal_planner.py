"""Goal planning layer for J.A.R.V.I.S. NEO.

Turns a high-level user objective into a safe, inspectable sequence of
registered ActionEngine actions. The planner itself does not execute actions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .action_engine import ActionEngine, ActionResult


@dataclass(frozen=True)
class GoalStep:
    """One planned action and the arguments required to execute it."""

    action: str
    kwargs: dict[str, Any] = field(default_factory=dict)
    description: str = ""


@dataclass(frozen=True)
class GoalPlan:
    """An inspectable plan generated for a user objective."""

    objective: str
    steps: tuple[GoalStep, ...]


@dataclass(frozen=True)
class GoalRunResult:
    """Result of executing a previously generated goal plan."""

    objective: str
    success: bool
    results: tuple[ActionResult, ...]
    failed_step: int | None = None


class GoalPlanner:
    """Build and execute safe goal plans on top of ActionEngine."""

    def __init__(self, action_engine: ActionEngine) -> None:
        self.action_engine = action_engine

    def plan(self, objective: str) -> GoalPlan:
        objective = objective.strip()
        if not objective:
            raise ValueError("L'objectif ne peut pas être vide.")

        # Explicit deterministic plans for known high-level intents.
        # More advanced Ollama planning can be plugged into this layer later.
        normalized = objective.lower()
        steps: list[GoalStep] = []

        if "notification" in normalized:
            steps.append(
                GoalStep(
                    "action.notify",
                    {"message": objective},
                    "Notifier l'utilisateur.",
                )
            )

        if not steps:
            raise ValueError(
                "Aucun plan sûr et déterministe n'est disponible pour cet objectif."
            )

        return GoalPlan(objective=objective, steps=tuple(steps))

    def execute(self, plan: GoalPlan) -> GoalRunResult:
        results: list[ActionResult] = []
        for index, step in enumerate(plan.steps, start=1):
            result = self.action_engine.execute(step.action, **step.kwargs)
            results.append(result)
            if not result.success or not result.verified:
                return GoalRunResult(
                    objective=plan.objective,
                    success=False,
                    results=tuple(results),
                    failed_step=index,
                )

        return GoalRunResult(
            objective=plan.objective,
            success=True,
            results=tuple(results),
        )

    def run(self, objective: str) -> GoalRunResult:
        return self.execute(self.plan(objective))


__all__ = ["GoalPlanner", "GoalPlan", "GoalStep", "GoalRunResult"]
