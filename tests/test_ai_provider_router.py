from core.ai_provider_router import AIProviderRouter


class FakeProvider:
    def __init__(self, result=None, error=None, configured=True):
        self.result = result
        self.error = error
        self.configured = configured
        self.calls = 0

    def chat(self, messages, **kwargs):
        self.calls += 1
        if self.error:
            raise RuntimeError(self.error)
        return self.result


def test_groq_success_does_not_call_fallback():
    groq = FakeProvider(result="groq")
    ollama = FakeProvider(result="ollama")
    router = AIProviderRouter(groq, ollama, prefer_groq=True)

    assert router.chat([]) == "groq"
    assert groq.calls == 1
    assert ollama.calls == 0
    assert router.status["active_provider"] == "groq"


def test_groq_failure_falls_back_to_ollama():
    groq = FakeProvider(error="quota exceeded")
    ollama = FakeProvider(result="ollama")
    router = AIProviderRouter(groq, ollama, prefer_groq=True)

    assert router.chat([]) == "ollama"
    assert groq.calls == 1
    assert ollama.calls == 1
    assert router.status["active_provider"] == "ollama"
    assert router.status["last_error"] is None


def test_fallback_can_be_disabled():
    groq = FakeProvider(error="quota exceeded")
    ollama = FakeProvider(result="ollama")
    router = AIProviderRouter(groq, ollama, prefer_groq=True, fallback_to_ollama=False)

    try:
        router.chat([])
    except RuntimeError as exc:
        assert "quota exceeded" in str(exc)
    else:
        raise AssertionError("Le routeur aurait dû s'arrêter après l'échec Groq.")

    assert ollama.calls == 0


def test_ollama_only_mode_skips_groq():
    groq = FakeProvider(result="groq")
    ollama = FakeProvider(result="ollama")
    router = AIProviderRouter(groq, ollama, prefer_groq=False)

    assert router.chat([]) == "ollama"
    assert groq.calls == 0
    assert ollama.calls == 1
