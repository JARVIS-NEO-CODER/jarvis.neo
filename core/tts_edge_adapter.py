"""Adapter that replaces the current speech callback with Edge neural TTS."""
from __future__ import annotations

import asyncio
from pathlib import Path

from core.tts_edge_engine import EdgeTTSEngine


class EdgeSpeechAdapter:
    def __init__(self, voice: str = "fr-FR-HenriNeural"):
        self.engine = EdgeTTSEngine(voice=voice)

    async def speak(self, text: str, state=None) -> bool:
        if not text or (state is not None and getattr(state, "abort_requested", False)):
            return False
        import pygame
        output = Path(tempfile_name := f".jarvis_edge_tts_{id(self)}.mp3")
        try:
            ok = await asyncio.to_thread(self.engine.synthesize, text, output)
            if not ok:
                return False
            if state is not None and getattr(state, "abort_requested", False):
                return False
            pygame.mixer.music.load(str(output))
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                if state is not None and getattr(state, "abort_requested", False):
                    pygame.mixer.music.stop()
                    return False
                await asyncio.sleep(0.03)
            return True
        finally:
            try:
                output.unlink(missing_ok=True)
            except Exception:
                pass
