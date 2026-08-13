"""Runtime bridge: J.A.R.V.I.S. core <-> NEO HUD.

Keeps assistant.py as the brain while making ui/neo_hud.py the desktop UI.
"""
from __future__ import annotations

import sys
import threading

from PyQt6.QtWidgets import QApplication

from ui.neo_hud import NeoHud


def main() -> None:
    app = QApplication(sys.argv)

    # Import the existing assistant only after Qt is ready.
    import assistant as core

    # Start the same background services used by the legacy desktop UI.
    threading.Thread(target=core.command_worker, daemon=True).start()
    threading.Thread(target=core.voice_worker, daemon=True).start()
    threading.Thread(target=core.reminder_worker, daemon=True).start()
    threading.Thread(target=core.run_web_server, daemon=True).start()
    threading.Thread(target=core.security_worker, daemon=True).start()
    threading.Thread(target=core.system_monitor_worker, daemon=True).start()
    threading.Thread(target=core.retro_vision_worker, daemon=True).start()

    hud = NeoHud()
    hud.setMinimumSize(1000, 650)
    hud.resize(1250, 760)

    def on_log(sender: str, message: str) -> None:
        if message == "__CLEAR_CHAT__":
            hud.terminal.clear()
            return
        speaker = "USER" if "Vous" in sender else sender
        hud.append_terminal(speaker, message)

    def on_status(status: str) -> None:
        value = str(status).upper()
        if "ERREUR" in value:
            hud.set_reactor_state("error")
        elif "RÉFLEXION" in value or "REFLEXION" in value:
            hud.set_reactor_state("thinking")
        else:
            hud.set_reactor_state("online")

    def on_stats(data: dict) -> None:
        hud.set_system_value("CPU", f"{int(data.get('cpu', 0))}%")
        hud.set_system_value("RAM", f"{int(data.get('ram', 0))}%")
        hud.set_system_value("NET", "ONLINE")

    def on_listening(active: bool) -> None:
        if active:
            hud.set_reactor_state("listening")
        elif not core.state.is_speaking and not core.state.is_processing:
            hud.set_reactor_state("online")

    def on_speaking(active: bool) -> None:
        if active:
            hud.set_reactor_state("speaking")
        elif not core.state.is_listening and not core.state.is_processing:
            hud.set_reactor_state("online")

    core.signals.log_msg.connect(on_log)
    core.signals.status_change.connect(on_status)
    core.signals.stats_update.connect(on_stats)
    core.signals.listening_change.connect(on_listening)
    core.signals.speaking_change.connect(on_speaking)
    core.signals.model_tier_change.connect(
        lambda tier: hud.append_terminal("SYSTEM", f"Mode IA : {tier}")
    )

    # Initial state.
    hud.set_reactor_state("online")
    hud.append_terminal("SYSTEM", "NEO HUD connecté au noyau J.A.R.V.I.S.")
    hud.show()

    core.speech.say("Systèmes quantiques en ligne. Prêt à exécuter vos ordres.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
