"""JARVIS NEO HUD enhancement layer."""
from __future__ import annotations
import time
from dataclasses import dataclass
from typing import Any
try:
    import psutil
except Exception:
    psutil = None

@dataclass
class HudSnapshot:
    provider: str = "Local"
    model: str = ""
    listening: bool = False
    speaking: bool = False
    cpu: float = 0.0
    ram: float = 0.0
    temperature: float | None = None
    network: str = "ONLINE"
    latency_ms: float | None = None
    mode: str = "NORMAL"
    activity: str = "IDLE"

class HudTelemetry:
    def __init__(self) -> None:
        self.started = time.monotonic()
    def snapshot(self, **state: Any) -> HudSnapshot:
        cpu = float(psutil.cpu_percent(interval=None)) if psutil else 0.0
        ram = float(psutil.virtual_memory().percent) if psutil else 0.0
        temperature = None
        if psutil and hasattr(psutil, "sensors_temperatures"):
            try:
                temps = psutil.sensors_temperatures()
                vals = [v.current for group in temps.values() for v in group if v.current is not None]
                temperature = round(max(vals), 1) if vals else None
            except Exception:
                pass
        return HudSnapshot(provider=str(state.get("provider", "Local")), model=str(state.get("model", "")),
            listening=bool(state.get("listening", False)), speaking=bool(state.get("speaking", False)),
            cpu=cpu, ram=ram, temperature=temperature, network=str(state.get("network", "ONLINE")),
            latency_ms=state.get("latency_ms"), mode=str(state.get("mode", "NORMAL")),
            activity=str(state.get("activity", "IDLE")))

def hud_capabilities() -> dict[str, list[str]]:
    return {"core":["status","activity","event_history"],"system":["cpu","ram","temperature","network"],
            "voice":["microphone","listening","speaking"],"ai":["provider","model","latency","fallback"],
            "modes":["normal","agent","sentinel"],"actions":["app","web","files","music","settings"],
            "layout":["compact","cockpit","widget_visibility","always_on_top"]}
