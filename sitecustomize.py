"""Optional startup bridge: route text-only Ollama chat through Groq when configured.

This keeps the legacy assistant runtime compatible while the modular provider
router is being adopted. Vision requests (messages containing ``images``) stay
on Ollama so local vision is unaffected.
"""
from __future__ import annotations

import json
import os
from pathlib import Path


def _load_config() -> dict:
    path = Path.home() / ".jarvis_neo" / "jarvis_config.json"
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except Exception:
        return {}


def _install_bridge() -> None:
    try:
        import ollama
        from core.groq_provider import GroqProvider
    except Exception:
        return

    client_cls = getattr(ollama, "Client", None)
    if client_cls is None or getattr(client_cls, "_jarvis_groq_bridge", False):
        return

    original_chat = getattr(client_cls, "chat", None)
    if original_chat is None:
        return

    def chat(self, model=None, messages=None, **kwargs):
        config = _load_config()
        provider_name = str(config.get("ai_provider", "groq")).lower()
        api_key = str(config.get("groq_api_key", "") or os.getenv("GROQ_API_KEY", "")).strip()
        use_groq = provider_name == "groq" and bool(api_key)

        # Never send image/vision requests to the text-only Groq bridge.
        has_images = any(isinstance(m, dict) and m.get("images") for m in (messages or []))
        if not use_groq or has_images:
            return original_chat(self, model=model, messages=messages, **kwargs)

        options = kwargs.get("options") or {}
        temperature = options.get("temperature", kwargs.get("temperature", 0.2))
        max_tokens = options.get("num_predict", kwargs.get("max_tokens", 2048))
        groq = GroqProvider(
            api_key=api_key,
            model=str(config.get("groq_model", "llama-3.1-8b-instant")),
            timeout=float(config.get("groq_timeout", 60)),
        )
        try:
            content = groq.chat(messages or [], temperature=temperature, max_tokens=max_tokens)
            return {"message": {"role": "assistant", "content": content}}
        except Exception:
            # Preserve legacy behavior and local-first resilience on provider failure.
            if bool(config.get("groq_fallback_to_ollama", True)):
                return original_chat(self, model=model, messages=messages, **kwargs)
            raise

    client_cls.chat = chat
    client_cls._jarvis_groq_bridge = True


_install_bridge()
