"""Adapter that installs the new NEO HUD without rewriting assistant.py.

The legacy JarvisWindow stays alive underneath the new HUD so all existing
methods, signals and widgets remain available while the visual shell changes.
"""

from __future__ import annotations

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QStackedWidget

from .neo_hud import NeoHud


class NeoWindow:
    """Factory/wrapper around the existing assistant.JarvisWindow class."""

    @staticmethod
    def build(legacy_class):
        class _NeoWindow(legacy_class):
            def __init__(self):
                super().__init__()

                # Keep the complete legacy UI alive so existing methods continue
                # to have valid widget references. Only the visible surface changes.
                self._legacy_central = self.centralWidget()
                self.neo_hud = NeoHud()

                self._neo_stack = QStackedWidget()
                self._neo_stack.setObjectName("neoWindowStack")
                self._neo_stack.addWidget(self._legacy_central)
                self._neo_stack.addWidget(self.neo_hud)
                self._neo_stack.setCurrentWidget(self.neo_hud)
                self.setCentralWidget(self._neo_stack)

                # Mirror the existing event bus into the new visual shell.
                signals.log_msg.connect(self._neo_log)
                signals.status_change.connect(self._neo_status)
                signals.stats_update.connect(self._neo_stats)
                signals.listening_change.connect(self._neo_listening)
                signals.speaking_change.connect(self._neo_speaking)

                # A small initial entry makes the terminal visibly alive.
                self.neo_hud.append_terminal("JARVIS", "NEO HUD INITIALIZED")

            def _neo_log(self, speaker, message):
                self.neo_hud.append_terminal(str(speaker), str(message))

            def _neo_status(self, status):
                text = str(status).lower()
                if "écout" in text or "listen" in text:
                    state = "listening"
                elif "parl" in text or "voix" in text or "speak" in text:
                    state = "speaking"
                elif "trait" in text or "process" in text or "sync" in text:
                    state = "thinking"
                elif "error" in text or "erreur" in text:
                    state = "error"
                else:
                    state = "online"
                self.neo_hud.set_reactor_state(state)

            def _neo_stats(self, data):
                self.neo_hud.set_system_value("CPU", f"{int(data.get('cpu', 0))}%")
                self.neo_hud.set_system_value("RAM", f"{int(data.get('ram', 0))}%")
                self.neo_hud.set_system_value("GPU", "N/A")
                self.neo_hud.set_system_value("TEMP", "N/A")
                self.neo_hud.set_system_value("NET", "ONLINE")

            def _neo_listening(self, active):
                if active:
                    self.neo_hud.set_reactor_state("listening")
                elif not getattr(state, "is_speaking", False):
                    self.neo_hud.set_reactor_state("online")

            def _neo_speaking(self, active):
                if active:
                    self.neo_hud.set_reactor_state("speaking")
                elif not getattr(state, "is_listening", False):
                    self.neo_hud.set_reactor_state("online")

        return _NeoWindow
