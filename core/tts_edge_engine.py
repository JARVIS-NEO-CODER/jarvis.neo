"""High-quality Edge TTS engine for JARVIS NEO.

This engine is intentionally independent from Pocket TTS. It uses Microsoft's
Edge TTS service through the existing edge-tts dependency and keeps synthesis
out of the Qt/audio thread.
"""

from __future__ import annotations

import asyncio
import re
import tempfile
from pathlib import Path
from typing import Optional


class EdgeTTSEngine:
    """French neural TTS backend with safe cleanup and interruption support."""

    def __init__(self, voice: str = "fr-FR-HenriNeural", rate: str = "+0%", volume: str = "+0%"):
        self.voice = voice
        self.rate = rate
        self.volume = volume

    @staticmethod
    def normalize_text(text: str) -> str:
        text = re.sub(r"```.*?```", " ", str(text), flags=re.S)
        text = re.sub(r"https?://\S+", " lien web ", text)
        text = re.sub(r"\bJ\.A\.R\.V\.I\.S\.?\b", "JARVIS", text, flags=re.I)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    async def _synthesize_async(self, text: str, output: Path) -> None:
        import edge_tts
        communicate = edge_tts.Communicate(
            text,
            self.voice,
            rate=self.rate,
            volume=self.volume,
        )
        await communicate.save(str(output))

    def synthesize(self, text: str, output: Path) -> bool:
        text = self.normalize_text(text)
        if not text:
            return False
        try:
            asyncio.run(self._synthesize_async(text, output))
            return output.exists() and output.stat().st_size > 0
        except Exception:
            return False

    def available(self) -> bool:
        try:
            import edge_tts  # noqa: F401
            return True
        except ImportError:
            return False


__all__ = ["EdgeTTSEngine"]
