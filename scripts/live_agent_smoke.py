from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

from neo_agent.agent_loop import AgentLoop
from neo_agent.models import AgentConfig, TaskState
from neo_agent.ollama import OllamaAdapter
from neo_agent.permissions import PermissionPolicy
from neo_agent.task_manager import TaskManager
from neo_agent.tools import ToolRegistry


MARKER = "BLACK_HALO_LIVE_TEST_OK_2026"


def _inside_sandbox(root: Path, supplied: str) -> Path:
    candidate = (root / supplied).resolve() if not Path(supplied).is_absolute() else Path(supplied).resolve()
    if candidate != root and root not in candidate.parents:
        raise PermissionError("Test runner only allows paths inside its temporary sandbox")
    return candidate


def build_safe_registry(root: Path) -> ToolRegistry:
    """Expose only sandboxed file operations; no shell, browser, delete or network."""
    policy = PermissionPolicy(mode=2)
    registry = ToolRegistry(policy=policy, cwd=str(root))
    registry._tools.clear()

    def write(path: str, content: str) -> dict[str, Any]:
        target = _inside_sandbox(root, path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return {"path": str(target), "bytes": target.stat().st_size}

    def read(path: str, max_chars: int = 100_000) -> str:
        target = _inside_sandbox(root, path)
        return target.read_text(encoding="utf-8")[:max(1, min(int(max_chars), 500_000))]

    def list_dir(path: str = ".") -> list[str]:
        target = _inside_sandbox(root, path)
        return sorted(item.name + ("/" if item.is_dir() else "") for item in target.iterdir())[:100]

    registry.register("filesystem.write", "Create a UTF-8 text file inside the isolated test folder", "filesystem.write", write)
    registry.register("filesystem.read", "Read a UTF-8 text file inside the isolated test folder", "filesystem.read", read)
    registry.register("filesystem.list", "List files inside the isolated test folder", "filesystem.read", list_dir)
    return registry


def run_live_test(model: str, host: str) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="black-halo-live-test-") as temporary:
        root = Path(temporary).resolve()
        state_dir = root / ".task-state"
        config = AgentConfig(
            permission_mode=2,
            max_steps=12,
            max_retries_per_step=1,
            cwd=str(root),
            state_dir=str(state_dir),
            persist_tasks=False,
        )
        agent = AgentLoop(
            llm=OllamaAdapter(model=model, host=host),
            config=config,
            tools=build_safe_registry(root),
            tasks=TaskManager(str(state_dir)),
        )
        goal = (
            "Dans le dossier de test isolé, crée le fichier live_check.txt avec exactement "
            f"le texte {MARKER}. Ensuite, relis le fichier pour vérifier son contenu. "
            "N'annonce la réussite qu'après cette vérification."
        )
        task = agent.start(goal)
        target = root / "live_check.txt"
        file_exists = target.is_file()
        actual_content = target.read_text(encoding="utf-8") if file_exists else None
        verified = task.state == TaskState.COMPLETED and actual_content == MARKER
        return {
            "goal": goal,
            "model": model,
            "host": host,
            "state": task.state.value,
            "steps": task.step,
            "tool_events": [
                event.get("result", {})
                for event in task.history
                if event.get("event") == "tool_result"
            ],
            "file_exists": file_exists,
            "expected_content": MARKER,
            "actual_content": actual_content,
            "passed": verified,
            "note": "This runs the real local Ollama model against a sandboxed tool set; it does not test the full GUI/HUD.",
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a real Black Halo agent request against local Ollama in a safe sandbox.")
    parser.add_argument("--model", default="llama3.2:3b", help="Installed Ollama model name (default: llama3.2:3b)")
    parser.add_argument("--host", default="http://127.0.0.1:11434", help="Ollama HTTP endpoint")
    args = parser.parse_args()

    try:
        report = run_live_test(args.model, args.host)
    except Exception as exc:
        report = {
            "passed": False,
            "error": f"{type(exc).__name__}: {exc}",
            "hint": "Check that Ollama is running and the selected model is installed.",
        }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("passed") else 1


if __name__ == "__main__":
    sys.exit(main())
