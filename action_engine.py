"""NEO Action Engine: safe, local-first context-driven actions.

The engine turns a detected context into a named action. It deliberately uses
an allow-listed registry instead of executing arbitrary shell commands.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass(frozen=True)
class ActionResult:
    ok: bool
    action: str
    message: str
    skipped: bool = False


class ActionEngine:
    def __init__(self, dispatcher: Callable[[str], object], event: Optional[Callable[[str, str], None]] = None):
        self.dispatcher = dispatcher
        self.event = event
        self._lock = threading.Lock()
        self._last_run: dict[str, float] = {}
        self._cooldown = 120.0
        self._enabled = True
        self._actions: dict[str, Callable[[], object]] = {}
        self.register("gaming_mode", lambda: self.dispatcher("active le mode gaming"))

    def register(self, name: str, callback: Callable[[], object]):
        self._actions[name] = callback

    def enable(self, enabled: bool = True):
        self._enabled = bool(enabled)

    def _log(self, level: str, message: str):
        if self.event:
            try:
                self.event(level, message)
            except Exception:
                pass

    def run(self, name: str, *, force: bool = False) -> ActionResult:
        if not self._enabled:
            return ActionResult(False, name, "Action Engine désactivé", True)
        action = self._actions.get(name)
        if action is None:
            return ActionResult(False, name, "Action inconnue")

        now = time.time()
        with self._lock:
            last = self._last_run.get(name, 0.0)
            if not force and now - last < self._cooldown:
                return ActionResult(True, name, "Action déjà exécutée récemment", True)
            self._last_run[name] = now

        self._log("ACTION", f"NEO exécute {name}")
        try:
            result = action()
            ok = not (isinstance(result, dict) and result.get("ok") is False)
            message = "Action exécutée" if ok else str(result.get("error", "Action refusée"))
            self._log("ACTION", f"{name}: {message}")
            return ActionResult(ok, name, message)
        except Exception as exc:
            self._log("ERROR", f"{name}: {exc}")
            return ActionResult(False, name, str(exc))

    def on_context(self, context: str, confidence: float, reason: str) -> Optional[ActionResult]:
        if context != "gaming" or confidence < 0.90:
            return None
        self._log("CONTEXT", f"Gaming détecté à {confidence:.0%} ({reason})")
        return self.run("gaming_mode")
