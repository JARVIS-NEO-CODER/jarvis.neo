"""Local neural TTS voice configuration for J.A.R.V.I.S. NEO.

Primary voice: Piper VITS French Siwis, medium quality.
No cloud fallback is used. The voice is intentionally explicit so the
assistant does not silently switch to a generic Windows/cloud voice.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
import tempfile
import os


@dataclass(frozen=True)
class VoiceProfile:
    id: str
    language: str
    model_filename: str
    quality: str = "medium"


# Chosen deliberately: French, neural VITS, medium quality, local execution.
DEFAULT_VOICE = VoiceProfile(
    id="fr_FR-siwis-medium",
    language="fr-FR",
    model_filename="fr_FR-siwis-medium.onnx",
)


class LocalVoice:
    """Small adapter around the bundled Piper executable/model."""

    def __init__(self, root: Path | None = None, voice: VoiceProfile = DEFAULT_VOICE):
        self.root = root or Path(__file__).resolve().parent.parent / "assets" / "voices"
        self.voice = voice
        self.model = self.root / voice.model_filename
        self.piper = self.root / "piper.exe"

    def available(self) -> bool:
        return self.piper.is_file() and self.model.is_file()

    def synthesize(self, text: str, output: Path) -> Path:
        if not self.available():
            raise RuntimeError(
                f"Voix locale indisponible: {self.voice.id}. "
                "Le moteur ne bascule volontairement pas vers une voix de secours."
            )
        text = text.strip()
        if not text:
            raise ValueError("Texte vide")
        output.parent.mkdir(parents=True, exist_ok=True)
        proc = subprocess.run(
            [str(self.piper), "--model", str(self.model), "--output_file", str(output)],
            input=text,
            text=True,
            capture_output=True,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or "Piper TTS a échoué")
        return output
