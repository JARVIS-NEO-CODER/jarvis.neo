"""Bridge the voice worker to the application resolver and local Pocket TTS."""
from __future__ import annotations

import re
import time


def _install_application_resolver(assistant) -> None:
    try:
        from core.application_resolver import ApplicationResolver
        tools = getattr(assistant, "tools", None)
        processor = getattr(assistant, "processor", None)
        action_engine = getattr(processor, "_neo_action_engine", None) if processor else None
        aliases = {
            "calculatrice": "calc.exe", "calc": "calc.exe", "bloc-notes": "notepad.exe",
            "notepad": "notepad.exe", "explorateur": "explorer.exe", "explorer": "explorer.exe",
            "vscode": "code", "visual studio code": "code", "chrome": "chrome",
            "google chrome": "chrome", "discord": "Discord", "spotify": "Spotify", "steam": "steam",
        }
        resolver = ApplicationResolver(aliases)

        def open_application(requested: str = "", command: str | None = None, name: str | None = None, **_kwargs):
            value = requested or command or name or ""
            app_name = str(value).strip()
            if not app_name:
                return False, "Nom d'application manquant."
            if app_name.lower().startswith(("http://", "https://")):
                assistant.signals.open_url.emit(app_name)
                return True, f"Navigation ouverte : {app_name}"
            try:
                match = resolver.launch(app_name)
                try:
                    if tools is not None:
                        tools.activity("outil", f"Lancement {app_name} via {match.source}")
                except Exception:
                    pass
                return True, f"{app_name} lancé."
            except FileNotFoundError:
                return False, f"Application introuvable : '{app_name}'."
            except (OSError, ValueError) as exc:
                return False, f"Impossible de lancer {app_name} : {exc}"

        if tools is not None and not getattr(tools, "_neo_application_resolver", False):
            tools.open_application = open_application
            tools._neo_application_resolver = True
            tools._neo_application_resolver_instance = resolver
        if action_engine is not None:
            definition = getattr(action_engine, "_actions", {}).get("action.launch_app")
            if definition is not None and not getattr(action_engine, "_neo_application_resolver", False):
                definition.handler = open_application
                action_engine._neo_application_resolver = True
    except Exception as exc:
        try:
            assistant.log.debug(f"Résolveur applications non installé : {exc}")
        except Exception:
            pass


def _microphone_index(assistant):
    raw = assistant.CONFIG.get("microphone_device_index")
    if raw in (None, "", "default"):
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _try_direct_app_command(assistant, text: str) -> bool:
    normalized = str(text or "").strip()
    match = re.match(
        r"^(?:ouvre|lance|démarre|demarre|démarrer|demarrer|ouvrir)\s+(?:l['’]application\s+|l['’]app\s+)?(.+?)\s*[.!?]*$",
        normalized, flags=re.I,
    )
    if not match:
        return False
    app_name = match.group(1).strip(" \t.,!?\"'")
    if not app_name:
        return False
    try:
        opener = getattr(getattr(assistant, "tools", None), "open_application", None)
        if not callable(opener):
            return False
        success, message = opener(app_name)
        if success:
            assistant.signals.log_msg.emit("J.A.R.V.I.S.", message)
            return True
        assistant.log.info("VOICE: lancement direct impossible pour '%s': %s", app_name, message)
    except Exception as exc:
        assistant.log.warning("VOICE: lancement direct échoué pour '%s': %s", app_name, exc)
    return False


def _install_pocket_tts(assistant) -> None:
    try:
        from core.piper_tts_engine import install
        install(assistant)
    except Exception as exc:
        try:
            assistant.log.error(f"VOICE: Pocket TTS indisponible : {exc}")
        except Exception:
            pass


def install(assistant, session) -> bool:
    if getattr(assistant, "_neo_voice_session_bridge", False):
        return True
    try:
        sr = assistant.sr
        np = assistant.np
        sound_ok = bool(assistant.SOUND_OK)
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
    _install_pocket_tts(assistant)
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
                    raw = np.frombuffer(audio.get_raw_data(), dtype=np.int16) if sound_ok else None
                    if raw is not None and len(raw) > 0:
                        level = min(1.0, float(np.abs(raw).mean()) / 6000.0)
                        state.audio_level = level
                        signals.audio_level.emit(level)
                    text = None
                    whisper_available = bool(getattr(assistant, "WHISPER_OK", False))
                    if (config.get("use_whisper") or whisper_available) and sound_ok and raw is not None:
                        try:
                            text = transcribe_audio(raw.astype(np.float32) / 32768.0, sample_rate=audio.sample_rate)
                        except Exception as exc:
                            assistant.log.debug(f"STT Whisper indisponible : {exc}")
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
                            clean_cmd = re.sub(rf"\b{re.escape(hotword)}\b", "", normalized, flags=re.I).strip(" ,.!?")
                            signals.log_msg.emit("Vous (Voix)", normalized)
                            if clean_cmd:
                                if not _try_direct_app_command(assistant, clean_cmd):
                                    enqueue_command(clean_cmd)
                            else:
                                session.begin_response()
                                try:
                                    speech.say("Oui ?")
                                finally:
                                    session.touch()
                        elif session.accepts_followup():
                            signals.log_msg.emit("Vous (Voix)", normalized)
                            if not _try_direct_app_command(assistant, normalized):
                                enqueue_command(normalized)
                    else:
                        session.start()
                        signals.log_msg.emit("Vous (Voix)", normalized)
                        if not _try_direct_app_command(assistant, normalized):
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
