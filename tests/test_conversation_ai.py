from core.conversation_ai import ConversationAI


class FakeOllama:
    class Client:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def chat(self, **kwargs):
            return {"message": {"content": "ollama"}}


def test_refresh_applies_provider_and_fallback_changes(monkeypatch):
    class FakeGroq:
        def __init__(self, api_key=None, model=None, timeout=60):
            self.api_key = api_key
            self.model = model
            self.timeout = timeout

        @property
        def configured(self):
            return bool(self.api_key)

        def chat(self, messages, **kwargs):
            return "groq"

    monkeypatch.setattr("core.conversation_ai.GroqProvider", FakeGroq)
    config = {
        "groq_api_key": "test-key",
        "groq_model": "test-model",
        "ai_provider": "groq",
        "ollama_enabled": True,
        "groq_fallback_to_ollama": True,
    }
    ai = ConversationAI(config, FakeOllama)

    assert ai.status["groq_configured"] is True
    assert ai.status["fallback_to_ollama"] is True

    config["ai_provider"] = "ollama"
    config["groq_fallback_to_ollama"] = False
    status = ai.refresh()

    assert status["fallback_to_ollama"] is False
    assert ai.router.prefer_groq is False
    assert ai.chat([]) == "ollama"
