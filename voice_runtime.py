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


def run(assistant) -> None:
    """Persistent microphone worker with reconnect and explicit diagnostics.

    The legacy worker reopened and recalibrated the microphone on every phrase.
    This version keeps one input stream open, reconnects on device errors and
    uses the configured SpeechRecognition/PyAudio default device.
    """
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 300
    recognizer.dynamic_energy_threshold = True
    recognizer.dynamic_energy_adjustment_damping = 0.15
    recognizer.dynamic_energy_ratio = 1.5
    recognizer.pause_threshold = 0.75
    recognizer.phrase_threshold = 0.25
    recognizer.non_speaking_duration = 0.35

    while True:
        if not bool(getattr(assistant.state, "mic_enabled", True)):
            time.sleep(0.5)
            continue

        source = None
        try:
            names = sr.Microphone.list_microphone_names()
            if not names:
                raise RuntimeError("Aucun périphérique microphone détecté par PyAudio")

            # Optional explicit device selection, otherwise Windows/PyAudio default.
            configured_index = assistant.CONFIG.get("microphone_device_index")
            index = int(configured_index) if configured_index not in (None, "", "default") else None
            source = sr.Microphone(device_index=index)
            with source as mic:
                _log(assistant, f"microphone prêt: {names[index] if index is not None and index < len(names) else 'périphérique par défaut'}")
                recognizer.adjust_for_ambient_noise(mic, duration=0.8)
                _log(assistant, f"seuil audio: {recognizer.energy_threshold:.0f}")

                while bool(getattr(assistant.state, "mic_enabled", True)):
                    if assistant.state.is_processing or assistant.state.is_speaking:
                        time.sleep(0.25)
                        continue

                    try:
                        _set_listening(assistant, True)
                        audio = recognizer.listen(mic, timeout=2.0, phrase_time_limit=8.0)
                    except sr.WaitTimeoutError:
                        _set_listening(assistant, False)
                        continue

                    _set_listening(assistant, False)
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
                            continue
                        except sr.RequestError as exc:
                            _log(assistant, f"reconnaissance Google indisponible: {exc}")
                            continue

                    if not text:
                        continue
                    text_lower = text.lower().strip()
                    _log(assistant, f"entendu: {text}")

                    if getattr(assistant.state, "passive_listening", True):
                        hotword = str(getattr(assistant, "HOTWORD", "jarvis")).lower().strip()
                        if hotword and hotword in text_lower:
                            try:
                                assistant.play_wake_chime()
                            except Exception:
                                pass
                            clean_cmd = re.sub(rf"\b{re.escape(hotword)}\b", "", text_lower).strip()
                            try:
                                assistant.signals.log_msg.emit("Vous (Voix)", text)
                            except Exception:
                                pass
                            if clean_cmd:
                                assistant.command_queue.put(clean_cmd)
                            else:
                                try:
                                    assistant.speech.say("À vos ordres, monsieur.")
                                except Exception:
                                    pass
                    else:
                        try:
                            assistant.signals.log_msg.emit("Vous (Voix)", text)
                        except Exception:
                            pass
                        assistant.command_queue.put(text)

        except Exception as exc:
            _set_listening(assistant, False)
            _log(assistant, f"microphone en erreur, nouvelle tentative: {exc}")
            time.sleep(2.0)
        finally:
            _set_listening(assistant, False)
            source = None
