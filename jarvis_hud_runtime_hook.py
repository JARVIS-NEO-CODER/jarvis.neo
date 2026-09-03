"""PyInstaller runtime hook: attach the discrete J.A.R.V.I.S. HUD to the real window."""
from __future__ import annotations

import sys
import threading
import time


def _install_show_hook() -> None:
    for _ in range(240):
        assistant = sys.modules.get("assistant")
        window_cls = getattr(assistant, "JarvisWindow", None) if assistant else None
        if window_cls is not None:
            if getattr(window_cls, "_jarvis_discrete_hud_hooked", False):
                return
            original_show = window_cls.show

            def show_with_hud(self, *args, **kwargs):
                result = original_show(self, *args, **kwargs)
                if getattr(self, "_jarvis_discrete_hud", None) is None:
                    try:
                        from ui.discrete_hud import DiscreteHud
                        hud = DiscreteHud(self)
                        self._jarvis_discrete_hud = hud
                        hud.show_discrete()
                    except Exception:
                        pass
                return result

            window_cls.show = show_with_hud
            window_cls._jarvis_discrete_hud_hooked = True
            return
        time.sleep(0.05)


if not any("pytest" in str(arg).lower() for arg in sys.argv):
    threading.Thread(target=_install_show_hook, name="jarvis-discrete-hud-hook", daemon=True).start()
