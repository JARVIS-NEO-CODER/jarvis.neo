"""Goal-oriented execution loop with bounded recovery for J.A.R.V.I.S. NEO."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .action_engine import ActionEngine, ActionResult
from .goal_planner import GoalPlan, GoalPlanner
from .memory import NeoMemory
from .system_observer import SystemObserver, SystemSnapshot


@dataclass(frozen=True)
class AgentRunResult:
    objective: str
    success: bool
    plan: GoalPlan | None
    results: tuple[ActionResult, ...]
    failed_step: int | None = None
    error: str | None = None
    recovery_attempts: int = 0


class AgentEngine:
    """Coordinate plan -> observe -> execute -> observe -> recover -> report."""

    def __init__(self, action_engine: ActionEngine, planner: GoalPlanner | None = None,
                 memory: NeoMemory | None = None, event_bus: Any | None = None,
                 observer: SystemObserver | None = None, max_retries: int = 3) -> None:
        self.action_engine = action_engine
        self.planner = planner or GoalPlanner(action_engine)
        self.memory = memory or action_engine.memory
        self.event_bus = event_bus
        self.observer = observer or (SystemObserver(event_bus) if event_bus is not None else None)
        self.max_retries = max(0, int(max_retries))
        self._running = False

    @property
    def running(self) -> bool:
        return self._running

    def run(self, objective: str, *, confirm: Callable[[GoalPlan], bool] | None = None) -> AgentRunResult:
        objective = objective.strip()
        if not objective:
            raise ValueError("L'objectif ne peut pas être vide.")
        if self._running:
            raise RuntimeError("Un agent est déjà en cours d'exécution.")

        self._running = True
        self._emit("agent.started", {"objective": objective})
        self.memory.record_event("agent", f"Agent started: {objective}", source="agent_engine")
        try:
            plan = self._make_plan(objective)
            if plan is None:
                return self._failure(objective, None, (), None, "Impossible de créer un plan.", 0)
            if confirm is not None and not confirm(plan):
                return self._failure(objective, plan, (), None, "Plan refusé par l'utilisateur.", 0)

            all_results: list[ActionResult] = []
            retries = 0
            current_plan = plan
            step_index = 0
            while retries <= self.max_retries:
                for offset, step in enumerate(current_plan.steps, start=1):
                    step_index = offset
                    before = self._observe(step_index, "before", step.action)
                    self._emit("agent.step_started", {"objective": objective, "step": step_index,
                        "total": len(current_plan.steps), "action": step.action,
                        "description": step.description, "system_before": self._snapshot_dict(before)})
                    result = self.action_engine.execute(step.action, **step.kwargs)
                    all_results.append(result)
                    after = self._observe(step_index, "after", step.action)
                    verification = self._verify_transition(before, after, result)
                    self._emit("agent.step_finished", {"objective": objective, "step": step_index,
                        "total": len(current_plan.steps), "action": step.action, "success": result.success,
                        "verified": result.verified, "message": result.message,
                        "system_after": self._snapshot_dict(after), "system_change": verification})
                    self.memory.record_event("agent.observation", f"Step {step_index} {step.action}: {verification}", source="agent_engine")

                    if not result.success or not result.verified:
                        if retries >= self.max_retries:
                            return self._failure(objective, current_plan, tuple(all_results), step_index,
                                                  result.message, retries)
                        retries += 1
                        self._emit("agent.recovery_started", {"objective": objective, "step": step_index,
                            "attempt": retries, "error": result.message, "observation": verification})
                        self.memory.record_event("agent.recovery", f"Recovery attempt {retries}: {result.message}", source="agent_engine")
                        try:
                            current_plan = self._make_plan(objective, failure=result.message, observation=verification)
                        except Exception as exc:
                            if retries >= self.max_retries:
                                return self._failure(objective, current_plan, tuple(all_results), step_index, str(exc), retries)
                            continue
                        if current_plan is None or not current_plan.steps:
                            return self._failure(objective, current_plan, tuple(all_results), step_index,
                                                  "La replanification n'a produit aucune étape sûre.", retries)
                        self._emit("agent.replanned", {"objective": objective, "attempt": retries,
                            "steps": [s.action for s in current_plan.steps]})
                        break
                else:
                    self.memory.record_event("agent", f"Agent completed: {objective}", source="agent_engine")
                    self._emit("agent.completed", {"objective": objective, "steps": len(all_results), "recovery_attempts": retries})
                    return AgentRunResult(objective, True, current_plan, tuple(all_results), recovery_attempts=retries)
                continue

            return self._failure(objective, current_plan, tuple(all_results), step_index,
                                  "Nombre maximal de tentatives atteint.", retries)
        finally:
            self._running = False

    def _make_plan(self, objective: str, *, failure: str | None = None, observation: dict[str, Any] | None = None) -> GoalPlan | None:
        if failure is None:
            plan = self.planner.plan(objective)
        else:
            replanning = getattr(self.planner, "replan", None)
            if callable(replanning):
                plan = replanning(objective, failure=failure, observation=observation or {})
            else:
                plan = self.planner.plan(objective)
        self._emit("agent.plan_ready", {"objective": objective, "steps": [s.action for s in plan.steps]})
        self.memory.record_event("agent.plan", f"Plan created with {len(plan.steps)} step(s)", source="agent_engine")
        return plan

    def _observe(self, step: int, phase: str, action: str) -> SystemSnapshot | None:
        if self.observer is None:
            return None
        try:
            snapshot = self.observer.snapshot()
            self._emit("agent.system_observed", {"step": step, "phase": phase, "action": action,
                "snapshot": self._snapshot_dict(snapshot)})
            return snapshot
        except Exception as exc:
            self.memory.record_event("agent.observation", f"Observation failed: {exc}", source="agent_engine")
            return None

    @staticmethod
    def _verify_transition(before: SystemSnapshot | None, after: SystemSnapshot | None, result: ActionResult) -> dict[str, Any]:
        if before is None or after is None:
            return {"available": False, "action_result": result.success}
        return {"available": True, "action_result": result.success,
            "cpu_delta": None if before.cpu_percent is None or after.cpu_percent is None else round(after.cpu_percent - before.cpu_percent, 1),
            "ram_delta": None if before.ram_percent is None or after.ram_percent is None else round(after.ram_percent - before.ram_percent, 1),
            "foreground_changed": (before.active_window, before.active_process) != (after.active_window, after.active_process),
            "before_process": before.active_process, "after_process": after.active_process}

    @staticmethod
    def _snapshot_dict(snapshot: SystemSnapshot | None) -> dict[str, Any] | None:
        return None if snapshot is None else {"timestamp": snapshot.timestamp, "cpu_percent": snapshot.cpu_percent,
            "ram_percent": snapshot.ram_percent, "active_window": snapshot.active_window, "active_process": snapshot.active_process}

    def _failure(self, objective: str, plan: GoalPlan | None, results: tuple[ActionResult, ...], failed_step: int | None,
                 error: str, retries: int) -> AgentRunResult:
        self.memory.record_event("agent", f"Agent failed: {objective} — {error}", source="agent_engine")
        self._emit("agent.failed", {"objective": objective, "failed_step": failed_step, "error": error, "recovery_attempts": retries})
        return AgentRunResult(objective, False, plan, results, failed_step, error, retries)

    def _emit(self, name: str, payload: dict[str, Any]) -> None:
        if self.event_bus is not None:
            from .bus import Event
            self.event_bus.publish(Event(name=name, payload=payload, priority=10))


__all__ = ["AgentEngine", "AgentRunResult"]
