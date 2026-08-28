"""Bridge between goal execution and local context memory."""
from __future__ import annotations

from typing import Any


class GoalContextBridge:
    def __init__(self, goal_engine: Any, context_memory: Any) -> None:
        self.goal_engine = goal_engine
        self.context_memory = context_memory

    def run_objective(self, objective: str) -> Any:
        self.context_memory.record("goal.started", {"objective": objective})
        goal = self.goal_engine.create_goal(objective)
        result = self.goal_engine.run(goal)
        self.context_memory.record(
            "goal.completed" if result.status.value == "completed" else "goal.failed",
            {"objective": objective, "status": result.status.value},
        )
        return result


__all__ = ["GoalContextBridge"]
