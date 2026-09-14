"""Core services for J.A.R.V.I.S. NEO."""

from .memory import NeoMemory
from .action_engine import ActionDefinition, ActionEngine, ActionResult, ControlMode
from .goal_planner import GoalPlan, GoalPlanner, GoalStep, GoalRunResult
from .agent_engine import AgentEngine, AgentRunResult
from .ollama_planner import OllamaPlanner

try:
    from .mobile_control import install as _install_mobile_control
    _install_mobile_control()
except Exception:
    pass

try:
    from .hud import install as _install_hud
    _install_hud()
except Exception:
    pass

# Install the autonomous natural-language bridge before assistant.py creates
# its CommandProcessor instance. Legacy explicit intents remain unchanged.
try:
    from neo_agent.desktop_bridge import install as _install_desktop_agent
    _install_desktop_agent()
except Exception:
    pass

__all__ = [
    "NeoMemory",
    "ActionDefinition", "ActionEngine", "ActionResult", "ControlMode",
    "GoalPlan", "GoalPlanner", "GoalStep", "GoalRunResult",
    "AgentEngine", "AgentRunResult", "OllamaPlanner",
]
