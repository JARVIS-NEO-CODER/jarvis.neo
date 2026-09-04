"""Stable entry point for the focused J.A.R.V.I.S. NEO command center."""
from __future__ import annotations

import threading
import sys

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
    """Migrate the old default voice while preserving explicit user choices."""
    cfg = getattr(assistant, "CONFIG", None)
    if not isinstance(cfg, dict):
        return
    if str(cfg.get("voice", "")).strip() in {"fr-FR-HenriNeural", "fr-FR-ClaudeNeural"}:
        cfg["voice"] = "pocket-estelle"
        cfg["tts_rate"] = "-5%"
        try:
            assistant.save_config(cfg)
        except Exception:
            pass
    assistant.VOICE = str(cfg.get("voice", assistant.VOICE))


def _install_pocket_tts() -> None:
    """Install Pocket TTS as the primary voice backend when available."""
    try:
        from core.pocket_tts_engine import install
        install(assistant)
    except Exception as exc:
        try:
            assistant.log.warning(f"Pocket TTS non chargé, moteur vocal précédent conservé : {exc}")
        except Exception:
            pass


def _start_mobile_bridge() -> None:
    """Start the authenticated PC/mobile bridge once the core is ready."""
    try:
        import uvicorn
        from jarvis_mobile_bridge import bridge

        def action_handler(action: str, args: dict):
            if action == "command":
                command = str(args.get("command", "")).strip()
                if not command:
                    return {"accepted": False, "reason": "EMPTY_COMMAND"}
                assistant.signals.log_msg.emit("Vous (Mobile)", command)
                assistant.command_queue.put(command)
                return {"accepted": True, "command": command}
            if action == "agent":
                instruction = str(args.get("instruction", "")).strip()
                if not instruction:
                    return {"accepted": False, "reason": "EMPTY_INSTRUCTION"}
                assistant.signals.log_msg.emit("Vous (Mobile)", instruction)
                assistant.command_queue.put(instruction)
                return {"accepted": True, "instruction": instruction}
            if action == "agent.stop":
                assistant.state.abort_requested = True
                return {"accepted": True, "stopped": True}
            return {"accepted": False, "reason": "UNKNOWN_ACTION"}

        def state_provider():
            metrics = assistant.collect_system_metrics()
            return {
                "status": "online" if assistant.state.is_active else "offline",
                "cpu": metrics.get("cpu_percent", 0),
                "ram": metrics.get("ram_percent", 0),
                "disk": metrics.get("disk_percent", 0),
                "battery": metrics.get("battery_percent"),
                "cpu_percent": metrics.get("cpu_percent", 0),
                "ram_percent": metrics.get("ram_percent", 0),
                "disk_percent": metrics.get("disk_percent", 0),
                "battery_percent": metrics.get("battery_percent"),
                "mic_enabled": bool(assistant.state.mic_enabled),
                "voice_enabled": bool(assistant.state.voice_enabled),
                "listening": bool(assistant.state.is_listening),
                "speaking": bool(assistant.state.is_speaking),
                "processing": bool(assistant.state.is_processing),
                "model": assistant.get_active_model(False),
                "provider": assistant.CONFIG.get("ai_provider", "ollama"),
            }

        bridge.action_handler = action_handler
        bridge.state_provider = state_provider
        bridge.start_discovery()
        threading.Thread(
            target=lambda: uvicorn.run(bridge.app, host=bridge.host, port=bridge.port, log_level="warning"),
            daemon=True,
            name="NEO-mobile-bridge",
        ).start()
        assistant.log.info(f"MOBILE: passerelle active sur le port {bridge.port} | code: {bridge.pairing_code}")
    except Exception as exc:
        try:
            assistant.log.warning(f"MOBILE: passerelle non démarrée : {exc}")
        except Exception:
            pass


def main() -> None:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    sitecustomize.install_runtime_fixes(assistant)
    _upgrade_voice_profile()
    _install_pocket_tts()

    from ui.neo_main_hud_v2 import NeoMainHud
    hud = NeoMainHud(assistant)

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

    QTimer.singleShot(0, _start_core_workers)
    QTimer.singleShot(500, _start_mobile_bridge)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
