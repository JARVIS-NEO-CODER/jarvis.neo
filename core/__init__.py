"""Core services for J.A.R.V.I.S. NEO."""

from .memory import NeoMemory
from .action_engine import ActionDefinition, ActionEngine, ActionResult, ControlMode
from .goal_planner import GoalPlan, GoalPlanner, GoalStep, GoalRunResult
from .agent_engine import AgentEngine, AgentRunResult
from .ollama_planner import OllamaPlanner

# The mobile control adapter is installed at core import time so the stable
# launcher can keep using the existing MobileBridge wiring while the mobile
# app gains a richer, explicit PC-control contract.
try:
    from .mobile_control import install as _install_mobile_control
    _install_mobile_control()
except Exception:
    # Mobile control is an optional integration and must never prevent the
    # desktop core from starting if a dependency is temporarily unavailable.
    pass

__all__ = [
    "NeoMemory",
    "ActionDefinition", "ActionEngine", "ActionResult", "ControlMode",
    "GoalPlan", "GoalPlanner", "GoalStep", "GoalRunResult",
    "AgentEngine", "AgentRunResult", "OllamaPlanner",
]
