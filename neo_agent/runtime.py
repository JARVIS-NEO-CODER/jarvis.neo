from __future__ import annotations

import threading
from typing import Any, Callable

from .agent_loop import AgentLoop
from .environment import snapshot
from .models import AgentConfig, TaskState
from .ollama import OllamaAdapter
from .settings import AgentSettings


class JarvisAgentRuntime:
    """Runtime for background autonomous tasks, including restart recovery."""

    def __init__(self, config: AgentConfig | None = None, model: str = "qwen2.5:7b", event: Callable[[str, dict[str, Any]], None] | None = None):
        self.settings = AgentSettings()
        self.config = config or self.settings.load()
        self.model = model
        self.event = event
        self.agent = AgentLoop(OllamaAdapter(model=model), config=self.config, event=event)
        self._threads: dict[str, threading.Thread] = {}
        self._lock = threading.RLock()

    def submit(self, goal: str, *, context: dict[str, Any] | None = None, background: bool = True):
        merged = {"environment": snapshot(self.config.cwd)}
        if context:
            merged.update(context)
        task = self.agent.tasks.create(goal, merged)
        if background:
            self._start(task.id)
        else:
            self.agent.run(task.id)
        return task

    def _start(self, task_id: str) -> None:
        with self._lock:
            thread = self._threads.get(task_id)
            if thread and thread.is_alive():
                return
            thread = threading.Thread(target=self._run_thread, args=(task_id,), daemon=True, name=f"jarvis-task-{task_id}")
            self._threads[task_id] = thread
            thread.start()

    def _run_thread(self, task_id: str) -> None:
        try:
            self.agent.run(task_id)
        finally:
            with self._lock:
                self._threads.pop(task_id, None)

    def recover(self) -> list[str]:
        """Resume tasks interrupted by a JARVIS restart."""
        recovered: list[str] = []
        for task in self.agent.tasks.list():
            if task.state in {TaskState.PENDING, TaskState.RUNNING}:
                self._start(task.id)
                recovered.append(task.id)
        return recovered

    def stop(self, task_id: str) -> None:
        self.agent.request_stop(task_id)

    def approve(self, task_id: str):
        return self.agent.approve(task_id)

    def resume(self, task_id: str):
        self._start(task_id)
        return self.agent.tasks.get(task_id)

    def status(self, task_id: str):
        return self.agent.tasks.get(task_id)

    def active_tasks(self):
        with self._lock:
            return [task_id for task_id, thread in self._threads.items() if thread.is_alive()]
