"""Runtime data sources for configurable J.A.R.V.I.S. NEO lists."""
from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any


REPOSITORY_DATA_FILE = Path(__file__).resolve().parent.parent / "config" / "jarvis_data.json"
USER_DATA_FILE = Path.home() / ".jarvis_neo" / "jarvis_data.json"


def _read(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError, TypeError):
        return {}


def load_data() -> dict[str, Any]:
    """Load repository defaults, then merge user overrides when present."""
    path = Path(os.getenv("JARVIS_NEO_DATA_FILE", "")) if os.getenv("JARVIS_NEO_DATA_FILE") else None
    data = _read(path) if path else _read(REPOSITORY_DATA_FILE)
    if USER_DATA_FILE.exists() and USER_DATA_FILE != path:
        user = _read(USER_DATA_FILE)
        for key, value in user.items():
            if isinstance(value, dict) and isinstance(data.get(key), dict):
                data[key] = {**data[key], **value}
            else:
                data[key] = value
    return data


def get_data(key: str, default: Any = None) -> Any:
    value = load_data().get(key, default)
    return deepcopy(value)


__all__ = ["REPOSITORY_DATA_FILE", "USER_DATA_FILE", "load_data", "get_data"]
