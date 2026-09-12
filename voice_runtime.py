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
    hotword = str(getattr(assistant, "HOTWORD", "jarvis")).lower().strip()
    result = recognizer.recognize_google(audio, language=assistant.LANGUAGE, show_all=True)
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
    if not hotword:
        return text, False
    if re.match(rf"^\s*{re.escape(hotword)}\b", text, re.IGNORECASE):
        return text, False
    aliases = {
        "jarvis": ("service", "jervis", "jarvice", "jarvi", "jarvisse", "jarviss"),
    }
    candidates = aliases.get(hotword, ())
    if not candidates:
        return text, False
    alias_pattern = re.compile(rf"^\s*(?:{'|'.join(map(re.escape, candidates))})\b", re.IGNORECASE)
    if not alias_pattern.match(text):
        return text, False
    return alias_pattern.sub(hotword, text, count=1), True


def _capture_until_silence(recognizer, mic, max_duration: float, phrase_timeout: float, silence_timeout: float):
    """Capture a complete utterance: start on speech, then stop only after silence."""
    try:
        audio = recognizer.listen(
            mic,
            timeout=phrase_timeout,
            phrase_time_limit=max_duration,
        )
    except sr.WaitTimeoutError:
        return None

    # SpeechRecognition's phrase_time_limit prevents an utterance from growing forever.
    # Once the speaker stops, listen() returns after its normal pause threshold.
    return audio


def run(assistant) -> None:
    """Persistent microphone worker capturing complete phrases instead of fixed 6s chunks."""
    recognizer = sr.Recognizer()
    recognizer.pause_threshold = 0.9
    recognizer.non_speaking_duration = 0.35
    recognizer.dynamic_energy_threshold = True
    device_reported = False

    try:
        max_duration = float(assistant.CONFIG.get("voice_max_phrase_duration", 30.0))
    except (TypeError, ValueError):
        max_duration = 30.0
    max_duration = max(5.0, min(60.0, max_duration))

    try:
        phrase_timeout = float(assistant.CONFIG.get("voice_phrase_timeout", 2.0))
    except (TypeError, ValueError):
        phrase_timeout = 2.0
    phrase_timeout = max(0.5, min(10.0, phrase_timeout))

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
                        _log(assistant, f"écoute en attente d'une phrase (max {max_duration:.0f}s)")
                        audio = _capture_until_silence(
                            recognizer, mic,
                            max_duration=max_duration,
                            phrase_timeout=phrase_timeout,
                            silence_timeout=0.9,
                        )
                    except Exception as exc:
                        _set_listening(assistant, False)
                        _log(assistant, f"capture audio impossible: {exc}")
                        time.sleep(0.5)
                        continue

                    _set_listening(assistant, False)
                    if audio is None:
                        continue

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
                        except sr.UnknownValueError:
                            _log(assistant, "STT: aucune parole reconnue dans la capture")
                            continue
                        except sr.RequestError as exc:
                            _log(assistant, f"reconnaissance Google indisponible: {exc}")
                            try:
                                text = recognizer.recognize_sphinx(audio, language="fr-FR")
                                _log(assistant, "fallback Sphinx utilisé")
                            except Exception:
                                continue

                    if not text:
                        continue

                    text_lower = str(text).strip().lower()
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
