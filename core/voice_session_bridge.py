"""Bridge the legacy voice worker to the short-lived conversational session."""
from __future__ import annotations

import re
import time


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

    def voice_worker():
        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 300
        recognizer.dynamic_energy_threshold = True
        recognizer.pause_threshold = 0.8
        recognizer.phrase_threshold = 0.3

        while True:
            if not state.mic_enabled or state.is_processing or state.is_speaking:
                time.sleep(0.3)
                continue
            try:
                with sr.Microphone() as source:
                    state.is_listening = True
                    signals.listening_change.emit(True)
                    recognizer.adjust_for_ambient_noise(source, duration=0.4)
                    audio = recognizer.listen(source, timeout=3, phrase_time_limit=8)

                    raw = np.frombuffer(audio.get_raw_data(), dtype=np.int16) if SOUND_OK else None
                    if raw is not None and len(raw) > 0:
                        level = min(1.0, float(np.abs(raw).mean()) / 8000.0)
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
                            clean_cmd = re.sub(rf"\b{re.escape(hotword)}\b", "", normalized, flags=re.I).strip(" ,.!?")
                            signals.log_msg.emit("Vous (Voix)", normalized)
                            if clean_cmd:
                                queue.put(clean_cmd)
                            else:
                                speech.say("Oui ?")
                        elif session.accepts_followup():
                            session.touch()
                            signals.log_msg.emit("Vous (Voix)", normalized)
                            queue.put(normalized)
                    else:
                        session.start()
                        signals.log_msg.emit("Vous (Voix)", normalized)
                        queue.put(normalized)
            except sr.WaitTimeoutError:
                state.is_listening = False
                signals.listening_change.emit(False)
            except sr.UnknownValueError:
                state.is_listening = False
                signals.listening_change.emit(False)
            except Exception as exc:
                state.is_listening = False
                signals.listening_change.emit(False)
                assistant.log.debug(f"STT : {exc}")
            time.sleep(0.2)

    assistant.voice_worker = voice_worker
    assistant._neo_voice_session_bridge = True
    return True


__all__ = ["install"]
