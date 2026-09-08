import unittest
from pathlib import Path
from unittest.mock import patch

from core.application_resolver import ApplicationResolver
from core.tts_edge_engine import EdgeTTSEngine


class VoiceAndApplicationTests(unittest.TestCase):
    def test_edge_tts_normalizes_jarvis_and_chat_formatting(self):
        text = "Bonjour J . A . R . V . I . S . !  Voici https://example.com"
        normalized = EdgeTTSEngine.normalize_text(text)
        self.assertIn("JARVIS", normalized)
        self.assertNotIn("https://", normalized)
        self.assertNotIn("J . A . R . V . I . S", normalized)

    def test_edge_tts_uses_french_neural_voice(self):
        engine = EdgeTTSEngine()
        self.assertEqual(engine.voice, "fr-FR-HenriNeural")
        self.assertEqual(engine.rate, "+0%")

    def test_application_resolver_accepts_alias(self):
        resolver = ApplicationResolver({"calculatrice": "calc.exe"})
        match = resolver.resolve("calculatrice")
        self.assertIsNotNone(match)
        self.assertEqual(match.source, "config")

    def test_application_resolver_accepts_start_menu_match(self):
        fake = Path("C:/ProgramData/Microsoft/Windows/Start Menu/Programs")
        with patch.object(ApplicationResolver, "_start_menu_roots", return_value=(fake,)):
            with patch.object(Path, "exists", return_value=True):
                with patch.object(Path, "rglob", return_value=[fake / "Google Chrome.lnk"]):
                    resolver = ApplicationResolver()
                    match = resolver.resolve("google chrome")
        self.assertIsNotNone(match)
        self.assertEqual(match.source, "start_menu")


if __name__ == "__main__":
    unittest.main()
