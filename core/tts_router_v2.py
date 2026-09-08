"""TTS backend selection for JARVIS NEO.

Edge TTS is deliberately independent from Pocket TTS.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from core.tts_edge_engine import EdgeTTSEngine


class TTSRouter:
    def __init__(self, voice: str = "fr-FR-HenriNeural"):
        self.engine = EdgeTTSEngine(voice=voice)

    async def synthesize(self, text: str, output: Path) -> bool:
        return await asyncio.to_thread(self.engine.synthesize, text, output)

    def available(self) -> bool:
        return self.engine.available()


__all__ = ["TTSRouter"]
