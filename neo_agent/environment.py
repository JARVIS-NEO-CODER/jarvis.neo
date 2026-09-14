from __future__ import annotations

import os
import platform
import shutil
from pathlib import Path
from typing import Any


def snapshot(cwd: str = ".") -> dict[str, Any]:
    """Return lightweight environment context. File contents stay out of prompts."""
    root = Path(cwd).resolve()
    try:
        entries = [p.name + ("/" if p.is_dir() else "") for p in root.iterdir()]
        entries = sorted(entries)[:200]
    except Exception:
        entries = []

    return {
        "os": platform.platform(),
        "python": platform.python_version(),
        "cwd": str(root),
        "files": entries,
        "executables": {
            name: bool(shutil.which(name))
            for name in ("python", "git", "node", "npm", "powershell", "ollama")
        },
        "user": os.environ.get("USERNAME") or os.environ.get("USER"),
    }
