"""Runtime bridge: J.A.R.V.I.S. core <-> NEO HUD."""
from __future__ import annotations

import sys
import threading

from PyQt6.QtWidgets import QApplication

from ui.neo_hud import NeoHud
from context_engine import ContextEngine


def main() -> None:
    app = QApplication(sys.argv)

    # Import the existing assistant only after Qt is ready.
    import assistant as core

    # Existing NEO services.
    for worker in (
        core.command_worker, core.voice_worker, core.reminder_worker,
        core.run_web_server, core.security_worker, core.system_monitor_worker,
        core.retro_vision_worker,
    ):
        threading.Thread(target=worker, daemon=True).start()

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

    # Local-first context engine: no Ollama call for routine observation.
    def on_context(context: str, confidence: float, reason: str) -> None:
        if context == "gaming" and confidence >= 0.72:
            hud.append_terminal(
                "NEO",
                f"Contexte GAMING détecté ({confidence:.0%}) — {reason}"
            )
            hud.set_reactor_state("thinking")
            # We deliberately do not change Windows settings silently yet.
            # The learned context is persisted and ready for the Action Engine.

    context_engine = ContextEngine(on_context=on_context).start(interval=15.0)
    app.aboutToQuit.connect(context_engine.stop)

    hud.set_reactor_state("online")
    hud.append_terminal("SYSTEM", "NEO HUD connecté au noyau J.A.R.V.I.S.")
    hud.append_terminal("SYSTEM", "Context Engine local actif — apprentissage des habitudes")
    hud.show()

    core.speech.say("Systèmes quantiques en ligne. Prêt à exécuter vos ordres.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
