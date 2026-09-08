import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from core.application_resolver import ApplicationResolver
from core.piper_tts_engine import MODEL_NAME
from core.voice_session_bridge import _try_direct_app_command


class VoiceAndApplicationTests(unittest.TestCase):
    def test_piper_uses_french_neural_model(self):
        self.assertEqual(MODEL_NAME, "fr_FR-siwis-medium")

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

    def test_direct_voice_launch_handles_lance_without_path(self):
        calls = []
        fake_tools = SimpleNamespace(
            open_application=lambda name: (calls.append(name) or (True, f"{name} lancé."))
        )
        fake_signals = SimpleNamespace(log_msg=SimpleNamespace(emit=lambda *_args: None))
        fake_log = SimpleNamespace(info=lambda *_args: None, warning=lambda *_args: None)
        assistant = SimpleNamespace(tools=fake_tools, signals=fake_signals, log=fake_log)

        self.assertTrue(_try_direct_app_command(assistant, "lance Minecraft"))
        self.assertEqual(calls, ["Minecraft"])

    def test_direct_voice_launch_handles_ouvre(self):
        calls = []
        fake_tools = SimpleNamespace(
            open_application=lambda name: (calls.append(name) or (True, f"{name} lancé."))
        )
        fake_signals = SimpleNamespace(log_msg=SimpleNamespace(emit=lambda *_args: None))
        fake_log = SimpleNamespace(info=lambda *_args: None, warning=lambda *_args: None)
        assistant = SimpleNamespace(tools=fake_tools, signals=fake_signals, log=fake_log)

        self.assertTrue(_try_direct_app_command(assistant, "ouvre Discord"))
        self.assertEqual(calls, ["Discord"])


if __name__ == "__main__":
    unittest.main()
