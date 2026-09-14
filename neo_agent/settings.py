from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from threading import RLock

from .models import AgentConfig


class AgentSettings:
    """Small persistent settings store for autonomy/agent configuration."""

    def __init__(self, path: str = ".jarvis/agent_settings.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

    def load(self) -> AgentConfig:
        with self._lock:
            if not self.path.exists():
                return AgentConfig()
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                allowed = {field for field in AgentConfig.__dataclass_fields__}
                return AgentConfig(**{k: v for k, v in data.items() if k in allowed})
            except Exception:
                return AgentConfig()

    def save(self, config: AgentConfig) -> None:
        with self._lock:
            temp = self.path.with_suffix(".tmp")
            temp.write_text(json.dumps(asdict(config), ensure_ascii=False, indent=2), encoding="utf-8")
            temp.replace(self.path)

    def set_permission_mode(self, mode: int) -> AgentConfig:
        config = self.load()
        config.permission_mode = max(1, min(3, int(mode)))
        self.save(config)
        return config
