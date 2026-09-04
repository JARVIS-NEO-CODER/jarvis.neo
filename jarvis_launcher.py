"""Stable entry point for the focused J.A.R.V.I.S. NEO command center."""
from __future__ import annotations

import sys
import threading
import time

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

        safe_actions = {
            "command", "agent", "agent.stop", "pc.volume", "pc.media", "pc.app.open",
            "pc.browser.open", "jarvis.mode.set", "pc.performance", "sync.request",
        }
        confirmation_required = {
            "pc.system.shutdown", "pc.system.restart", "pc.input.keyboard",
            "pc.input.mouse", "pc.file.delete", "pc.remote.session",
        }

        def action_handler(action: str, args: dict):
            action = str(action).strip()
            if action in confirmation_required:
                return {"accepted": False, "requires_confirmation": True, "reason": "HIGH_RISK_ACTION_REQUIRES_LOCAL_CONFIRMATION"}
            if action not in safe_actions:
                return {"accepted": False, "reason": "ACTION_NOT_ALLOWLISTED"}
            if action == "sync.request":
                return {"accepted": True, "sync": "state"}
            if action == "pc.performance":
                try:
                    return {"accepted": True, "performance": assistant.collect_system_metrics()}
                except Exception as exc:
                    return {"accepted": False, "error": str(exc)}
            if action == "jarvis.mode.set":
                mode = str(args.get("mode", "normal")).strip().lower()
                command = {"normal": "mode normal", "conversation": "mode conversation", "agent": "mode agent", "sentinel": "active le mode sentinelle"}.get(mode)
                if command is None:
                    return {"accepted": False, "reason": "MODE_NOT_ALLOWED"}
            elif action == "pc.volume":
                delta = int(args.get("delta", 0))
                if delta not in {-10, -5, 5, 10}:
                    return {"accepted": False, "reason": "VOLUME_DELTA_NOT_ALLOWED"}
                command = f"volume {'+' if delta > 0 else '-'} {abs(delta)}"
            elif action == "pc.media":
                command_name = str(args.get("command", "")).strip().lower()
                if command_name not in {"play_pause", "next", "previous", "stop"}:
                    return {"accepted": False, "reason": "MEDIA_COMMAND_NOT_ALLOWED"}
                command = {"play_pause": "pause la musique", "next": "musique suivante", "previous": "musique précédente", "stop": "arrête la musique"}[command_name]
            elif action == "pc.app.open":
                app = str(args.get("app", "")).strip().lower()
                command = {"ets2": "ouvre euro truck simulator 2", "notepad": "ouvre le bloc-notes", "calculator": "ouvre la calculatrice"}.get(app)
                if command is None:
                    return {"accepted": False, "reason": "APP_NOT_ALLOWLISTED"}
            elif action == "pc.browser.open":
                url = str(args.get("url", "")).strip()
                if not (url.startswith("https://") or url.startswith("http://")) or len(url) > 500:
                    return {"accepted": False, "reason": "URL_INVALID"}
                command = f"ouvre {url}"
            elif action == "agent.stop":
                assistant.state.abort_requested = True
                return {"accepted": True, "stopped": True}
            elif action == "agent":
                instruction = str(args.get("instruction", "")).strip()
                if not instruction or len(instruction) > 2000:
                    return {"accepted": False, "reason": "INSTRUCTION_INVALID"}
                command = instruction
            else:
                command = str(args.get("command", "")).strip()
                if not command or len(command) > 2000:
                    return {"accepted": False, "reason": "COMMAND_INVALID"}

            assistant.signals.log_msg.emit("Vous (Mobile)", command)
            assistant.command_queue.put(command)
            return {"accepted": True, "queued": True, "command": command}

        def state_provider():
            try:
                metrics = assistant.collect_system_metrics()
            except Exception:
                metrics = {}
            state = getattr(assistant, "state", None)
            cfg = getattr(assistant, "CONFIG", {})
            return {
                "status": "online" if bool(getattr(state, "is_active", True)) else "offline",
                "cpu_percent": metrics.get("cpu_percent", 0),
                "ram_percent": metrics.get("ram_percent", 0),
                "disk_percent": metrics.get("disk_percent", 0),
                "battery_percent": metrics.get("battery_percent"),
                "mic_enabled": bool(getattr(state, "mic_enabled", True)),
                "voice_enabled": bool(getattr(state, "voice_enabled", True)),
                "listening": bool(getattr(state, "is_listening", False)),
                "speaking": bool(getattr(state, "is_speaking", False)),
                "processing": bool(getattr(state, "is_processing", False)),
                "model": assistant.get_active_model(False),
                "provider": cfg.get("ai_provider", "ollama"),
                "timestamp": time.time(),
            }

        bridge.action_handler = action_handler
        bridge.state_provider = state_provider
        assistant.signals.log_msg.connect(
            lambda sender, message: bridge.publish_from_thread("log", {"sender": sender, "message": message})
        )
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
