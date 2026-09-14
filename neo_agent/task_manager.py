from __future__ import annotations

import json
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import TaskState


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Task:
    id: str
    goal: str
    state: TaskState = TaskState.PENDING
    step: int = 0
    retries: int = 0
    context: dict[str, Any] = field(default_factory=dict)
    history: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def record(self, event: str, **data: Any) -> None:
        self.history.append({"time": _now(), "event": event, **data})
        self.updated_at = _now()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["state"] = self.state.value
        return data


class TaskManager:
    """Persistent task state so long-running work can survive restarts."""

    def __init__(self, state_dir: str = ".jarvis/tasks"):
        self.root = Path(state_dir)
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._tasks: dict[str, Task] = {}
        self._load()

    def create(self, goal: str, context: dict[str, Any] | None = None) -> Task:
        task = Task(uuid.uuid4().hex[:12], goal, context=context or {})
        task.record("created", goal=goal)
        with self._lock:
            self._tasks[task.id] = task
            self._save(task)
        return task

    def get(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)

    def update(self, task: Task, state: TaskState | None = None, **changes: Any) -> None:
        with self._lock:
            if state is not None:
                task.state = state
            for key, value in changes.items():
                if hasattr(task, key):
                    setattr(task, key, value)
            task.updated_at = _now()
            self._save(task)

    def save_event(self, task: Task, event: str, **data: Any) -> None:
        with self._lock:
            task.record(event, **data)
            self._save(task)

    def cancel(self, task_id: str) -> bool:
        task = self.get(task_id)
        if task is None:
            return False
        self.update(task, TaskState.CANCELLED)
        self.save_event(task, "cancelled")
        return True

    def list(self) -> list[Task]:
        return sorted(self._tasks.values(), key=lambda t: t.updated_at, reverse=True)

    def _save(self, task: Task) -> None:
        target = self.root / f"{task.id}.json"
        temp = target.with_suffix(".tmp")
        temp.write_text(json.dumps(task.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(target)

    def _load(self) -> None:
        for path in self.root.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                data["state"] = TaskState(data.get("state", TaskState.PENDING.value))
                task = Task(**data)
                self._tasks[task.id] = task
            except Exception:
                # A corrupted task must not prevent JARVIS from starting.
                continue
