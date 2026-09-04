"""Stable entry point for the focused J.A.R.V.I.S. NEO command center."""
from __future__ import annotations

import sys
import threading

from PyQt6.QtCore import QTimer
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


def _upgrade_voice_profile() -> None:
    """Replace the old default Henri voice with a more natural French profile."""
    cfg = getattr(assistant, "CONFIG", None)
    if not isinstance(cfg, dict):
        return

    # Keep an explicitly chosen voice untouched. Only migrate the old default.
    if str(cfg.get("voice", "")).strip() == "fr-FR-HenriNeural":
        cfg["voice"] = "fr-FR-ClaudeNeural"
        cfg["tts_rate"] = "-5%"
        try:
            assistant.save_config(cfg)
        except Exception:
            pass
        assistant.VOICE = cfg["voice"]
        assistant.log.info("VOICE: profil vocal amélioré -> fr-FR-ClaudeNeural (-5%)")
    else:
        # Keep the runtime value synchronized with the persisted configuration.
        assistant.VOICE = str(cfg.get("voice", assistant.VOICE))


def main() -> None:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    sitecustomize.install_runtime_fixes(assistant)
    _upgrade_voice_profile()

    from ui.neo_main_hud_v2 import NeoMainHud
    hud = NeoMainHud(assistant)

    # Le HUD principal doit toujours être visible au démarrage.
    # L'ancien paramètre main_hud_enabled pouvait laisser le HUD caché tout
    # en continuant à exécuter son timer _refresh en arrière-plan.
    cfg = getattr(assistant, "CONFIG", None)
    if isinstance(cfg, dict):
        cfg["main_hud_enabled"] = True
        try:
            assistant.save_config(cfg)
        except Exception:
            pass

    hud.show()
    hud.raise_()
    hud.activateWindow()

    try:
        assistant.speech.say("Centre de commande NEO en ligne.")
    except Exception:
        pass

    # Les workers démarrent seulement après l'affichage du HUD et l'entrée
    # dans la boucle Qt, afin qu'aucun service ne bloque son initialisation.
    QTimer.singleShot(0, _start_core_workers)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
