"""Local system metrics and anomaly detection for J.A.R.V.I.S. NEO."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any

try:
    import psutil
except ImportError:  # Optional dependency until installed in the runtime.
    psutil = None


@dataclass(frozen=True)
class SystemSnapshot:
    timestamp: str
    cpu_percent: float
    ram_percent: float
    disk_percent: float
    battery_percent: float | None


class SystemMonitor:
    """Collects local metrics and flags sustained abnormal usage."""

    def __init__(self, cpu_threshold: float = 95.0, ram_threshold: float = 90.0) -> None:
        self.cpu_threshold = cpu_threshold
        self.ram_threshold = ram_threshold
        self.history: list[SystemSnapshot] = []

    def snapshot(self) -> dict[str, Any]:
        if psutil is None:
            return {"available": False, "reason": "psutil_not_installed"}
        battery = psutil.sensors_battery()
        data = SystemSnapshot(
            datetime.now().isoformat(),
            psutil.cpu_percent(interval=None),
            psutil.virtual_memory().percent,
            psutil.disk_usage("/").percent,
            battery.percent if battery else None,
        )
        self.history.append(data)
        return {"available": True, **asdict(data), "anomalies": self.anomalies()}

    def anomalies(self) -> list[str]:
        if not self.history:
            return []
        current = self.history[-1]
        issues: list[str] = []
        if current.cpu_percent >= self.cpu_threshold:
            issues.append("high_cpu_usage")
        if current.ram_percent >= self.ram_threshold:
            issues.append("high_ram_usage")
        if current.disk_percent >= 95:
            issues.append("disk_nearly_full")
        return issues

    def status(self) -> dict[str, Any]:
        return self.snapshot()


__all__ = ["SystemMonitor", "SystemSnapshot"]
