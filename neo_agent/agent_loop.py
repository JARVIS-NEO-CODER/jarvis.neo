from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any, Callable, Protocol

from .models import AgentConfig, AgentDecision, TaskState, ToolResult
from .permissions import PermissionPolicy
from .task_manager import Task, TaskManager
from .tools import ToolRegistry


class LLMAdapter(Protocol):
    def decide(self, context: dict[str, Any]) -> dict[str, Any] | str: ...


class AgentLoop:
    """Goal -> decision -> tool -> observation -> decision loop.

    The LLM is treated as an untrusted planner. It cannot call Python directly;
    every requested operation passes through ToolRegistry and PermissionPolicy.
    """

    def __init__(
        self,
        llm: LLMAdapter,
        config: AgentConfig | None = None,
        tools: ToolRegistry | None = None,
        tasks: TaskManager | None = None,
        event: Callable[[str, dict[str, Any]], None] | None = None,
    ):
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
        if task is None:
            return None
        if task.state in {TaskState.COMPLETED, TaskState.CANCELLED}:
            return task
        self.run(task_id)
        return task

    def approve(self, task_id: str) -> Task | None:
        """Resume a task after an approval-gated tool call.

        The actual approval token is consumed by the next requested action via
        task context, keeping the UI layer separate from the execution layer.
        """
        task = self.tasks.get(task_id)
        if task is None:
            return None
        task.context["approval_granted"] = True
        self.tasks.save_event(task, "approval_granted")
        self.run(task_id)
        return task

    def run(self, task_id: str) -> Task | None:
        task = self.tasks.get(task_id)
        if task is None:
            return None
        if task.state in {TaskState.COMPLETED, TaskState.CANCELLED}:
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
                raw = self.llm.decide(context)
                decision = self._normalize_decision(raw)
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

            approved = bool(task.context.pop("approval_granted", False))
            result = self.tools.execute(decision.tool, decision.arguments, approved=approved)
            self._record_result(task, result)

            if result.requires_approval:
                task.context["pending_tool"] = {
                    "tool": decision.tool,
                    "arguments": decision.arguments,
                }
                self.tasks.update(task, TaskState.WAITING_APPROVAL)
                break

            task.step += 1
            task.retries = 0
            if not result.ok:
                # Feed the failure back into the next model decision instead of
                # crashing or silently pretending the action succeeded.
                task.context["last_error"] = result.error
            else:
                task.context["last_result"] = result.data

            self.tasks.update(task, TaskState.RUNNING)
        else:
            self.tasks.update(task, TaskState.FAILED)
            self.tasks.save_event(task, "step_limit", max_steps=self.config.max_steps)

        self._emit("task.updated", task)
        return task

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
                "After meaningful actions, inspect the result and correct failures.",
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
        return AgentDecision(
            kind=kind,
            tool=raw.get("tool"),
            arguments=arguments,
            message=str(raw.get("message", "")),
            task_status=raw.get("task_status"),
        )

    def _emit(self, event: str, task: Task) -> None:
        if self.event:
            try:
                self.event(event, {"task": asdict(task)})
            except Exception:
                pass
