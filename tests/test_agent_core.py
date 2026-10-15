from pathlib import Path

from neo_agent.agent_loop import AgentLoop
from neo_agent.models import AgentConfig, TaskState
from neo_agent.permissions import PermissionMode, PermissionPolicy
from neo_agent.task_manager import TaskManager
from neo_agent.tools import ToolRegistry


class FakeLLM:
    def __init__(self, decisions):
        self.decisions = iter(decisions)

    def decide(self, context):
        return next(self.decisions)


def test_mode_three_skips_routine_approval():
    policy = PermissionPolicy(PermissionMode.UNRESTRICTED)
    tools = ToolRegistry(policy)
    result = tools.execute("filesystem.write", {"path": "x.txt", "content": "ok"})
    assert result.ok


def test_prudent_mode_requests_approval_for_delete(tmp_path):
    target = tmp_path / "x.txt"
    target.write_text("x", encoding="utf-8")
    policy = PermissionPolicy(PermissionMode.PRUDENT)
    tools = ToolRegistry(policy, str(tmp_path))
    result = tools.execute("filesystem.delete", {"path": "x.txt"})
    assert not result.ok
    assert result.requires_approval
    assert target.exists()


def test_task_survives_reload(tmp_path):
    manager = TaskManager(str(tmp_path))
    task = manager.create("test")
    manager.update(task, TaskState.RUNNING)

    restored = TaskManager(str(tmp_path)).get(task.id)
    assert restored is not None
    assert restored.goal == "test"
    assert restored.state == TaskState.RUNNING


def test_agent_finishes_after_tool(tmp_path):
    manager = TaskManager(str(tmp_path / "tasks"))
    config = AgentConfig(permission_mode=PermissionMode.UNRESTRICTED, cwd=str(tmp_path), state_dir=str(tmp_path / "tasks"))
    tools = ToolRegistry(PermissionPolicy(config.permission_mode), str(tmp_path))
    llm = FakeLLM([
        {"kind": "tool", "tool": "filesystem.write", "arguments": {"path": "hello.txt", "content": "hello"}},
        {"kind": "tool", "tool": "filesystem.read", "arguments": {"path": "hello.txt"}},
        {"kind": "finish", "message": "done"},
    ])
    agent = AgentLoop(llm, config=config, tools=tools, tasks=manager)
    task = agent.start("create hello")
    assert task.state == TaskState.COMPLETED
    assert Path(tmp_path / "hello.txt").read_text(encoding="utf-8") == "hello"



def test_agent_cannot_claim_completion_after_a_failed_tool(tmp_path):
    manager = TaskManager(str(tmp_path / "tasks"))
    config = AgentConfig(
        permission_mode=PermissionMode.UNRESTRICTED,
        cwd=str(tmp_path),
        state_dir=str(tmp_path / "tasks"),
        max_retries_per_step=2,
    )
    tools = ToolRegistry(PermissionPolicy(config.permission_mode), str(tmp_path))
    llm = FakeLLM([
        {"kind": "tool", "tool": "filesystem.read", "arguments": {"path": "missing.txt"}},
        {"kind": "finish", "message": "Everything succeeded."},
        {"kind": "finish", "message": "Everything succeeded."},
        {"kind": "finish", "message": "Everything succeeded."},
    ])
    agent = AgentLoop(llm, config=config, tools=tools, tasks=manager)
    task = agent.start("Read missing.txt and report the result")

    assert task.state == TaskState.FAILED
    assert task.context.get("last_error")
    assert any(item["event"] == "finish_rejected_unverified" for item in task.history)
    assert not any(item["event"] == "completed" for item in task.history)
