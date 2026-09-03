import json

from core.ai_model_catalog import GROQ_MODELS, OLLAMA_MODELS, apply_provider_settings, model_catalog


def test_model_catalog_contains_selectable_groq_and_ollama_models():
    assert model_catalog("Groq") == GROQ_MODELS
    assert model_catalog("Ollama") == OLLAMA_MODELS
    assert "openai/gpt-oss-120b" in [model_id for _, model_id in GROQ_MODELS]
    assert "llama3.2:3b" in [model_id for _, model_id in OLLAMA_MODELS]


def test_provider_settings_persists_selected_groq_model():
    config = {}
    updated = apply_provider_settings(
        config,
        provider="Groq",
        api_key=" secret-key ",
        model="openai/gpt-oss-120b",
        fallback="Ollama",
        autostart=True,
    )

    assert updated["ai_provider"] == "groq"
    assert updated["groq_api_key"] == "secret-key"
    assert updated["groq_model"] == "openai/gpt-oss-120b"
    assert updated["groq_quota_fallback"] == "ollama"
    assert updated["groq_fallback_to_ollama"] is True
    assert updated["autostart"] is True
    assert "model" not in updated


def test_provider_settings_persists_selected_ollama_model():
    config = {}
    updated = apply_provider_settings(
        config,
        provider="Ollama",
        api_key="",
        model="llama3.2:3b",
        fallback="Mode Simple",
        autostart=False,
    )

    assert updated["ai_provider"] == "ollama"
    assert updated["model"] == "llama3.2:3b"
    assert updated["groq_quota_fallback"] == "simple"
    assert updated["groq_fallback_to_ollama"] is False
    assert updated["autostart"] is False
    assert json.dumps(updated, ensure_ascii=False)
