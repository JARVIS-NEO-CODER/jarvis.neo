"""J.A.R.V.I.S. NEO voice profile.

The default is a deliberately selected local French neural voice from Kyutai
Pocket TTS. No generic Windows/cloud fallback is permitted.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class VoiceProfile:
    id: str
    language: str
    engine: str = "pocket-tts"
    quality: str = "neural-24l"


DEFAULT_VOICE = VoiceProfile(
    id="estelle",
    language="fr-FR",
)


class LocalVoice:
    """Metadata adapter for the single approved JARVIS voice."""

    def __init__(self, root: Path | None = None, voice: VoiceProfile = DEFAULT_VOICE):
        self.root = root or Path.home() / ".jarvis_neo"
        self.voice = voice

    def available(self) -> bool:
        try:
            import pocket_tts  # noqa: F401
            return True
        except Exception:
            return False

    def synthesize(self, text: str, output: Path) -> Path:
        if not self.available():
            raise RuntimeError("Pocket TTS français est requis. Aucun fallback vocal n'est utilisé.")
        from core.piper_tts_engine import PocketTTSEngine
        return PocketTTSEngine(self.root).synthesize(text, output)
