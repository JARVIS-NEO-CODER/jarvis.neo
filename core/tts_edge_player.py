"""Non-Pocket TTS playback helper."""
from __future__ import annotations

import asyncio
from pathlib import Path

from core.tts_edge_engine import EdgeTTSEngine


async def speak(text: str, state=None, voice: str = "fr-FR-HenriNeural") -> bool:
    """Synthesize Edge speech and play it through pygame when available."""
    if state is not None and getattr(state, "abort_requested", False):
        return False
    engine = EdgeTTSEngine(voice=voice)
    if not engine.available():
        return False
    output = Path(".") / ".jarvis_edge_tts.mp3"
    try:
        ok = await asyncio.to_thread(engine.synthesize, text, output)
        if not ok:
            return False
        if state is not None and getattr(state, "abort_requested", False):
            return False
        import pygame
        pygame.mixer.music.load(str(output))
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            if state is not None and getattr(state, "abort_requested", False):
                pygame.mixer.music.stop()
                return False
            await asyncio.sleep(0.03)
        return True
    except Exception:
        return False
    finally:
        try:
            output.unlink(missing_ok=True)
        except Exception:
            pass
