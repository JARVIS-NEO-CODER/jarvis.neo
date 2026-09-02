from core.quick_responses import QuickResponseEngine


def test_quick_responses_are_loaded_from_runtime_data(monkeypatch):
    monkeypatch.setattr(
        "core.quick_responses.get_data",
        lambda key, default=None: {"salut": "Réponse dynamique"} if key == "quick_responses" else default,
    )

    engine = QuickResponseEngine()

    assert engine.match("Salut") == "Réponse dynamique"
