"""Independent Microsoft Edge neural TTS playback for J.A.R.V.I.S. NEO."""
from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from core.tts_edge_engine import EdgeTTSEngine


async def speak(text: str, state=None, voice: str = "fr-FR-HenriNeural", rate: str = "+0%", volume: str = "+0%") -> bool:
    """Synthesize and play one response, with interruption and cleanup support."""
    if not text or (state is not None and getattr(state, "abort_requested", False)):
        return False

    engine = EdgeTTSEngine(voice=voice, rate=rate, volume=volume)
    if not engine.available():
        return False

    try:
        import pygame
        with tempfile.TemporaryDirectory(prefix="jarvis_edge_tts_") as td:
            output = Path(td) / "speech.mp3"
            if not await asyncio.to_thread(engine.synthesize, text, output):
                return False
            if state is not None and getattr(state, "abort_requested", False):
                return False
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
            pygame.mixer.music.load(str(output))
            pygame.mixer.music.set_volume(1.0)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                if state is not None and getattr(state, "abort_requested", False):
                    pygame.mixer.music.stop()
                    return False
                await asyncio.sleep(0.03)
            return True
    except Exception:
        return False
