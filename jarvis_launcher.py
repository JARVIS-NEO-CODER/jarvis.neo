"""Stable packaged entry point for J.A.R.V.I.S. NEO."""
from __future__ import annotations

import assistant
import sitecustomize


def _wire_visible_ai_settings() -> None:
    """Make the visible left-panel AI settings open the canonical dialog."""
    from ui.provider_settings import ProviderSettingsDialog

    window_cls = assistant.JarvisWindow
    if getattr(window_cls, "_canonical_ai_settings_wired", False):
        return

    original_toggle = window_cls.toggle_sub_window

    def toggle_sub_window(self, title, widget, state_val):
        if title == "Paramètres IA" and state_val == 2:
            dialog = ProviderSettingsDialog(self)
            dialog.exec()
            return
        return original_toggle(self, title, widget, state_val)

    window_cls.toggle_sub_window = toggle_sub_window
    window_cls._canonical_ai_settings_wired = True


def main() -> None:
    # Apply fixes before the real application window is created.
    sitecustomize.install_runtime_fixes(assistant)
    _wire_visible_ai_settings()
    try:
        from ui.cockpit_bridge import install as install_cockpit
        install_cockpit(assistant)
    except Exception as exc:
        try:
            assistant.log.warning(f"Cockpit HUD non chargé : {exc}")
        except Exception:
            pass
    try:
        from ui.command_deck_bridge import install as install_command_deck
        install_command_deck(assistant)
    except Exception as exc:
        try:
            assistant.log.warning(f"Command Deck non chargé : {exc}")
        except Exception:
            pass
    assistant.main()


if __name__ == "__main__":
    main()
