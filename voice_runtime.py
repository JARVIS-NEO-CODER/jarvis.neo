from __future__ import annotations

import re
import time

import speech_recognition as sr


def _set_listening(assistant, active: bool) -> None:
    assistant.state.is_listening = active
    try:
        assistant.signals.listening_change.emit(active)
    except Exception:
        pass


def _log(assistant, message: str) -> None:
    try:
        assistant.log.info(f"VOICE: {message}")
    except Exception:
        pass


def _looks_like_command(text: str) -> bool:
    """Accept obvious directives even when the wake word was missed."""
    prefixes = (
        "ouvre ", "ferme ", "cherche ", "météo", "quelle heure", "quelle est l'heure",
        "processus", "performance", "stats", "batterie", "uptime", "aide", "help",
        "quel modèle", "modèle actuel", "mode ", "volume ", "copie ", "note ",
        "navigue ", "va sur ", "rappelle-moi ", "mes tâches", "mes mémos", "mon agenda",
        "whisper ", "écoute passive ", "sécurité ", "capture", "screenshot",
    )
    return text.startswith(prefixes)


def _dispatch_voice_command(assistant, text: str) -> None:
    try:
        assistant.signals.log_msg.emit("Vous (Voix)", text)
    except Exception:
        pass
    assistant.command_queue.put(text)
    _log(assistant, f"commande vocale envoyée: {text}")


def _recognize_google_with_hotword(assistant, recognizer, audio):
    """Use Google's alternatives so a correct wake word is preferred over a bad first guess."""
    hotword = str(getattr(assistant, "HOTWORD", "jarvis")).lower().strip()
    try:
        result = recognizer.recognize_google(audio, language=assistant.LANGUAGE, show_all=True)
    except sr.UnknownValueError:
        return None
    except sr.RequestError:
        raise

    if not result:
        return None

    alternatives = result.get("alternative", []) if isinstance(result, dict) else []
    transcripts = [str(item.get("transcript", "")).strip() for item in alternatives if item.get("transcript")]
    if not transcripts:
        return None

    if hotword:
        pattern = re.compile(rf"\b{re.escape(hotword)}\b", re.IGNORECASE)
        for candidate in transcripts:
            if pattern.search(candidate):
                return candidate

    return transcripts[0]


def _normalize_hotword(text: str, hotword: str) -> tuple[str, bool]:
    """Repair common French STT guesses for the wake word, only at the start."""
    if not hotword:
        return text, False

    pattern = re.compile(rf"^\s*(?P<wake>{re.escape(hotword)})\b", re.IGNORECASE)
    if pattern.match(text):
        return text, False

    aliases = {
        "jarvis": ("service", "jervis", "jarvice", "jarvi", "jarvisse", "jarviss"),
    }
    candidates = aliases.get(hotword, ())
    alias_pattern = re.compile(rf"^\s*(?P<wake>{'|'.join(map(re.escape, candidates))})\b", re.IGNORECASE)
    match = alias_pattern.match(text)
    if not match:
        return text, False

    repaired = alias_pattern.sub(hotword, text, count=1)
    return repaired, True


def run(assistant) -> None:
    """Persistent microphone worker without a pre-STT energy threshold."""
    recognizer = sr.Recognizer()
    device_reported = False
    try:
        record_duration = float(assistant.CONFIG.get("voice_record_duration", 6.0))
    except (TypeError, ValueError):
        record_duration = 6.0
    record_duration = max(1.0, min(12.0, record_duration))

    while True:
        if not bool(getattr(assistant.state, "mic_enabled", True)):
            time.sleep(0.5)
            continue

        source = None
        try:
            names = sr.Microphone.list_microphone_names()
            if not names:
                raise RuntimeError("Aucun périphérique microphone détecté par PyAudio")

            configured_index = assistant.CONFIG.get("microphone_device_index")
            index = int(configured_index) if configured_index not in (None, "", "default") else None
            if index is not None and not (0 <= index < len(names)):
                raise RuntimeError(f"Index microphone invalide: {index}. Périphériques disponibles: {len(names)}")

            source = sr.Microphone(device_index=index)
            with source as mic:
                selected_name = names[index] if index is not None else "périphérique par défaut Windows"
                _log(assistant, f"microphone prêt: {selected_name}")
                if not device_reported:
                    _log(assistant, "périphériques audio détectés: " + " | ".join(f"[{i}] {name}" for i, name in enumerate(names)))
                    device_reported = True

                while bool(getattr(assistant.state, "mic_enabled", True)):
                    if assistant.state.is_processing or assistant.state.is_speaking:
                        time.sleep(0.25)
                        continue

                    try:
                        _set_listening(assistant, True)
                        _log(assistant, f"capture audio ({record_duration:.1f}s)")
                        audio = recognizer.record(mic, duration=record_duration)
                    except Exception as exc:
                        _set_listening(assistant, False)
                        _log(assistant, f"capture audio impossible: {exc}")
                        time.sleep(0.5)
                        continue

                    _set_listening(assistant, False)
                    try:
                        raw_audio = audio.get_raw_data()
                        if raw_audio:
                            import numpy as np
                            samples = np.frombuffer(raw_audio, dtype=np.int16)
                            if samples.size:
                                level = float(np.sqrt(np.mean(samples.astype(np.float32) ** 2)) / 32768.0)
                                assistant.state.audio_level = min(1.0, level * 8.0)
                                _log(assistant, f"audio reçu | niveau={assistant.state.audio_level:.2f}")
                                try:
                                    assistant.signals.audio_level.emit(assistant.state.audio_level)
                                except Exception:
                                    pass
                    except Exception as exc:
                        _log(assistant, f"diagnostic audio indisponible: {exc}")

                    text = None
                    try:
                        if assistant.CONFIG.get("use_whisper") and getattr(assistant, "SOUND_OK", False):
                            import numpy as np
                            raw = np.frombuffer(audio.get_raw_data(), dtype=np.int16)
                            text = assistant.transcribe_audio(raw.astype(np.float32) / 32768.0, sample_rate=audio.sample_rate)
                    except Exception as exc:
                        _log(assistant, f"Whisper indisponible: {exc}")

                    if not text:
                        try:
                            text = _recognize_google_with_hotword(assistant, recognizer, audio)
                        except sr.RequestError as exc:
                            _log(assistant, f"reconnaissance Google indisponible: {exc}")
                            try:
                                text = recognizer.recognize_sphinx(audio, language="fr-FR")
                                _log(assistant, "fallback Sphinx utilisé")
                            except Exception:
                                continue

                    if not text:
                        _log(assistant, "STT: aucune parole reconnue dans la capture")
                        continue

                    text = str(text).strip()
                    text_lower = text.lower()
                    hotword = str(getattr(assistant, "HOTWORD", "jarvis")).lower().strip()
                    normalized_text, corrected = _normalize_hotword(text_lower, hotword)
                    if corrected:
                        _log(assistant, f"STT: correction du mot d'activation: {text_lower!r} -> {normalized_text!r}")
                        text_lower = normalized_text
                    _log(assistant, f"entendu: {text_lower}")

                    if getattr(assistant.state, "passive_listening", True):
                        if hotword and re.search(rf"\b{re.escape(hotword)}\b", text_lower):
                            try:
                                assistant.play_wake_chime()
                            except Exception:
                                pass
                            clean_cmd = re.sub(rf"\b{re.escape(hotword)}\b", "", text_lower, count=1).strip()
                            if clean_cmd:
                                _dispatch_voice_command(assistant, clean_cmd)
                            else:
                                try:
                                    assistant.signals.log_msg.emit("Vous (Voix)", text_lower)
                                    assistant.speech.say("À vos ordres, monsieur.")
                                except Exception:
                                    pass
                        elif _looks_like_command(text_lower):
                            _log(assistant, "mot d'activation absent, mais directive reconnue")
                            _dispatch_voice_command(assistant, text_lower)
                        else:
                            _log(assistant, f"parole ignorée: mot d'activation absent ({hotword or 'aucun'})")
                    else:
                        _dispatch_voice_command(assistant, text_lower)

        except Exception as exc:
            _set_listening(assistant, False)
            _log(assistant, f"microphone en erreur, nouvelle tentative: {exc}")
            time.sleep(2.0)
        finally:
            _set_listening(assistant, False)
            source = None
