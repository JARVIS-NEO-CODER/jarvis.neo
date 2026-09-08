from pathlib import Path

from core.tts_edge_engine import EdgeTTSEngine


def test_edge_tts_normalization():
    text = EdgeTTSEngine.normalize_text("Bonjour   J.A.R.V.I.S.\nhttps://example.com")
    assert "JARVIS" in text
    assert "lien web" in text
    assert "  " not in text


def test_edge_tts_empty_text():
    engine = EdgeTTSEngine()
    assert engine.synthesize("   ", Path("unused.mp3")) is False
