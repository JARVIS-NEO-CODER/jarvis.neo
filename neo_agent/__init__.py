"""JARVIS NEO agent core.

The package is intentionally independent from the existing HUD/assistant.py so
it can be integrated incrementally without breaking the current application.
"""

from .agent_loop import AgentLoop
from .models import AgentConfig, AgentDecision, TaskState, ToolResult
from .permissions import PermissionMode, PermissionPolicy
from .task_manager import TaskManager
from .tools import ToolRegistry

__all__ = [
    "AgentConfig",
    "AgentDecision",
    "AgentLoop",
    "PermissionMode",
    "PermissionPolicy",
    "TaskManager",
    "TaskState",
    "ToolRegistry",
    "ToolResult",
]
