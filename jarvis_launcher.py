"""Stable entry point for the J.A.R.V.I.S. NEO cockpit command center."""
from __future__ import annotations

import os
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
    """Use an independent Microsoft Edge neural voice and migrate old Pocket settings."""
    cfg = getattr(assistant, "CONFIG", None)
    if not isinstance(cfg, dict):
        return
    current = str(cfg.get("voice", "")).strip()
    if current in {"pocket-estelle", "pocket_tts", "pocket-tts", "estelle"}:
        cfg["voice"] = "fr-FR-RemyMultilingualNeural"
        cfg["tts_rate"] = "+0%"
        try:
            assistant.save_config(cfg)
        except Exception:
            pass
    assistant.VOICE = str(cfg.get("voice", assistant.VOICE))


def _install_independent_edge_tts() -> None:
    """Route JARVIS speech through the independent Edge neural backend."""
    speech_cls = getattr(assistant, "SpeechEngine", None)
    if speech_cls is None or getattr(speech_cls, "_neo_edge_tts", False):
        return
    original_say = getattr(speech_cls, "_say", None)
    if original_say is None:
        return
    try:
        from core.tts_edge_player import speak as edge_speak
    except Exception as exc:
        assistant.log.warning(f"VOICE: moteur Edge indépendant non chargé : {exc}")
        return

    async def edge_say(self, text):
        state = getattr(assistant, "state", None)
        if state is None or not getattr(state, "voice_enabled", True) or not text:
            return
        voice = str(getattr(assistant, "CONFIG", {}).get("voice", "fr-FR-HenriNeural"))
        if voice.startswith("pocket") or voice in {"estelle", "pocket-tts"}:
            voice = "fr-FR-RemyMultilingualNeural"
        ok = await edge_speak(
            text,
            state=state,
            voice=voice,
            rate=str(getattr(assistant, "CONFIG", {}).get("tts_rate", "+0%")),
            volume=str(getattr(assistant, "CONFIG", {}).get("tts_volume", "+0%")),
        )
        if not ok:
            await original_say(self, text)

    speech_cls._say = edge_say
    speech_cls._neo_edge_tts = True
    assistant.log.info(f"VOICE: Edge neural indépendant activé ({assistant.VOICE})")


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
        relay_url = str(os.getenv("JARVIS_REMOTE_RELAY_URL", "")).strip()
        if relay_url:
            try:
                from jarvis_remote_client import RemoteTunnelClient
                remote = RemoteTunnelClient(bridge, relay_url)
                remote.start()
                assistant.log.info(f"REMOTE: tunnel sortant actif | node_id={remote.node_id} | relais={remote.remote_url}")
            except Exception as exc:
                assistant.log.warning(f"REMOTE: tunnel non démarré : {exc}")
        else:
            assistant.log.info("REMOTE: désactivé (JARVIS_REMOTE_RELAY_URL non configurée)")
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
    _install_independent_edge_tts()

    from ui.cockpit_hud import CockpitHud
    hud = CockpitHud(assistant)
    assistant.cockpit = hud
    assistant.show_cockpit_panel = hud.show_dynamic_panel
    assistant.remove_cockpit_panel = hud.remove_dynamic_panel
    assistant.clear_cockpit_panels = hud.clear_dynamic_panels
    assistant.get_cockpit_panels = hud.dynamic_panels

    # The cockpit runtime is deliberately attached after the HUD exists, so
    # command/AI requests can update Qt only through the established UI bridge.
    try:
        from core.cockpit_runtime import CockpitRuntime
        assistant.cockpit_runtime = CockpitRuntime(assistant)
        assistant.cockpit_runtime.install()
        assistant.log.info("COCKPIT: runtime dynamique connecté au moteur de commandes et à l'IA")
    except Exception as exc:
        assistant.log.warning(f"COCKPIT: runtime dynamique non chargé : {exc}")

    cfg = getattr(assistant, "CONFIG", None)
    if isinstance(cfg, dict):
        cfg["main_hud_enabled"] = True
        cfg["cockpit_enabled"] = True
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
