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


def run(assistant) -> None:
    """Persistent microphone worker with diagnostics and reconnect handling."""
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 300
    recognizer.dynamic_energy_threshold = True
    recognizer.dynamic_energy_adjustment_damping = 0.15
    recognizer.dynamic_energy_ratio = 1.5
    recognizer.pause_threshold = 0.75
    recognizer.phrase_threshold = 0.25
    recognizer.non_speaking_duration = 0.35
    device_reported = False

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
                recognizer.adjust_for_ambient_noise(mic, duration=0.8)
                _log(assistant, f"seuil audio: {recognizer.energy_threshold:.0f}")

                while bool(getattr(assistant.state, "mic_enabled", True)):
                    if assistant.state.is_processing or assistant.state.is_speaking:
                        time.sleep(0.25)
                        continue

                    try:
                        _set_listening(assistant, True)
                        _log(assistant, "écoute active")
                        audio = recognizer.listen(mic, timeout=2.0, phrase_time_limit=7.0)
                    except sr.WaitTimeoutError:
                        _set_listening(assistant, False)
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
                            text = recognizer.recognize_google(audio, language=assistant.LANGUAGE)
                        except sr.UnknownValueError:
                            _log(assistant, "audio reçu mais parole non comprise")
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
                    text = str(text).strip()
                    text_lower = text.lower()
                    _log(assistant, f"entendu: {text}")

                    if getattr(assistant.state, "passive_listening", True):
                        hotword = str(getattr(assistant, "HOTWORD", "jarvis")).lower().strip()
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
                                    assistant.signals.log_msg.emit("Vous (Voix)", text)
                                    assistant.speech.say("À vos ordres, monsieur.")
                                except Exception:
                                    pass
                        elif _looks_like_command(text_lower):
                            _log(assistant, "mot d'activation absent, mais directive reconnue")
                            _dispatch_voice_command(assistant, text_lower)
                        else:
                            _log(assistant, f"parole ignorée: mot d'activation absent ({hotword or 'aucun'})")
                    else:
                        _dispatch_voice_command(assistant, text)

        except Exception as exc:
            _set_listening(assistant, False)
            _log(assistant, f"microphone en erreur, nouvelle tentative: {exc}")
            time.sleep(2.0)
        finally:
            _set_listening(assistant, False)
            source = None
