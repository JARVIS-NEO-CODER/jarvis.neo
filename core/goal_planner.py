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
    """Build, validate and replan safe action sequences."""
    def __init__(self, action_engine: ActionEngine, llm_planner: Callable[[str, tuple[str, ...]], Any] | None = None) -> None:
        self.action_engine = action_engine
        self.llm_planner = llm_planner

    @classmethod
    def with_ollama(cls, action_engine: ActionEngine, *, model: str = "llama3.2:3b", base_url: str = "http://127.0.0.1:11434", timeout: float = 60.0) -> "GoalPlanner":
        from .ollama_planner import OllamaPlanner
        return cls(action_engine, OllamaPlanner(model=model, base_url=base_url, timeout=timeout))

    def available_actions(self) -> tuple[str, ...]:
        return tuple(sorted(self.action_engine._actions))

    def plan(self, objective: str) -> GoalPlan:
        objective = objective.strip()
        if not objective:
            raise ValueError("L'objectif ne peut pas être vide.")
        deterministic = self._deterministic_plan(objective)
        if deterministic is not None:
            return deterministic
        if self.llm_planner is None:
            raise ValueError("Aucun plan sûr et déterministe n'est disponible pour cet objectif.")
        return self._parse_llm_plan(objective, self.llm_planner(objective, self.available_actions()))

    def replan(self, objective: str, *, failure: str, observation: dict[str, Any], attempted_actions: tuple[str, ...] = ()) -> GoalPlan:
        objective = objective.strip()
        if not objective:
            raise ValueError("L'objectif ne peut pas être vide.")
        replanner = getattr(self.llm_planner, "replan", None)
        if not callable(replanner):
            raise ValueError("Le planner actuel ne supporte pas la replanification.")
        raw = replanner(objective, self.available_actions(), failure=failure, observation=observation, attempted_actions=attempted_actions)
        plan = self._parse_llm_plan(objective, raw)
        if attempted_actions and all(step.action in attempted_actions for step in plan.steps):
            raise ValueError("La replanification n'a proposé aucune action différente.")
        return plan

    def _deterministic_plan(self, objective: str) -> GoalPlan | None:
        if "notification" in objective.lower():
            return GoalPlan(objective, (GoalStep("action.notify", {"message": objective}, "Notifier l'utilisateur."),))
        return None

    def _parse_llm_plan(self, objective: str, raw: Any) -> GoalPlan:
        raw_steps = raw.get("steps", []) if isinstance(raw, dict) else raw
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
