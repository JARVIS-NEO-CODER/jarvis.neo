"""Local neural TTS backend for J.A.R.V.I.S. NEO using Piper.

Piper is deliberately isolated from the main speech engine so the voice stack does
not depend on a cloud websocket or Pocket TTS. The French voice is downloaded lazily
on first use and then kept in the local JARVIS data directory.
"""
from __future__ import annotations

import subprocess
import sys
import threading
import wave
from pathlib import Path
from typing import Any

MODEL_NAME = "fr_FR-siwis-medium"


class PiperTTSEngine:
    def __init__(self, base_dir: Path, log: Any | None = None) -> None:
        self.base_dir = Path(base_dir)
        self.model_dir = self.base_dir / "tts_models"
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.model_path = self.model_dir / f"{MODEL_NAME}.onnx"
        self._voice = None
        self._lock = threading.Lock()
        self.log = log

    def _log(self, level: str, message: str) -> None:
        try:
            getattr(self.log, level)(message)
        except Exception:
            pass

    def _ensure_model(self) -> Path:
        if self.model_path.exists() and self.model_path.with_suffix(".onnx.json").exists():
            return self.model_path

        self._log("info", "VOICE: téléchargement initial de la voix Piper fr_FR-siwis-medium...")
        command = [
            sys.executable,
            "-m",
            "piper.download_voices",
            MODEL_NAME,
            "--download-dir",
            str(self.model_dir),
        ]
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        if result.returncode != 0 or not self.model_path.exists():
            detail = (result.stderr or result.stdout or "échec inconnu").strip()
            raise RuntimeError(f"Téléchargement Piper impossible: {detail[-500:]}")
        return self.model_path

    def _load(self):
        if self._voice is not None:
            return self._voice
        with self._lock:
            if self._voice is not None:
                return self._voice
            from piper import PiperVoice

            model_path = self._ensure_model()
            self._voice = PiperVoice.load(model_path)
            self._log("info", "VOICE: Piper neural local prêt (fr_FR-siwis-medium)")
            return self._voice

    def synthesize(self, text: str, output_path: Path) -> Path:
        voice = self._load()
        with wave.open(str(output_path), "wb") as wav_file:
            voice.synthesize_wav(text, wav_file)
        return output_path


def install(assistant) -> bool:
    """Install Piper as the primary JARVIS TTS implementation."""
    speech = getattr(assistant, "speech", None)
    if speech is None:
        return False
    if getattr(speech, "_neo_piper_installed", False):
        return True

    try:
        import piper  # noqa: F401
    except Exception as exc:
        try:
            assistant.log.warning(f"Piper TTS indisponible: {exc}")
        except Exception:
            pass
        return False

    import asyncio
    import time

    engine = PiperTTSEngine(getattr(assistant, "BASE_DIR", Path.home() / ".jarvis_neo"), getattr(assistant, "log", None))
    state = assistant.state
    signals = assistant.signals
    pygame = getattr(assistant, "pygame", None)
    pygame_ok = bool(getattr(assistant, "PYGAME_OK", False) and pygame is not None)
    stop_event = assistant.stop_event

    async def _say(text: str):
        if not state.voice_enabled or not text:
            return
        path = engine.base_dir / f"speech_{time.time_ns()}.wav"
        state.is_speaking = True
        signals.speaking_change.emit(True)
        try:
            await asyncio.to_thread(engine.synthesize, text, path)
            if not pygame_ok:
                raise RuntimeError("pygame audio indisponible")
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
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
                assistant.log.warning(f"Piper TTS échec : {exc}")
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
    speech._neo_piper_installed = True
    speech._neo_piper_engine = engine
    try:
        assistant.log.info("VOICE: Piper neural local activé (fr_FR-siwis-medium)")
    except Exception:
        pass
    return True


__all__ = ["PiperTTSEngine", "MODEL_NAME", "install"]
