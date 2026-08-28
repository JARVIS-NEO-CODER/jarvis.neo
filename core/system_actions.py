"""Concrete, safety-oriented system actions for J.A.R.V.I.S. NEO."""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


class SystemActions:
    """Small explicit adapters that can be registered by DeepActionEngine."""

    @staticmethod
    def launch_program(command: str, *args: str) -> dict[str, Any]:
        process = subprocess.Popen([command, *args])
        return {"success": True, "pid": process.pid, "command": command}

    @staticmethod
    def list_directory(path: str) -> dict[str, Any]:
        directory = Path(path).expanduser().resolve()
        if not directory.is_dir():
            return {"success": False, "error": f"Directory not found: {directory}"}
        items = [
            {"name": item.name, "type": "directory" if item.is_dir() else "file"}
            for item in directory.iterdir()
        ]
        return {"success": True, "path": str(directory), "items": items}

    @staticmethod
    def copy_file(source: str, destination: str) -> dict[str, Any]:
        src = Path(source).expanduser().resolve()
        dst = Path(destination).expanduser().resolve()
        if not src.is_file():
            return {"success": False, "error": f"File not found: {src}"}
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return {"success": dst.is_file(), "source": str(src), "destination": str(dst)}

    @staticmethod
    def move_file(source: str, destination: str) -> dict[str, Any]:
        src = Path(source).expanduser().resolve()
        dst = Path(destination).expanduser().resolve()
        if not src.exists():
            return {"success": False, "error": f"Path not found: {src}"}
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        return {"success": dst.exists(), "source": str(src), "destination": str(dst)}

    @staticmethod
    def terminate_process(pid: int) -> dict[str, Any]:
        if pid <= 0:
            return {"success": False, "error": "Invalid PID"}
        try:
            os.kill(pid, 15)
            return {"success": True, "pid": pid}
        except ProcessLookupError:
            return {"success": False, "error": "Process not found", "pid": pid}
        except PermissionError:
            return {"success": False, "error": "Permission denied", "pid": pid}

    @staticmethod
    def run_command(command: list[str]) -> dict[str, Any]:
        if not command:
            return {"success": False, "error": "Empty command"}
        completed = subprocess.run(command, capture_output=True, text=True, timeout=60)
        return {
            "success": completed.returncode == 0,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }


__all__ = ["SystemActions"]
