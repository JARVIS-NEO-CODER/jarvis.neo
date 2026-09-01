"""Conversation AI facade for J.A.R.V.I.S. NEO.

Keeps normal text conversation on the configured AI provider path while
leaving vision-specific Ollama calls untouched in assistant.py.
"""
from __future__ import annotations

from typing import Any

from .ai_provider_router import AIProviderRouter
from .groq_provider import GroqProvider


DEFAULT_GROQ_MODEL = "llama-3.1-8b-instant"


class OllamaChatProvider:
    """Small adapter exposing Ollama's chat API through the provider interface."""

    def __init__(self, ollama_module: Any, model: str, base_url: str | None = None):
        self.ollama = ollama_module
        self.model = model
        self.base_url = base_url

    @property
    def available(self) -> bool:
        return self.ollama is not None

    def chat(self, messages: list[dict[str, Any]], *, temperature: float = 0.2,
             max_tokens: int = 2048) -> str:
        if self.ollama is None:
            raise RuntimeError("Ollama n'est pas installé.")

        client_kwargs = {}
        if self.base_url:
            client_kwargs["host"] = self.base_url

        client = self.ollama.Client(**client_kwargs)
        response = client.chat(
            model=self.model,
            messages=messages,
            options={
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        )
        try:
            return response["message"]["content"]
        except (KeyError, TypeError) as exc:
            raise RuntimeError("Réponse Ollama invalide.") from exc


class ConversationAI:
    """Single entry point for JARVIS text conversations.

    Groq is preferred when configured. The router falls back to Ollama when
    Groq is unavailable or fails. This class deliberately does not handle
    vision requests, which continue using the existing Ollama vision path.
    """

    def __init__(self, config: dict[str, Any], ollama_module: Any):
        self.config = config
        self.ollama_module = ollama_module
        self.config.setdefault("groq_model", DEFAULT_GROQ_MODEL)
        self.router = self._build_router()

    def _build_router(self) -> AIProviderRouter:
        groq = GroqProvider(
            api_key=self.config.get("groq_api_key", ""),
            model=self.config.get("groq_model", DEFAULT_GROQ_MODEL),
            timeout=float(self.config.get("groq_timeout", 60)),
        )

        ollama = None
        if self.config.get("ollama_enabled", True):
            ollama = OllamaChatProvider(
                self.ollama_module,
                self.config.get("model", "llama3.2:3b"),
                self.config.get("ollama_base_url", "http://127.0.0.1:11434"),
            )

        prefer_groq = self.config.get("ai_provider", "groq") != "ollama"
        return AIProviderRouter(
            groq=groq,
            ollama=ollama,
            prefer_groq=prefer_groq,
        )

    def chat(self, messages: list[dict[str, Any]], *, temperature: float = 0.2,
             max_tokens: int = 2048) -> str:
        return self.router.chat(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    @property
    def status(self) -> dict[str, Any]:
        return self.router.status


__all__ = ["ConversationAI", "OllamaChatProvider"]
