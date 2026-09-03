"""Stable entry point for the focused J.A.R.V.I.S. NEO command center."""
from __future__ import annotations

import sys
import threading

from PyQt6.QtWidgets import QApplication

import assistant
import sitecustomize
import voice_runtime


def _start_core_workers() -> None:
    workers = (
        assistant.command_worker,
        voice_runtime.run,
        assistant.reminder_worker,
        assistant.run_web_server,
        assistant.security_worker,
        assistant.system_monitor_worker,
        assistant.retro_vision_worker,
    )
    for worker in workers:
        try:
            target = (lambda w=worker: w(assistant)) if worker is voice_runtime.run else worker
            threading.Thread(target=target, daemon=True, name=f"NEO-{worker.__name__}").start()
        except Exception as exc:
            try:
                assistant.log.warning(f"Service NEO non lancé : {exc}")
            except Exception:
                pass


def main() -> None:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    sitecustomize.install_runtime_fixes(assistant)
    _start_core_workers()

    from ui.neo_main_hud_v2 import NeoMainHud
    hud = NeoMainHud(assistant)
    hud.show()
    hud.raise_()
    hud.activateWindow()

    if not bool(assistant.CONFIG.get("main_hud_enabled", True)):
        hud.hide_hud()
    else:
        try:
            assistant.speech.say("Centre de commande NEO en ligne.")
        except Exception:
            pass
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
