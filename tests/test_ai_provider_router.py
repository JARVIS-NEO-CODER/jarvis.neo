from pathlib import Path

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


def test_quota_429_falls_back_to_ollama():
    groq = FakeProvider(error="Groq HTTP 429: rate limit exceeded")
    ollama = FakeProvider(result="ollama")
    router = AIProviderRouter(groq, ollama, prefer_groq=True, quota_fallback_mode="ollama")

    assert router.chat([]) == "ollama"
    assert groq.calls == 1
    assert ollama.calls == 1
    assert router.status["active_provider"] == "ollama"
    assert router.status["last_fallback_reason"] == "quota_or_temporary_error"


def test_non_quota_groq_error_does_not_fallback():
    groq = FakeProvider(error="Groq HTTP 401: invalid api key")
    ollama = FakeProvider(result="ollama")
    router = AIProviderRouter(groq, ollama, prefer_groq=True)

    try:
        router.chat([])
    except RuntimeError as exc:
        assert "invalid api key" in str(exc)
    else:
        raise AssertionError("Une erreur d'authentification Groq ne doit pas basculer automatiquement.")

    assert ollama.calls == 0


def test_simple_mode_is_used_after_quota_error():
    groq = FakeProvider(error="quota exceeded")
    ollama = FakeProvider(result="ollama")
    router = AIProviderRouter(groq, ollama, prefer_groq=True, quota_fallback_mode="simple")

    result = router.chat([])

    assert result.startswith("Mode Simple actif")
    assert groq.calls == 1
    assert ollama.calls == 0
    assert router.status["active_provider"] == "simple"
    assert router.status["quota_fallback_mode"] == "simple"


def test_simple_mode_works_without_ollama_fallback_permission():
    groq = FakeProvider(error="Groq HTTP 429: quota exceeded")
    router = AIProviderRouter(groq, None, prefer_groq=True, fallback_to_ollama=False, quota_fallback_mode="simple")

    assert router.chat([]).startswith("Mode Simple actif")
    assert router.status["active_provider"] == "simple"


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


def test_screenshot_context_uses_local_vision_model(tmp_path, monkeypatch):
    screenshot = tmp_path / "agent.png"
    screenshot.write_bytes(b"not-a-real-image")

    class FakeClient:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.calls = []

        def chat(self, **kwargs):
            self.calls.append(kwargs)
            assert kwargs["model"] == "qwen3-vl:2b"
            assert kwargs["messages"][-1]["images"] == [str(screenshot.resolve())]
            return {"message": {"content": '{"kind":"finish","message":"observed"}'}}

    class FakeOllamaModule:
        def __init__(self):
            self.client = None

        def Client(self, **kwargs):
            self.client = FakeClient(**kwargs)
            return self.client

    fake_module = FakeOllamaModule()
    ollama = FakeProvider()
    ollama.ollama = fake_module
    ollama.base_url = "http://127.0.0.1:11434"
    router = AIProviderRouter(FakeProvider(result="groq"), ollama, prefer_groq=True)
    monkeypatch.delenv("JARVIS_AGENT_VISION_MODEL", raising=False)

    context = {"goal": "naviguer", "context": {"last_result": {"path": str(screenshot)}}}
    result = router.chat([{"role": "system", "content": "system"}, {"role": "user", "content": __import__("json").dumps(context)}])

    assert result == '{"kind":"finish","message":"observed"}'
    assert router.status["active_provider"] == "ollama-vision:qwen3-vl:2b"


if __name__ == "__main__":
    pass
