"""Local Pocket TTS engine for J.A.R.V.I.S. NEO.

Pocket TTS is loaded lazily so JARVIS can still start when the optional
package has not been installed yet. The engine uses the French Pocket TTS
model and keeps the voice state cached in memory.
"""
from __future__ import annotations

import asyncio
import threading
from pathlib import Path


class PocketTTSEngine:
    """Small local French TTS adapter with lazy model loading."""

    def __init__(self, assistant):
        self.assistant = assistant
        self._model = None
        self._voice_state = None
        self._lock = threading.Lock()
        self._available: bool | None = None

    def available(self) -> bool:
        if self._available is not None:
            return self._available
        try:
            from pocket_tts import TTSModel  # noqa: F401
            import scipy.io.wavfile  # noqa: F401
            self._available = True
        except Exception as exc:
            self._available = False
            try:
                self.assistant.log.info(f"Pocket TTS non installé : {exc}")
            except Exception:
                pass
        return self._available

    def _load(self) -> None:
        if self._model is not None and self._voice_state is not None:
            return

        from pocket_tts import TTSModel

        # French is currently exposed by Pocket TTS through french_24l.
        # Try int8 quantization first when the optional backend is available,
        # then fall back to the normal CPU model without adding dependencies.
        try:
            self._model = TTSModel.load_model(language="french_24l", quantize=True)
        except Exception:
            self._model = TTSModel.load_model(language="french_24l")

        # "estelle" is Pocket TTS's built-in default French voice.
        self._voice_state = self._model.get_state_for_audio_prompt("estelle")

    def synthesize(self, text: str, output_path: Path) -> int:
        if not self.available():
            raise RuntimeError("Pocket TTS n'est pas installé")

        clean = str(text or "").strip()
        if not clean:
            raise ValueError("Texte vocal vide")

        with self._lock:
            self._load()
            audio = self._model.generate_audio(self._voice_state, clean)
            import scipy.io.wavfile

            scipy.io.wavfile.write(
                str(output_path),
                self._model.sample_rate,
                audio.detach().cpu().numpy(),
            )
            return int(self._model.sample_rate)


_ENGINE: PocketTTSEngine | None = None
_ENGINE_LOCK = threading.Lock()


def get_engine(assistant) -> PocketTTSEngine:
    global _ENGINE
    with _ENGINE_LOCK:
        if _ENGINE is None or _ENGINE.assistant is not assistant:
            _ENGINE = PocketTTSEngine(assistant)
        return _ENGINE


def install(assistant) -> bool:
    """Make Pocket TTS the primary speech backend, keeping the old backend as fallback."""
    speech_cls = getattr(assistant, "SpeechEngine", None)
    if speech_cls is None or getattr(speech_cls, "_neo_pocket_tts", False):
        return False

    original_say = getattr(speech_cls, "_say", None)
    if original_say is None:
        return False

    engine = get_engine(assistant)
    if not engine.available():
        return False

    async def pocket_say(self, text):
        state = getattr(assistant, "state", None)
        if state is None or not state.voice_enabled or not text:
            return

        path = assistant.BASE_DIR / f"pocket_speech_{assistant.time.time_ns()}.wav"
        state.is_speaking = True
        assistant.signals.speaking_change.emit(True)
        spoken = False
        try:
            await asyncio.to_thread(engine.synthesize, str(text), path)
            if not assistant.PYGAME_OK:
                raise RuntimeError("pygame audio indisponible")
            if not assistant.pygame.mixer.get_init():
                assistant.pygame.mixer.init(frequency=24000, size=-16, channels=1, buffer=1024)
            assistant.pygame.mixer.music.load(str(path))
            assistant.pygame.mixer.music.set_volume(1.0)
            assistant.pygame.mixer.music.play()
            while assistant.pygame.mixer.music.get_busy():
                if assistant.stop_event.is_set() or state.abort_requested:
                    assistant.pygame.mixer.music.stop()
                    break
                await asyncio.sleep(0.05)
            spoken = True
        except Exception as exc:
            try:
                assistant.log.warning(f"Pocket TTS indisponible, retour au moteur vocal précédent : {exc}")
            except Exception:
                pass
        finally:
            try:
                if path.exists():
                    path.unlink()
            except Exception:
                pass

        if not spoken:
            # sitecustomize's Edge TTS implementation remains the fallback.
            await original_say(self, text)
            return

        state.is_speaking = False
        assistant.signals.speaking_change.emit(False)

    speech_cls._say = pocket_say
    speech_cls._neo_pocket_tts = True
    try:
        assistant.log.info("VOICE: Pocket TTS local activé (français / Estelle)")
    except Exception:
        pass
    return True
