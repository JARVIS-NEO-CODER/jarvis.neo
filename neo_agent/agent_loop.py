from __future__ import annotations

import json
from typing import Any, Callable, Protocol

from .models import AgentConfig, AgentDecision, TaskState, ToolResult
from .permissions import PermissionPolicy
from .task_manager import Task, TaskManager
from .tools import ToolRegistry


class LLMAdapter(Protocol):
    def decide(self, context: dict[str, Any]) -> dict[str, Any] | str: ...


class AgentLoop:
    """Goal -> decision -> tool -> observation -> decision loop."""

    def __init__(self, llm: LLMAdapter, config: AgentConfig | None = None, tools: ToolRegistry | None = None, tasks: TaskManager | None = None, event: Callable[[str, dict[str, Any]], None] | None = None):
        self.config = config or AgentConfig()
        self.policy = PermissionPolicy(self.config.permission_mode)
        self.tools = tools or ToolRegistry(self.policy, self.config.cwd)
        self.tasks = tasks or TaskManager(self.config.state_dir)
        self.llm = llm
        self.event = event
        self._stop_requested: set[str] = set()

    def start(self, goal: str, context: dict[str, Any] | None = None) -> Task:
        task = self.tasks.create(goal, context)
        self.run(task.id)
        return task

    def request_stop(self, task_id: str) -> None:
        self._stop_requested.add(task_id)
        task = self.tasks.get(task_id)
        if task and task.state not in {TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED}:
            self.tasks.update(task, TaskState.CANCELLED)
            self.tasks.save_event(task, "stop_requested")

    def resume(self, task_id: str) -> Task | None:
        task = self.tasks.get(task_id)
        if task is None or task.state in {TaskState.COMPLETED, TaskState.CANCELLED}:
            return task
        self._stop_requested.discard(task_id)
        self.run(task_id)
        return task

    def approve(self, task_id: str) -> Task | None:
        task = self.tasks.get(task_id)
        if task is None:
            return None
        pending = task.context.pop("pending_tool", None)
        if not pending:
            self.tasks.save_event(task, "approval_ignored", reason="no pending tool")
            return task
        self.tasks.save_event(task, "approval_granted", tool=pending["tool"])
        result = self.tools.execute(pending["tool"], pending["arguments"], approved=True)
        self._record_result(task, result)
        self._apply_result(task, result)
        self.tasks.update(task, TaskState.RUNNING)
        self.run(task_id)
        return task

    def run(self, task_id: str) -> Task | None:
        task = self.tasks.get(task_id)
        if task is None or task.state in {TaskState.COMPLETED, TaskState.CANCELLED}:
            return task
        self.tasks.update(task, TaskState.RUNNING)
        self._emit("task.started", task)

        for _ in range(self.config.max_steps):
            if task.id in self._stop_requested:
                self.tasks.update(task, TaskState.CANCELLED)
                self.tasks.save_event(task, "cancelled")
                break

            context = self._build_context(task)
            try:
                decision = self._normalize_decision(self.llm.decide(context))
            except Exception as exc:
                task.retries += 1
                self.tasks.save_event(task, "decision_error", error=str(exc))
                if task.retries > self.config.max_retries_per_step:
                    self.tasks.update(task, TaskState.FAILED)
                    break
                continue

            self.tasks.save_event(task, "decision", decision=decision.to_dict())

            if decision.kind == "finish":
                task.context["result"] = decision.message
                self.tasks.update(task, TaskState.COMPLETED)
                self.tasks.save_event(task, "completed", result=decision.message)
                break

            if decision.kind == "wait":
                task.context["waiting_message"] = decision.message
                self.tasks.update(task, TaskState.WAITING_APPROVAL)
                self.tasks.save_event(task, "waiting", message=decision.message)
                break

            if decision.kind != "tool" or not decision.tool:
                task.retries += 1
                self.tasks.save_event(task, "invalid_decision", reason="expected tool, finish or wait")
                if task.retries > self.config.max_retries_per_step:
                    self.tasks.update(task, TaskState.FAILED)
                    break
                continue

            result = self.tools.execute(decision.tool, decision.arguments, approved=False)
            self._record_result(task, result)
            if result.requires_approval:
                task.context["pending_tool"] = {"tool": decision.tool, "arguments": decision.arguments}
                self.tasks.update(task, TaskState.WAITING_APPROVAL)
                break
            self._apply_result(task, result)
            self.tasks.update(task, TaskState.RUNNING)
        else:
            self.tasks.update(task, TaskState.FAILED)
            self.tasks.save_event(task, "step_limit", max_steps=self.config.max_steps)

        self._emit("task.updated", task)
        return task

    def _apply_result(self, task: Task, result: ToolResult) -> None:
        task.step += 1
        task.retries = 0
        if result.ok:
            task.context["last_result"] = result.data
            task.context.pop("last_error", None)
        else:
            task.context["last_error"] = result.error or result.message

    def _record_result(self, task: Task, result: ToolResult) -> None:
        self.tasks.save_event(task, "tool_result", result=result.to_dict())

    def _build_context(self, task: Task) -> dict[str, Any]:
        return {
            "goal": task.goal,
            "task_id": task.id,
            "step": task.step,
            "state": task.state.value,
            "context": task.context,
            "recent_history": task.history[-12:],
            "available_tools": self.tools.describe(),
            "agent_rules": [
                "Never claim a tool succeeded when its result is an error.",
                "Use tools instead of inventing files, programs, web results or system state.",
                "If the goal is ambiguous, ask for clarification instead of guessing.",
                "After meaningful actions, inspect or test the result and correct failures.",
                "Do not repeat an identical failed action without a changed approach.",
                "Finish only when the requested goal is actually achieved or impossible.",
            ],
        }

    @staticmethod
    def _normalize_decision(raw: dict[str, Any] | str) -> AgentDecision:
        if isinstance(raw, str):
            raw = json.loads(raw)
        if not isinstance(raw, dict):
            raise ValueError("LLM decision must be a JSON object")
        kind = str(raw.get("kind", "")).strip().lower()
        if kind not in {"tool", "finish", "wait"}:
            raise ValueError("Unknown decision kind")
        arguments = raw.get("arguments", {})
        if not isinstance(arguments, dict):
            raise ValueError("Tool arguments must be an object")
        return AgentDecision(kind=kind, tool=raw.get("tool"), arguments=arguments, message=str(raw.get("message", "")), task_status=raw.get("task_status"))

    def _emit(self, event: str, task: Task) -> None:
        if self.event:
            try:
                self.event(event, {"task": task.to_dict()})
            except Exception:
                pass
