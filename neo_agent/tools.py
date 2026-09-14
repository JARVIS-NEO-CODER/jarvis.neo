from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .models import ToolResult
from .permissions import PermissionPolicy


@dataclass
class ToolSpec:
    name: str
    description: str
    permission: str
    handler: Callable[..., Any]


class ToolRegistry:
    """Registry and executor for JARVIS capabilities.

    Tools are ordinary Python callables. The LLM only gets tool names,
    descriptions and JSON arguments. The registry validates permissions and
    normalizes errors before anything reaches Python.
    """

    def __init__(self, policy: PermissionPolicy | None = None, cwd: str = "."):
        self.policy = policy or PermissionPolicy()
        self.cwd = Path(cwd).resolve()
        self._tools: dict[str, ToolSpec] = {}
        self._register_builtin_tools()

    def register(self, name: str, description: str, permission: str, handler: Callable[..., Any]) -> None:
        if not name or "." not in name:
            raise ValueError("Tool name must use a namespace, e.g. filesystem.read")
        self._tools[name] = ToolSpec(name, description, permission, handler)

    def describe(self) -> list[dict[str, str]]:
        return [
            {"name": t.name, "description": t.description, "permission": t.permission}
            for t in self._tools.values()
        ]

    def execute(self, name: str, arguments: dict[str, Any] | None = None, *, approved: bool = False) -> ToolResult:
        arguments = arguments or {}
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult(False, name, error="unknown_tool")
        if not isinstance(arguments, dict):
            return ToolResult(False, name, error="invalid_arguments")
        if not self.policy.allowed(tool.permission):
            return ToolResult(False, name, error="permission_denied")
        if self.policy.requires_approval(tool.permission) and not approved:
            return ToolResult(
                False,
                name,
                message="Cette action nécessite une approbation.",
                requires_approval=True,
                error="approval_required",
            )
        try:
            value = tool.handler(**arguments)
            return ToolResult(True, name, message="ok", data=value)
        except TypeError as exc:
            return ToolResult(False, name, error=f"invalid_arguments: {exc}")
        except Exception as exc:
            return ToolResult(False, name, error=f"execution_error: {type(exc).__name__}: {exc}")

    def _safe_path(self, path: str) -> Path:
        candidate = Path(path).expanduser()
        if not candidate.is_absolute():
            candidate = self.cwd / candidate
        return candidate.resolve()

    def _register_builtin_tools(self) -> None:
        self.register("filesystem.list", "Lister un dossier", "filesystem.read", self._list)
        self.register("filesystem.read", "Lire un fichier texte", "filesystem.read", self._read)
        self.register("filesystem.write", "Créer ou remplacer un fichier texte", "filesystem.write", self._write)
        self.register("filesystem.search", "Rechercher des fichiers par nom", "filesystem.read", self._search)
        self.register("filesystem.delete", "Supprimer un fichier", "filesystem.delete", self._delete)
        self.register("system.run_command", "Exécuter une commande sans shell", "system.run_command", self._run_command)

    def _list(self, path: str = ".") -> list[str]:
        p = self._safe_path(path)
        return sorted(item.name + ("/" if item.is_dir() else "") for item in p.iterdir())

    def _read(self, path: str, max_chars: int = 100_000) -> str:
        p = self._safe_path(path)
        return p.read_text(encoding="utf-8")[:max_chars]

    def _write(self, path: str, content: str) -> dict[str, Any]:
        p = self._safe_path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return {"path": str(p), "bytes": p.stat().st_size}

    def _search(self, query: str, path: str = ".", max_results: int = 100) -> list[str]:
        root = self._safe_path(path)
        needle = query.lower()
        results: list[str] = []
        for item in root.rglob("*"):
            if len(results) >= max_results:
                break
            if needle in item.name.lower():
                results.append(str(item.relative_to(root)))
        return results

    def _delete(self, path: str) -> dict[str, str]:
        p = self._safe_path(path)
        if p.is_dir():
            raise IsADirectoryError("Refusing to delete directories with filesystem.delete")
        p.unlink()
        return {"deleted": str(p)}

    def _run_command(self, command: str | list[str], timeout: int = 60) -> dict[str, Any]:
        argv = shlex.split(command, posix=False) if isinstance(command, str) else [str(x) for x in command]
        if not argv:
            raise ValueError("Empty command")
        completed = subprocess.run(
            argv,
            cwd=str(self.cwd),
            shell=False,
            capture_output=True,
            text=True,
            timeout=max(1, min(timeout, 300)),
        )
        return {
            "returncode": completed.returncode,
            "stdout": completed.stdout[-20_000:],
            "stderr": completed.stderr[-20_000:],
        }
