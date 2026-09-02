"""Goal-oriented execution loop with bounded recovery, budget control and verification."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable
from .action_engine import ActionEngine, ActionResult
from .goal_planner import GoalPlan, GoalPlanner
from .goal_verifier import GoalVerification, GoalVerifier
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
    verification: GoalVerification | None = None
    ia_calls: int = 0

class AgentEngine:
    """Coordinate plan -> execute -> observe -> verify objective -> recover."""
    def __init__(self, action_engine: ActionEngine, planner: GoalPlanner | None = None, memory: NeoMemory | None = None,
                 event_bus: Any | None = None, observer: SystemObserver | None = None,
                 verifier: GoalVerifier | None = None, max_retries: int = 3,
                 max_steps: int = 15, max_ia_calls: int = 30) -> None:
        self.action_engine = action_engine
        self.planner = planner or GoalPlanner(action_engine)
        self.memory = memory or action_engine.memory
        self.event_bus = event_bus
        self.observer = observer or (SystemObserver(event_bus) if event_bus is not None else None)
        self.verifier = verifier or GoalVerifier()
        self.max_retries = max(0, int(max_retries))
        self.max_steps = max(1, int(max_steps))
        self.max_ia_calls = max(1, int(max_ia_calls))
        self._running = False
        self.ia_calls = 0

    @property
    def running(self) -> bool: return self._running

    def estimate_budget(self, objective: str) -> dict[str, int | str]:
        """Return a conservative warning before an agent run starts."""
        try:
            plan = self.planner.plan(objective.strip())
            steps = len(plan.steps)
        except Exception:
            steps = min(5, self.max_steps)
        estimated_calls = min(self.max_ia_calls, max(1, steps * 2 + self.max_retries))
        level = "faible" if estimated_calls <= 5 else "moyenne" if estimated_calls <= 15 else "élevée"
        return {"estimated_steps": steps, "estimated_ia_calls": estimated_calls, "risk": level}

    def run(self, objective: str, *, confirm: Callable[[GoalPlan], bool] | None = None,
            budget_confirm: Callable[[dict[str, int | str]], bool] | None = None) -> AgentRunResult:
        objective = objective.strip()
        if not objective: raise ValueError("L'objectif ne peut pas être vide.")
        if self._running: raise RuntimeError("Un agent est déjà en cours d'exécution.")
        self._running = True
        self.ia_calls = 0
        self._emit("agent.started", {"objective": objective})
        self.memory.record_event("agent", f"Agent started: {objective}", source="agent_engine")
        try:
            budget = self.estimate_budget(objective)
            self._emit("agent.budget_warning", {"objective": objective, **budget})
            if budget_confirm is not None and not budget_confirm(budget):
                return self._failure(objective, None, (), None, "Exécution Agent annulée à cause du budget IA.", 0, None)
            plan = self._make_plan(objective)
            if plan is None: return self._failure(objective, None, (), None, "Impossible de créer un plan.", 0, None)
            if len(plan.steps) > self.max_steps:
                return self._failure(objective, plan, (), None, f"Plan trop long: {len(plan.steps)} étapes, maximum {self.max_steps}.", 0, None)
            if confirm is not None and not confirm(plan):
                return self._failure(objective, plan, (), None, "Plan refusé par l'utilisateur.", 0, None)
            all_results: list[ActionResult] = []
            retries = 0
            current_plan = plan
            attempted_actions: list[str] = []
            last_verification: GoalVerification | None = None
            while retries <= self.max_retries:
                replanned = False
                for step_index, step in enumerate(current_plan.steps, start=1):
                    if self.ia_calls >= self.max_ia_calls:
                        return self._failure(objective, current_plan, tuple(all_results), step_index, "Budget maximal d'appels IA atteint.", retries, last_verification)
                    before = self._observe(step_index, "before", step.action)
                    self._emit("agent.step_started", {"objective": objective, "step": step_index, "total": len(current_plan.steps), "action": step.action, "description": step.description, "system_before": self._snapshot_dict(before)})
                    result = self.action_engine.execute(step.action, **step.kwargs)
                    self.ia_calls += 1
                    all_results.append(result)
                    attempted_actions.append(step.action)
                    after = self._observe(step_index, "after", step.action)
                    transition = self._verify_transition(before, after, result)
                    last_verification = self.verifier.verify(objective, before=before, after=after, action_success=result.success, action_verified=result.verified)
                    self._emit("agent.objective_verified", {"objective": objective, "step": step_index, "achieved": last_verification.achieved, "confidence": last_verification.confidence, "reason": last_verification.reason, "evidence": last_verification.evidence})
                    self._emit("agent.step_finished", {"objective": objective, "step": step_index, "total": len(current_plan.steps), "action": step.action, "success": result.success, "verified": result.verified, "message": result.message, "system_after": self._snapshot_dict(after), "system_change": transition, "objective_achieved": last_verification.achieved, "verification_confidence": last_verification.confidence})
                    if last_verification.achieved:
                        self.memory.record_event("agent", f"Agent objective achieved: {objective}", source="agent_engine")
                        self._emit("agent.completed", {"objective": objective, "steps": len(all_results), "recovery_attempts": retries, "ia_calls": self.ia_calls, "verification": last_verification.evidence})
                        return AgentRunResult(objective, True, current_plan, tuple(all_results), recovery_attempts=retries, verification=last_verification, ia_calls=self.ia_calls)
                    if not result.success or not result.verified or step_index == len(current_plan.steps):
                        if retries >= self.max_retries:
                            return self._failure(objective, current_plan, tuple(all_results), step_index, last_verification.reason, retries, last_verification)
                        retries += 1
                        self._emit("agent.recovery_started", {"objective": objective, "step": step_index, "attempt": retries, "error": result.message, "verification": last_verification.evidence})
                        try:
                            current_plan = self.planner.replan(objective, failure=last_verification.reason, observation={**transition, "verification": last_verification.evidence}, attempted_actions=tuple(attempted_actions))
                            self.ia_calls += 1
                        except Exception as exc:
                            if retries >= self.max_retries: return self._failure(objective, current_plan, tuple(all_results), step_index, str(exc), retries, last_verification)
                            continue
                        if not current_plan.steps: return self._failure(objective, current_plan, tuple(all_results), step_index, "La replanification n'a produit aucune étape sûre.", retries, last_verification)
                        if len(current_plan.steps) > self.max_steps: return self._failure(objective, current_plan, tuple(all_results), step_index, "La replanification dépasse le budget d'étapes.", retries, last_verification)
                        self._emit("agent.replanned", {"objective": objective, "attempt": retries, "steps": [s.action for s in current_plan.steps]})
                        replanned = True
                        break
                if not replanned:
                    return self._failure(objective, current_plan, tuple(all_results), None, "Le plan est terminé mais l'objectif n'est pas vérifié.", retries, last_verification)
            return self._failure(objective, current_plan, tuple(all_results), None, "Nombre maximal de tentatives atteint.", retries, last_verification)
        finally:
            self._running = False

    def _make_plan(self, objective: str) -> GoalPlan | None:
        plan = self.planner.plan(objective)
        self.ia_calls += 1
        self._emit("agent.plan_ready", {"objective": objective, "steps": [s.action for s in plan.steps]})
        self.memory.record_event("agent.plan", f"Plan created with {len(plan.steps)} step(s)", source="agent_engine")
        return plan

    def _observe(self, step: int, phase: str, action: str) -> SystemSnapshot | None:
        if self.observer is None: return None
        try:
            snapshot = self.observer.snapshot()
            self._emit("agent.system_observed", {"step": step, "phase": phase, "action": action, "snapshot": self._snapshot_dict(snapshot)})
            return snapshot
        except Exception as exc:
            self.memory.record_event("agent.observation", f"Observation failed: {exc}", source="agent_engine")
            return None

    @staticmethod
    def _verify_transition(before, after, result):
        if before is None or after is None: return {"available": False, "action_result": result.success}
        return {"available": True, "action_result": result.success, "cpu_delta": None if before.cpu_percent is None or after.cpu_percent is None else round(after.cpu_percent - before.cpu_percent, 1), "ram_delta": None if before.ram_percent is None or after.ram_percent is None else round(after.ram_percent - before.ram_percent, 1), "foreground_changed": (before.active_window, before.active_process) != (after.active_window, after.active_process), "before_process": before.active_process, "after_process": after.active_process}

    @staticmethod
    def _snapshot_dict(snapshot):
        return None if snapshot is None else {"timestamp": snapshot.timestamp, "cpu_percent": snapshot.cpu_percent, "ram_percent": snapshot.ram_percent, "active_window": snapshot.active_window, "active_process": snapshot.active_process}

    def _failure(self, objective, plan, results, failed_step, error, retries, verification):
        self.memory.record_event("agent", f"Agent failed: {objective} — {error}", source="agent_engine")
        self._emit("agent.failed", {"objective": objective, "failed_step": failed_step, "error": error, "recovery_attempts": retries, "ia_calls": self.ia_calls, "verification": None if verification is None else verification.evidence})
        return AgentRunResult(objective, False, plan, results, failed_step, error, retries, verification, self.ia_calls)

    def _emit(self, name: str, payload: dict[str, Any]) -> None:
        if self.event_bus is not None:
            from .bus import Event
            self.event_bus.publish(Event(name=name, payload=payload, priority=10))

__all__ = ["AgentEngine", "AgentRunResult"]
