"""Safe, inspectable goal planning layer for J.A.R.V.I.S. NEO."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from .action_engine import ActionEngine, ActionResult
from .capability_registry import CapabilityRegistry

@dataclass(frozen=True)
class GoalStep:
    action: str; kwargs: dict[str, Any] = field(default_factory=dict); description: str = ""
@dataclass(frozen=True)
class GoalPlan:
    objective: str; steps: tuple[GoalStep, ...]
@dataclass(frozen=True)
class GoalRunResult:
    objective: str; success: bool; results: tuple[ActionResult, ...]; failed_step: int | None = None

class GoalPlanner:
    """Build, validate and replan using the live CapabilityRegistry."""
    def __init__(self, action_engine: ActionEngine, llm_planner: Any | None = None, capabilities: CapabilityRegistry | None = None) -> None:
        self.action_engine=action_engine; self.capabilities=capabilities or action_engine.capabilities; self.llm_planner=llm_planner
    @classmethod
    def with_ollama(cls, action_engine, *, model="llama3.2:3b", base_url="http://127.0.0.1:11434", timeout=60.0):
        from .ollama_planner import OllamaPlanner
        return cls(action_engine, OllamaPlanner(model=model,base_url=base_url,timeout=timeout))
    def available_actions(self): return self.capabilities.names()
    def capability_manifest(self): return self.capabilities.manifest()
    def plan(self, objective):
        objective=objective.strip()
        if not objective: raise ValueError("L'objectif ne peut pas être vide.")
        if "notification" in objective.lower(): return GoalPlan(objective,(GoalStep("action.notify",{"message":objective},"Notifier l'utilisateur."),))
        if self.llm_planner is None: raise ValueError("Aucun planner IA n'est configuré.")
        return self._parse_llm_plan(objective,self.llm_planner.plan(objective,self.capability_manifest()))
    def replan(self, objective, *, failure, observation, attempted_actions=()):
        if self.llm_planner is None or not callable(getattr(self.llm_planner,"replan",None)): raise ValueError("Le planner actuel ne supporte pas la replanification.")
        raw=self.llm_planner.replan(objective.strip(),self.capability_manifest(),failure=failure,observation=observation,attempted_actions=attempted_actions)
        plan=self._parse_llm_plan(objective.strip(),raw)
        if attempted_actions and all(s.action in attempted_actions for s in plan.steps): raise ValueError("La replanification n'a proposé aucune capacité différente.")
        return plan
    def _parse_llm_plan(self,objective,raw):
        raw_steps=raw.get("steps",[]) if isinstance(raw,dict) else raw
        if not isinstance(raw_steps,list) or not raw_steps: raise ValueError("Le plan IA est vide ou invalide.")
        steps=[]
        for item in raw_steps:
            if not isinstance(item,dict): raise ValueError("Étape IA invalide.")
            action=str(item.get("action","")).strip(); cap=self.capabilities.get(action)
            if cap is None: raise ValueError(f"Capacité non enregistrée: {action}")
            kwargs=item.get("kwargs",{})
            if not isinstance(kwargs,dict): raise ValueError(f"Arguments invalides pour {action}.")
            steps.append(GoalStep(action,kwargs,str(item.get("description",""))))
        return GoalPlan(objective,tuple(steps))
    def execute(self,plan):
        results=[]
        for index,step in enumerate(plan.steps,1):
            result=self.action_engine.execute(step.action,**step.kwargs); results.append(result)
            if not result.success or not result.verified: return GoalRunResult(plan.objective,False,tuple(results),index)
        return GoalRunResult(plan.objective,True,tuple(results))
    def run(self,objective): return self.execute(self.plan(objective))

__all__=["GoalPlanner","GoalPlan","GoalStep","GoalRunResult"]
