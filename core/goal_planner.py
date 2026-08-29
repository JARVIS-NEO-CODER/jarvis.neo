"""Safe, inspectable goal planning layer for J.A.R.V.I.S. NEO."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .action_engine import ActionEngine, ActionResult


@dataclass(frozen=True)
class GoalStep:
    action: str
    kwargs: dict[str, Any] = field(default_factory=dict)
    description: str = ""


@dataclass(frozen=True)
class GoalPlan:
    objective: str
    steps: tuple[GoalStep, ...]


@dataclass(frozen=True)
class GoalRunResult:
    objective: str
    success: bool
    results: tuple[ActionResult, ...]
    failed_step: int | None = None


class GoalPlanner:
    """Build deterministic plans and optionally delegate planning to Ollama."""

    def __init__(
        self,
        action_engine: ActionEngine,
        llm_planner: Callable[[str, tuple[str, ...]], Any] | None = None,
    ) -> None:
        self.action_engine = action_engine
        self.llm_planner = llm_planner

    def available_actions(self) -> tuple[str, ...]:
        """Return registered action names without exposing handlers."""
        return tuple(sorted(self.action_engine._actions))

    def plan(self, objective: str) -> GoalPlan:
        objective = objective.strip()
        if not objective:
            raise ValueError("L'objectif ne peut pas être vide.")

        deterministic = self._deterministic_plan(objective)
        if deterministic is not None:
            return deterministic

        if self.llm_planner is not None:
            return self._parse_llm_plan(objective, self.llm_planner(objective, self.available_actions()))

        raise ValueError("Aucun plan sûr et déterministe n'est disponible pour cet objectif.")

    def _deterministic_plan(self, objective: str) -> GoalPlan | None:
        normalized = objective.lower()
        if "notification" in normalized:
            return GoalPlan(objective, (
                GoalStep("action.notify", {"message": objective}, "Notifier l'utilisateur."),
            ))
        return None

    def _parse_llm_plan(self, objective: str, raw: Any) -> GoalPlan:
        """Validate an LLM-produced plan before it can reach ActionEngine."""
        if isinstance(raw, dict):
            raw_steps = raw.get("steps", [])
        else:
            raw_steps = raw
        if not isinstance(raw_steps, list) or not raw_steps:
            raise ValueError("Le plan IA est vide ou invalide.")

        allowed = set(self.available_actions())
        steps: list[GoalStep] = []
        for item in raw_steps:
            if not isinstance(item, dict):
                raise ValueError("Étape IA invalide.")
            action = str(item.get("action", "")).strip()
            if action not in allowed:
                raise ValueError(f"Action non autorisée dans le plan IA: {action}")
            kwargs = item.get("kwargs", {})
            if not isinstance(kwargs, dict):
                raise ValueError(f"Arguments invalides pour {action}.")
            steps.append(GoalStep(action, kwargs, str(item.get("description", ""))))
        return GoalPlan(objective, tuple(steps))

    def execute(self, plan: GoalPlan) -> GoalRunResult:
        results: list[ActionResult] = []
        for index, step in enumerate(plan.steps, start=1):
            result = self.action_engine.execute(step.action, **step.kwargs)
            results.append(result)
            if not result.success or not result.verified:
                return GoalRunResult(plan.objective, False, tuple(results), index)
        return GoalRunResult(plan.objective, True, tuple(results))

    def run(self, objective: str) -> GoalRunResult:
        return self.execute(self.plan(objective))


__all__ = ["GoalPlanner", "GoalPlan", "GoalStep", "GoalRunResult"]
