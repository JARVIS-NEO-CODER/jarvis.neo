"""Shared AI provider/model catalog for J.A.R.V.I.S. NEO."""
from __future__ import annotations

from typing import Any

GROQ_MODELS = [
    ("Llama 3.1 8B Instant", "llama-3.1-8b-instant"),
    ("Llama 3.3 70B Versatile", "llama-3.3-70b-versatile"),
    ("GPT-OSS 20B", "openai/gpt-oss-20b"),
    ("GPT-OSS 120B", "openai/gpt-oss-120b"),
    ("Qwen 3.8 27B", "qwen/qwen3.8-27b"),
    ("Groq Compound", "groq/compound"),
    ("Groq Compound Mini", "groq/compound-mini"),
]

OLLAMA_MODELS = [
    ("Grand • Llama 3.1 8B", "llama3.1:8b"),
    ("Moyen • Llama 3.2 3B", "llama3.2:3b"),
    ("Petit • Phi-3 Mini", "phi3:mini"),
    ("Mini • Gemma 2 2B", "gemma2:2b"),
]


def model_catalog(provider: str) -> list[tuple[str, str]]:
    return list(GROQ_MODELS if str(provider).lower() == "groq" else OLLAMA_MODELS)


def apply_provider_settings(
    config: dict[str, Any],
    *,
    provider: str,
    api_key: str,
    model: str,
    fallback: str,
    autostart: bool,
) -> dict[str, Any]:
    """Apply and normalize provider settings without depending on Qt."""
    provider = "groq" if str(provider).lower() == "groq" else "ollama"
    selected_model = str(model).strip()
    if provider == "groq":
        selected_model = selected_model or GROQ_MODELS[0][1]
    else:
        selected_model = selected_model or OLLAMA_MODELS[1][1]
    config["ai_provider"] = provider
    config["groq_api_key"] = str(api_key).strip()
    if provider == "groq":
        config["groq_model"] = selected_model
    else:
        config["model"] = selected_model
    config["groq_quota_fallback"] = "simple" if str(fallback).lower() in {"simple", "mode simple"} else "ollama"
    config["groq_fallback_to_ollama"] = config["groq_quota_fallback"] == "ollama"
    config["autostart"] = bool(autostart)
    return config


__all__ = ["GROQ_MODELS", "OLLAMA_MODELS", "model_catalog", "apply_provider_settings"]
