"""JARVIS NEO agent core.

The package is intentionally independent from the existing HUD/assistant.py so
it can be integrated incrementally without breaking the current application.
"""

from .agent_loop import AgentLoop
from .environment import snapshot
from .models import AgentConfig, AgentDecision, TaskState, ToolResult
from .ollama import OllamaAdapter
from .permissions import PermissionMode, PermissionPolicy
from .runtime import JarvisAgentRuntime
from .settings import AgentSettings
from .task_manager import TaskManager
from .tools import ToolRegistry

__all__ = [
    "AgentConfig",
    "AgentDecision",
    "AgentLoop",
    "AgentSettings",
    "JarvisAgentRuntime",
    "OllamaAdapter",
    "PermissionMode",
    "PermissionPolicy",
    "TaskManager",
    "TaskState",
    "ToolRegistry",
    "ToolResult",
    "snapshot",
]
