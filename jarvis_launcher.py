"""Stable entry point for the redesigned J.A.R.V.I.S. NEO desktop HUD."""
from __future__ import annotations

import sys
import threading

from PyQt6.QtWidgets import QApplication

import assistant
import sitecustomize


def _wire_visible_ai_settings() -> None:
    """Keep the legacy AI settings button compatible with the canonical dialog."""
    window_cls = getattr(assistant, "JarvisWindow", None)
    if window_cls is None or getattr(window_cls, "_canonical_ai_settings_wired", False):
        return
    original_toggle = window_cls.toggle_sub_window

    def toggle_sub_window(self, title, widget, state_val):
        if title == "Paramètres IA" and state_val == 2:
            from ui.provider_settings import ProviderSettingsDialog
            ProviderSettingsDialog(self).exec()
            return
        return original_toggle(self, title, widget, state_val)

    window_cls.toggle_sub_window = toggle_sub_window
    window_cls._canonical_ai_settings_wired = True


def _start_core_workers() -> None:
    """Start the same background services used by the assistant without opening the old HUD."""
    for worker in (
        assistant.command_worker,
        assistant.voice_worker,
        assistant.reminder_worker,
        assistant.run_web_server,
        assistant.security_worker,
        assistant.system_monitor_worker,
        assistant.retro_vision_worker,
    ):
        try:
            threading.Thread(target=worker, daemon=True).start()
        except Exception as exc:
            try:
                assistant.log.warning(f"Service NEO non lancé : {exc}")
            except Exception:
                pass


def main() -> None:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    sitecustomize.install_runtime_fixes(assistant)
    _wire_visible_ai_settings()
    _start_core_workers()

    from ui.neo_main_hud import NeoMainHud
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
