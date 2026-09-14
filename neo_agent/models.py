from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class TaskState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AgentConfig:
    permission_mode: int = 1
    max_steps: int = 40
    max_retries_per_step: int = 2
    cwd: str = "."
    persist_tasks: bool = True
    state_dir: str = ".jarvis/tasks"


@dataclass
class ToolResult:
    ok: bool
    tool: str
    message: str = ""
    data: Any = None
    error: str | None = None
    requires_approval: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AgentDecision:
    """Normalized decision produced by the LLM adapter.

    The LLM is never allowed to execute anything directly. It can only request
    one of these typed actions, which the core validates against the registry.
    """

    kind: str
    tool: str | None = None
    arguments: dict[str, Any] = field(default_factory=dict)
    message: str = ""
    task_status: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
