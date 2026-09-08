"""Small TTS router independent from Pocket TTS."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from core.tts_edge_engine import EdgeTTSEngine


class TTSRouter:
    """Use Edge neural TTS first, with the existing speech engine as fallback."""

    def __init__(self, fallback_say=None, voice="fr-FR-HenriNeural"):
        self.fallback_say = fallback_say
        self.engine = EdgeTTSEngine(voice=voice)

    async def say(self, text, state=None):
        text = self.engine.normalize_text(text)
        if not text:
            return
        if state is not None and getattr(state, "abort_requested", False):
            return
        try:
            from core import voice_playback
            play = getattr(voice_playback, "play_file", None)
        except Exception:
            play = None
        if play is None:
            if self.fallback_say:
                result = self.fallback_say(text)
                if asyncio.iscoroutine(result):
                    await result
            return
        with tempfile.TemporaryDirectory(prefix="jarvis_tts_") as td:
            output = Path(td) / "speech.mp3"
            ok = await asyncio.to_thread(self.engine.synthesize, text, output)
            if not ok:
                if self.fallback_say:
                    result = self.fallback_say(text)
                    if asyncio.iscoroutine(result):
                        await result
                return
            if state is not None and getattr(state, "abort_requested", False):
                return
            result = play(str(output), state=state)
            if asyncio.iscoroutine(result):
                await result


__all__ = ["TTSRouter"]
