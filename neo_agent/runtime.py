from __future__ import annotations

import threading
from typing import Any, Callable

from .agent_loop import AgentLoop
from .environment import snapshot
from .models import AgentConfig
from .ollama import OllamaAdapter
from .settings import AgentSettings


class JarvisAgentRuntime:
    """Convenience runtime for wiring the new core into the existing HUD later."""

    def __init__(
        self,
        config: AgentConfig | None = None,
        model: str = "qwen2.5:7b",
        event: Callable[[str, dict[str, Any]], None] | None = None,
    ):
        self.settings = AgentSettings()
        self.config = config or self.settings.load()
        self.model = model
        self.event = event
        self.agent = AgentLoop(
            OllamaAdapter(model=model),
            config=self.config,
            event=event,
        )
        self._threads: dict[str, threading.Thread] = {}

    def submit(self, goal: str, *, context: dict[str, Any] | None = None, background: bool = True):
        merged = {"environment": snapshot(self.config.cwd)}
        if context:
            merged.update(context)
        task = self.agent.tasks.create(goal, merged)
        if background:
            thread = threading.Thread(target=self.agent.run, args=(task.id,), daemon=True, name=f"jarvis-task-{task.id}")
            self._threads[task.id] = thread
            thread.start()
        else:
            self.agent.run(task.id)
        return task

    def stop(self, task_id: str) -> None:
        self.agent.request_stop(task_id)

    def approve(self, task_id: str):
        return self.agent.approve(task_id)

    def resume(self, task_id: str):
        return self.agent.resume(task_id)
