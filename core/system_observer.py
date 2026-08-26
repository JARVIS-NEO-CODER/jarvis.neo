"""Generic local system observation for J.A.R.V.I.S. NEO."""
from __future__ import annotations

import ctypes
import os
import threading
import time
from dataclasses import dataclass, asdict

from .bus import Event, EventBus


@dataclass(frozen=True)
class SystemSnapshot:
    timestamp: float
    cpu_percent: float | None = None
    ram_percent: float | None = None
    active_window: str | None = None
    active_process: str | None = None


class SystemObserver:
    """Poll neutral OS signals without any predefined app/game list."""

    def __init__(self, bus: EventBus, interval: float = 2.0) -> None:
        self.bus = bus
        self.interval = max(0.25, float(interval))
        self._running = False
        self._thread: threading.Thread | None = None
        self._last_cpu: tuple[int, int] | None = None

    def snapshot(self) -> SystemSnapshot:
        cpu = self._cpu_percent()
        ram = self._ram_percent()
        window, process = self._foreground_window()
        return SystemSnapshot(time.time(), cpu, ram, window, process)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, name="jarvis-system-observer", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 2.0) -> None:
        self._running = False
        thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=timeout)
        self._thread = None

    def _loop(self) -> None:
        while self._running:
            try:
                snapshot = self.snapshot()
                self.bus.publish(Event(name="system.metric", payload=asdict(snapshot), priority=10, timestamp=snapshot.timestamp))
            except Exception:
                pass
            time.sleep(self.interval)

    def _cpu_percent(self) -> float | None:
        if os.name != "nt":
            return None
        idle, kernel, user = self._filetime_totals()
        if idle is None:
            return None
        total = kernel + user
        current = (idle, total)
        previous = self._last_cpu
        self._last_cpu = current
        if previous is None:
            return None
        idle_delta = idle - previous[0]
        total_delta = total - previous[1]
        if total_delta <= 0:
            return None
        return round(max(0.0, min(100.0, (1.0 - idle_delta / total_delta) * 100.0)), 1)

    @staticmethod
    def _filetime_totals() -> tuple[int | None, int, int]:
        class FILETIME(ctypes.Structure):
            _fields_ = [("dwLowDateTime", ctypes.c_uint32), ("dwHighDateTime", ctypes.c_uint32)]
        idle, kernel, user = FILETIME(), FILETIME(), FILETIME()
        if not ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)):
            return None, 0, 0
        def value(ft: FILETIME) -> int:
            return (ft.dwHighDateTime << 32) | ft.dwLowDateTime
        return value(idle), value(kernel), value(user)

    @staticmethod
    def _ram_percent() -> float | None:
        if os.name != "nt":
            return None
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_uint32), ("dwMemoryLoad", ctypes.c_uint32), ("ullTotalPhys", ctypes.c_uint64), ("ullAvailPhys", ctypes.c_uint64), ("ullTotalPageFile", ctypes.c_uint64), ("ullAvailPageFile", ctypes.c_uint64), ("ullTotalVirtual", ctypes.c_uint64), ("ullAvailVirtual", ctypes.c_uint64), ("sullAvailExtendedVirtual", ctypes.c_uint64)]
        status = MEMORYSTATUSEX()
        status.dwLength = ctypes.sizeof(status)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return None
        return float(status.dwMemoryLoad)

    @staticmethod
    def _foreground_window() -> tuple[str | None, str | None]:
        if os.name != "nt":
            return None, None
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None, None
        length = user32.GetWindowTextLengthW(hwnd)
        title = ctypes.create_unicode_buffer(max(1, length + 1))
        user32.GetWindowTextW(hwnd, title, len(title))
        window_title = title.value or None
        process_name = None
        pid = ctypes.c_uint32()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value:
            handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid.value)
            if handle:
                try:
                    size = ctypes.c_uint32(1024)
                    buffer = ctypes.create_unicode_buffer(size.value)
                    if ctypes.windll.kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
                        process_name = buffer.value.rsplit("\\", 1)[-1] or None
                finally:
                    ctypes.windll.kernel32.CloseHandle(handle)
        return window_title, process_name


__all__ = ["SystemObserver", "SystemSnapshot"]
