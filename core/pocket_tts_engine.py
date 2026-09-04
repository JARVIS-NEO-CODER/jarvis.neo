"""Local Pocket TTS engine for J.A.R.V.I.S. NEO.

Pocket TTS is loaded lazily so JARVIS can still start when the optional
package has not been installed yet. The engine uses the French Pocket TTS
model and keeps the voice state cached in memory.
"""
from __future__ import annotations

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
