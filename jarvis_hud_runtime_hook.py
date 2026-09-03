"""PyInstaller runtime hook: attach the discrete J.A.R.V.I.S. HUD to the real window."""
from __future__ import annotations

import sys
import threading
import time


def _attach_discrete_hud() -> None:
    for _ in range(240):
        assistant = sys.modules.get("assistant")
        window = getattr(assistant, "_jarvis_window_instance", None) if assistant else None
        if window is not None:
            try:
                from ui.discrete_hud import DiscreteHud
                hud = DiscreteHud(window)
                window._jarvis_discrete_hud = hud
                hud.show_discrete()
                return
            except Exception:
                return
        time.sleep(0.05)


if not any("pytest" in str(arg).lower() for arg in sys.argv):
    threading.Thread(target=_attach_discrete_hud, name="jarvis-discrete-hud", daemon=True).start()
