"""Primary local neural TTS for J.A.R.V.I.S. NEO.

The historical filename is kept for compatibility with the voice bridge, but the
implementation is now Kyutai Pocket TTS with its dedicated French model and the
predefined Estelle voice. There is deliberately no cloud or generic OS fallback.
"""
from __future__ import annotations

import asyncio
import threading
import time
from pathlib import Path
from typing import Any

MODEL_NAME = "french_24l"
VOICE_NAME = "estelle"


class PocketTTSEngine:
    def __init__(self, base_dir: Path, log: Any | None = None) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.log = log
        self._model = None
        self._voice_state = None
        self._lock = threading.Lock()

    def _log(self, level: str, message: str) -> None:
        try:
            getattr(self.log, level)(message)
        except Exception:
            pass

    def _load(self):
        if self._model is not None and self._voice_state is not None:
            return self._model, self._voice_state
        with self._lock:
            if self._model is not None and self._voice_state is not None:
                return self._model, self._voice_state
            try:
                from pocket_tts import TTSModel
            except Exception as exc:
                raise RuntimeError("Pocket TTS n'est pas installé.") from exc

            self._log("info", "VOICE: chargement du modèle neural français Pocket TTS...")
            model = TTSModel.load_model(language=MODEL_NAME, quantize=True)
            voice_state = model.get_state_for_audio_prompt(VOICE_NAME)
            self._model = model
            self._voice_state = voice_state
            self._log("info", "VOICE: Pocket TTS français prêt, voix Estelle.")
            return model, voice_state

    def synthesize(self, text: str, output_path: Path) -> Path:
        if not text or not text.strip():
            raise ValueError("Texte vide")
        model, voice_state = self._load()
        import scipy.io.wavfile

        audio = model.generate_audio(voice_state, text.strip())
        scipy.io.wavfile.write(str(output_path), model.sample_rate, audio.detach().cpu().numpy())
        return output_path


def install(assistant) -> bool:
    """Install Pocket TTS as the only JARVIS speech synthesis backend."""
    speech = getattr(assistant, "speech", None)
    if speech is None or getattr(speech, "_neo_pocket_tts_installed", False):
        return bool(speech)

    try:
        import pocket_tts  # noqa: F401
    except Exception as exc:
        raise RuntimeError("Pocket TTS est requis pour la voix J.A.R.V.I.S. NEO.") from exc

    engine = PocketTTSEngine(
        getattr(assistant, "BASE_DIR", Path.home() / ".jarvis_neo"),
        getattr(assistant, "log", None),
    )
    state = assistant.state
    signals = assistant.signals
    pygame = getattr(assistant, "pygame", None)
    if not getattr(assistant, "PYGAME_OK", False) or pygame is None:
        raise RuntimeError("Le moteur audio pygame est requis pour J.A.R.V.I.S. NEO.")
    stop_event = assistant.stop_event

    async def _say(text: str):
        if not state.voice_enabled or not text:
            return
        path = engine.base_dir / f"speech_{time.time_ns()}.wav"
        state.is_speaking = True
        signals.speaking_change.emit(True)
        try:
            await asyncio.to_thread(engine.synthesize, text, path)
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=24000, size=-16, channels=1, buffer=512)
            pygame.mixer.music.load(str(path))
            pygame.mixer.music.set_volume(1.0)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                if stop_event.is_set() or state.abort_requested:
                    pygame.mixer.music.stop()
                    break
                await asyncio.sleep(0.04)
        except Exception as exc:
            try:
                assistant.log.error(f"VOICE: Pocket TTS échec : {exc}")
            except Exception:
                pass
        finally:
            state.is_speaking = False
            signals.speaking_change.emit(False)
            try:
                path.unlink(missing_ok=True)
            except Exception:
                pass

    speech._say = _say
    speech._neo_pocket_tts_installed = True
    speech._neo_pocket_tts_engine = engine
    try:
        assistant.log.info("VOICE: Pocket TTS français / Estelle activé, sans fallback.")
    except Exception:
        pass
    return True


PiperTTSEngine = PocketTTSEngine
__all__ = ["PocketTTSEngine", "PiperTTSEngine", "MODEL_NAME", "VOICE_NAME", "install"]
