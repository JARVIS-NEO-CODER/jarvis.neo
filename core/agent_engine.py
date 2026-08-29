"""Goal-oriented execution loop for J.A.R.V.I.S. NEO.

The AgentEngine coordinates planning and execution. It deliberately delegates
actual computer operations to ActionEngine, so permissions remain centralized.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .action_engine import ActionEngine, ActionResult
from .goal_planner import GoalPlan, GoalPlanner
from .memory import NeoMemory


@dataclass(frozen=True)
class AgentRunResult:
    objective: str
    success: bool
    plan: GoalPlan | None
    results: tuple[ActionResult, ...]
    failed_step: int | None = None
    error: str | None = None


class AgentEngine:
    """Coordinate plan -> execute -> observe -> report for one goal."""

    def __init__(
        self,
        action_engine: ActionEngine,
        planner: GoalPlanner | None = None,
        memory: NeoMemory | None = None,
        event_bus: Any | None = None,
    ) -> None:
        self.action_engine = action_engine
        self.planner = planner or GoalPlanner(action_engine)
        self.memory = memory or action_engine.memory
        self.event_bus = event_bus
        self._running = False

    @property
    def running(self) -> bool:
        return self._running

    def run(
        self,
        objective: str,
        *,
        confirm: Callable[[GoalPlan], bool] | None = None,
    ) -> AgentRunResult:
        objective = objective.strip()
        if not objective:
            raise ValueError("L'objectif ne peut pas être vide.")
        if self._running:
            raise RuntimeError("Un agent est déjà en cours d'exécution.")

        self._running = True
        self._emit("agent.started", {"objective": objective})
        self.memory.record_event("agent", f"Agent started: {objective}", source="agent_engine")

        try:
            try:
                plan = self.planner.plan(objective)
            except Exception as exc:
                return self._failure(objective, None, (), None, str(exc))

            self._emit("agent.plan_ready", {
                "objective": objective,
                "steps": [step.action for step in plan.steps],
            })
            self.memory.record_event(
                "agent.plan",
                f"Plan created with {len(plan.steps)} step(s)",
                source="agent_engine",
            )

            if confirm is not None and not confirm(plan):
                return self._failure(objective, plan, (), None, "Plan refusé par l'utilisateur.")

            results: list[ActionResult] = []
            for index, step in enumerate(plan.steps, start=1):
                self._emit("agent.step_started", {
                    "objective": objective,
                    "step": index,
                    "total": len(plan.steps),
                    "action": step.action,
                    "description": step.description,
                })
                result = self.action_engine.execute(step.action, **step.kwargs)
                results.append(result)
                self._emit("agent.step_finished", {
                    "objective": objective,
                    "step": index,
                    "total": len(plan.steps),
                    "action": step.action,
                    "success": result.success,
                    "verified": result.verified,
                    "message": result.message,
                })
                if not result.success or not result.verified:
                    return self._failure(objective, plan, tuple(results), index, result.message)

            self.memory.record_event("agent", f"Agent completed: {objective}", source="agent_engine")
            self._emit("agent.completed", {
                "objective": objective,
                "steps": len(results),
            })
            return AgentRunResult(objective, True, plan, tuple(results))
        finally:
            self._running = False

    def _failure(
        self,
        objective: str,
        plan: GoalPlan | None,
        results: tuple[ActionResult, ...],
        failed_step: int | None,
        error: str,
    ) -> AgentRunResult:
        self.memory.record_event("agent", f"Agent failed: {objective} — {error}", source="agent_engine")
        self._emit("agent.failed", {
            "objective": objective,
            "failed_step": failed_step,
            "error": error,
        })
        return AgentRunResult(objective, False, plan, results, failed_step, error)

    def _emit(self, name: str, payload: dict[str, Any]) -> None:
        if self.event_bus is not None:
            from .bus import Event
            self.event_bus.publish(Event(name=name, payload=payload, priority=10))


__all__ = ["AgentEngine", "AgentRunResult"]
