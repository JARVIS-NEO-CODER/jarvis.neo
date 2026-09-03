"""Windows per-user autostart for J.A.R.V.I.S. NEO."""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_KEY = "JARVIS_NEO"


def _command() -> str:
    if getattr(sys, "frozen", False):
        return f'"{Path(sys.executable).resolve()}"'
    script = Path(__file__).resolve().parents[1] / "assistant.py"
    return f'"{Path(sys.executable).resolve()}" "{script}"'


def set_enabled(enabled: bool = True) -> bool:
    """Enable/disable startup for the current Windows user only."""
    if sys.platform != "win32":
        return False
    try:
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                winreg.SetValueEx(key, APP_KEY, 0, winreg.REG_SZ, _command())
            else:
                try:
                    winreg.DeleteValue(key, APP_KEY)
                except FileNotFoundError:
                    pass
        return True
    except (OSError, ImportError):
        return False


def is_enabled() -> bool:
    if sys.platform != "win32":
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, APP_KEY)
            return True
    except (OSError, ImportError):
        return False


def ensure_from_config(config: dict) -> bool:
    return set_enabled(bool(config.get("autostart", True)))


__all__ = ["set_enabled", "is_enabled", "ensure_from_config"]
