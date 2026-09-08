"""Bridge the legacy voice worker to a reliable microphone and app resolver."""
from __future__ import annotations

import re
import time


def _install_application_resolver(assistant) -> None:
    """Replace the legacy hardcoded app registry with runtime discovery."""
    try:
        from core.application_resolver import ApplicationResolver
        tools = getattr(assistant, "tools", None)
        if tools is None or getattr(tools, "_neo_application_resolver", False):
            return

        aliases = {
            "calculatrice": "calc.exe",
            "calc": "calc.exe",
            "bloc-notes": "notepad.exe",
            "notepad": "notepad.exe",
            "explorateur": "explorer.exe",
            "explorer": "explorer.exe",
            "vscode": "code",
            "visual studio code": "code",
            "chrome": "chrome",
            "discord": "Discord",
            "spotify": "Spotify",
            "steam": "steam",
        }
        resolver = ApplicationResolver(aliases)

        def open_application(requested: str):
            name = str(requested or "").strip()
            if not name:
                return False, "Nom d'application manquant."
            if name.lower().startswith(("http://", "https://")):
                assistant.signals.open_url.emit(name)
                return True, f"Navigation ouverte : {name}"
            try:
                match = resolver.launch(name)
                try:
                    tools.activity("outil", f"Lancement {name} via {match.source}")
                except Exception:
                    pass
                return True, f"{name} lancé."
            except FileNotFoundError:
                # Do not invent a filesystem path. The resolver searches Start Menu,
                # PATH and configured aliases before reporting the app as unknown.
                return False, f"Application introuvable : '{name}'."
            except (OSError, ValueError) as exc:
                return False, f"Impossible de lancer {name} : {exc}"

        tools.open_application = open_application
        tools._neo_application_resolver = True
        tools._neo_application_resolver_instance = resolver
    except Exception as exc:
        try:
            assistant.log.debug(f"Résolveur applications non installé : {exc}")
        except Exception:
            pass


def _microphone_index(assistant):
    """Return an explicitly configured input device, otherwise let Windows choose its default."""
    raw = assistant.CONFIG.get("microphone_device_index")
    if raw in (None, "", "default"):
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def install(assistant, session) -> bool:
    """Replace the legacy passive-listening loop with session-aware behavior."""
    if getattr(assistant, "_neo_voice_session_bridge", False):
        return True
    try:
        sr = assistant.sr
        np = assistant.np
        SOUND_OK = bool(assistant.SOUND_OK)
        speech = assistant.speech
        state = assistant.state
        signals = assistant.signals
        config = assistant.CONFIG
        language = assistant.LANGUAGE
        hotword = str(assistant.HOTWORD).lower().strip()
        queue = assistant.command_queue
        transcribe_audio = assistant.transcribe_audio
        play_wake_chime = assistant.play_wake_chime
    except Exception:
        return False

    _install_application_resolver(assistant)
    device_index = _microphone_index(assistant)

    def enqueue_command(text: str) -> None:
        session.begin_response()
        queue.put(text)

    def voice_worker():
        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 220
        recognizer.dynamic_energy_threshold = True
        recognizer.dynamic_energy_adjustment_damping = 0.15
        recognizer.dynamic_energy_ratio = 1.5
        recognizer.pause_threshold = 0.65
        recognizer.phrase_threshold = 0.25
        recognizer.non_speaking_duration = 0.35
        calibrated = False

        while True:
            if not state.mic_enabled or state.is_processing or state.is_speaking:
                time.sleep(0.25)
                continue
            try:
                mic_kwargs = {} if device_index is None else {"device_index": device_index}
                with sr.Microphone(**mic_kwargs) as source:
                    state.is_listening = True
                    signals.listening_change.emit(True)

                    # Calibrate once. Recalibrating before every sentence can move the
                    # threshold above the user's voice and make JARVIS appear deaf.
                    if not calibrated:
                        recognizer.adjust_for_ambient_noise(source, duration=0.8)
                        recognizer.energy_threshold = max(120, min(recognizer.energy_threshold, 900))
                        calibrated = True
                        assistant.log.info(
                            "VOICE: microphone prêt%s | seuil audio: %s",
                            f" #{device_index}" if device_index is not None else " (périphérique Windows par défaut)",
                            int(recognizer.energy_threshold),
                        )

                    audio = recognizer.listen(source, timeout=4, phrase_time_limit=8)

                    raw = np.frombuffer(audio.get_raw_data(), dtype=np.int16) if SOUND_OK else None
                    if raw is not None and len(raw) > 0:
                        level = min(1.0, float(np.abs(raw).mean()) / 6000.0)
                        state.audio_level = level
                        signals.audio_level.emit(level)

                    text = None
                    if config.get("use_whisper") and SOUND_OK and raw is not None:
                        text = transcribe_audio(raw.astype(np.float32) / 32768.0, sample_rate=audio.sample_rate)
                    if not text:
                        text = recognizer.recognize_google(audio, language=language)

                    state.is_listening = False
                    signals.listening_change.emit(False)
                    if not text:
                        continue

                    normalized = text.strip()
                    lower = normalized.lower()
                    if state.passive_listening:
                        has_wake = bool(hotword and re.search(rf"\b{re.escape(hotword)}\b", lower))
                        if has_wake:
                            play_wake_chime()
                            session.start()
                            clean_cmd = re.sub(
                                rf"\b{re.escape(hotword)}\b", "", normalized, flags=re.I
                            ).strip(" ,.!?")
                            signals.log_msg.emit("Vous (Voix)", normalized)
                            if clean_cmd:
                                enqueue_command(clean_cmd)
                            else:
                                session.begin_response()
                                try:
                                    speech.say("Oui ?")
                                finally:
                                    session.touch()
                        elif session.accepts_followup():
                            signals.log_msg.emit("Vous (Voix)", normalized)
                            enqueue_command(normalized)
                    else:
                        session.start()
                        signals.log_msg.emit("Vous (Voix)", normalized)
                        enqueue_command(normalized)
            except sr.WaitTimeoutError:
                state.is_listening = False
                signals.listening_change.emit(False)
            except sr.UnknownValueError:
                state.is_listening = False
                signals.listening_change.emit(False)
            except (OSError, AttributeError) as exc:
                state.is_listening = False
                signals.listening_change.emit(False)
                calibrated = False
                assistant.log.warning(f"VOICE: microphone indisponible : {exc}")
                time.sleep(1.0)
            except Exception as exc:
                state.is_listening = False
                signals.listening_change.emit(False)
                assistant.log.debug(f"STT : {exc}")
            time.sleep(0.15)

    assistant.voice_worker = voice_worker
    assistant._neo_voice_session_bridge = True
    return True


__all__ = ["install"]
