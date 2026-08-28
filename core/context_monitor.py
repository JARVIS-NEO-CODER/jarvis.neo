"""Local event monitor used to build context without sending every event to AI."""
from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any


class ContextMonitor:
    def __init__(self, recorder: Callable[[str, dict[str, Any]], Any], interval: float = 5.0) -> None:
        self.recorder = recorder
        self.interval = max(0.5, interval)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self, observer: Callable[[], list[tuple[str, dict[str, Any]]]]) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, args=(observer,), daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=self.interval + 1)

    def _loop(self, observer: Callable[[], list[tuple[str, dict[str, Any]]]]) -> None:
        while not self._stop.is_set():
            try:
                for name, data in observer():
                    self.recorder(name, data)
            except Exception:
                pass
            self._stop.wait(self.interval)
