"""Runtime bridge: J.A.R.V.I.S. core <-> NEO HUD."""
from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import threading
import types

from PyQt6.QtWidgets import QApplication

from ui.neo_hud import NeoHud
from ui.mini_hud import MiniHud
from context_engine import ContextEngine


def _install_runtime_guards(core) -> None:
    """Patch the legacy runtime at its real entry point without touching old UI code."""
    # SQLite accepts scalar values only. Some action paths return tuples such as
    # (success, message), so normalize anything structured before persistence.
    memory = getattr(core, "memory", None)
    if memory is not None and not getattr(memory, "_neo_runtime_safe", False):
        original_add_message = memory.add_message
        original_log_activity = getattr(memory, "log_activity", None)

        def sqlite_safe(value):
            if isinstance(value, (dict, list, tuple, set)):
                return json.dumps(value, ensure_ascii=False, default=str)
            return value if value is None or isinstance(value, (str, int, float, bytes)) else str(value)

        def safe_add_message(role, content):
            return original_add_message(sqlite_safe(role), sqlite_safe(content))

        memory.add_message = safe_add_message
        if original_log_activity is not None:
            def safe_log_activity(category, message, level="INFO"):
                return original_log_activity(sqlite_safe(category), sqlite_safe(message), sqlite_safe(level))
            memory.log_activity = safe_log_activity
        memory._neo_runtime_safe = True

    # Edge TTS can currently fail with a WebSocket 403. Keep it as the first
    # choice, but make Windows SAPI a real local fallback so NEO can still speak.
    speech_cls = getattr(core, "SpeechEngine", None)
    if speech_cls is None or getattr(speech_cls, "_neo_sapi_fallback", False):
        return

    async def safe_say(self, text):
        if not getattr(core, "state", None).voice_enabled or not text:
            return
        path = core.BASE_DIR / f"speech_{core.time.time_ns()}.mp3"
        core.state.is_speaking = True
        core.signals.speaking_change.emit(True)
        spoken = False
        try:
            if core.edge_tts is not None and core.PYGAME_OK:
                communicate = core.edge_tts.Communicate(
                    text,
                    core.VOICE,
                    rate=core.CONFIG.get("tts_rate", "+5%"),
                    volume=core.CONFIG.get("tts_volume", "+0%"),
                )
                await communicate.save(str(path))
                if not core.pygame.mixer.get_init():
                    core.pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
                core.pygame.mixer.music.load(str(path))
                core.pygame.mixer.music.set_volume(1.0)
                core.pygame.mixer.music.play()
                while core.pygame.mixer.music.get_busy():
                    if core.stop_event.is_set() or core.state.abort_requested:
                        core.pygame.mixer.music.stop()
                        break
                    await asyncio.sleep(0.05)
                spoken = True
        except Exception as exc:
            core.log.warning(f"Edge TTS indisponible, fallback vocal local : {exc}")
        finally:
            try:
                if path.exists():
                    path.unlink()
            except Exception:
                pass

        if not spoken and sys.platform == "win32":
            script = (
                "Add-Type -AssemblyName System.Speech; "
                "$text=[Console]::In.ReadToEnd(); "
                "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                "try {$s.SelectVoiceByHints([System.Speech.Synthesis.VoiceGender]::NotSet," 
                "[System.Speech.Synthesis.VoiceAge]::NotSet,0," 
                "[System.Globalization.CultureInfo]::GetCultureInfo('fr-FR'))} catch {}; "
                "$s.Speak($text); $s.Dispose()"
            )
            try:
                result = await asyncio.to_thread(
                    subprocess.run,
                    ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                    input=str(text),
                    text=True,
                    capture_output=True,
                    timeout=30,
                    check=False,
                )
                if result.returncode != 0:
                    raise RuntimeError(result.stderr.strip() or f"PowerShell exit {result.returncode}")
                spoken = True
            except Exception as exc:
                core.log.error(f"Fallback vocal Windows échoué : {exc}")

        if not spoken:
            core.log.error("Aucun moteur vocal disponible pour J.A.R.V.I.S.")
        core.state.is_speaking = False
        core.signals.speaking_change.emit(False)

    speech_cls._say = safe_say
    speech_cls._neo_sapi_fallback = True


def main() -> None:
    app = QApplication(sys.argv)

    # Import the existing assistant only after Qt is ready.
    import assistant as core
    _install_runtime_guards(core)

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

    # Compact floating HUD: always visible independently from the main cockpit.
    mini_hud = MiniHud()
    mini_hud.place_top_right()
    mini_hud.show()
    app.aboutToQuit.connect(mini_hud.close)

    def sync_mini_devices() -> None:
        mini_hud.set_devices(
            bool(core.CONFIG.get("microphone_enabled", True)),
            bool(getattr(core.state, "voice_enabled", True)),
        )

    def on_log(sender: str, message: str) -> None:
        if message == "__CLEAR_CHAT__":
            hud.terminal.clear()
            return
        speaker = "USER" if "Vous" in sender else sender
        hud.append_terminal(speaker, str(message))

    def on_status(status: str) -> None:
        value = str(status).upper()
        if "ERREUR" in value:
            state = "error"
        elif "RÉFLEXION" in value or "REFLEXION" in value:
            state = "thinking"
        elif "ÉCOUTE" in value or "ECOUTE" in value:
            state = "listening"
        elif "PARLE" in value:
            state = "speaking"
        else:
            state = "online"
        hud.set_reactor_state(state)
        mini_hud.set_state(state)

    def on_stats(data: dict) -> None:
        cpu = f"{int(data.get('cpu', 0))}%"
        ram = f"{int(data.get('ram', 0))}%"
        hud.set_system_value("CPU", cpu)
        hud.set_system_value("RAM", ram)
        hud.set_system_value("NET", "ONLINE")
        mini_hud.set_stats(cpu, ram)

    def on_listening(active: bool) -> None:
        if active:
            hud.set_reactor_state("listening")
            mini_hud.set_state("listening")
        elif not core.state.is_speaking and not core.state.is_processing:
            hud.set_reactor_state("online")
            mini_hud.set_state("online")
        sync_mini_devices()

    def on_speaking(active: bool) -> None:
        if active:
            hud.set_reactor_state("speaking")
            mini_hud.set_state("speaking")
        elif not core.state.is_listening and not core.state.is_processing:
            hud.set_reactor_state("online")
            mini_hud.set_state("online")
        sync_mini_devices()

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
            mini_hud.set_state("thinking")

    context_engine = ContextEngine(on_context=on_context).start(interval=15.0)
    app.aboutToQuit.connect(context_engine.stop)

    hud.set_reactor_state("online")
    mini_hud.set_state("online")
    sync_mini_devices()
    hud.append_terminal("SYSTEM", "NEO HUD connecté au noyau J.A.R.V.I.S.")
    hud.append_terminal("SYSTEM", "Context Engine local actif — apprentissage des habitudes")
    hud.show()

    core.speech.say("Systèmes quantiques en ligne. Prêt à exécuter vos ordres.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
